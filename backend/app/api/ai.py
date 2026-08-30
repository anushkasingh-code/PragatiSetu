from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.ai import (
    VectorSearchRequest,
    VectorSearchResponse,
    VectorIndexRequest,
    VectorIndexResponse,
    ExplainRequest,
    ExplainResponse
)
from backend.app.services.ai.vector_indexer import index_schedule_activities
from backend.app.services.ai.vector_retriever import search_schedule_activities
from backend.app.services.ai.groq_service import GroqExplanationService

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
