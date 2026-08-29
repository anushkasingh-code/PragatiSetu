# PragatiSetu — Resolver Specification (Normalization & Candidate Generation)

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

---

## 1. Overview
The Resolver module in **PragatiSetu** converts raw `ExtractedEvent` records into normalized event representations and constructs a ranked shortlist of baseline `ScheduleActivity` candidates.

### Critical Scope Boundary
- **Candidate Generation & Scoring**: Evaluates candidate compatibility and outputs Top 1-5 candidate activities with explainable component scores and `top_2_margin`.
- **Match Decision & Linking**: Explicitly deferred to later milestones. Does **NOT** execute `AUTO_LINK`, `HUMAN_REVIEW`, or actual schedule updates.

---

## 2. Normalization Engine
Raw field entries contain spelling variations, inconsistent spacing, hyphens, and shorthand. Normalization standardizes these variants deterministically while preserving raw source values (`raw_identifier`, `raw_action`, `raw_location`).

### Dictionaries Used
- `06_identifier_normalization_dictionary.xlsx`: Maps tag variants to canonical IDs (e.g. `P-101A` -> `EQ-ALPHA-101`, `Line 201-A` -> `LINE-ALPHA-201`, `Sub-3` -> `Substation 3`).
- `05_activity_terminology_dictionary.xlsx`: Maps field actions to standard terms (e.g. `hydrotesting` -> `Hydrostatic Testing`, `tie-in` -> `Hot Tie-In Connection`, `cable pulling` -> `Electrical Cable Laying`, `alignment` -> `Pump Alignment`).

---

## 3. Component Evidence Scores (0–100 Range)

Candidates are evaluated across 8 independent component scoring signals:

1. **Identifier Score (`identifier_score`, 30%)**: Direct tag match = 100. Substring = 85. Missing = 50 (neutral). Conflict = 0.
2. **Discipline Score (`discipline_score`, 15%)**: Discipline match = 100. Missing = 50. Disciplinary conflict = 0.
3. **Location Score (`location_score`, 15%)**: Exact location match = 100. Substring = 80. Missing = 50. Conflict = 20.
4. **Semantic Score (`semantic_score`, 20%)**: Cosine similarity between event text and cached activity vector embedding (`all-MiniLM-L6-v2` loaded once on CPU).
5. **Action Score (`action_score`, 10%)**: Standard terminology match = 100. Partial overlap = 65. Missing = 50.
6. **Fuzzy Score (`fuzzy_score`, 5%)**: String similarity calculated via `RapidFuzz` `token_set_ratio`.
7. **Temporal Score (`temporal_score`, 3%)**: Within planned start/finish = 100. Within 14 days = 70. Within 30 days = 50.
8. **Dependency Score (`dependency_score`, 2%)**: WBS predecessor completed = 100. Predecessor pending = 40. Default = 80.

### Overall Heuristic Score Formula
$$\text{overall\_score} = \sum_{k} \text{score}_k \times \text{weight}_k$$

> **Note**: `overall_score` is an explainable heuristic compatibility score (0-100), **NOT** a calibrated statistical probability.

---

## 4. REST APIs

### 1. Normalize Extracted Event (`POST /events/{event_id}/normalize`)
Normalizes event tags, actions, objects, and locations using dictionary lookups.

### 2. Generate Candidate Shortlist (`POST /events/{event_id}/candidates`)
Generates Top 5-10 ranked candidates, computes 8 component scores, calculates `top_2_margin`, and persists `MatchCandidate` records.

### 3. Retrieve Candidate Shortlist (`GET /events/{event_id}/candidates`)
Retrieves stored candidate results for an event.
