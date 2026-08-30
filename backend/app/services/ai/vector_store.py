import os
import logging
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.config import settings
from backend.app.services.ai.embedding_adapter import PragatiSetuEmbeddingAdapter

logger = logging.getLogger("pragatisetu.vector_store")

_CHROMA_CLIENT: Optional[chromadb.ClientAPI] = None

def get_chroma_client(persist_directory: Optional[str] = None, in_memory: bool = False) -> chromadb.ClientAPI:
    """
    Returns a singleton ChromaDB client instance configured for local persistent storage.
    If in_memory=True or during testing, creates an ephemeral in-memory client.
    """
    global _CHROMA_CLIENT
    if in_memory:
        return chromadb.EphemeralClient()

    if _CHROMA_CLIENT is not None:
        return _CHROMA_CLIENT

    dir_path = persist_directory or getattr(settings, "VECTOR_DB_DIR", "vector_store")
    os.makedirs(dir_path, exist_ok=True)

    try:
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=dir_path,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
    except Exception as e:
        logger.warning(f"Could not initialize PersistentClient at '{dir_path}': {e}. Using EphemeralClient fallback.")
        _CHROMA_CLIENT = chromadb.EphemeralClient()

    return _CHROMA_CLIENT

def get_activity_collection(
    client: Optional[chromadb.ClientAPI] = None,
    collection_name: Optional[str] = None
):
    """
    Retrieves or creates the ScheduleActivity vector collection using the unified embedding adapter.
    """
    c = client or get_chroma_client()
    col_name = collection_name or getattr(settings, "VECTOR_COLLECTION_NAME", "pragatisetu_activities")
    adapter = PragatiSetuEmbeddingAdapter()
    return c.get_or_create_collection(
        name=col_name,
        embedding_function=adapter,
        metadata={"hnsw:space": "cosine"}
    )
