"""
mcp_servers/log_mcp.py — Application log MCP server.

Handles all CRUD for the application_logs table.
"""

from datetime import date
from typing import Any, Optional

from supabase._async.client import AsyncClient as AsyncSupabase

from backend.mcp_servers.base_mcp import BaseMCP


class LogMCP(BaseMCP):
    def __init__(self, supabase: AsyncSupabase) -> None:
        super().__init__()
        self._db = supabase

    async def append_log(
        self,
        user_id: str,
        job_id: str,
        resume_id: str,
        cover_letter_id: Optional[str],
        applied: bool = False,
        applied_on: Optional[str] = None,
        feedback_rating: Optional[int] = None,
        feedback_notes: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            row: dict[str, Any] = {
                "user_id": user_id,
                "job_id": job_id,
                "resume_id": resume_id,
                "cover_letter_id": cover_letter_id,  # nullable
                "applied": applied,
            }
            if applied_on:
                row["applied_on"] = applied_on
            if feedback_rating is not None:
                row["feedback_rating"] = feedback_rating
            if feedback_notes:
                row["feedback_notes"] = feedback_notes

            res = await self._db.table("application_logs").insert(row).execute()
            log_id = res.data[0]["id"]
            self.logger.info("Application log appended", user_id=user_id, log_id=log_id)
            return {"log_id": log_id}
        except Exception as exc:
            return self._error(str(exc), "APPEND_LOG_ERROR")

    async def mark_applied(
        self, log_id: str, user_id: str, applied_on: str
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("application_logs").update({
                "applied": True,
                "applied_on": applied_on,
            }).eq("id", log_id).eq("user_id", user_id).execute()
            if not res.data:
                return self._error("Log entry not found", "LOG_NOT_FOUND")
            return {"updated": True, "log_id": log_id}
        except Exception as exc:
            return self._error(str(exc), "MARK_APPLIED_ERROR")

    async def get_all_logs(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        try:
            res = await self._db.table("application_logs").select(
                """
                id, applied, applied_on, feedback_rating, feedback_notes, logged_at,
                jobs(company_name, job_title, ats_score_initial),
                resumes(id, version, ats_score_final, pdf_url),
                cover_letters(id, pdf_url)
                """
            ).eq("user_id", user_id).order(
                "logged_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            return {"logs": res.data, "total": len(res.data)}
        except Exception as exc:
            return self._error(str(exc), "GET_LOGS_ERROR")

    async def filter_logs(
        self,
        user_id: str,
        applied: Optional[bool] = None,
        min_score: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            query = self._db.table("application_logs").select(
                """
                id, applied, applied_on, feedback_rating, feedback_notes, logged_at,
                jobs(company_name, job_title, ats_score_initial),
                resumes(id, version, ats_score_final, pdf_url)
                """
            ).eq("user_id", user_id)

            if applied is not None:
                query = query.eq("applied", applied)
            if date_from:
                query = query.gte("logged_at", date_from)
            if date_to:
                query = query.lte("logged_at", date_to)

            res = await query.order("logged_at", desc=True).execute()
            rows = res.data or []

            # Filter by ATS score (requires join data — done in Python)
            if min_score is not None:
                rows = [
                    r for r in rows
                    if r.get("resumes", {}) and
                    (r["resumes"].get("ats_score_final") or 0) >= min_score
                ]

            return {"logs": rows}
        except Exception as exc:
            return self._error(str(exc), "FILTER_LOGS_ERROR")

    async def get_stats(self, user_id: str) -> dict[str, Any]:
        try:
            res = await self._db.table("application_logs").select(
                "applied, feedback_rating, resumes(ats_score_final)"
            ).eq("user_id", user_id).execute()

            rows = res.data or []
            total = len(rows)
            total_applied = sum(1 for r in rows if r.get("applied"))

            scores = [
                r["resumes"]["ats_score_final"]
                for r in rows
                if r.get("resumes") and r["resumes"].get("ats_score_final") is not None
            ]
            avg_ats = round(sum(scores) / len(scores), 2) if scores else 0.0

            ratings = [
                r["feedback_rating"]
                for r in rows
                if r.get("feedback_rating") is not None
            ]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

            return {
                "total_applications": total,
                "total_applied": total_applied,
                "avg_ats_score": avg_ats,
                "avg_rating": avg_rating,
            }
        except Exception as exc:
            return self._error(str(exc), "GET_STATS_ERROR")
