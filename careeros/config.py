"""Application configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/careeros"

    # Anthropic
    anthropic_api_key: str = ""

    # Auth
    secret_key: str = "dev-secret-key-change-in-production-256-bits"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # File Storage
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10

    # LLM Models
    sonnet_model: str = "claude-sonnet-4-5-20251022"
    haiku_model: str = "claude-haiku-4-5-20251001"

    # Embedding
    embedding_model: str = "all-mpnet-base-v2"
    embedding_dimension: int = 768

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
