from typing import Tuple, List, Any, Optional

SUPPORTED_EVIDENCE_FIELDS = [
    "identifier",
    "location",
    "discipline",
    "action",
    "status",
    "event_date",
    "quantity"
]

def calculate_evidence_completeness(event: Any) -> Tuple[float, List[str]]:
    """
    Calculates evidence availability percentage (0-100) across 7 supported fields.
    Returns (evidence_completeness_score, missing_evidence_list).
    """
    present_count = 0
    missing_fields = []

    # 1. Identifier
    if event.identifier or getattr(event, "normalized_identifier", None):
        present_count += 1
    else:
        missing_fields.append("identifier")

    # 2. Location
    if event.location or getattr(event, "normalized_location", None):
        present_count += 1
    else:
        missing_fields.append("location")

    # 3. Discipline
    if event.discipline:
        present_count += 1
    else:
        missing_fields.append("discipline")

    # 4. Action
    if event.action or getattr(event, "normalized_action", None):
        present_count += 1
    else:
        missing_fields.append("action")

    # 5. Status
    if event.status:
        present_count += 1
    else:
        missing_fields.append("status")

    # 6. Date
    if event.event_date:
        present_count += 1
    else:
        missing_fields.append("event_date")

    # 7. Quantity / Percent
    if event.quantity is not None or event.percent_complete is not None:
        present_count += 1
    else:
        missing_fields.append("quantity")

    score = round((present_count / float(len(SUPPORTED_EVIDENCE_FIELDS))) * 100.0, 2)
    return score, missing_fields

def derive_evidence_reasons(event: Any, top_candidate: Optional[Any]) -> List[str]:
    """Derives explainable, signal-level evidence strings based on computed candidate scores."""
    reasons = []
    if not top_candidate:
        return ["No candidate activities available for evaluation."]

    if top_candidate.identifier_score >= 85.0:
        reasons.append(f"Identifier '{event.normalized_identifier or event.identifier}' strongly matched baseline tag.")
    elif top_candidate.identifier_score == 0.0:
        reasons.append("Identifier conflict detected with candidate baseline tag.")

    if top_candidate.discipline_score == 100.0:
        reasons.append(f"Discipline '{event.discipline}' matches candidate activity discipline.")
    elif top_candidate.discipline_score == 0.0:
        reasons.append("Disciplinary mismatch between event and candidate activity.")

    if top_candidate.location_score >= 80.0:
        reasons.append(f"Location '{event.normalized_location or event.location}' matches candidate site location.")
    elif top_candidate.location_score == 20.0:
        reasons.append("Location mismatch between event and candidate site area.")

    if top_candidate.action_score >= 65.0:
        reasons.append(f"Action '{event.normalized_action or event.action}' is compatible with candidate description.")

    if top_candidate.semantic_score >= 80.0:
        reasons.append("High semantic similarity between event description and baseline activity.")

    if top_candidate.fuzzy_score >= 75.0:
        reasons.append("Strong text phrase overlap detected via fuzzy matching.")

    if top_candidate.temporal_score == 100.0:
        reasons.append("Event date falls within planned baseline schedule window.")
    elif top_candidate.temporal_score == 70.0:
        reasons.append("Event date falls within close proximity (<= 14 days) of planned window.")

    if top_candidate.dependency_score == 100.0:
        reasons.append("WBS predecessor sequence requirements satisfied.")

    return reasons
