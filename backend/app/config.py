import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "PragatiSetu Backend"
    API_V1_STR: str = ""
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./site2schedule.db"
    UPLOAD_DIR: str = "uploads"
    AUDIO_UPLOAD_DIR: str = "uploads/audio"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_AUDIO_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    CORS_ORIGINS: str = "*"

    # Voice / STT Configuration
    VOICE_ENABLED: bool = True
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Matching & Safety Thresholds
    MATCH_SCORE_THRESHOLD: float = 85.0
    EVIDENCE_COMPLETENESS_THRESHOLD: float = 70.0
    TOP2_MARGIN_THRESHOLD: float = 12.0

    # Vector DB Configuration (ChromaDB)
    VECTOR_DB_DIR: str = "vector_store"
    VECTOR_COLLECTION_NAME: str = "pragatisetu_activities"

    # Optional Groq LLM Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
