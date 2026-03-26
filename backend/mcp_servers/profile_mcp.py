"""
mcp_servers/profile_mcp.py — Profile MCP server.

Provides read/write access to the profiles table.
All reads go through Redis first (TTL 30 min); writes invalidate the cache.
"""

import json
from typing import Any

import redis.asyncio as aioredis
from supabase._async.client import AsyncClient as AsyncSupabase

from backend.core.config import get_settings
from backend.core.rate_limit import get_redis
from backend.mcp_servers.base_mcp import BaseMCP

settings = get_settings()

PROFILE_KEY = "profile:{user_id}"


class ProfileMCP(BaseMCP):
    def __init__(self, supabase: AsyncSupabase) -> None:
        super().__init__()
        self._db = supabase

    # ── Cache helpers ─────────────────────────────────────────────────────

    async def _cache_get(self, key: str) -> Any | None:
        try:
            redis: aioredis.Redis = get_redis()
            raw = await redis.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            self.logger.warning("Redis cache read failed", key=key, error=str(exc))
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int) -> None:
        try:
            redis: aioredis.Redis = get_redis()
            await redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            self.logger.warning("Redis cache write failed", key=key, error=str(exc))

    async def _cache_delete(self, key: str) -> None:
        try:
            redis: aioredis.Redis = get_redis()
            await redis.delete(key)
        except Exception as exc:
            self.logger.warning("Redis cache delete failed", key=key, error=str(exc))

    # ── Tools ─────────────────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        cache_key = PROFILE_KEY.format(user_id=user_id)
        cached = await self._cache_get(cache_key)
        if cached:
            self.logger.info("Profile cache hit", user_id=user_id)
            return cached

        try:
            res = (
                await self._db.table("profiles")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if not res.data:
                return self._error("Profile not found", "PROFILE_NOT_FOUND")
            profile = res.data
            await self._cache_set(cache_key, profile, settings.redis_profile_ttl)
            return profile
        except Exception as exc:
            return self._error(str(exc), "DB_ERROR")

    async def get_resume_text(self, user_id: str) -> dict[str, Any]:
        profile = await self.get_profile(user_id)
        if self._is_error(profile):
            return profile
        return {"resume_text": profile.get("raw_resume_text", "")}

    async def get_skills(self, user_id: str) -> dict[str, Any]:
        cache_key = PROFILE_KEY.format(user_id=user_id)
        cached = await self._cache_get(cache_key)
        if cached:
            return {"skills": cached.get("skills_json", [])}
        profile = await self.get_profile(user_id)
        if self._is_error(profile):
            return profile
        return {"skills": profile.get("skills_json", [])}

    async def get_soft_skills(self, user_id: str) -> dict[str, Any]:
        profile = await self.get_profile(user_id)
        if self._is_error(profile):
            return profile
        return {"soft_skills": profile.get("soft_skills_json", [])}

    async def get_experience(self, user_id: str) -> dict[str, Any]:
        profile = await self.get_profile(user_id)
        if self._is_error(profile):
            return profile
        return {"experience": profile.get("experience_json", [])}

    async def update_profile(self, user_id: str, fields: dict) -> dict[str, Any]:
        # Strip fields that should never be updated via this tool
        forbidden = {"id", "user_id", "created_at"}
        safe_fields = {k: v for k, v in fields.items() if k not in forbidden}

        try:
            from datetime import datetime, timezone
            safe_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            res = (
                await self._db.table("profiles")
                .update(safe_fields)
                .eq("user_id", user_id)
                .execute()
            )
            # Invalidate cache immediately after write
            await self._cache_delete(PROFILE_KEY.format(user_id=user_id))
            self.logger.info("Profile updated, cache invalidated", user_id=user_id)
            return {"profile": res.data[0] if res.data else {}}
        except Exception as exc:
            return self._error(str(exc), "DB_ERROR")

    async def upsert_profile(self, user_id: str, fields: dict) -> dict[str, Any]:
        """Create profile if it doesn't exist, otherwise update."""
        forbidden = {"id", "created_at"}
        safe_fields = {k: v for k, v in fields.items() if k not in forbidden}
        safe_fields["user_id"] = user_id

        try:
            from datetime import datetime, timezone
            safe_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            res = (
                await self._db.table("profiles")
                .upsert(safe_fields, on_conflict="user_id")
                .execute()
            )
            await self._cache_delete(PROFILE_KEY.format(user_id=user_id))
            return {"profile": res.data[0] if res.data else {}}
        except Exception as exc:
            return self._error(str(exc), "DB_ERROR")
