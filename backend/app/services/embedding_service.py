import numpy as np
from typing import Dict, List, Optional, Any

_MODEL_INSTANCE = None
_MODEL_LOADED = False
_SCHEDULE_EMBEDDINGS_CACHE: Dict[str, np.ndarray] = {}

def get_embedding_model():
    global _MODEL_INSTANCE, _MODEL_LOADED
    if _MODEL_LOADED:
        return _MODEL_INSTANCE

    try:
        from sentence_transformers import SentenceTransformer
        # Load small 22MB sentence-transformer model on CPU
        _MODEL_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    except Exception as e:
        print(f"[EmbeddingService] SentenceTransformer model load notice: {e}. Using fallback TF-IDF similarity.")
        _MODEL_INSTANCE = None

    _MODEL_LOADED = True
    return _MODEL_INSTANCE

def precompute_schedule_embeddings(activities: List[Any]) -> None:
    """Precomputes and caches vector representations for ScheduleActivity objects in memory."""
    global _SCHEDULE_EMBEDDINGS_CACHE
    model = get_embedding_model()

    for act in activities:
        act_id = str(act.activity_id)
        if act_id in _SCHEDULE_EMBEDDINGS_CACHE:
            continue

        text_representation = f"{act.discipline or ''} {act.description or ''} {act.location or ''} {act.equipment_or_line_id or ''}".strip()

        if model is not None:
            try:
                emb = model.encode(text_representation, convert_to_numpy=True)
                _SCHEDULE_EMBEDDINGS_CACHE[act_id] = emb
                continue
            except Exception:
                pass
        
        # Fallback pseudo-vector / text representation
        _SCHEDULE_EMBEDDINGS_CACHE[act_id] = text_representation

def compute_semantic_similarity(event_text: str, activity: Any) -> float:
    """
    Computes cosine similarity between event text and activity text representation.
    Returns float score between 0.0 and 100.0.
    """
    if not event_text or not event_text.strip():
        return 50.0

    act_id = str(activity.activity_id)
    if act_id not in _SCHEDULE_EMBEDDINGS_CACHE:
        precompute_schedule_embeddings([activity])

    cached_item = _SCHEDULE_EMBEDDINGS_CACHE.get(act_id)
    model = get_embedding_model()

    if model is not None and isinstance(cached_item, np.ndarray):
        try:
            event_emb = model.encode(event_text, convert_to_numpy=True)
            norm_event = np.linalg.norm(event_emb)
            norm_act = np.linalg.norm(cached_item)
            if norm_event > 0 and norm_act > 0:
                sim = np.dot(event_emb, cached_item) / (norm_event * norm_act)
                # Map [-1, 1] to [0, 100]
                score = max(0.0, min(100.0, float((sim + 1.0) / 2.0 * 100.0)))
                return round(score, 2)
        except Exception:
            pass

    # Term-overlap fallback
    act_text = str(cached_item) if cached_item is not None else f"{activity.discipline} {activity.description}".lower()
    event_words = set(event_text.lower().split())
    act_words = set(act_text.lower().split())

    if not event_words or not act_words:
        return 50.0

    overlap = len(event_words.intersection(act_words))
    union = len(event_words.union(act_words))
    jaccard = overlap / union if union > 0 else 0.0
    return round(float(jaccard * 100.0), 2)
