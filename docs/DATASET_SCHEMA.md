# PragatiSetu — Ground Truth Dataset Schema Documentation

> **IMPORTANT NOTICE**: This dataset is entirely **SYNTHETIC** development/evaluation ground truth. It is NOT real Oil India Limited data.

## Dataset Overview

- **PragatiSetu**: 75 baseline schedule activities, 400 labelled field events (280 dev, 60 val, 60 test).
- **Project Beta**: 30 baseline schedule activities, 100 field report events.
- **QA Checks**: 45 checks reported as PASS in `10_dataset_quality_report.md`.

---

## Detailed File Inspection

### File: `01_baseline_schedule.xlsx`
- **Workbook Sheets**: `['Baseline']`

#### Sheet: `Baseline`
- **Total Rows**: `75`
- **Total Columns**: `18`
- **Columns**: `['project_id', 'project_name', 'wbs_level_1', 'wbs_level_2', 'wbs_level_3', 'activity_id', 'discipline', 'activity_description', 'location', 'equipment_or_line_id', 'planned_start', 'planned_finish', 'planned_duration_days', 'predecessor_activity_id', 'successor_activity_id', 'planned_percent_complete', 'baseline_status', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `project_id` | `str` | `0` | `ALPHA-001` |
| `project_name` | `str` | `0` | `Project Alpha — Pump, Pipeline & Utility Expansion` |
| `wbs_level_1` | `str` | `0` | `Project Alpha — Pump, Pipeline & Utility Expansion` |
| `wbs_level_2` | `str` | `0` | `Civil Works` |
| `wbs_level_3` | `str` | `0` | `Site Preparation / Pump Area` |
| `activity_id` | `str` | `0` | `CIV-101` |
| `discipline` | `str` | `0` | `Civil` |
| `activity_description` | `str` | `0` | `Site clearing and grubbing at Pump Area` |
| `location` | `str` | `0` | `Pump Area` |
| `equipment_or_line_id` | `str` | `0` | `AREA-PA` |
| `planned_start` | `datetime64[us]` | `0` | `2026-09-01 00:00:00` |
| `planned_finish` | `datetime64[us]` | `0` | `2026-09-02 00:00:00` |
| `planned_duration_days` | `int64` | `0` | `2` |
| `predecessor_activity_id` | `str` | `5` | `CIV-101` |
| `successor_activity_id` | `str` | `14` | `CIV-102|CIV-114|CIV-119|CIV-121` |
| `planned_percent_complete` | `int64` | `0` | `0` |
| `baseline_status` | `str` | `0` | `NOT_STARTED` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `02_field_report_events.xlsx`
- **Workbook Sheets**: `['Events']`

#### Sheet: `Events`
- **Total Rows**: `400`
- **Total Columns**: `40`
- **Columns**: `['event_id', 'project_id', 'report_id', 'report_date', 'source_type', 'reported_discipline', 'raw_text', 'ground_truth_activity_id', 'ground_truth_action', 'ground_truth_status', 'ground_truth_location', 'ground_truth_identifier', 'reported_quantity', 'reported_percent_complete', 'is_ambiguous', 'is_unplanned', 'is_irrelevant', 'is_duplicate', 'is_conflict', 'is_multi_event_source', 'duplicate_group_id', 'conflict_group_id', 'source_sentence_id', 'progress_signal_for_activity_id', 'data_quality_tag', 'difficulty_level', 'expected_routing', 'has_identifier', 'has_location', 'has_discipline', 'has_action', 'has_status', 'has_quantity', 'has_date', 'evidence_completeness_expected', 'notes', 'synthetic_generator_version', 'generated_date', 'validation_status', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `event_id` | `str` | `0` | `EV-A-0001` |
| `project_id` | `str` | `0` | `ALPHA-001` |
| `report_id` | `str` | `0` | `DPR-A-001` |
| `report_date` | `datetime64[us]` | `0` | `2026-09-01 00:00:00` |
| `source_type` | `str` | `0` | `DPR_TEXT` |
| `reported_discipline` | `str` | `0` | `Civil` |
| `raw_text` | `str` | `0` | `Site clearing and grubbing at Pump Area began today at Pump Area.` |
| `ground_truth_activity_id` | `str` | `60` | `CIV-101` |
| `ground_truth_action` | `str` | `15` | `clear` |
| `ground_truth_status` | `str` | `0` | `STARTED` |
| `ground_truth_location` | `str` | `22` | `Pump Area` |
| `ground_truth_identifier` | `str` | `60` | `AREA-PA` |
| `reported_quantity` | `str` | `370` | `1 work-front units` |
| `reported_percent_complete` | `float64` | `354` | `20.0` |
| `is_ambiguous` | `bool` | `0` | `False` |
| `is_unplanned` | `bool` | `0` | `False` |
| `is_irrelevant` | `bool` | `0` | `False` |
| `is_duplicate` | `bool` | `0` | `False` |
| `is_conflict` | `bool` | `0` | `False` |
| `is_multi_event_source` | `bool` | `0` | `False` |
| `duplicate_group_id` | `str` | `370` | `DUP-A-001` |
| `conflict_group_id` | `str` | `370` | `CON-A-001` |
| `source_sentence_id` | `str` | `0` | `SRC-EV-A-0001` |
| `progress_signal_for_activity_id` | `str` | `60` | `CIV-101` |
| `data_quality_tag` | `str` | `0` | `CLEAN` |
| `difficulty_level` | `str` | `0` | `EASY` |
| `expected_routing` | `str` | `0` | `AUTO_LINK_ELIGIBLE` |
| `has_identifier` | `bool` | `0` | `True` |
| `has_location` | `bool` | `0` | `True` |
| `has_discipline` | `bool` | `0` | `True` |
| `has_action` | `bool` | `0` | `True` |
| `has_status` | `bool` | `0` | `True` |
| `has_quantity` | `bool` | `0` | `False` |
| `has_date` | `bool` | `0` | `True` |
| `evidence_completeness_expected` | `int64` | `0` | `95` |
| `notes` | `str` | `310` | `Multiple plausible baseline activities; safe routing is human review.` |
| `synthetic_generator_version` | `str` | `0` | `v1.0` |
| `generated_date` | `datetime64[us]` | `0` | `2026-08-29 00:00:00` |
| `validation_status` | `str` | `0` | `PASS` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `03_daily_progress_reports.xlsx`
- **Workbook Sheets**: `['DPRs']`

#### Sheet: `DPRs`
- **Total Rows**: `63`
- **Total Columns**: `11`
- **Columns**: `['report_id', 'report_date', 'discipline', 'report_title', 'reported_by_role', 'raw_report_text', 'number_of_ground_truth_events', 'contains_irrelevant_text', 'contains_ambiguous_event', 'contains_conflict', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `report_id` | `str` | `0` | `DPR-A-001` |
| `report_date` | `datetime64[us]` | `0` | `2026-09-01 00:00:00` |
| `discipline` | `str` | `0` | `Civil` |
| `report_title` | `str` | `0` | `Daily Progress Report — 2026-09-01 — Civil` |
| `reported_by_role` | `str` | `0` | `Civil Engineer` |
| `raw_report_text` | `str` | `0` | `1. Site clearing and grubbing at Pump Area began today at Pump Area.
2. Site clearing and grubbing at Pump Area commenced at Pump Area.
3. Site clearing at Pump Area is ongoing.
4. AREAPA area clearing is continuing at Pmp Area.
5. Site clearing and grubbing at Pump Area began today at Pump Area.` |
| `number_of_ground_truth_events` | `int64` | `0` | `5` |
| `contains_irrelevant_text` | `bool` | `0` | `False` |
| `contains_ambiguous_event` | `bool` | `0` | `False` |
| `contains_conflict` | `bool` | `0` | `False` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `04_discipline_progress_reports.xlsx`
- **Workbook Sheets**: `['Civil', 'Piping', 'Electrical']`

#### Sheet: `Civil`
- **Total Rows**: `40`
- **Total Columns**: `10`
- **Columns**: `['Date', 'Location', 'Work Description', 'Equipment/Line ID', 'Status', 'Quantity', 'Percent Complete', 'Supervisor Role', 'Ground Truth Activity ID', 'Synthetic Flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `Date` | `datetime64[us]` | `0` | `2026-09-01 00:00:00` |
| `Location` | `str` | `0` | `Pump Area` |
| `Work Description` | `str` | `0` | `Site clearing and grubbing at Pump Area began today at Pump Area.` |
| `Equipment/Line ID` | `str` | `0` | `AREA-PA` |
| `Status` | `str` | `0` | `STARTED` |
| `Quantity` | `float64` | `40` | `None` |
| `Percent Complete` | `float64` | `40` | `None` |
| `Supervisor Role` | `str` | `0` | `Civil Engineer` |
| `Ground Truth Activity ID` | `str` | `0` | `CIV-101` |
| `Synthetic Flag` | `bool` | `0` | `True` |


#### Sheet: `Piping`
- **Total Rows**: `40`
- **Total Columns**: `10`
- **Columns**: `['Date', 'Location', 'Work Description', 'Equipment/Line ID', 'Status', 'Quantity', 'Percent Complete', 'Supervisor Role', 'Ground Truth Activity ID', 'Synthetic Flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `Date` | `datetime64[us]` | `0` | `2026-09-12 00:00:00` |
| `Location` | `str` | `0` | `Rack B` |
| `Work Description` | `str` | `0` | `AREA-PA filling is ongoing at Pump Area, AREA-GEN area restoration began today at Project Area, and SUP-RB1 installation is ongoing at Rack B.` |
| `Equipment/Line ID` | `str` | `0` | `SUP-RB1` |
| `Status` | `str` | `0` | `IN_PROGRESS` |
| `Quantity` | `float64` | `40` | `None` |
| `Percent Complete` | `float64` | `40` | `None` |
| `Supervisor Role` | `str` | `0` | `Piping Supervisor` |
| `Ground Truth Activity ID` | `str` | `0` | `PIP-201` |
| `Synthetic Flag` | `bool` | `0` | `True` |


#### Sheet: `Electrical`
- **Total Rows**: `40`
- **Total Columns**: `10`
- **Columns**: `['Date', 'Location', 'Work Description', 'Equipment/Line ID', 'Status', 'Quantity', 'Percent Complete', 'Supervisor Role', 'Ground Truth Activity ID', 'Synthetic Flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `Date` | `datetime64[us]` | `0` | `2026-09-19 00:00:00` |
| `Location` | `str` | `0` | `Rack B` |
| `Work Description` | `str` | `0` | `12-P-211 alignment and fit-up began today at Pump Area, PIP-CLOSE final closure is in progress at Project Area, and TRAY-RB-SUP erection completed at Rack B.` |
| `Equipment/Line ID` | `str` | `0` | `TRAY-RB-SUP` |
| `Status` | `str` | `0` | `COMPLETED` |
| `Quantity` | `float64` | `40` | `None` |
| `Percent Complete` | `float64` | `40` | `None` |
| `Supervisor Role` | `str` | `0` | `Electrical Engineer` |
| `Ground Truth Activity ID` | `str` | `0` | `ELE-301` |
| `Synthetic Flag` | `bool` | `0` | `True` |


### File: `05_activity_terminology_dictionary.xlsx`
- **Workbook Sheets**: `['Terminology']`

#### Sheet: `Terminology`
- **Total Rows**: `78`
- **Total Columns**: `6`
- **Columns**: `['canonical_term', 'discipline', 'synonym_or_alias', 'abbreviation', 'example_usage', 'confidence_of_domain_usage']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `canonical_term` | `str` | `0` | `excavation` |
| `discipline` | `str` | `0` | `Civil` |
| `synonym_or_alias` | `str` | `0` | `digging` |
| `abbreviation` | `float64` | `78` | `None` |
| `example_usage` | `str` | `0` | `Digging is in progress.` |
| `confidence_of_domain_usage` | `str` | `0` | `HIGH` |


### File: `06_identifier_normalization_dictionary.xlsx`
- **Workbook Sheets**: `['Normalization']`

#### Sheet: `Normalization`
- **Total Rows**: `140`
- **Total Columns**: `5`
- **Columns**: `['identifier_type', 'canonical_identifier', 'observed_variant', 'normalization_rule', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `identifier_type` | `str` | `0` | `equipment_or_line_id` |
| `canonical_identifier` | `str` | `0` | `AREAPA` |
| `observed_variant` | `str` | `0` | `AREA-PA` |
| `normalization_rule` | `str` | `0` | `remove spaces/hyphens; uppercase; retain alphanumeric characters` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `07_dataset_test_split.xlsx`
- **Workbook Sheets**: `['Splits']`

#### Sheet: `Splits`
- **Total Rows**: `400`
- **Total Columns**: `6`
- **Columns**: `['event_id', 'split', 'reason_for_split', 'activity_seen_in_development', 'wording_seen_in_development', 'difficulty_level']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `event_id` | `str` | `0` | `EV-A-0001` |
| `split` | `str` | `0` | `development` |
| `reason_for_split` | `str` | `0` | `Development set for matcher/extractor iteration; grouped units preserved.` |
| `activity_seen_in_development` | `bool` | `0` | `True` |
| `wording_seen_in_development` | `bool` | `0` | `True` |
| `difficulty_level` | `str` | `0` | `EASY` |


### File: `08_project_beta_baseline.xlsx`
- **Workbook Sheets**: `['Baseline']`

#### Sheet: `Baseline`
- **Total Rows**: `30`
- **Total Columns**: `18`
- **Columns**: `['project_id', 'project_name', 'wbs_level_1', 'wbs_level_2', 'wbs_level_3', 'activity_id', 'discipline', 'activity_description', 'location', 'equipment_or_line_id', 'planned_start', 'planned_finish', 'planned_duration_days', 'predecessor_activity_id', 'successor_activity_id', 'planned_percent_complete', 'baseline_status', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `project_id` | `str` | `0` | `BETA-001` |
| `project_name` | `str` | `0` | `Project Beta — Compressor & Utility Upgrade` |
| `wbs_level_1` | `str` | `0` | `Project Beta — Compressor & Utility Upgrade` |
| `wbs_level_2` | `str` | `0` | `Civil Works` |
| `wbs_level_3` | `str` | `0` | `Compressor Foundations / C21` |
| `activity_id` | `str` | `0` | `CIV-401` |
| `discipline` | `str` | `0` | `Civil` |
| `activity_description` | `str` | `0` | `Excavation for Compressor Foundation C21` |
| `location` | `str` | `0` | `Compressor Area` |
| `equipment_or_line_id` | `str` | `0` | `C21` |
| `planned_start` | `datetime64[us]` | `0` | `2026-10-01 00:00:00` |
| `planned_finish` | `datetime64[us]` | `0` | `2026-10-02 00:00:00` |
| `planned_duration_days` | `int64` | `0` | `2` |
| `predecessor_activity_id` | `str` | `7` | `CIV-401` |
| `successor_activity_id` | `str` | `8` | `CIV-402` |
| `planned_percent_complete` | `int64` | `0` | `0` |
| `baseline_status` | `str` | `0` | `NOT_STARTED` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `09_project_beta_reports.xlsx`
- **Workbook Sheets**: `['Events']`

#### Sheet: `Events`
- **Total Rows**: `100`
- **Total Columns**: `40`
- **Columns**: `['event_id', 'project_id', 'report_id', 'report_date', 'source_type', 'reported_discipline', 'raw_text', 'ground_truth_activity_id', 'ground_truth_action', 'ground_truth_status', 'ground_truth_location', 'ground_truth_identifier', 'reported_quantity', 'reported_percent_complete', 'is_ambiguous', 'is_unplanned', 'is_irrelevant', 'is_duplicate', 'is_conflict', 'is_multi_event_source', 'duplicate_group_id', 'conflict_group_id', 'source_sentence_id', 'progress_signal_for_activity_id', 'data_quality_tag', 'difficulty_level', 'expected_routing', 'has_identifier', 'has_location', 'has_discipline', 'has_action', 'has_status', 'has_quantity', 'has_date', 'evidence_completeness_expected', 'notes', 'synthetic_generator_version', 'generated_date', 'validation_status', 'synthetic_data_flag']`

| Column Name | Data Type | Null Count | Sample Value |
| --- | --- | --- | --- |
| `event_id` | `str` | `0` | `EV-B-0001` |
| `project_id` | `str` | `0` | `BETA-001` |
| `report_id` | `str` | `0` | `DPR-B-001` |
| `report_date` | `datetime64[us]` | `0` | `2026-10-01 00:00:00` |
| `source_type` | `str` | `0` | `DPR_TEXT` |
| `reported_discipline` | `str` | `0` | `Civil` |
| `raw_text` | `str` | `0` | `Excavation for Compressor Foundation C21 started at Compressor Area.` |
| `ground_truth_activity_id` | `str` | `8` | `CIV-401` |
| `ground_truth_action` | `str` | `1` | `excavate` |
| `ground_truth_status` | `str` | `0` | `STARTED` |
| `ground_truth_location` | `str` | `2` | `Compressor Area` |
| `ground_truth_identifier` | `str` | `8` | `C21` |
| `reported_quantity` | `str` | `95` | `1 work-front units` |
| `reported_percent_complete` | `float64` | `94` | `20.0` |
| `is_ambiguous` | `bool` | `0` | `False` |
| `is_unplanned` | `bool` | `0` | `False` |
| `is_irrelevant` | `bool` | `0` | `False` |
| `is_duplicate` | `bool` | `0` | `False` |
| `is_conflict` | `bool` | `0` | `False` |
| `is_multi_event_source` | `bool` | `0` | `False` |
| `duplicate_group_id` | `str` | `98` | `DUP-B-001` |
| `conflict_group_id` | `str` | `98` | `CON-B-001` |
| `source_sentence_id` | `str` | `0` | `SRC-EV-B-0001` |
| `progress_signal_for_activity_id` | `str` | `8` | `CIV-401` |
| `data_quality_tag` | `str` | `0` | `CLEAN` |
| `difficulty_level` | `str` | `0` | `EASY` |
| `expected_routing` | `str` | `0` | `AUTO_LINK_ELIGIBLE` |
| `has_identifier` | `bool` | `0` | `True` |
| `has_location` | `bool` | `0` | `True` |
| `has_discipline` | `bool` | `0` | `True` |
| `has_action` | `bool` | `0` | `True` |
| `has_status` | `bool` | `0` | `True` |
| `has_quantity` | `bool` | `0` | `False` |
| `has_date` | `bool` | `0` | `True` |
| `evidence_completeness_expected` | `int64` | `0` | `95` |
| `notes` | `str` | `90` | `Hidden-project ambiguity case.` |
| `synthetic_generator_version` | `str` | `0` | `v1.0` |
| `generated_date` | `datetime64[us]` | `0` | `2026-08-29 00:00:00` |
| `validation_status` | `str` | `0` | `PASS` |
| `synthetic_data_flag` | `bool` | `0` | `True` |


### File: `10_dataset_quality_report.md`
**Content Snippet**:
```markdown
# Site2Schedule AI — Synthetic Dataset Quality Report

**Scope:** SIH26122 prototype dataset for Site2Schedule AI.

> This dataset is entirely synthetic and was created for prototyping and evaluating Site2Schedule AI for SIH26122. It is not Oil India Limited data and must not be represented as real sponsor data.

## File Inventory

1. `01_baseline_schedule.xlsx` — PragatiSetu baseline schedule (75 activities).
2. `02_field_report_events.xlsx` — 400 labelled PragatiSetu field-report events.
3. `0...
```
