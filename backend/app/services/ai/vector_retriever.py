import logging
from typing import List, Optional, Any
from backend.app.schemas.ai import VectorSearchResult
from backend.app.services.ai.vector_store import get_activity_collection

logger = logging.getLogger("pragatisetu.vector_retriever")

def search_schedule_activities(
    project_id: str,
    query: str,
    top_k: int = 5,
    client: Any = None
) -> List[VectorSearchResult]:
    """
    Executes semantic vector search for activities matching query within the designated project.
    Strict project boundary: ChromaDB metadata filter `where={'project_id': project_id}` ensures
    queries for PragatiSetu will never retrieve Project Beta activities.
    """
    if not query or not query.strip() or not project_id:
        return []

    collection = get_activity_collection(client=client)

    # Check collection count to avoid querying empty collection
    if collection.count() == 0:
        return []

    safe_top_k = max(1, min(int(top_k), 50))

    try:
        results = collection.query(
            query_texts=[query.strip()],
            n_results=safe_top_k,
            where={"project_id": project_id}
        )
    except Exception as e:
        logger.warning(f"Vector search query failed: {e}")
        return []

    search_results: List[VectorSearchResult] = []

    ids_list = results.get("ids", [[]])[0] if results.get("ids") else []
    docs_list = results.get("documents", [[]])[0] if results.get("documents") else []
    metas_list = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    dists_list = results.get("distances", [[]])[0] if results.get("distances") else []

    for i, vid in enumerate(ids_list):
        meta = metas_list[i] if i < len(metas_list) and metas_list[i] else {}
        doc = docs_list[i] if i < len(docs_list) and docs_list[i] else ""
        dist = dists_list[i] if i < len(dists_list) and dists_list[i] is not None else 1.0

        act_id = meta.get("activity_id") or vid.split("::")[-1]
        proj_id = meta.get("project_id") or project_id

        # Cosine distance in Chroma ranges [0, 2]. Convert to similarity score [0.0, 1.0]
        # Similarity = 1.0 - (distance / 2.0)
        similarity = max(0.0, min(1.0, round(1.0 - (float(dist) / 2.0), 4)))

        search_results.append(
            VectorSearchResult(
                activity_id=act_id,
                project_id=proj_id,
                similarity=similarity,
                document=doc,
                metadata=meta
            )
        )

    return search_results
