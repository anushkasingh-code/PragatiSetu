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

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message author role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = None

class ChatActivityItem(BaseModel):
    activity_id: str
    description: str
    wbs_id: str
    percent_complete: float = 0.0
    status: str = "NOT_STARTED"
    similarity: float = 0.0
    discipline: Optional[str] = None

class ChatRequest(BaseModel):
    project_id: str = Field(default="PROJ-ALPHA", description="Project identifier to query")
    messages: List[ChatMessage] = Field(default_factory=list, description="Conversation history messages")
    message: Optional[str] = Field(default=None, description="Optional single latest message if messages list is omitted")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of relevant activities to retrieve from Vector DB")
    api_key: Optional[str] = Field(default=None, description="Optional runtime Groq API key")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant reply in markdown format")
    grounded_candidates: List[str] = Field(default_factory=list, description="Activity IDs referenced and verified in response")
    activities: List[ChatActivityItem] = Field(default_factory=list, description="Structured matching activities from live schedule")
    project_id: str
    source: str = Field(default="local_rag", description="Engine used: 'groq' or 'local_rag'")
    model: Optional[str] = None

class KeyConfigRequest(BaseModel):
    groq_api_key: str = Field(..., description="Groq API key to save")

class KeyConfigResponse(BaseModel):
    status: str
    message: str
    configured: bool
    source: str

class KeyStatusResponse(BaseModel):
    configured: bool
    source: str
    model: str
    masked_key: Optional[str] = None



