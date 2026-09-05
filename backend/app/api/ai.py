from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.ai import (
    VectorSearchRequest,
    VectorSearchResponse,
    VectorIndexRequest,
    VectorIndexResponse,
    ExplainRequest,
    ExplainResponse,
    ChatRequest,
    ChatResponse,
    KeyConfigRequest,
    KeyConfigResponse,
    KeyStatusResponse
)
from backend.app.services.ai.vector_indexer import index_schedule_activities
from backend.app.services.ai.vector_retriever import search_schedule_activities
from backend.app.services.ai.groq_service import GroqExplanationService
from backend.app.services.ai.chat_service import PragatiSetuChatService

router = APIRouter(prefix="/ai", tags=["AI Enhancement (Vector Search & Groq LLM)"])

@router.post("/index", response_model=VectorIndexResponse, status_code=status.HTTP_200_OK)
def index_activities_endpoint(
    payload: VectorIndexRequest = VectorIndexRequest(),
    db: Session = Depends(get_db)
):
    """
    Indexes baseline ScheduleActivity records from the database into the local Chroma Vector DB.
    Idempotent and repeatable: utilizes upsert to prevent duplicate vector entries.
    """
    try:
        count = index_schedule_activities(
            db=db,
            project_id=payload.project_id,
            force_reindex=payload.force_reindex
        )
        return VectorIndexResponse(
            indexed_count=count,
            project_id=payload.project_id,
            status="SUCCESS",
            message=f"Successfully indexed {count} schedule activities into Vector DB."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector indexing failed: {str(e)}"
        )

@router.post("/search", response_model=VectorSearchResponse, status_code=status.HTTP_200_OK)
def search_activities_endpoint(
    payload: VectorSearchRequest
):
    """
    Performs semantic vector search across indexed ScheduleActivity records for a given project.
    Strict project boundary: only activities belonging to the specified project_id are returned.
    """
    try:
        results = search_schedule_activities(
            project_id=payload.project_id,
            query=payload.query,
            top_k=payload.top_k
        )
        return VectorSearchResponse(
            query=payload.query,
            project_id=payload.project_id,
            count=len(results),
            results=results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )

@router.post("/explain", response_model=ExplainResponse, status_code=status.HTTP_200_OK)
def explain_query_endpoint(
    payload: ExplainRequest
):
    """
    Retrieves semantic activity context via Vector DB and generates a grounded natural-language explanation using Groq LLM.
    If Groq is disabled, unavailable, or misconfigured, returns structured semantic retrieval context gracefully without failing.
    """
    try:
        service = GroqExplanationService()
        res = service.explain_query_context(
            project_id=payload.project_id,
            query=payload.query,
            activity_ids=payload.activity_ids,
            top_k=payload.top_k
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI explanation failed: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Conversational AI Copilot for PragatiSetu.
    Grounded in live database state and Chroma vector schedule embeddings.
    Seamlessly utilizes Groq LLM if GROQ_API_KEY is configured, or local dynamic RAG engine if not.
    """
    try:
        service = PragatiSetuChatService()
        return service.generate_chat_reply(payload=payload, db=db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )

@router.get("/key-status", response_model=KeyStatusResponse, status_code=status.HTTP_200_OK)
def get_key_status_endpoint():
    """
    Checks whether Groq API key is currently active or configured.
    """
    try:
        from backend.app.services.ai.chat_service import get_groq_key_status
        status_data = get_groq_key_status()
        return KeyStatusResponse(**status_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check key status: {str(e)}"
        )

@router.post("/configure-key", response_model=KeyConfigResponse, status_code=status.HTTP_200_OK)
def configure_key_endpoint(payload: KeyConfigRequest):
    """
    Saves and activates the Groq API key dynamically without requiring a manual server restart.
    Persists to .env files and immediately configures os.environ and application settings.
    """
    try:
        from backend.app.services.ai.chat_service import save_groq_api_key
        cleaned = payload.groq_api_key.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key cannot be empty."
            )
        save_groq_api_key(cleaned)
        return KeyConfigResponse(
            status="SUCCESS",
            message="Groq API key configured and activated successfully.",
            configured=True,
            source="groq"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure key: {str(e)}"
        )


