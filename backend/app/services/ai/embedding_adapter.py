import hashlib
from typing import List, Any
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from backend.app.services.embedding_service import get_embedding_model

class PragatiSetuEmbeddingAdapter(EmbeddingFunction[Documents]):
    """
    Thin adapter that connects ChromaDB to PragatiSetu's existing SentenceTransformer CPU embedding pipeline.
    Reuses get_embedding_model() singleton to prevent duplicate model loads and memory waste.
    Provides deterministic fallback vectors when the transformer model is not locally cached or offline.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    @staticmethod
    def name() -> str:
        return "pragatisetu_embedding_adapter"

    def get_config(self) -> dict:
        return {"dimension": self.dimension}

    @staticmethod
    def build_from_config(config: dict) -> "PragatiSetuEmbeddingAdapter":
        return PragatiSetuEmbeddingAdapter(dimension=config.get("dimension", 384))

    def _fallback_embed(self, text: str) -> List[float]:
        """Generates a deterministic normalized pseudo-embedding vector for offline / model-free environments."""
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(b / 255.0) * 2.0 - 1.0 for b in h]
        repeated = (vec * ((self.dimension // len(vec)) + 1))[:self.dimension]
        arr = np.array(repeated, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def __call__(self, input: Documents) -> Embeddings:
        model = get_embedding_model()
        if model is not None:
            try:
                raw = model.encode(list(input), convert_to_numpy=True)
                if isinstance(raw, np.ndarray):
                    return raw.tolist()
                return [list(x) for x in raw]
            except Exception:
                pass

        # Offline / fallback deterministic embeddings
        return [self._fallback_embed(doc) for doc in input]
