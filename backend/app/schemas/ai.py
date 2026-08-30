from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class VectorSearchRequest(BaseModel):
    project_id: str = Field(..., description="Project identifier to search within", min_length=1)
    query: str = Field(..., description="Semantic query text (e.g., event description or activity keywords)", min_length=1)
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of candidate activities to retrieve")

class VectorSearchResult(BaseModel):
    activity_id: str
    project_id: str
    similarity: float
    document: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VectorSearchResponse(BaseModel):
    query: str
    project_id: str
    count: int
    results: List[VectorSearchResult]

class VectorIndexRequest(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Optional project ID to index. If omitted, all projects are indexed.")
    force_reindex: bool = Field(default=False, description="Whether to reindex existing activity embeddings")

class VectorIndexResponse(BaseModel):
    indexed_count: int
    project_id: Optional[str] = None
    status: str
    message: str

class ExplainRequest(BaseModel):
    project_id: str = Field(..., description="Project identifier", min_length=1)
    query: str = Field(..., description="User query or field report event line", min_length=1)
    activity_ids: Optional[List[str]] = Field(default=None, description="Optional specific candidate activity IDs to explain. If omitted, vector search finds top candidates.")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of candidates to retrieve if activity_ids not provided")

class ExplainResponse(BaseModel):
    available: bool = Field(description="Whether Groq LLM service was available and executed successfully")
    summary: str = Field(description="Natural language summary / explanation")
    grounded_candidates: List[str] = Field(default_factory=list, description="Verified candidate activity IDs strictly grounded in the retrieved baseline context")
    reasoning: List[str] = Field(default_factory=list, description="Step-by-step reasoning points from the explanation")
    warnings: List[str] = Field(default_factory=list, description="Warnings, including any rejected hallucinated activity IDs or fallback notices")
    retrieved_context: List[VectorSearchResult] = Field(default_factory=list, description="Underlying candidate activities retrieved from the Vector DB")
