# PragatiSetu — Safety Decision Policy Specification

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

---

## 1. Overview
The Safety Routing & Match Decision engine in **PragatiSetu** evaluates candidate match results and evidence availability to safely route events into one of four controlled decision states:
- `AUTO_LINK`: Safety layer permits automatic linking.
- `HUMAN_REVIEW`: Abstains due to ambiguity, low confidence, weak evidence, or small margin.
- `UNPLANNED_REVIEW`: No sufficiently supported baseline schedule activity exists.
- `IGNORE`: Contextual or administrative statements (no schedule impact).

---

## 2. Core Safety Rule: NO Schedule Modification

> [!IMPORTANT]
> A decision of `AUTO_LINK` means **"The safety layer has determined that automatic linking is permitted."**
> It **DOES NOT** modify `ScheduleActivity` objects, change `percent_complete`, set `actual_start`/`actual_finish`, or edit baseline schedules.
> Schedule updates belong strictly to Milestone 6.

---

## 3. Three Independent Safety Controls

Decision routing relies on three independent safety controls:

1. **Match Confidence Score (`match_confidence`, 0–100)**: Primary match-strength heuristic calculated during candidate generation in Milestone 4.
2. **Evidence Completeness Score (`evidence_completeness`, 0–100)**: Independent measure of event evidence availability across 7 supported fields (`identifier`, `location`, `discipline`, `action`, `status`, `event_date`, `quantity`).
3. **Top-2 Score Margin (`top_2_margin`)**: Score gap between Candidate Rank 1 and Candidate Rank 2 ($\text{Rank}_1 - \text{Rank}_2$).

---

## 4. AUTO-LINK Policy Thresholds

Automatic linking (`AUTO_LINK`) requires all three conditions to be satisfied simultaneously:

$$\text{match\_confidence} \ge 85.0 \quad \text{AND} \quad \text{evidence\_completeness} \ge 70.0 \quad \text{AND} \quad \text{top\_2\_margin} \ge 12.0$$

- If any single condition is not met, the event routes safely to `HUMAN_REVIEW`, `UNPLANNED_REVIEW`, or `IGNORE`.

---

## 5. REST APIs

- `POST /events/{event_id}/decision`: Evaluates decision policy thresholds, persists `MatchDecision` DB record, and returns judge-facing explanation reasons.
- `GET /events/{event_id}/decision`: Retrieves stored decision record.
