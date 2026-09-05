import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
import chromadb
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.ai.vector_store import get_chroma_client, get_activity_collection
from backend.app.services.ai.embedding_adapter import PragatiSetuEmbeddingAdapter
from backend.app.services.ai.vector_indexer import (
    index_schedule_activities,
    construct_activity_document,
    construct_activity_metadata
)
from backend.app.services.ai.vector_retriever import search_schedule_activities
from backend.app.services.ai.groq_service import GroqExplanationService
from backend.app.schemas.ai import VectorSearchResult, ExplainResponse

@pytest.fixture(autouse=True)
def setup_baseline_data(db_session):
    """Imports the actual baseline schedule dataset into test DB session."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

@pytest.fixture
def ephemeral_chroma():
    """Provides a fresh isolated ephemeral ChromaDB client per test."""
    client = chromadb.EphemeralClient(settings=chromadb.config.Settings(allow_reset=True, anonymized_telemetry=False))
    try:
        client.reset()
    except Exception:
        pass
    yield client
    try:
        client.reset()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# 1. VECTOR DB INITIALIZATION & EMBEDDING ADAPTER
# ══════════════════════════════════════════════════════════════════════════════

def test_1_vector_db_initialization(ephemeral_chroma):
    """Test ChromaDB client creation and collection creation."""
    col = get_activity_collection(client=ephemeral_chroma, collection_name="test_init_col")
    assert col is not None
    assert col.name == "test_init_col"
    assert col.count() == 0

def test_2_embedding_adapter_fallback():
    """Test deterministic fallback embeddings when transformer model is not loaded."""
    adapter = PragatiSetuEmbeddingAdapter(dimension=384)
    with patch("backend.app.services.ai.embedding_adapter.get_embedding_model", return_value=None):
        embs = adapter(["Test activity description for piping"])
        assert len(embs) == 1
        assert len(embs[0]) == 384
        # Check determinism
        embs_repeat = adapter(["Test activity description for piping"])
        assert list(embs[0]) == list(embs_repeat[0])

# ══════════════════════════════════════════════════════════════════════════════
# 2. VECTOR INDEXING WITH REAL DATA & REPEATABILITY
# ══════════════════════════════════════════════════════════════════════════════

def test_3_vector_indexing_real_activities(db_session, ephemeral_chroma):
    """Indexes actual ScheduleActivity records from 01_baseline_schedule.xlsx."""
    count = index_schedule_activities(
        db=db_session,
        project_id="PROJ-ALPHA",
        client=ephemeral_chroma
    )
    assert count == 75
    col = get_activity_collection(client=ephemeral_chroma)
    assert col.count() == 75

def test_4_repeated_indexing_idempotence(db_session, ephemeral_chroma):
    """Re-indexing does not duplicate vector entries (upsert behavior)."""
    count1 = index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    assert count1 == 75
    col = get_activity_collection(client=ephemeral_chroma)
    assert col.count() == 75

    # Run second time
    count2 = index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    assert count2 == 75
    assert col.count() == 75  # Count remains exactly 75, not 150

# ══════════════════════════════════════════════════════════════════════════════
# 3. SEMANTIC RETRIEVAL & TOP-K
# ══════════════════════════════════════════════════════════════════════════════

def test_5_semantic_retrieval(db_session, ephemeral_chroma):
    """Tests semantic vector search returns relevant activity."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    results = search_schedule_activities(
        project_id="PROJ-ALPHA",
        query="foundation concreting F12",
        top_k=3,
        client=ephemeral_chroma
    )
    assert len(results) >= 1
    top_result = results[0]
    assert isinstance(top_result, VectorSearchResult)
    assert top_result.project_id == "PROJ-ALPHA"
    assert 0.0 <= top_result.similarity <= 1.0
    assert "activity_id" in top_result.metadata

def test_6_top_k_retrieval(db_session, ephemeral_chroma):
    """Tests retrieval strictly respects top_k count."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    results = search_schedule_activities(
        project_id="PROJ-ALPHA",
        query="piping spool erection",
        top_k=2,
        client=ephemeral_chroma
    )
    assert len(results) == 2

# ══════════════════════════════════════════════════════════════════════════════
# 4. PROJECT BOUNDARY ISOLATION
# ══════════════════════════════════════════════════════════════════════════════

def test_7_project_isolation(db_session, ephemeral_chroma):
    """Tests that queries for PragatiSetu never retrieve Project Beta activities."""
    # Create Project Beta activity
    proj_b = Project(project_id="PROJ-BETA", name="Project Beta")
    db_session.add(proj_b)
    db_session.commit()

    act_beta = ScheduleActivity(
        activity_id="BETA-ACT-001",
        project_id="PROJ-BETA",
        discipline="Electrical",
        description="Transformer installation at Substation Beta",
        planned_start=date(2026, 1, 1),
        planned_finish=date(2026, 1, 10),
        status="NOT_STARTED"
    )
    db_session.add(act_beta)
    db_session.commit()

    # Index both projects
    index_schedule_activities(db=db_session, client=ephemeral_chroma)
    col = get_activity_collection(client=ephemeral_chroma)
    assert col.count() == 76  # 75 Alpha + 1 Beta

    # Search within PROJ-ALPHA
    res_alpha = search_schedule_activities(
        project_id="PROJ-ALPHA",
        query="Transformer installation",
        top_k=5,
        client=ephemeral_chroma
    )
    # BETA-ACT-001 must NEVER appear in PROJ-ALPHA search results
    alpha_ids = {r.activity_id for r in res_alpha}
    assert "BETA-ACT-001" not in alpha_ids

    # Search within PROJ-BETA
    res_beta = search_schedule_activities(
        project_id="PROJ-BETA",
        query="Transformer installation",
        top_k=5,
        client=ephemeral_chroma
    )
    assert len(res_beta) == 1
    assert res_beta[0].activity_id == "BETA-ACT-001"

# ══════════════════════════════════════════════════════════════════════════════
# 5. METADATA PRESERVATION & EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

def test_8_metadata_preservation(db_session, ephemeral_chroma):
    """Verifies all required metadata fields are stored and retrieved."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    results = search_schedule_activities(
        project_id="PROJ-ALPHA",
        query="Civil excavation",
        top_k=1,
        client=ephemeral_chroma
    )
    assert len(results) == 1
    meta = results[0].metadata
    assert "activity_id" in meta
    assert "project_id" in meta
    assert "discipline" in meta
    assert "status" in meta

def test_9_empty_query_handling(db_session, ephemeral_chroma):
    """Empty or whitespace queries return empty list gracefully."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    assert search_schedule_activities("PROJ-ALPHA", "", client=ephemeral_chroma) == []
    assert search_schedule_activities("PROJ-ALPHA", "   ", client=ephemeral_chroma) == []

def test_10_missing_project_handling(db_session, ephemeral_chroma):
    """Non-existent project ID returns empty list gracefully."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    res = search_schedule_activities("NONEXISTENT-PROJ", "Piping erection", client=ephemeral_chroma)
    assert res == []

def test_11_empty_collection_handling(ephemeral_chroma):
    """Search against empty vector store returns empty list without error."""
    res = search_schedule_activities("PROJ-ALPHA", "Piping", client=ephemeral_chroma)
    assert res == []

# ══════════════════════════════════════════════════════════════════════════════
# 6. GROQ SERVICE — OPTIONALITY, MOCKING & HALLUCINATION GUARDS
# ══════════════════════════════════════════════════════════════════════════════

def test_12_groq_disabled_mode(db_session, ephemeral_chroma):
    """When GROQ_ENABLED=False, explain service returns graceful semantic context."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    service = GroqExplanationService()

    with patch.object(settings, "GROQ_ENABLED", False):
        res = service.explain_query_context(
            project_id="PROJ-ALPHA",
            query="Foundation F12 concreting",
            chroma_client=ephemeral_chroma
        )
        assert isinstance(res, ExplainResponse)
        assert res.available is False
        assert "disabled" in res.summary.lower()
        assert len(res.retrieved_context) > 0

def test_13_groq_missing_api_key(db_session, ephemeral_chroma):
    """When GROQ_API_KEY is empty, explain service returns graceful fallback."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)
    service = GroqExplanationService()

    with patch.object(settings, "GROQ_ENABLED", True), patch.object(settings, "GROQ_API_KEY", ""):
        res = service.explain_query_context(
            project_id="PROJ-ALPHA",
            query="Foundation F12 concreting",
            chroma_client=ephemeral_chroma
        )
        assert res.available is False
        assert "not configured" in res.summary.lower()

def test_14_mocked_groq_success(db_session, ephemeral_chroma):
    """Tests successful Groq explanation parsing with mocked Groq SDK client."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"summary": "Matches sand bedding", "candidate_activity_ids": ["PIP-218"], "reasoning": ["Identifier aligns with trench T1"], "warnings": []}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    service = GroqExplanationService(client=mock_client)

    with patch.object(settings, "GROQ_ENABLED", True), patch.object(settings, "GROQ_API_KEY", "mock_key"):
        res = service.explain_query_context(
            project_id="PROJ-ALPHA",
            query="Sand bedding preparation in cable trench T1",
            chroma_client=ephemeral_chroma
        )
        assert res.available is True
        assert res.summary == "Matches sand bedding"
        assert "PIP-218" in res.grounded_candidates
        assert len(res.reasoning) == 1

def test_15_mocked_groq_failure_network_error(db_session, ephemeral_chroma):
    """Tests Groq network timeout / API error is caught gracefully without backend crash."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Connection timed out to api.groq.com")

    service = GroqExplanationService(client=mock_client)

    with patch.object(settings, "GROQ_ENABLED", True), patch.object(settings, "GROQ_API_KEY", "mock_key"):
        res = service.explain_query_context(
            project_id="PROJ-ALPHA",
            query="Foundation F12 concreting",
            chroma_client=ephemeral_chroma
        )
        assert res.available is False
        assert "unavailable" in res.summary.lower()
        assert any("timed out" in w for w in res.warnings)

def test_16_hallucinated_activity_id_rejected(db_session, ephemeral_chroma):
    """CRITICAL SAFETY: Groq output containing unknown activity IDs not in candidate set is rejected."""
    index_schedule_activities(db=db_session, project_id="PROJ-ALPHA", client=ephemeral_chroma)

    # Mock response where Groq hallucinates a fake ID "FAKE-ACTIVITY-999"
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"summary": "Hallucinated match", "candidate_activity_ids": ["CIV-107", "FAKE-ACTIVITY-999"], "reasoning": ["Some reason"], "warnings": []}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    service = GroqExplanationService(client=mock_client)

    with patch.object(settings, "GROQ_ENABLED", True), patch.object(settings, "GROQ_API_KEY", "mock_key"):
        res = service.explain_query_context(
            project_id="PROJ-ALPHA",
            query="Foundation F12 concreting",
            chroma_client=ephemeral_chroma
        )
        assert res.available is True
        # FAKE-ACTIVITY-999 MUST NOT be present in grounded_candidates
        assert "FAKE-ACTIVITY-999" not in res.grounded_candidates
        # It must be recorded in warnings
        assert any("Rejected hallucinated activity ID 'FAKE-ACTIVITY-999'" in w for w in res.warnings)

# ══════════════════════════════════════════════════════════════════════════════
# 7. FASTAPI API CONTRACT TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_17_api_index_endpoint(client):
    """Tests POST /ai/index endpoint."""
    res = client.post("/ai/index", json={"project_id": "PROJ-ALPHA"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["indexed_count"] >= 0

def test_18_api_search_endpoint(client):
    """Tests POST /ai/search endpoint."""
    # First index
    client.post("/ai/index", json={"project_id": "PROJ-ALPHA"})

    # Then search
    res = client.post("/ai/search", json={
        "project_id": "PROJ-ALPHA",
        "query": "Piping spool erection",
        "top_k": 3
    })
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == "PROJ-ALPHA"
    assert "results" in data
    assert isinstance(data["results"], list)

def test_19_api_explain_endpoint(client):
    """Tests POST /ai/explain endpoint."""
    client.post("/ai/index", json={"project_id": "PROJ-ALPHA"})

    res = client.post("/ai/explain", json={
        "project_id": "PROJ-ALPHA",
        "query": "Foundation F12 completed",
        "top_k": 2
    })
    assert res.status_code == 200
    data = res.json()
    assert "available" in data
    assert "summary" in data
    assert "retrieved_context" in data
