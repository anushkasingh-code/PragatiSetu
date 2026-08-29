# Site2Schedule AI — Synthetic Dataset Quality Report

**Scope:** SIH26122 prototype dataset for Site2Schedule AI.

> This dataset is entirely synthetic and was created for prototyping and evaluating Site2Schedule AI for SIH26122. It is not Oil India Limited data and must not be represented as real sponsor data.

## File Inventory

1. `01_baseline_schedule.xlsx` — Project Alpha baseline schedule (75 activities).
2. `02_field_report_events.xlsx` — 400 labelled Project Alpha field-report events.
3. `03_daily_progress_reports.xlsx` — grouped DPR-style reports.
4. `04_discipline_progress_reports.xlsx` — structured Civil/Piping/Electrical progress sheets.
5. `05_activity_terminology_dictionary.xlsx` — terminology/alias dictionary.
6. `06_identifier_normalization_dictionary.xlsx` — identifier and location normalization examples.
7. `07_dataset_test_split.xlsx` — development/validation/test allocation.
8. `08_project_beta_baseline.xlsx` — hidden Project Beta baseline.
9. `09_project_beta_reports.xlsx` — 100 hidden Project Beta report events.
10. `10_dataset_quality_report.md` — this report.
11. `README.md` — usage and schema guide.

## Counts

- Project Alpha activities: **75**
- Project Alpha events: **400**
- Project Beta activities: **30**
- Project Beta events: **100**
- Project Alpha DPRs: **63**
- Structured discipline rows: **120**

## Project Alpha Event Distribution

- PARAPHRASE: 90
- CLEAN: 80
- ABBREVIATED: 50
- TYPO: 35
- PARTIAL_PROGRESS: 30
- HINGLISH: 25
- AMBIGUOUS: 25
- UNPLANNED: 20
- IRRELEVANT: 15
- CONFLICT: 15
- DUPLICATE: 15

## Difficulty Distribution

- EASY: 65
- HARD: 125
- MEDIUM: 210

## Routing Distribution

- AUTO_LINK_ELIGIBLE: 233
- HUMAN_REVIEW: 117
- UNPLANNED_REVIEW: 20
- IGNORE: 15
- CONFLICT_REVIEW: 15

## Train / Validation / Test Split

- development: 280
- validation: 60
- test: 60

## Automated Validation Checks

- PASS — Alpha schedule — Unique activity IDs
- PASS — Alpha schedule — Valid date order
- PASS — Alpha schedule — Positive durations
- PASS — Alpha schedule — Duration matches dates
- PASS — Alpha schedule — All predecessors exist
- PASS — Alpha schedule — No circular dependencies
- PASS — Alpha schedule — Predecessor finishes before successor starts
- PASS — Alpha schedule — No duplicate activity descriptions
- PASS — Beta schedule — Unique activity IDs
- PASS — Beta schedule — Valid date order
- PASS — Beta schedule — Positive durations
- PASS — Beta schedule — Duration matches dates
- PASS — Beta schedule — All predecessors exist
- PASS — Beta schedule — No circular dependencies
- PASS — Beta schedule — Predecessor finishes before successor starts
- PASS — Beta schedule — No duplicate activity descriptions
- PASS — Alpha events — Mapped activity IDs exist
- PASS — Alpha events — Mapped discipline consistent
- PASS — Alpha events — Ambiguous rows have no forced activity
- PASS — Alpha events — Unplanned rows have no forced activity
- PASS — Alpha events — Irrelevant rows route to IGNORE
- PASS — Alpha events — Percent complete in range
- PASS — Alpha events — Partial progress not mislabeled completed
- PASS — Alpha events — Duplicate groups contain at least two records
- PASS — Alpha events — Conflict groups contain at least two records
- PASS — Alpha events — All report IDs assigned
- PASS — Alpha events — Evidence scores valid
- PASS — Beta events — Mapped activity IDs exist
- PASS — Beta events — Mapped discipline consistent
- PASS — Beta events — Ambiguous rows have no forced activity
- PASS — Beta events — Unplanned rows have no forced activity
- PASS — Beta events — Irrelevant rows route to IGNORE
- PASS — Beta events — Percent complete in range
- PASS — Beta events — Partial progress not mislabeled completed
- PASS — Beta events — Duplicate groups contain at least two records
- PASS — Beta events — Conflict groups contain at least two records
- PASS — Beta events — All report IDs assigned
- PASS — Beta events — Evidence scores valid
- PASS — Split — Split counts 280/60/60
- PASS — Split — No exact development-test text overlap
- PASS — Split — No near-duplicate development-test pairs >=0.97
- PASS — Beta independence — Project IDs differ
- PASS — Beta independence — Activity IDs disjoint
- PASS — Beta independence — Locations meaningfully differ
- PASS — Beta independence — Equipment IDs distinct from Alpha

## Remaining Limitations

- The dataset is synthetic and cannot reproduce every reporting habit, abbreviation, typo pattern, or organization-specific terminology found on a real project.
- The baseline contains 75 activities and three disciplines only; a production project can contain thousands of activities and many more disciplines.
- The dependency network is intentionally simplified for prototype testing and does not model every Primavera relationship type, lag, calendar, resource constraint, or contractual milestone.
- Scanned handwriting, OCR degradation, voice transcription errors, photographs, and production ASR are outside this internal-round dataset.
- The Hinglish examples are intentionally limited and should not be treated as a comprehensive multilingual corpus.
- Evidence-completeness values are deterministic dataset annotations, not calibrated model confidence probabilities.
- Project Beta is a synthetic generalization test, not proof of performance on real Oil India projects.

## Recommended Evaluation Use

Use the development split for implementation, the validation split for confidence/review thresholds, and the test split only for final internal evaluation. Report real measured Top-1 accuracy, Top-3 recall, incorrect auto-link rate, abstention/review quality, ambiguity detection, duplicate/conflict detection, and latency after the matcher has actually been run.