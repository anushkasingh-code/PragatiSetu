# PragatiSetu — State Progress Update & Audit Trail Specification

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

---

## 1. Overview
The State Validation, Actual Progress Update, Conflict Detection, and Audit Trail module in **PragatiSetu** consumes accepted `MatchDecision` records (specifically `AUTO_LINK` or approved decisions) and safely updates baseline schedule actuals while preserving complete historical audit traceability.

---

## 2. Core Safety Rule: Immutable Planned Schedule Baseline

> [!IMPORTANT]
> Baseline planned schedule dates (`planned_start`, `planned_finish`) are **IMMUTABLE** and **MUST NEVER BE OVERWRITTEN** by actual field updates (`actual_start`, `actual_finish`).
> Actual progress modifies ONLY:
> - `actual_start`
> - `actual_finish`
> - `percent_complete`
> - `status`

---

## 3. Controlled Schedule Statuses & Valid Transitions

Controlled Python Enum (`ActivityStatusEnum`):
- `NOT_STARTED`
- `STARTED`
- `IN_PROGRESS`
- `COMPLETED`
- `REWORK`

### Valid Transition Matrix
- `NOT_STARTED` $\rightarrow$ `STARTED`, `IN_PROGRESS`, `COMPLETED`
- `STARTED` $\rightarrow$ `IN_PROGRESS`, `COMPLETED`
- `IN_PROGRESS` $\rightarrow$ `COMPLETED`
- `COMPLETED` $\rightarrow$ `REWORK`
- `REWORK` $\rightarrow$ `IN_PROGRESS`, `COMPLETED`

---

## 4. Progress Update Rules

- **`STARTED`**: Sets `actual_start = event_date` if `actual_start` is `NULL` (preserves existing `actual_start`). Sets status to `STARTED` or `IN_PROGRESS`.
- **`IN_PROGRESS`**: Updates `percent_complete` ONLY when explicit percentage is reported. Does **NOT** invent percentages.
- **`COMPLETED`**: Sets `percent_complete = 100.0` and `actual_finish = event_date`.
- **`REWORK`**: Handles valid `COMPLETED` $\rightarrow$ `REWORK` transitions without corrupting schedule history.

---

## 5. Conflict Detection & Dependency Warnings

- **Conflict Detection**: Flags conflicts if a new event contradicts existing accepted schedule state (e.g. activity is `COMPLETED` 100%, new event reports `IN_PROGRESS` 60% $\rightarrow$ flags `STATUS_CONFLICT`, preserves schedule state).
- **Dependency Warnings**: If a successor is finished before its mandatory predecessor, emits `DEPENDENCY_WARNING` without automatic rejection.

---

## 6. Atomic Database Transactions & Immutable Audit Trail

Schedule updates, `AuditRecord` creation, and event processing status updates (`APPLIED`) are executed in an **ATOMIC DATABASE TRANSACTION**.
- If any step fails $\rightarrow$ complete transaction rollback occurs!
- **`AuditRecord`** stores JSON snapshots of BEFORE (`previous_value`) and AFTER (`new_value`) state:

```json
{
  "audit_id": "AUD-9A3F12BC",
  "activity_id": "ACT-ALPHA-020",
  "event_id": "EVT-20260829-9A3F12BC-01",
  "previous_value": {
    "status": "IN_PROGRESS",
    "percent_complete": 60.0,
    "actual_start": "2026-01-01",
    "actual_finish": null
  },
  "new_value": {
    "status": "COMPLETED",
    "percent_complete": 100.0,
    "actual_start": "2026-01-01",
    "actual_finish": "2026-01-05"
  },
  "system_decision": "AUTO_LINK",
  "confidence": 94.25,
  "reason": "Applied progress update from event 'EVT-20260829-9A3F12BC-01'. Status: COMPLETED, Progress: 100.0%.",
  "matcher_version": "v1",
  "scoring_policy_version": "v1"
}
```

---

## 7. REST APIs

- `POST /events/{event_id}/apply`: Applies accepted decision, executes atomic progress update, creates `AuditRecord`, and returns structured status.
- `GET /activities/{activity_id}/audit`: Retrieves historical audit trail records for an activity.
