import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "PragatiSetu Backend"
    API_V1_STR: str = ""
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./site2schedule.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    AUDIO_UPLOAD_DIR: str = os.getenv("AUDIO_UPLOAD_DIR", "uploads/audio")
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_AUDIO_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # Voice / STT Configuration
    VOICE_ENABLED: bool = True
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "tiny")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # Matching & Safety Thresholds
    MATCH_SCORE_THRESHOLD: float = float(os.getenv("MATCH_SCORE_THRESHOLD", "85.0"))
    EVIDENCE_COMPLETENESS_THRESHOLD: float = float(os.getenv("EVIDENCE_COMPLETENESS_THRESHOLD", "70.0"))
    TOP2_MARGIN_THRESHOLD: float = float(os.getenv("TOP2_MARGIN_THRESHOLD", "12.0"))

    # Vector DB Configuration (ChromaDB)
    VECTOR_DB_DIR: str = os.getenv("VECTOR_DB_DIR", "vector_store")
    VECTOR_COLLECTION_NAME: str = os.getenv("VECTOR_COLLECTION_NAME", "pragatisetu_activities")

    # Optional Groq LLM Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_ENABLED: bool = os.getenv("GROQ_ENABLED", "false").lower() in ("true", "1", "yes")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
