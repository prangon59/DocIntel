"""Application configuration module using pydantic-settings."""

from decimal import Decimal

from pydantic import Field, model_validator
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
    LLM_MODEL: str = Field(default="gemini-3.5-flash", description="Primary LLM model name")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash", description="Gemini model name")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001", description="Embedding model name")
    EMBEDDING_DIMENSIONS: int = Field(default=768, description="Dimensions for vector embeddings")
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, description="Timeout for LLM API calls")
    LLM_MAX_REQUESTS_PER_MINUTE: int = Field(
        default=10, description="Max requests per minute allowed to LLM"
    )
    LLM_CONCURRENCY_LIMIT: int = Field(
        default=2, description="Maximum concurrent active requests to LLM"
    )
    LLM_CACHE_DIR: str = Field(
        default="eval/.cache", description="Directory to cache LLM responses"
    )

    @model_validator(mode="after")
    def sync_model_names(self) -> "Settings":
        if self.LLM_MODEL and self.LLM_MODEL != "gemini-3.5-flash" and self.GEMINI_MODEL == "gemini-3.5-flash":
            self.GEMINI_MODEL = self.LLM_MODEL
        elif self.GEMINI_MODEL and self.GEMINI_MODEL != "gemini-3.5-flash" and self.LLM_MODEL == "gemini-3.5-flash":
            self.LLM_MODEL = self.GEMINI_MODEL
        return self

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
