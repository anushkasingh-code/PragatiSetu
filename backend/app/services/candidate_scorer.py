import datetime
from typing import Dict, Any, Optional
from rapidfuzz import fuzz
from backend.app.services.embedding_service import compute_semantic_similarity
from backend.app.services.normalizer_service import normalize_identifier, normalize_location

MATCH_WEIGHTS = {
    "identifier": 0.30,
    "discipline": 0.15,
    "location": 0.15,
    "semantic": 0.20,
    "action": 0.10,
    "fuzzy": 0.05,
    "temporal": 0.03,
    "dependency": 0.02
}

def score_identifier(event_norm_id: Optional[str], act_id: str, act_eq_id: Optional[str]) -> float:
    if not event_norm_id:
        return 50.0  # Neutral missing evidence

    norm_act_id = normalize_identifier(act_id)
    norm_eq_id = normalize_identifier(act_eq_id) if act_eq_id else None

    # Exact match
    if event_norm_id == norm_act_id or (norm_eq_id and event_norm_id == norm_eq_id):
        return 100.0

    # Substring match
    if (norm_act_id and event_norm_id in norm_act_id) or (norm_eq_id and event_norm_id in norm_eq_id):
        return 85.0

    return 0.0  # Contradictory tag

def score_discipline(event_disc: Optional[str], act_disc: Optional[str]) -> float:
    if not event_disc:
        return 50.0
    if not act_disc:
        return 50.0

    if event_disc.strip().lower() == act_disc.strip().lower():
        return 100.0
    return 0.0  # Disciplinary conflict

def score_location(event_norm_loc: Optional[str], act_loc: Optional[str]) -> float:
    if not event_norm_loc:
        return 50.0

    norm_act_loc = normalize_location(act_loc)
    if not norm_act_loc:
        return 50.0

    norm_event_loc = normalize_location(event_norm_loc) or event_norm_loc
    e_clean = norm_event_loc.strip().upper()
    a_clean = norm_act_loc.strip().upper()

    if e_clean == a_clean:
        return 100.0
    if e_clean in a_clean or a_clean in e_clean:
        return 80.0
    return 20.0

def score_action(event_norm_action: Optional[str], act_desc: str) -> float:
    if not event_norm_action:
        return 50.0
    if not act_desc:
        return 50.0

    action_lower = event_norm_action.lower()
    desc_lower = act_desc.lower()

    if action_lower in desc_lower:
        return 100.0

    # Partial word overlap
    act_words = set(action_lower.split())
    desc_words = set(desc_lower.split())
    if act_words.intersection(desc_words):
        return 65.0

    return 30.0

def score_fuzzy(event_raw_text: str, act_desc: str) -> float:
    if not event_raw_text or not act_desc:
        return 50.0
    score = float(fuzz.token_set_ratio(event_raw_text, act_desc))
    return round(score, 2)

def score_semantic(event_raw_text: str, activity: Any) -> float:
    return compute_semantic_similarity(event_raw_text, activity)

def score_temporal(event_date: Optional[datetime.date], planned_start: datetime.date, planned_finish: datetime.date) -> float:
    if not event_date or not planned_start or not planned_finish:
        return 50.0

    if planned_start <= event_date <= planned_finish:
        return 100.0

    # Days outside planned window
    if event_date < planned_start:
        delta = (planned_start - event_date).days
    else:
        delta = (event_date - planned_finish).days

    if delta <= 14:
        return 70.0
    elif delta <= 30:
        return 50.0
    else:
        return 30.0

def score_dependency(act_predecessor_id: Optional[str]) -> float:
    if not act_predecessor_id:
        return 80.0
    return 100.0

def compute_all_candidate_scores(event: Any, activity: Any) -> Dict[str, float]:
    id_s = score_identifier(event.normalized_identifier, activity.activity_id, activity.equipment_or_line_id)
    disc_s = score_discipline(event.discipline, activity.discipline)
    loc_s = score_location(event.normalized_location, activity.location)
    act_s = score_action(event.normalized_action, activity.description)
    fuzz_s = score_fuzzy(event.raw_text, activity.description)
    sem_s = score_semantic(event.raw_text, activity)
    temp_s = score_temporal(event.event_date, activity.planned_start, activity.planned_finish)
    dep_s = score_dependency(activity.predecessor_activity_id)

    scores = {
        "identifier_score": id_s,
        "discipline_score": disc_s,
        "location_score": loc_s,
        "action_score": act_s,
        "fuzzy_score": fuzz_s,
        "semantic_score": sem_s,
        "temporal_score": temp_s,
        "dependency_score": dep_s
    }

    overall = (
        id_s * MATCH_WEIGHTS["identifier"] +
        disc_s * MATCH_WEIGHTS["discipline"] +
        loc_s * MATCH_WEIGHTS["location"] +
        sem_s * MATCH_WEIGHTS["semantic"] +
        act_s * MATCH_WEIGHTS["action"] +
        fuzz_s * MATCH_WEIGHTS["fuzzy"] +
        temp_s * MATCH_WEIGHTS["temporal"] +
        dep_s * MATCH_WEIGHTS["dependency"]
    )

    scores["overall_score"] = round(overall, 2)
    return scores
