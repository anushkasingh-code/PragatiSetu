# PragatiSetu — REST API Documentation

> **NOTICE**: Synthetic prototype dataset — not real Oil India Limited data.

## Base URL
Default local development base URL: `http://127.0.0.1:8000`

Interactive OpenAPI / Swagger UI: `http://127.0.0.1:8000/docs`

---

## Endpoints Summary

### 1. Health Check
`GET /health`

---

### 2. List Projects
`GET /projects`

---

### 3. Create Project
`POST /projects`

---

### 4. Get Project Details
`GET /projects/{project_id}`

---

### 5. Upload Baseline Schedule Excel
`POST /projects/{project_id}/schedule/upload`

---

### 6. Get Project WBS Hierarchy
`GET /projects/{project_id}/wbs`

---

### 7. Get Project Activities
`GET /projects/{project_id}/activities`

---

### 8. Get Activity Details
`GET /activities/{activity_id}`

---

### 9. Upload Field Progress Report
`POST /reports/upload`

---

### 10. Get Report Details
`GET /reports/{report_id}`

---

### 11. Get Project Reports
`GET /projects/{project_id}/reports`

---

### 12. Extract Events from Report
`POST /reports/{report_id}/extract-events` & `POST /reports/{report_id}/extract`

---

### 13. Retrieve Extracted Events
`GET /reports/{report_id}/events`

---

### 14. Normalize Extracted Event
`POST /events/{event_id}/normalize`

---

### 15. Generate Candidate Shortlist
`POST /events/{event_id}/candidates`

---

### 16. Retrieve Event Candidates
`GET /events/{event_id}/candidates`

---

### 17. Evaluate Event Safety Decision / Match
`POST /events/{event_id}/decision` & `POST /events/{event_id}/match`

---

### 18. Submit Human Review Decision
`POST /reviews/{event_id}/decision`

---

### 19. Apply Event Schedule Progress
`POST /events/{event_id}/apply`

---

### 20. Retrieve Activity Audit Trail
`GET /activities/{activity_id}/audit`

---

### 21. Query Global & Filtered Audit Logs
`GET /audit`

---

### 22. Get Project Timeline (Gantt Data)
`GET /projects/{project_id}/timeline`

---

### 23. Get Project Dashboard Metrics
`GET /projects/{project_id}/dashboard`

---

### 24. Upload & Transcribe Spoken Voice Audio
`POST /voice/transcribe`

**Description**: Uploads a spoken voice audio file (.wav, .mp3, .m4a, .webm, .ogg), validates format and size (max 10MB limit), runs local CPU-first Speech-to-Text (Whisper), records `Transcription` DB provenance, and returns transcript.

---

### 25. Retrieve Transcription Details
`GET /transcriptions/{transcription_id}`

---

### 26. Edit / Correct Spoken Transcript
`PATCH /transcriptions/{transcription_id}`

---

### 27. Process Voice Transcript to Events
`POST /transcriptions/{transcription_id}/process` & `POST /voice/process`

**Description**: Submits a completed voice transcript into the existing text event extraction pipeline, creating extracted events and candidate match decisions without directly mutating the schedule.

---

### 28. Get System Metrics
`GET /metrics`
