"""
core/config.py — Pydantic Settings with startup validation.

Fail-fast: if any required env var is missing the app refuses to start.
All config is read ONCE at import time and cached via lru_cache.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM keys ────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., min_length=10)
    openai_api_key: str = Field(..., min_length=10)

    # ── Supabase ─────────────────────────────────────────────────────────
    supabase_url: AnyHttpUrl = Field(...)
    supabase_anon_key: str = Field(..., min_length=10)
    supabase_service_role_key: str = Field(..., min_length=10)
    supabase_db_url: str = Field(..., min_length=10)

    # ── Redis ────────────────────────────────────────────────────────────
    upstash_redis_url: AnyHttpUrl = Field(...)
    upstash_redis_token: str = Field(..., min_length=10)

    # ── App ──────────────────────────────────────────────────────────────
    backend_url: AnyHttpUrl = Field(default="http://localhost:8000")
    frontend_url: AnyHttpUrl = Field(default="http://localhost:5173")
    secret_key: str = Field(..., min_length=32)
    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")

    # ── LLM constants ────────────────────────────────────────────────────
    claude_opus_model: str = "claude-opus-4-5"
    claude_sonnet_model: str = "claude-sonnet-4-5"
    gpt4o_model: str = "gpt-4o"

    # Max output tokens per call — cost control
    claude_opus_max_tokens: int = 4096
    claude_sonnet_max_tokens: int = 8192
    gpt4o_max_tokens_per_bullet: int = 512

    # ── ATS thresholds ───────────────────────────────────────────────────
    ats_pass_threshold: float = 95.0
    ats_max_retries: int = 3

    # ── Rate limits ──────────────────────────────────────────────────────
    rate_limit_graph_runs_per_hour: int = 5
    rate_limit_profile_updates_per_hour: int = 20
    rate_limit_global_per_minute: int = 60

    # ── Redis TTLs (seconds) ─────────────────────────────────────────────
    redis_profile_ttl: int = 1800   # 30 min
    redis_ats_ttl: int = 3600       # 60 min

    # ── Circuit breaker ──────────────────────────────────────────────────
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_reset_timeout: int = 60   # seconds

    # ── Input guardrail limits ───────────────────────────────────────────
    jd_text_min_chars: int = 50
    jd_text_max_chars: int = 10_000
    company_name_max_chars: int = 200
    job_title_max_chars: int = 200
    resume_text_min_chars: int = 200
    resume_text_max_chars: int = 8_000

    # ── Allowed CORS origins ─────────────────────────────────────────────
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @property
    def cors_origins(self) -> List[str]:
        return [str(self.frontend_url).rstrip("/")]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton. Import and call this everywhere."""
    return Settings()
