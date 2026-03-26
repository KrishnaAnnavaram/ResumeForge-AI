"""
core/rate_limit.py — Redis sliding-window rate limiter.

Per-user, per-endpoint limits backed by Upstash Redis.
Falls back to allowing the request if Redis is unavailable (fail open)
to avoid blocking users when cache is down.
"""

import time
from typing import Optional

import redis.asyncio as aioredis

from backend.core.config import get_settings
from backend.core.exceptions import RateLimitError
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Redis client ─────────────────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            str(settings.upstash_redis_url),
            password=settings.upstash_redis_token,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis_client


# ── Sliding window implementation ─────────────────────────────────────────────

async def check_rate_limit(
    user_id: str,
    action: str,
    limit: int,
    window_seconds: int,
) -> None:
    """
    Raise RateLimitError if user has exceeded `limit` calls in the
    last `window_seconds` for `action`.

    Uses a sorted-set sliding window: members are timestamps (as float
    strings), scores are timestamps. We trim old entries then count.
    """
    key = f"rl:{action}:{user_id}"
    now = time.time()
    window_start = now - window_seconds

    try:
        redis = get_redis()
        pipe = redis.pipeline()
        # Remove entries older than the window
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count remaining entries
        pipe.zcard(key)
        # Add current timestamp
        pipe.zadd(key, {str(now): now})
        # Set TTL so the key auto-expires
        pipe.expire(key, window_seconds + 10)
        results = await pipe.execute()

        current_count: int = results[1]
        if current_count >= limit:
            logger.warning(
                "Rate limit exceeded",
                user_id=user_id,
                action=action,
                count=current_count,
                limit=limit,
            )
            raise RateLimitError(
                f"Rate limit exceeded for '{action}'. "
                f"Maximum {limit} requests per "
                f"{window_seconds // 60} minute(s)."
            )

    except RateLimitError:
        raise
    except Exception as exc:
        # Redis unavailable — fail open, log warning
        logger.warning(
            "Rate limiter Redis error — failing open",
            action=action,
            user_id=user_id,
            error=str(exc),
        )


# ── Convenience helpers ───────────────────────────────────────────────────────

async def check_graph_run_limit(user_id: str) -> None:
    await check_rate_limit(
        user_id,
        "graph_run",
        settings.rate_limit_graph_runs_per_hour,
        3600,
    )


async def check_profile_update_limit(user_id: str) -> None:
    await check_rate_limit(
        user_id,
        "profile_update",
        settings.rate_limit_profile_updates_per_hour,
        3600,
    )


async def check_global_limit(user_id: str) -> None:
    await check_rate_limit(
        user_id,
        "global",
        settings.rate_limit_global_per_minute,
        60,
    )
