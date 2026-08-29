import re
from typing import List, Optional, Any, Tuple
from backend.app.db.models.decision import DecisionEnum

MATCH_SCORE_THRESHOLD = 85.0
EVIDENCE_COMPLETENESS_THRESHOLD = 70.0
TOP2_MARGIN_THRESHOLD = 12.0
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
    Returns (DecisionEnum, selected_top_candidate).
    """
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

    # 3. AUTO_LINK Check: Match score >= 85 AND Evidence completeness >= 70 AND Top-2 margin >= 12
    if (
        top_cand.overall_score >= MATCH_SCORE_THRESHOLD and
        evidence_completeness >= EVIDENCE_COMPLETENESS_THRESHOLD and
        effective_margin >= TOP2_MARGIN_THRESHOLD
    ):
        return DecisionEnum.AUTO_LINK, top_cand

    # 4. HUMAN_REVIEW Check: Safe abstention for ambiguous cases
    return DecisionEnum.HUMAN_REVIEW, top_cand
