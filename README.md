# Pragati Setu

### Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management

> **Smart India Hackathon 2026 — SIH26122**

An AI-powered system that bridges the gap between **planned project schedules** and **actual site execution** by automatically converting unstructured field updates into structured project activities and intelligently mapping them to the correct **L5/L6 schedule activities**.

---

## 📌 Problem Statement

Large infrastructure projects are typically planned and monitored using structured project-management tools such as **Primavera P6** and **Microsoft Project**.

However, actual site progress is often reported through:

- Daily Progress Reports (DPRs)
- Site diaries
- Excel spreadsheets
- PDFs
- Free-text updates
- Supervisor observations
- Voice-based updates

The language and level of detail used in these reports often differ significantly from the terminology and structure used in the official project schedule.

### Example

#### Planned Schedule

```text
Activity ID: PIP-204-017
Activity: Erect 24-inch Pipeline Section A
Discipline: Piping
Planned Start: 12-Aug-2026
Planned Finish: 17-Aug-2026
```

#### Site Report

```text
"24 inch line spool erection completed today."
```

The site report does not explicitly mention the Activity ID.

The challenge is to automatically understand the field update and determine which planned **L5/L6 activity** it corresponds to.

---

# 💡 Our Solution

We propose an **AI-powered Planning-to-Execution Bridge** that transforms unstructured site information into structured, schedule-linked project updates.

```text
                    ┌──────────────────────┐
                    │   Project Schedule   │
                    │ Primavera / MS       │
                    │ Project / Excel      │
                    └──────────┬───────────┘
                               │
                               ▼
                     ┌─────────────────┐
                     │ Schedule Parser │
                     └────────┬────────┘
                              │
                              ▼
                    L5/L6 Activity Database
                              │
                              │
                              │
┌─────────────────┐           │
│   Site Reports  │           │
│ PDF / Excel     │           │
│ Text / Voice    │           │
└────────┬────────┘           │
         │                    │
         ▼                    │
┌─────────────────┐           │
│ Data Extraction │           │
│      LLM        │           │
└────────┬────────┘           │
         │                    │
         ▼                    │
┌─────────────────────────────┐
│ Structured Execution Event  │
└──────────────┬──────────────┘
               │
               ▼
       Semantic Retrieval
          + Embeddings
               │
               ▼
      Top Candidate Activities
               │
               ▼
       Validation & Reranking
               │
               ▼
        Confidence Scoring
          ┌────┴────┐
          │         │
       High       Low
          │         │
          ▼         ▼
     Auto Update  Human Review
          │         │
          └────┬────┘
               ▼
        Updated Project View
               │
               ▼
       Gantt / Progress / Alerts
```

---

# 🎯 Objectives

The system aims to:

1. Automatically extract meaningful execution events from field reports.
2. Understand construction and infrastructure terminology.
3. Map field observations to the correct L5/L6 schedule activities.
4. Handle differences in terminology and granularity.
5. Assign confidence scores to AI-generated mappings.
6. Route ambiguous cases to human reviewers.
7. Maintain an auditable history of every AI-generated update.
8. Reduce manual effort involved in progress tracking.
9. Provide near-real-time visibility of project execution against the plan.

---

# 🧠 Key Concept: L5 and L6 Activities

Infrastructure projects use hierarchical **Work Breakdown Structures (WBS)**.

A simplified structure may look like:

```text
Project
│
├── Pipeline Construction
│   │
│   ├── Section A
│   │   │
│   │   └── Pipeline Installation
│   │       │
│   │       ├── L5: Install 24-inch Pipeline
│   │       │    │
│   │       │    ├── L6: Spool P-204-07
│   │       │    ├── L6: Spool P-204-08
│   │       │    └── L6: Spool P-204-09
│   │       │
│   │       └── L5: Pipeline Welding
│   │            │
│   │            ├── L6: Joint 101
│   │            ├── L6: Joint 102
│   │            └── L6: Joint 103
```

The system's primary task is to connect a field observation to the appropriate scheduled activity.

---

# 🔍 Example Workflow

### Input

A supervisor submits:

```text
"Spool P204-07 erection completed today.
Welding for Section B started."
```

### Step 1 — Information Extraction

The LLM converts the report into structured events:

```json
[
  {
    "equipment": "P204-07",
    "activity": "spool erection",
    "status": "COMPLETED",
    "date": "2026-08-30"
  },
  {
    "section": "B",
    "activity": "welding",
    "status": "STARTED",
    "date": "2026-08-30"
  }
]
```

### Step 2 — Semantic Retrieval

The system searches the schedule for matching activities.

```text
Candidate Activities

1. PIP-204-017
   Spool P204-07 Erection
   Similarity: 0.95

2. PIP-204-021
   Spool P204-08 Erection
   Similarity: 0.71

3. PIP-204-025
   Section B Welding
   Similarity: 0.68
```

### Step 3 — Validation

The system evaluates:

- Activity description
- Equipment/asset identifiers
- Discipline
- WBS context
- Date compatibility
- Location/section
- Semantic similarity

### Step 4 — Confidence Decision

```text
Confidence: 95%
Status: HIGH CONFIDENCE
Action: Auto-update
```

For an ambiguous case:

```text
Confidence: 61%
Status: LOW CONFIDENCE
Action: Human Review Required
```

---

# 🏗️ System Architecture

## 1. Data Ingestion Layer

Supports multiple sources:

```text
PDF
Excel
CSV
Text
Site Diary
Voice
```

The ingestion layer converts these inputs into a common internal representation.

---

## 2. Schedule Processing

Project schedules are converted into structured activity records.

Example:

```json
{
  "activity_id": "PIP-204-017",
  "wbs_level": "L6",
  "activity_name": "Erect 24-inch Pipeline Section A",
  "discipline": "Piping",
  "planned_start": "2026-08-12",
  "planned_finish": "2026-08-17"
}
```

---

## 3. AI Information Extraction

An LLM extracts:

- Activity/event
- Equipment
- Location
- Discipline
- Status
- Progress
- Dates
- Quantities
- Remarks

The model produces structured output rather than directly modifying the schedule.

---

## 4. Semantic Matching

The extracted event is converted into an embedding.

The system then searches the schedule activity database for semantically similar activities.

```text
Field Update
     │
     ▼
Embedding
     │
     ▼
Vector Search
     │
     ▼
Top-K Activities
```

This allows the system to handle different wording.

### Example

```text
"24 inch line erection completed"

                ≈

"Erect 24-inch Pipeline Section A"
```

even though the wording is not identical.

---

## 5. Context-Aware Validation

Semantic similarity alone is not sufficient.

The system combines:

```text
Semantic Similarity
        +
Equipment ID
        +
Discipline
        +
Location
        +
WBS Context
        +
Date
        +
Schedule Dependencies
```

to improve matching reliability.

---

## 6. Confidence & Human-in-the-Loop

The system never blindly trusts AI output.

### High Confidence

```text
Confidence ≥ Threshold

        ↓

Automatic Update
```

### Low Confidence

```text
Confidence < Threshold

        ↓

Human Review Queue
```

The reviewer can:

- Approve
- Reject
- Select another activity
- Mark as unmatched

---

# 🛡️ Safety & Reliability

A core design principle is:

> **The AI must never invent a schedule activity.**

The system can only:

1. Match against existing schedule activities.
2. Mark an event as unmatched.
3. Request human intervention.

This prevents hallucinated Activity IDs and incorrect schedule modifications.

---

# 🔄 Handling Difficult Cases

## Similar Activities

```text
Install Pump P-204
Install Pump P-205
Install Pump P-206
```

If the report only says:

> "Pump installation completed."

The system should not guess.

Instead:

```text
⚠️ Ambiguous Match

Multiple possible activities found.

Human Review Required.
```

---

## Unmatched Activity

If a report contains:

> "Temporary access road constructed."

but no corresponding schedule activity exists:

```text
⚠️ No Matching Activity

Event:
Temporary access road construction

Action:
Planner Review
```

---

## Conflicting Reports

If two reports provide contradictory information:

```text
Supervisor A:
Welding completed.

Supervisor B:
Welding 80% complete.
```

the system flags:

```text
⚠️ Conflicting Progress Reports

Human verification required.
```

---

# 📊 Proposed Technology Stack

| Component | Technology |
|---|---|
| Frontend | React / Next.js |
| Backend | Python / FastAPI |
| LLM | Gemini / GPT-class API |
| Embeddings | BGE-M3 |
| Vector Search | FAISS |
| Database | PostgreSQL |
| Document Processing | Python |
| OCR | PaddleOCR / Tesseract |
| Speech-to-Text | Whisper |
| Visualization | Gantt / Timeline UI |
| Deployment | Docker |

> The exact model/provider can be changed depending on API availability, latency, cost and deployment requirements.

---

# 📁 Dataset Strategy

The prototype dataset will consist of three primary components.

## Schedule Dataset

```text
activity_id
wbs_level
activity_name
discipline
location
equipment
planned_start
planned_finish
dependencies
```

## Field Report Dataset

```text
report_id
report_date
supervisor
discipline
raw_text
source
```

## Ground Truth Dataset

```text
report_id
expected_activity_id
event_type
status
confidence_label
```

---

# 🧪 Evaluation

The system will be evaluated using labelled field-report/activity pairs.

## Activity Matching

- Top-1 Accuracy
- Top-3 Accuracy
- Precision
- Recall
- F1 Score

## Information Extraction

Evaluate extraction of:

- Activity
- Equipment
- Status
- Date
- Progress
- Location

## Safety Metrics

Measure:

- False Matches
- Unmatched Detection
- Human Review Rate
- Incorrect Auto-Updates

A key objective is to **minimize false activity mappings**, because an incorrect schedule update can be more harmful than requesting human review.

---

# 📈 Expected Benefits

The proposed system can help project teams:

- Reduce manual progress-entry effort.
- Improve schedule-to-execution visibility.
- Reduce delays between site reporting and schedule updates.
- Identify unmatched or unexpected work.
- Detect conflicting progress information.
- Improve data consistency.
- Provide an auditable AI-assisted workflow.
- Enable project managers to focus on exceptions instead of routine data entry.

---

# 👥 Human-in-the-Loop Design

The system is designed as an **AI assistant**, not an autonomous project manager.

```text
             AI
              │
              ▼
      Recommendation
              │
              ▼
      Confidence Score
              │
        ┌─────┴─────┐
        │           │
      Clear      Ambiguous
        │           │
        ▼           ▼
    Auto/Quick    Human
     Approval     Review
        │           │
        └─────┬─────┘
              ▼
       Schedule Update
```

This provides both automation and human control.

---

# 🚀 MVP Scope

The initial prototype focuses on the most important workflow:

```text
Excel Schedule
      +
Text Field Report
      ↓
AI Extraction
      ↓
Semantic Activity Matching
      ↓
Confidence Score
      ↓
Human Approval
      ↓
Updated Gantt / Progress View
```

### Phase 2

- PDF processing
- OCR
- Voice input
- Multilingual reports
- Advanced progress estimation
- Conflict detection
- Historical analytics

### Phase 3

- Primavera/MS Project integration
- Enterprise PMIS integration
- Real-time notifications
- Project-level analytics
- Continuous terminology learning

---

# 🗺️ Future Scope

The platform can be extended into a broader infrastructure execution intelligence system.

Potential capabilities include:

- Delay-risk detection
- Progress forecasting
- Automated daily progress summaries
- Contractor performance analytics
- Resource bottleneck detection
- Schedule variance analysis
- Automated management reports
- Multi-project portfolio monitoring
- Conversational project queries

### Example

> **"Which activities are behind schedule in Section B?"**

The system could respond using the latest validated project data.

---

# 🔐 Design Principles

### 1. AI-Assisted, Human-Controlled

AI recommends; humans retain authority over important schedule changes.

### 2. Evidence-Based Updates

Every AI-generated update should be traceable to its source report.

### 3. No Hallucinated Activities

The AI cannot create arbitrary schedule IDs.

### 4. Confidence-Aware Automation

Only sufficiently reliable matches should be automatically processed.

### 5. Auditable

Every mapping and modification should have:

```text
Source
Timestamp
Activity ID
AI Decision
Confidence
Reviewer
Final Action
```

---

# 🎯 Project Vision

> **Bridge the gap between what the project schedule says should happen and what the site reports actually say happened.**

Our goal is to transform project monitoring from:

```text
Site Report
     ↓
Manual Reading
     ↓
Manual Mapping
     ↓
Manual Schedule Update
     ↓
Delayed Visibility
```

into:

```text
Site Report
     ↓
AI Understanding
     ↓
Semantic Schedule Matching
     ↓
Confidence Validation
     ↓
Human Approval
     ↓
Near-Real-Time Project Visibility
```

---

# 🏆 Smart India Hackathon 2026

| Detail | Information |
|---|---|
| Problem Statement | **SIH26122** |
| Theme | **Smart Automation** |
| Category | **Software** |
| Organization | **Oil India Limited** |

---

# 📜 Disclaimer

This repository contains a prototype implementation developed for **Smart India Hackathon 2026**.

Demonstration datasets may be synthetic and are intended to reproduce the structure and challenges of real infrastructure project-management data.

The prototype should not be considered a replacement for official project-management systems or professional project controls without appropriate validation, security controls and enterprise integration.

---

# ⭐ Key Takeaway

**SIH26122 is not simply an AI chatbot.**

The core innovation is the reliable transformation:

```text
Unstructured Site Information
             ↓
      Structured Events
             ↓
     L5/L6 Schedule Mapping
             ↓
      Confidence Validation
             ↓
       Human Approval
             ↓
       Schedule Update
```

The primary objective is to create a trustworthy **Planning-to-Execution Bridge** for large infrastructure projects.

---

## 📌 Built for Smart India Hackathon 2026

**SIH26122 · Oil India Limited · Smart Automation**
