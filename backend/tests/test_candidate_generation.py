import os
import pytest
from datetime import date
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.normalizer_service import (
    normalize_identifier,
    normalize_action,
    normalize_object,
    normalize_location
)
from backend.app.services.candidate_scorer import (
    score_identifier,
    score_discipline,
    score_location,
    score_action,
    score_fuzzy,
    score_semantic,
    score_temporal,
    score_dependency,
    compute_all_candidate_scores,
    MATCH_WEIGHTS
)
from backend.app.services.candidate_generator_service import CandidateGeneratorService
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.candidate import MatchCandidate
from backend.app.db.models.activity import ScheduleActivity

@pytest.fixture(autouse=True)
def setup_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def create_event(db_session, event_id="EVT-TEST-001", raw_text="24P201 spool erection started near Rack B", project_id="PROJ-ALPHA"):
    rep = db_session.query(SourceReport).filter(SourceReport.project_id == project_id).first()
    if not rep:
        rep = SourceReport(
            report_id=f"REP-{project_id}",
            project_id=project_id,
            filename="report.txt",
            source_type="TXT",
            report_date=date(2026, 1, 5),
            file_hash="dummyhash",
            file_size=100,
            stored_path="path",
            processing_status="VALIDATED"
        )
        db_session.add(rep)
        db_session.commit()

    evt = ExtractedEvent(
        event_id=event_id,
        report_id=rep.report_id,
        raw_text=raw_text,
        event_date=date(2026, 1, 5),
        discipline="Piping",
        action="erection",
        object="spool",
        identifier="24-P-201",
        location="Rack-B",
        status="STARTED",
        extraction_method="RULE_BASED",
        extraction_version="v1"
    )
    db_session.add(evt)
    db_session.commit()
    return evt

def test_1_identifier_normalization():
    assert normalize_identifier("24-P-201") == "24P201"
    assert normalize_identifier("24 P 201") == "24P201"

def test_2_identifier_dictionary_variants():
    assert normalize_identifier("24 P 201") == "24P201"
    assert normalize_identifier("P-201") == "P201"

def test_3_terminology_normalization():
    assert normalize_action("cable pulling") == "cable laying"
    assert normalize_action("line hydrotest") == "hydrotest"

def test_4_location_normalization():
    assert normalize_location("Rack-B") == "RACKB"
    assert normalize_location("SubstationArea") == "Substation Area"

def test_5_raw_values_preserved(db_session):
    evt = create_event(db_session, event_id="EVT-TEST-RAW")
    service = CandidateGeneratorService(db_session)
    norm_evt = service.normalize_event("EVT-TEST-RAW")

    assert norm_evt.identifier == "24-P-201"
    assert norm_evt.normalized_identifier == "24P201"

def test_6_normalization_version_stored(db_session):
    evt = create_event(db_session, event_id="EVT-TEST-VER")
    service = CandidateGeneratorService(db_session)
    norm_evt = service.normalize_event("EVT-TEST-VER")

    assert norm_evt.normalization_version == "v1"

def test_7_missing_identifier():
    assert normalize_identifier(None) is None
    assert normalize_identifier("") is None

def test_8_missing_location():
    assert normalize_location(None) is None

def test_9_unknown_terminology():
    assert normalize_action("custom trenching") == "Custom Trenching"

def test_10_exact_identifier_score():
    assert score_identifier("24P201", "ACT-ALPHA-001", "24P201") == 100.0

def test_11_discipline_score():
    assert score_discipline("Piping", "Piping") == 100.0
    assert score_discipline("Piping", "Civil") == 0.0
    assert score_discipline(None, "Piping") == 50.0

def test_12_location_score():
    assert score_location("RACKB", "Rack B") == 100.0
    assert score_location("RACKB", "Plot A") == 20.0

def test_13_action_score():
    assert score_action("Hydrostatic Testing", "Hydrostatic testing of line 201") == 100.0
    assert score_action("Unknown Action", "Some text") == 30.0

def test_14_fuzzy_score():
    score = score_fuzzy("24P201 spool erection", "Spool erection for line 24P201")
    assert score >= 70.0

def test_15_semantic_score(db_session):
    act = db_session.query(ScheduleActivity).first()
    score = score_semantic("Spool erection near Rack B", act)
    assert 0.0 <= score <= 100.0

def test_16_temporal_score():
    d_start = date(2026, 1, 1)
    d_finish = date(2026, 1, 10)
    assert score_temporal(date(2026, 1, 5), d_start, d_finish) == 100.0
    assert score_temporal(date(2026, 1, 20), d_start, d_finish) == 70.0
    assert score_temporal(date(2026, 3, 1), d_start, d_finish) == 30.0

def test_17_dependency_score():
    assert score_dependency(None) == 80.0
    assert score_dependency("ACT-ALPHA-001") == 100.0

def test_18_top_candidate_ranking(db_session):
    evt = create_event(db_session, event_id="EVT-RANK-01")
    service = CandidateGeneratorService(db_session)
    _, candidates, _ = service.generate_candidates_for_event("EVT-RANK-01", top_n=5)

    assert len(candidates) > 0
    scores = [c.overall_score for c in candidates]
    assert scores == sorted(scores, reverse=True)

def test_19_top_2_margin(db_session):
    evt = create_event(db_session, event_id="EVT-MARGIN-01")
    service = CandidateGeneratorService(db_session)
    _, candidates, margin = service.generate_candidates_for_event("EVT-MARGIN-01", top_n=5)

    if len(candidates) >= 2:
        expected_margin = round(float(candidates[0].overall_score) - float(candidates[1].overall_score), 2)
        assert margin == expected_margin

def test_20_top_candidate_limit(db_session):
    evt = create_event(db_session, event_id="EVT-LIMIT-01")
    service = CandidateGeneratorService(db_session)
    _, candidates, _ = service.generate_candidates_for_event("EVT-LIMIT-01", top_n=3)

    assert len(candidates) <= 3

def test_21_no_candidate_case(db_session):
    # Empty project with no activities
    service = CandidateGeneratorService(db_session)
    rep = SourceReport(
        report_id="REP-EMPTY-PROJ",
        project_id="PROJ-EMPTY",
        filename="empty.txt",
        source_type="TXT",
        report_date=date(2026, 1, 5),
        file_hash="emptyhash",
        file_size=10,
        stored_path="empty",
        processing_status="VALIDATED"
    )
    db_session.add(rep)

    evt = ExtractedEvent(
        event_id="EVT-EMPTY-PROJ",
        report_id="REP-EMPTY-PROJ",
        raw_text="No work",
        extraction_method="RULE_BASED",
        extraction_version="v1"
    )
    db_session.add(evt)
    db_session.commit()

    _, candidates, margin = service.generate_candidates_for_event("EVT-EMPTY-PROJ")
    assert len(candidates) == 0
    assert margin is None

def test_22_missing_evidence_case(db_session):
    evt = create_event(db_session, event_id="EVT-MISSING-EVID", raw_text="General work")
    evt.identifier = None
    evt.location = None
    db_session.commit()

    service = CandidateGeneratorService(db_session)
    _, candidates, _ = service.generate_candidates_for_event("EVT-MISSING-EVID")
    assert len(candidates) > 0

def test_23_conflicting_identifier_case():
    score = score_identifier("24P201", "ACT-001", "EQ-999")
    assert score == 0.0

def test_24_model_loads_once():
    from backend.app.services.embedding_service import get_embedding_model
    m1 = get_embedding_model()
    m2 = get_embedding_model()
    assert m1 is m2

def test_25_schedule_embeddings_reused(db_session):
    from backend.app.services.embedding_service import precompute_schedule_embeddings, _SCHEDULE_EMBEDDINGS_CACHE
    acts = db_session.query(ScheduleActivity).all()
    precompute_schedule_embeddings(acts)
    cache_size = len(_SCHEDULE_EMBEDDINGS_CACHE)
    assert cache_size > 0

def test_26_event_embedding_generated(db_session):
    act = db_session.query(ScheduleActivity).first()
    score = score_semantic("Hydrotesting completed for LINE-ALPHA-201", act)
    assert score >= 0.0

def test_27_cosine_similarity_bounds(db_session):
    act = db_session.query(ScheduleActivity).first()
    score = score_semantic("Random work text", act)
    assert 0.0 <= score <= 100.0

def test_28_cpu_only_operation():
    from backend.app.services.embedding_service import get_embedding_model
    model = get_embedding_model()
    if model is not None:
        assert str(model.device) in ["cpu", "device(type='cpu')"]

def test_29_match_candidate_persistence(db_session):
    create_event(db_session, event_id="EVT-PERSIST-01")
    service = CandidateGeneratorService(db_session)
    service.generate_candidates_for_event("EVT-PERSIST-01")

    persisted = db_session.query(MatchCandidate).filter(MatchCandidate.event_id == "EVT-PERSIST-01").all()
    assert len(persisted) > 0

def test_30_foreign_key_integrity(db_session):
    create_event(db_session, event_id="EVT-FK-01")
    service = CandidateGeneratorService(db_session)
    service.generate_candidates_for_event("EVT-FK-01")

    cand = db_session.query(MatchCandidate).filter(MatchCandidate.event_id == "EVT-FK-01").first()
    assert cand.event is not None
    assert cand.activity is not None

def test_31_matcher_version_persistence(db_session):
    create_event(db_session, event_id="EVT-VER-01")
    service = CandidateGeneratorService(db_session)
    service.generate_candidates_for_event("EVT-VER-01")

    cand = db_session.query(MatchCandidate).filter(MatchCandidate.event_id == "EVT-VER-01").first()
    assert cand.matcher_version == "v1"

def test_32_normalization_persistence(db_session):
    create_event(db_session, event_id="EVT-NORM-PERSIST")
    service = CandidateGeneratorService(db_session)
    evt = service.normalize_event("EVT-NORM-PERSIST")

    db_evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.event_id == "EVT-NORM-PERSIST").first()
    assert db_evt.normalized_identifier == "24P201"

def test_33_api_normalize_endpoint(client, db_session):
    create_event(db_session, event_id="EVT-API-NORM")
    res = client.post("/events/EVT-API-NORM/normalize")
    assert res.status_code == 200
    assert res.json()["normalized_identifier"] == "24P201"

def test_34_api_candidates_endpoint(client, db_session):
    create_event(db_session, event_id="EVT-API-CAND")
    res = client.post("/events/EVT-API-CAND/candidates")
    assert res.status_code == 200
    body = res.json()
    assert body["candidate_count"] > 0
    assert len(body["candidates"]) > 0

def test_35_api_get_candidates_endpoint(client, db_session):
    create_event(db_session, event_id="EVT-API-GET")
    client.post("/events/EVT-API-GET/candidates")

    res = client.get("/events/EVT-API-GET/candidates")
    assert res.status_code == 200
    assert res.json()["candidate_count"] > 0

def test_36_api_nonexistent_event(client):
    res = client.post("/events/NONEXISTENT-EVT/candidates")
    assert res.status_code == 404

def test_37_idempotent_candidate_generation(client, db_session):
    create_event(db_session, event_id="EVT-IDEMP-01")
    
    res1 = client.post("/events/EVT-IDEMP-01/candidates")
    assert res1.status_code == 200
    cnt1 = db_session.query(MatchCandidate).filter(MatchCandidate.event_id == "EVT-IDEMP-01").count()

    res2 = client.post("/events/EVT-IDEMP-01/candidates")
    assert res2.status_code == 200
    cnt2 = db_session.query(MatchCandidate).filter(MatchCandidate.event_id == "EVT-IDEMP-01").count()

    assert cnt1 == cnt2
