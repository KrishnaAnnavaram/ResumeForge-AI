"""
mcp_servers/storage_mcp.py — The ONLY server that writes to Supabase DB.

All agents that need to persist data call this server.
Agents NEVER import the Supabase client directly.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from supabase._async.client import AsyncClient as AsyncSupabase

from backend.mcp_servers.base_mcp import BaseMCP


class StorageMCP(BaseMCP):
    def __init__(self, supabase: AsyncSupabase) -> None:
        super().__init__()
        self._db = supabase

    # ── Jobs ──────────────────────────────────────────────────────────────

    async def save_job(
        self,
        user_id: str,
        company_name: str,
        job_title: str,
        jd_text: str,
        keywords_json: dict,
        ats_score: float,
        gap_json: dict,
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("jobs").insert({
                "user_id": user_id,
                "company_name": company_name,
                "job_title": job_title,
                "jd_raw_text": jd_text,
                "jd_keywords_json": keywords_json,
                "ats_score_initial": ats_score,
                "ats_gap_json": gap_json,
            }).execute()
            job_id = res.data[0]["id"]
            self.logger.info("Job saved", user_id=user_id, job_id=job_id)
            return {"job_id": job_id}
        except Exception as exc:
            return self._error(str(exc), "SAVE_JOB_ERROR")

    # ── Resumes ───────────────────────────────────────────────────────────

    async def save_resume(
        self,
        user_id: str,
        job_id: str,
        version: int,
        resume_text: str,
        ats_score_final: float,
    ) -> dict[str, Any]:
        try:
            # Deactivate all previous versions for this job
            await self._db.table("resumes").update(
                {"is_active": False}
            ).eq("job_id", job_id).eq("user_id", user_id).execute()

            res = await self._db.table("resumes").insert({
                "user_id": user_id,
                "job_id": job_id,
                "version": version,
                "generated_text": resume_text,
                "ats_score_final": ats_score_final,
                "is_active": True,
                "is_confirmed": False,
            }).execute()
            resume_id = res.data[0]["id"]
            self.logger.info(
                "Resume saved",
                user_id=user_id,
                job_id=job_id,
                version=version,
                resume_id=resume_id,
            )
            return {"resume_id": resume_id}
        except Exception as exc:
            return self._error(str(exc), "SAVE_RESUME_ERROR")

    async def confirm_resume(self, resume_id: str, user_id: str) -> dict[str, Any]:
        try:
            res = await self._db.table("resumes").update({
                "is_confirmed": True,
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", resume_id).eq("user_id", user_id).execute()
            if not res.data:
                return self._error("Resume not found", "RESUME_NOT_FOUND")
            return {"confirmed": True, "resume_id": resume_id}
        except Exception as exc:
            return self._error(str(exc), "CONFIRM_RESUME_ERROR")

    async def update_resume_pdf_url(
        self, resume_id: str, user_id: str, pdf_url: str
    ) -> dict[str, Any]:
        try:
            await self._db.table("resumes").update(
                {"pdf_url": pdf_url}
            ).eq("id", resume_id).eq("user_id", user_id).execute()
            return {"updated": True}
        except Exception as exc:
            return self._error(str(exc), "UPDATE_PDF_URL_ERROR")

    # ── Cover letters ─────────────────────────────────────────────────────

    async def save_cover_letter(
        self,
        user_id: str,
        resume_id: str,
        job_id: str,
        generated_text: str,
        soft_skills_used: list,
        pdf_url: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("cover_letters").insert({
                "user_id": user_id,
                "resume_id": resume_id,
                "job_id": job_id,
                "generated_text": generated_text,
                "soft_skills_used": soft_skills_used,
                "pdf_url": pdf_url,
            }).execute()
            cover_letter_id = res.data[0]["id"]
            self.logger.info(
                "Cover letter saved",
                user_id=user_id,
                cover_letter_id=cover_letter_id,
            )
            return {"cover_letter_id": cover_letter_id}
        except Exception as exc:
            return self._error(str(exc), "SAVE_COVER_LETTER_ERROR")

    # ── Queries ───────────────────────────────────────────────────────────

    async def get_resume_versions(
        self, job_id: str, user_id: str
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("resumes").select(
                "id, version, ats_score_final, is_confirmed, is_active, created_at"
            ).eq("job_id", job_id).eq("user_id", user_id).order(
                "version", desc=False
            ).execute()
            return {"versions": res.data}
        except Exception as exc:
            return self._error(str(exc), "GET_VERSIONS_ERROR")

    async def get_job_history(
        self, user_id: str, limit: int = 20
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("jobs").select(
                "id, company_name, job_title, ats_score_initial, created_at"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).limit(limit).execute()
            return {"jobs": res.data}
        except Exception as exc:
            return self._error(str(exc), "GET_JOB_HISTORY_ERROR")

    async def get_resume_by_id(
        self, resume_id: str, user_id: str
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("resumes").select("*").eq(
                "id", resume_id
            ).eq("user_id", user_id).single().execute()
            if not res.data:
                return self._error("Resume not found", "RESUME_NOT_FOUND")
            return {"resume": res.data}
        except Exception as exc:
            return self._error(str(exc), "GET_RESUME_ERROR")
