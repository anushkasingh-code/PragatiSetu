import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models.activity import ScheduleActivity
from backend.app.services.ai.vector_store import get_activity_collection

logger = logging.getLogger("pragatisetu.vector_indexer")

def construct_activity_document(activity: ScheduleActivity) -> str:
    """
    Constructs a rich, searchable text representation of a ScheduleActivity record.
    Includes activity ID, discipline, full description, location, and equipment/line identifier.
    """
    parts = [
        f"Activity ID: {activity.activity_id}",
        f"Discipline: {activity.discipline}",
        f"Description: {activity.description}",
    ]
    if activity.location:
        parts.append(f"Location: {activity.location}")
    if activity.equipment_or_line_id:
        parts.append(f"Identifier: {activity.equipment_or_line_id}")
    parts.append(f"Status: {activity.status}")
    return " | ".join(parts)

def construct_activity_metadata(activity: ScheduleActivity) -> Dict[str, Any]:
    """
    Extracts structured metadata to store alongside the vector in ChromaDB for filtering and grounding.
    """
    return {
        "activity_id": str(activity.activity_id),
        "project_id": str(activity.project_id),
        "discipline": str(activity.discipline or ""),
        "identifier": str(activity.equipment_or_line_id or ""),
        "location": str(activity.location or ""),
        "status": str(activity.status or ""),
        "description": str(activity.description or "")[:300],
    }

def index_schedule_activities(
    db: Session,
    project_id: Optional[str] = None,
    client: Any = None,
    force_reindex: bool = False
) -> int:
    """
    Indexes ScheduleActivity records from the database into the ChromaDB vector collection.
    Repeatable: uses upsert to update entries without creating duplicates.
    """
    query = db.query(ScheduleActivity)
    if project_id:
        query = query.filter(ScheduleActivity.project_id == project_id)

    activities: List[ScheduleActivity] = query.all()
    if not activities:
        logger.info(f"No ScheduleActivity records found to index (project_id={project_id}).")
        return 0

    collection = get_activity_collection(client=client)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for act in activities:
        # Unique vector id formatted with project to guarantee uniqueness across projects
        vid = f"{act.project_id}::{act.activity_id}"
        ids.append(vid)
        documents.append(construct_activity_document(act))
        metadatas.append(construct_activity_metadata(act))

    # Batch upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    logger.info(f"Successfully indexed {len(ids)} schedule activities into Vector DB.")
    return len(ids)
