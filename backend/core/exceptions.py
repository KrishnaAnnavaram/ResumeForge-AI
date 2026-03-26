"""
core/exceptions.py — Typed exception hierarchy.

Rules:
- Every custom exception maps to an HTTP status code.
- Internal details (stack traces, DB errors) are NEVER exposed to the client.
- Use AppError subclasses everywhere; the global exception handler converts them.
"""

from typing import Optional


class AppError(Exception):
    """Base class for all application errors."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        # detail is for internal logging only — never sent to client
        self.detail = detail

    def to_dict(self) -> dict:
        return {"error": self.error_code, "message": self.message}


# ── 400 Bad Request ───────────────────────────────────────────────────────────
class ValidationError(AppError):
    http_status = 400
    error_code = "VALIDATION_ERROR"


class InputTooLong(ValidationError):
    error_code = "INPUT_TOO_LONG"


class InputTooShort(ValidationError):
    error_code = "INPUT_TOO_SHORT"


class MissingField(ValidationError):
    error_code = "MISSING_FIELD"


# ── 401 Unauthorized ─────────────────────────────────────────────────────────
class AuthenticationError(AppError):
    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"


class InvalidToken(AuthenticationError):
    error_code = "INVALID_TOKEN"


class ExpiredToken(AuthenticationError):
    error_code = "EXPIRED_TOKEN"


# ── 403 Forbidden ────────────────────────────────────────────────────────────
class AuthorizationError(AppError):
    http_status = 403
    error_code = "FORBIDDEN"


class ResourceOwnershipError(AuthorizationError):
    error_code = "NOT_RESOURCE_OWNER"


# ── 404 Not Found ────────────────────────────────────────────────────────────
class NotFoundError(AppError):
    http_status = 404
    error_code = "NOT_FOUND"


class ProfileNotFound(NotFoundError):
    error_code = "PROFILE_NOT_FOUND"


class ResumeNotFound(NotFoundError):
    error_code = "RESUME_NOT_FOUND"


class JobNotFound(NotFoundError):
    error_code = "JOB_NOT_FOUND"


class RunNotFound(NotFoundError):
    error_code = "RUN_NOT_FOUND"


# ── 409 Conflict ─────────────────────────────────────────────────────────────
class ConflictError(AppError):
    http_status = 409
    error_code = "CONFLICT"


# ── 429 Too Many Requests ────────────────────────────────────────────────────
class RateLimitError(AppError):
    http_status = 429
    error_code = "RATE_LIMIT_EXCEEDED"


# ── 503 Service Unavailable ──────────────────────────────────────────────────
class ServiceUnavailableError(AppError):
    http_status = 503
    error_code = "SERVICE_UNAVAILABLE"


class CircuitOpenError(ServiceUnavailableError):
    error_code = "CIRCUIT_OPEN"


class LLMError(ServiceUnavailableError):
    error_code = "LLM_ERROR"


class ClaudeError(LLMError):
    error_code = "CLAUDE_ERROR"


class GPTError(LLMError):
    error_code = "GPT_ERROR"


class StorageError(ServiceUnavailableError):
    error_code = "STORAGE_ERROR"


class CacheError(AppError):
    """Non-fatal: cache miss falls back to DB."""
    http_status = 500
    error_code = "CACHE_ERROR"
