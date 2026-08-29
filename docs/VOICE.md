# PragatiSetu — Voice Input & Speech-To-Text Architecture

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

This specification documents the local, CPU-first voice input and speech-to-text (STT) transcription architecture implemented in **PragatiSetu**.

---

## 1. Core Principle — Voice as an Input Modality

In PragatiSetu, voice is strictly an **INPUT MODALITY**. It is **NOT** a separate reasoning system or matching engine.

```
VOICE AUDIO (.wav, .mp3, .m4a, .webm, .ogg)
                  ↓
SAFE AUDIO VALIDATOR (Format, Size Limit 10MB, Path Traversal Sanitization)
                  ↓
LOCAL CPU SPEECH-TO-TEXT (faster-whisper / whisper 'tiny')
                  ↓
SPOKEN TRANSCRIPT (Preserved separately from normalized fields)
                  ↓
EXISTING TEXT EVENT EXTRACTION ENGINE (EventExtractionService)
                  ↓
EXTRACTED EVENT
                  ↓
NORMALIZATION ENGINE (NormalizerService)
                  ↓
CANDIDATE GENERATOR & EMBEDDINGS (CandidateGeneratorService)
                  ↓
SAFETY DECISION POLICY ROUTER (85/70/12 Threshold Engine)
                  ↓
HUMAN PLANNER REVIEW (ACCEPT / SWITCH / REJECT / UNPLANNED)
                  ↓
STATE VALIDATION & ATOMIC PROGRESS UPDATE (ProgressUpdateService)
                  ↓
IMMUTABLE AUDIT TRAIL RECORD (AuditRecord)
```

---

## 2. Local CPU-First Speech-To-Text Engine
- **Engine**: `faster-whisper` (fallback to `openai-whisper` if installed)
- **Model Size**: `tiny` (configurable via `WHISPER_MODEL_SIZE` in `.env` / `config.py`)
- **Execution Device**: `cpu` (configurable via `WHISPER_DEVICE`)
- **Quantization / Compute Type**: `int8`
- **Singleton Caching**: Model is loaded **ONCE** on startup via `TranscriptionService` singleton and cached in memory across requests.
- **Zero Cloud Dependencies**: Operates 100% offline without requiring OpenAI API keys, Google Cloud Speech, or Azure Speech.

---

## 3. Audio Upload Safety & Validation
- **Supported Audio Formats**: `.wav`, `.mp3`, `.m4a`, `.webm`, `.ogg`, `.flac`
- **Maximum File Size**: 10 MB limit (`MAX_AUDIO_SIZE_BYTES`)
- **Path Traversal Protection**: Filenames sanitized using `os.path.basename` and removing `../` path components.
- **Temporary Storage**: Files saved temporarily under `uploads/audio/{hash[:12]}_{clean_name}` and deleted immediately after transcription completes.

---

## 4. REST API Contract

### 1. Upload & Transcribe Audio
`POST /voice/transcribe`
- **Content-Type**: `multipart/form-data`
- **Form Data**: `file` (Audio file), `project_id` (optional)
- **Response (`201 Created`)**:
  ```json
  {
    "transcription_id": "TRX-A1B2C3D4",
    "filename": "field_update.wav",
    "transcript": "24P201 spool erection commenced near Rack B",
    "language": "en",
    "duration_seconds": 3.5,
    "model": "faster-whisper:tiny",
    "processing_time_ms": 320,
    "status": "COMPLETED",
    "error_message": null,
    "created_at": "2026-08-29T23:42:00"
  }
  ```

### 2. Retrieve Transcription Details
`GET /transcriptions/{transcription_id}`

### 3. Human Transcript Correction
`PATCH /transcriptions/{transcription_id}`
- **Request Body**: `{"transcript": "24P201 spool erection commenced near Rack B."}`
- **Response (`200 OK`)**: Updated `TranscriptionResponse`.

### 4. Process Voice Transcript to Events
`POST /transcriptions/{transcription_id}/process` or `POST /voice/process`
- **Response (`200 OK`)**: Feeds transcript into `EventExtractionService`, returning extracted events ready for candidate matching and safety routing.

---

## 5. Safety & Immutability Guarantees
1. **Zero Direct Schedule Mutation**: Voice transcription itself **NEVER** modifies `ScheduleActivity`.
2. **Transcript Preservation**: Raw spoken transcript text is preserved side-by-side with normalized entity tags.
3. **Authoritative Safety Router**: All progress updates must pass through state validation and the 85/70/12 decision policy router.
