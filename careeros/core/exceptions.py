"""CareerOS custom exception hierarchy."""


class CareerOSError(Exception):
    """Base exception for all CareerOS errors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class VaultTooThinError(CareerOSError):
    """Vault has insufficient data for generation."""


class JDParseError(CareerOSError):
    """Failed to parse job description."""


class RetrievalError(CareerOSError):
    """Evidence retrieval failed."""


class GenerationError(CareerOSError):
    """Resume or cover letter generation failed."""


class TruthLockViolationError(CareerOSError):
    """Generated content contains unsupported claim."""


class LanguageNotSupportedError(CareerOSError):
    """Job description is not in English."""


class MaxIterationsError(CareerOSError):
    """Maximum refinement iterations reached."""


class SessionNotFoundError(CareerOSError):
    """Generation session not found."""


class InsufficientEvidenceError(CareerOSError):
    """Not enough evidence retrieved for quality generation."""


class DocumentParseError(CareerOSError):
    """Failed to parse uploaded document."""


class AuthenticationError(CareerOSError):
    """Authentication failed."""


class AuthorizationError(CareerOSError):
    """User not authorized to access this resource."""


class UserNotFoundError(CareerOSError):
    """User not found."""


class DuplicateResourceError(CareerOSError):
    """Resource already exists."""
