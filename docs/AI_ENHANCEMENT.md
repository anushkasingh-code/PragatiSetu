# PragatiSetu — AI Enhancement Documentation
## Local Vector Search (ChromaDB) & Grounded LLM Reasoning (Groq)

---

## 1. Overview & Architectural Role

PragatiSetu incorporates an isolated, optional **AI Enhancement Layer** designed strictly for:
1. **Semantic Search & Candidate Retrieval** across baseline schedule activities using local Vector DB (ChromaDB).
2. **Reviewer Assistance & Natural-Language Explanations** using an optional, grounded Groq LLM layer.

### Critical Safety Invariant
The AI Enhancement Layer is **strictly informational**. It operates alongside the core deterministic matching engine and **never** has authority to:
- Mutate baseline schedules, actual dates, or progress percentages.
- Make schedule update decisions (`AUTO_LINK`, `HUMAN_REVIEW`, `UNPLANNED_REVIEW`, `CONFLICT_REVIEW`, `IGNORE`).
- Create `AuditRecord` entries.
- Override or bypass the deterministic matching pipeline.

```
                 EXISTING AUTHORITATIVE BACKEND
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   Deterministic Pipeline                AI Enhancement Layer
   (Parser → RapidFuzz → Matcher         (ChromaDB + Groq)
    → Safety Gate → Schedule Update)               │
            │                                      ▼
            ▼                               INFORMATIONAL
     Schedule Mutation                       ASSISTANCE
     & Immutable Audit                      (Search & RAG)
```

---

## 2. Vector Database Architecture (ChromaDB)

- **Vector Database Engine:** ChromaDB (`PersistentClient` / `EphemeralClient` fallback).
- **Storage Location:** Configurable via `VECTOR_DB_DIR` (default: `./vector_store`).
- **Collection Name:** Configurable via `VECTOR_COLLECTION_NAME` (default: `pragatisetu_activities`).
- **Indexed Entity:** Baseline `ScheduleActivity` database records.
- **Embedding Pipeline:** Reuses PragatiSetu's existing `sentence-transformers` CPU model (`all-MiniLM-L6-v2`) via `PragatiSetuEmbeddingAdapter`.
- **Offline / Model-Free Fallback:** Deterministic 384-dimensional normalized pseudo-embeddings ensure 100% offline functionality without internet or GPU requirements.

### Searchable Document Representation
Each activity is compiled into a comprehensive text representation containing:
```
Activity ID: PIP-202 | Discipline: Piping | Description: Spool erection for line 24P201 | Location: Rack B | Identifier: 24P201 | Status: NOT_STARTED
```

### Metadata Stored Alongside Vectors
- `activity_id`: Primary activity identifier (e.g. `PIP-202`)
- `project_id`: Project identifier (e.g. `PROJ-ALPHA`)
- `discipline`: Engineering discipline (e.g. `Piping`, `Civil`)
- `identifier`: Equipment or line tag (e.g. `24P201`)
- `location`: Site location / zone (e.g. `Rack B`)
- `status`: Current baseline status
- `description`: Activity description summary

### Project Boundary Isolation
All vector retrieval queries strictly enforce project boundary filtering:
```python
collection.query(
    query_texts=[query],
    n_results=top_k,
    where={"project_id": project_id}
)
```
Activities from `PROJ-ALPHA` are never returned for `PROJ-BETA` queries.

---

## 3. Groq LLM Integration & Grounded RAG

Groq is integrated as an **optional** external provider for fast LLM inference.

### Configuration
```bash
GROQ_ENABLED=false
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### Grounding & Hallucination Protection
1. **RAG-Only Context:** Only the top-$K$ candidate activities retrieved from the Vector DB for the specific `project_id` are passed to Groq.
2. **Candidate ID Whitelist Verification:** Any activity ID generated in the Groq response is cross-checked against the retrieved candidate set. If Groq outputs an unknown or hallucinated activity ID, it is stripped from `grounded_candidates` and recorded in `warnings`.
3. **Structured JSON Validation:** Groq responses are validated using Pydantic models. Malformed responses fall back gracefully.

---

## 4. API Endpoints

### 4.1 Index Activities (`POST /ai/index`)
Populates or updates the local Vector DB from database `ScheduleActivity` records.

**Request:**
```json
{
  "project_id": "PROJ-ALPHA",
  "force_reindex": false
}
```

**Response (`200 OK`):**
```json
{
  "indexed_count": 75,
  "project_id": "PROJ-ALPHA",
  "status": "SUCCESS",
  "message": "Successfully indexed 75 schedule activities into Vector DB."
}
```

---

### 4.2 Semantic Search (`POST /ai/search`)
Performs semantic vector search across indexed activities within a project.

**Request:**
```json
{
  "project_id": "PROJ-ALPHA",
  "query": "spool erection line 24P201 near Rack B",
  "top_k": 3
}
```

**Response (`200 OK`):**
```json
{
  "query": "spool erection line 24P201 near Rack B",
  "project_id": "PROJ-ALPHA",
  "count": 3,
  "results": [
    {
      "activity_id": "PIP-204",
      "project_id": "PROJ-ALPHA",
      "similarity": 0.8842,
      "document": "Activity ID: PIP-204 | Discipline: Piping | Description: Erect spools 24-P-201 at Rack B | Location: Rack B | Identifier: 24-P-201 | Status: NOT_STARTED",
      "metadata": {
        "activity_id": "PIP-204",
        "project_id": "PROJ-ALPHA",
        "discipline": "Piping",
        "identifier": "24-P-201",
        "location": "Rack B",
        "status": "NOT_STARTED"
      }
    }
  ]
}
```

---

### 4.3 Grounded Explanation (`POST /ai/explain`)
Generates natural-language reasoning and candidate validation using Vector retrieval + Groq LLM.

**Request:**
```json
{
  "project_id": "PROJ-ALPHA",
  "query": "Foundation F12 concreting completed today",
  "top_k": 3
}
```

**Response (`200 OK`):**
```json
{
  "available": true,
  "summary": "The field report indicates concrete pouring completion for foundation F12, matching civil baseline activity CIV-107.",
  "grounded_candidates": ["CIV-107"],
  "reasoning": [
    "Identifier 'F12' matches foundation equipment tag in CIV-107.",
    "Discipline 'Civil' matches baseline activity schedule.",
    "Action 'concreting' matches RCC foundation work description."
  ],
  "warnings": [],
  "retrieved_context": [
    {
      "activity_id": "CIV-107",
      "project_id": "PROJ-ALPHA",
      "similarity": 0.8921,
      "document": "Activity ID: CIV-107 | Discipline: Civil | Description: RCC foundation concreting for F12 | Location: Plot A | Identifier: F12 | Status: NOT_STARTED",
      "metadata": {
        "activity_id": "CIV-107",
        "project_id": "PROJ-ALPHA",
        "discipline": "Civil",
        "identifier": "F12"
      }
    }
  ]
}
```

---

## 5. Offline & Failure Modes

| Scenario | Behavior |
|---|---|
| **No Internet / Offline** | Core backend & Vector DB function normally. Groq explanation returns `available: false` with vector search context. |
| **`GROQ_API_KEY` Missing** | App starts normally. `/ai/explain` returns `available: false` with graceful fallback context and notice. |
| **Groq Network Timeout** | Caught safely by exception handler. Returns `available: false` with warnings; zero backend crashes. |
| **Empty / Unindexed DB** | `/ai/search` returns `count: 0, results: []` gracefully. |

---

## 6. Security Guarantees

- **No Hardcoded Secrets:** `GROQ_API_KEY` is read strictly from environment variables.
- **Zero Secret Leakage:** API keys are never logged, persisted in vector metadata, or returned in API responses.
- **Filesystem Safety:** Vector DB storage directory is contained and ignored by Git (`vector_store/`).
