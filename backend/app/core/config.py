"""Application configuration module using pydantic-settings."""

from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global system configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "AI Document Intelligence System"
    API_V1_PREFIX: str = "/api/v1"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Security & Keys
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")

    # Databases
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/docintel",
        description="Async SQLAlchemy database connection URI",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URI for Celery and caching",
    )

    # Ingestion & Storage
    MAX_UPLOAD_MB: int = Field(default=50, description="Max allowed file upload size in MB")
    UPLOAD_DIR: str = Field(default="uploads", description="Directory to store uploaded documents")

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Validation Engine Thresholds
    MATH_TOLERANCE: Decimal = Decimal("0.01")
    CONFIDENCE_THRESHOLD: float = 0.70
    OCR_FALLBACK_CHAR_THRESHOLD: int = 30


settings = Settings()
