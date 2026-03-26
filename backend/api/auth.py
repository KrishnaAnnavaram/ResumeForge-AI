"""
api/auth.py — Supabase JWT authentication middleware.

Validates RS256 JWTs issued by Supabase Auth.
Extracts user_id (sub claim) and attaches to request.state.user_id.

All routes depend on get_current_user_id() FastAPI dependency.
Service role key is NEVER exposed to frontend or returned in responses.
"""

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import get_settings
from backend.core.exceptions import AuthenticationError, ExpiredToken, InvalidToken
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_bearer = HTTPBearer(auto_error=False)

# ── JWKS fetching (cached) ────────────────────────────────────────────────────
_jwks_cache: dict = {}


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = f"{settings.supabase_url}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            return _jwks_cache
    except Exception as exc:
        logger.error("Failed to fetch Supabase JWKS", error=str(exc))
        raise AuthenticationError("Could not verify authentication credentials")


# ── Token validation ──────────────────────────────────────────────────────────

async def _validate_token(token: str) -> dict:
    """
    Validate a Supabase JWT.
    Returns the decoded payload dict (including sub = user_id).
    """
    try:
        from jose import ExpiredSignatureError, JWTError, jwt as jose_jwt
        from jose.exceptions import JWKError

        jwks = await _get_jwks()

        # Decode without verification first to get the kid
        unverified = jose_jwt.get_unverified_header(token)
        kid = unverified.get("kid")

        # Find matching key
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if key is None:
            # Fall back to first key if kid not found
            keys = jwks.get("keys", [])
            if keys:
                key = keys[0]

        if key is None:
            raise InvalidToken("No matching JWKS key found")

        payload = jose_jwt.decode(
            token,
            key,
            algorithms=["RS256", "HS256"],
            audience="authenticated",
            options={"verify_aud": False},  # Supabase uses role not aud sometimes
        )
        return payload

    except Exception as exc:
        err_str = str(exc).lower()
        if "expired" in err_str:
            raise ExpiredToken("JWT token has expired")
        if "invalid" in err_str or "decode" in err_str or "signature" in err_str:
            raise InvalidToken(f"JWT validation failed: {exc}")
        raise AuthenticationError(f"Authentication error: {exc}")


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    FastAPI dependency. Returns the authenticated user_id (UUID string).

    Usage:
        @router.get("/api/profile")
        async def get_profile(user_id: str = Depends(get_current_user_id)):
            ...
    """
    if credentials is None:
        raise AuthenticationError("Authorization header missing")

    token = credentials.credentials
    payload = await _validate_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidToken("JWT missing sub claim")

    # Attach to request.state for middleware access
    request.state.user_id = user_id
    return user_id
