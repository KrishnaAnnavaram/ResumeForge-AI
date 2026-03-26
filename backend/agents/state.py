"""
agents/state.py — LangGraph ResumeState TypedDict.

Every field used across all graph nodes is declared here.
The PostgresSaver checkpointer serialises this to JSON in Supabase.
"""

from typing import Optional, TypedDict


class ResumeState(TypedDict):
    # ── Inputs — set at graph start ──────────────────────────────────────
    user_id: str
    job_id: str
    jd_text: str
    company_name: str
    job_title: str

    # ── ATS analysis stage ───────────────────────────────────────────────
    ats_score: float
    ats_gap: dict          # full rich gap JSON
    jd_keywords: dict

    # ── Generation stage ─────────────────────────────────────────────────
    resume_text: str
    resume_version: int
    retry_count: int

    # ── User decision gates ───────────────────────────────────────────────
    user_confirmed: bool        # Gate 1 — generate resume?
    is_confirmed: bool          # Gate 2 — confirm this version?
    wants_cover_letter: bool    # Gate 3 — generate cover letter?

    # ── Output fields ─────────────────────────────────────────────────────
    resume_id: str
    cover_letter_text: str
    cover_letter_id: str
    resume_pdf_url: str
    cover_pdf_url: str

    # ── Feedback fields ───────────────────────────────────────────────────
    applied: bool
    applied_on: Optional[str]
    feedback_rating: int        # 1–5
    feedback_notes: str

    # ── Internal metadata ─────────────────────────────────────────────────
    error_message: Optional[str]   # set on node failure; checked by routes
    run_id: Optional[str]          # LangGraph thread_id
