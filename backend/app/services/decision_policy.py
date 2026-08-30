import re
from typing import List, Optional, Any, Tuple
from backend.app.db.models.decision import DecisionEnum
from backend.app.config import settings

SCORING_POLICY_VERSION = "v1"

IGNORE_KEYWORDS_REGEX = re.compile(
    r"\b(safety meeting|toolbox talk|tool box talk|weather delay|heavy rain|holiday|no work carried out|no activities|administrative|site meeting)\b",
    re.IGNORECASE
)

def evaluate_decision_policy(
    event: Any,
    candidates: List[Any],
    evidence_completeness: float,
    top_2_margin: Optional[float]
) -> Tuple[DecisionEnum, Optional[Any]]:
    """
    Evaluates safety decision routing policy.
    Reads thresholds from settings for runtime configurability.
    Returns (DecisionEnum, selected_top_candidate).
    """
    # Read thresholds from settings at call-time (not module-load time)
    match_score_threshold = float(getattr(settings, "MATCH_SCORE_THRESHOLD", 85.0))
    evidence_threshold = float(getattr(settings, "EVIDENCE_COMPLETENESS_THRESHOLD", 70.0))
    top2_margin_threshold = float(getattr(settings, "TOP2_MARGIN_THRESHOLD", 12.0))

    raw_text = str(getattr(event, "raw_text", "")).strip()

    # 1. IGNORE Check: Administrative or non-work report statements
    if raw_text and IGNORE_KEYWORDS_REGEX.search(raw_text) and not getattr(event, "identifier", None):
        return DecisionEnum.IGNORE, None

    # 2. UNPLANNED_REVIEW Check: No candidates exist or top candidate has extremely weak compatibility (< 40.0)
    if not candidates:
        return DecisionEnum.UNPLANNED_REVIEW, None

    top_cand = candidates[0]
    if top_cand.overall_score < 40.0:
        return DecisionEnum.UNPLANNED_REVIEW, None

    # If only 1 candidate exists, effective top-2 margin is treated as 100.0 (unambiguous)
    effective_margin = top_2_margin if top_2_margin is not None else 100.0

    # 3. AUTO_LINK Check: Match score >= threshold AND Evidence completeness >= threshold AND Top-2 margin >= threshold
    if (
        top_cand.overall_score >= match_score_threshold and
        evidence_completeness >= evidence_threshold and
        effective_margin >= top2_margin_threshold
    ):
        return DecisionEnum.AUTO_LINK, top_cand

    # 4. HUMAN_REVIEW Check: Safe abstention for ambiguous cases
    return DecisionEnum.HUMAN_REVIEW, top_cand
