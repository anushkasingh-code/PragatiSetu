# PragatiSetu — Event Extraction Specification

> **IMPORTANT NOTICE**: The dataset supplied and processed in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

---

## 1. Overview
The Event Extraction module in **PragatiSetu** processes validated `SourceReport` records and converts unstructured/semi-structured field report text into structured `ExtractedEvent` records.

### Critical Scope Boundary: Extraction vs. Matching
- **Event Extraction** answers: **"What happened?"** (Extracts `identifier`, `action`, `object`, `location`, `status`, `percent_complete`, `quantity`, `unit`, `raw_text`, `source_position`).
- **Activity Matching** answers: **"Which baseline activity does this event refer to?"** (Explicitly deferred to later milestones).
- Event extraction does **NOT** assign Activity IDs, run vector embeddings, perform RapidFuzz matching, or calculate match confidence.

---

## 2. Ingestion-to-Extraction Workflow

```
VALIDATED SourceReport (TXT / CSV / XLSX)
        ↓
POST /reports/{report_id}/extract-events
        ↓
READ STORED RAW CONTENT / DATAFRAME
        ↓
TEXT SEGMENTATION (Multi-event splitting by sentences, semicolons, line breaks, conjunctions)
        ↓
FIELD EXTRACTORS (Status, Percent Complete, Identifiers, Actions, Objects, Locations, Quantities)
        ↓
PROVENANCE ATTACHMENT (raw_text, source_position, event_date_source, extraction_version="v1")
        ↓
STORE ExtractedEvent Records
        ↓
UPDATE SourceReport (processing_status = "EVENTS_EXTRACTED")
```

---

## 3. Extracted Event Schema

| Field Name | Type | Description |
| --- | --- | --- |
| `event_id` | `VARCHAR(50)` | Primary Key (e.g. `EVT-20260829-9A3F12BC`). |
| `report_id` | `VARCHAR(50)` | Foreign Key -> `source_reports.report_id`. |
| `raw_text` | `TEXT` | Exact original sentence/clause fragment (Evidence). |
| `event_date` | `DATE` | Explicit date if present, or inherited report date. |
| `event_date_source` | `VARCHAR(20)` | `EXPLICIT` vs `REPORT_DATE`. |
| `discipline` | `VARCHAR(100)` | Inherited report discipline or event-specific discipline. |
| `action` | `VARCHAR(150)` | Extracted action verb/phrase (e.g. `erection`, `concreting`). |
| `object` | `VARCHAR(150)` | Extracted target object (e.g. `spool`, `foundation`, `cable tray`). |
| `identifier` | `VARCHAR(100)` | Raw unnormalized tag (e.g. `24P201`, `EQ-ALPHA-101`, `F12`). |
| `location` | `VARCHAR(255)` | Raw unnormalized location phrase (e.g. `Rack B`, `Plot A`). |
| `status` | `VARCHAR(50)` | Status (`NOT_STARTED`, `STARTED`, `IN_PROGRESS`, `COMPLETED`, or `NULL`). |
| `percent_complete` | `FLOAT` | Explicit progress percentage (0.0 to 100.0) or `NULL`. |
| `quantity` | `FLOAT` | Explicit numeric quantity or `NULL`. |
| `unit` | `VARCHAR(50)` | Unit phrase (e.g. `meters`, `m`, `supports`) or `NULL`. |
| `source_position` | `JSON` | Provenance metadata (`{"type": "TXT_LINE", "line": 2, "clause_index": 1}`). |
| `extraction_method` | `VARCHAR(50)` | Method used (`RULE_BASED`, `STRUCTURED_COLUMN_MAPPING`). |
| `extraction_version` | `VARCHAR(20)` | Extraction engine version (e.g. `v1`). |
| `created_at` | `DATETIME` | Timestamp of extraction. |

---

## 4. Status Mapping Rules

Status is inferred strictly when evidence is present:
- `COMPLETED`: explicit `100%` or keywords `completed`, `complete`, `finished`, `done`.
- `IN_PROGRESS`: `0.0 < percent_complete < 100.0` or keywords `ongoing`, `in progress`, `continued`, `progressing`.
- `STARTED`: `commenced`, `started`, `began`, `initiated`.
- `NOT_STARTED`: explicit `0%` or keywords `not started`, `pending`.
- If no explicit status or percentage evidence is present: `status = NULL`.

---

## 5. API Endpoints

### 1. Extract Events from Report (`POST /reports/{report_id}/extract-events`)

**Response (`200 OK`)**:
```json
{
  "report_id": "REP-20260829-9A3F12BC",
  "processing_status": "EVENTS_EXTRACTED",
  "event_count": 2,
  "events": [
    {
      "event_id": "EVT-20260829-9A3F12BC-01",
      "report_id": "REP-20260829-9A3F12BC",
      "raw_text": "F12 reinforcement completed",
      "event_date": "2026-01-05",
      "event_date_source": "REPORT_DATE",
      "discipline": "Civil",
      "action": "reinforcement",
      "object": "foundation",
      "identifier": "F12",
      "location": null,
      "status": "COMPLETED",
      "percent_complete": 100.0,
      "quantity": null,
      "unit": null,
      "source_position": {
        "type": "TXT_LINE",
        "line": 1,
        "clause_index": 1
      },
      "extraction_method": "RULE_BASED",
      "extraction_version": "v1",
      "created_at": "2026-08-29T22:50:00Z"
    },
    {
      "event_id": "EVT-20260829-9A3F12BC-02",
      "report_id": "REP-20260829-9A3F12BC",
      "raw_text": "24P201 spool erection started near Rack B",
      "event_date": "2026-01-05",
      "event_date_source": "REPORT_DATE",
      "discipline": "Piping",
      "action": "erection",
      "object": "spool",
      "identifier": "24P201",
      "location": "Rack B",
      "status": "STARTED",
      "percent_complete": null,
      "quantity": null,
      "unit": null,
      "source_position": {
        "type": "TXT_LINE",
        "line": 1,
        "clause_index": 2
      },
      "extraction_method": "RULE_BASED",
      "extraction_version": "v1",
      "created_at": "2026-08-29T22:50:00Z"
    }
  ]
}
```

---

### 2. Retrieve Extracted Events (`GET /reports/{report_id}/events`)

**Response (`200 OK`)**: Returns array of `ExtractedEventResponse` objects.
