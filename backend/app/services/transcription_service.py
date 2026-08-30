import time
import logging
from typing import Optional, Dict, Any
from backend.app.config import settings

logger = logging.getLogger("pragatisetu.transcription")

class TranscriptionService:
    _instance = None
    _model = None
    _engine_type = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranscriptionService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        """Initializes and caches the local CPU-first Whisper Speech-to-Text model once."""
        model_size = getattr(settings, "WHISPER_MODEL_SIZE", "tiny")
        device = getattr(settings, "WHISPER_DEVICE", "cpu")
        compute_type = getattr(settings, "WHISPER_COMPUTE_TYPE", "int8")

        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel  # type: ignore
            logger.info(f"Loading faster-whisper model '{model_size}' on {device} ({compute_type})...")
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self._engine_type = "faster-whisper"
            logger.info("faster-whisper model loaded successfully.")
            return
        except ImportError:
            logger.debug("faster-whisper package not installed. Attempting openai-whisper fallback...")
        except Exception as e:
            logger.warning(f"Failed to initialize faster-whisper model: {e}")

        # Try openai-whisper fallback
        try:
            import whisper  # type: ignore
            logger.info(f"Loading openai-whisper model '{model_size}' on {device}...")
            self._model = whisper.load_model(model_size, device=device)
            self._engine_type = "openai-whisper"
            logger.info("openai-whisper model loaded successfully.")
            return
        except ImportError:
            logger.debug("openai-whisper package not installed.")
        except Exception as e:
            logger.warning(f"Failed to initialize openai-whisper model: {e}")

        self._model = None
        self._engine_type = "UNAVAILABLE"
        logger.warning("No local Speech-to-Text engine available.")

    @property
    def is_available(self) -> bool:
        return self._model is not None

    @property
    def engine_type(self) -> str:
        return self._engine_type or "UNAVAILABLE"

    def transcribe_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribes a local audio file to text using the cached local STT model.
        Returns duration, language, transcript, processing time, and model info.
        """
        if not self.is_available:
            raise RuntimeError("Local Speech-to-Text engine is unavailable in current environment.")
        assert self._model is not None

        start_time = time.time()

        if self._engine_type == "faster-whisper":
            segments, info = self._model.transcribe(file_path, beam_size=5, language="en")
            segment_list = list(segments)
            transcript_text = " ".join([s.text.strip() for s in segment_list if s.text]).strip()
            duration_seconds = round(float(info.duration), 2) if hasattr(info, "duration") else None
            detected_lang = getattr(info, "language", "en")

        elif self._engine_type == "openai-whisper":
            result = self._model.transcribe(file_path, language="en")
            transcript_text = (result.get("text") or "").strip()
            duration_seconds = None
            detected_lang = result.get("language", "en")

        else:
            raise RuntimeError("Unsupported STT engine type.")

        processing_time_ms = int((time.time() - start_time) * 1000)

        if not transcript_text:
            raise ValueError("No speech detected in audio file.")

        return {
            "transcript": transcript_text,
            "language": detected_lang,
            "duration_seconds": duration_seconds,
            "model": f"{self._engine_type}:{getattr(settings, 'WHISPER_MODEL_SIZE', 'tiny')}",
            "processing_time_ms": processing_time_ms
        }
