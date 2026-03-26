"""
mcp_servers/docgen_mcp.py — PDF generation via WeasyPrint + Supabase Storage.

Renders HTML templates to PDF and uploads to Supabase Storage.
PDF files are NEVER stored in the database — only the signed URL is stored.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from supabase._async.client import AsyncClient as AsyncSupabase

from backend.core.logger import get_logger
from backend.mcp_servers.base_mcp import BaseMCP

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class DocgenMCP(BaseMCP):
    def __init__(self, supabase: AsyncSupabase) -> None:
        super().__init__()
        self._db = supabase

    # ── PDF rendering ─────────────────────────────────────────────────────

    async def render_resume_pdf(
        self,
        resume_text: str,
        profile: dict,
        template: str,
        user_id: str,
        job_id: str,
        version: int,
    ) -> dict[str, Any]:
        try:
            html = self._build_resume_html(resume_text, profile, template)
            pdf_bytes = self._render_pdf(html)
            storage_path = f"{user_id}/jobs/{job_id}/resume_v{version}.pdf"
            pdf_url = await self._upload_pdf(pdf_bytes, storage_path, user_id)
            self.logger.info(
                "Resume PDF rendered and uploaded",
                user_id=user_id,
                job_id=job_id,
                version=version,
                path=storage_path,
            )
            return {"pdf_url": pdf_url}
        except Exception as exc:
            return self._error(str(exc), "RENDER_RESUME_PDF_ERROR")

    async def render_cover_pdf(
        self,
        cover_text: str,
        profile: dict,
        company: str,
        user_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        try:
            html = self._build_cover_html(cover_text, profile, company)
            pdf_bytes = self._render_pdf(html)
            storage_path = f"{user_id}/jobs/{job_id}/cover.pdf"
            pdf_url = await self._upload_pdf(pdf_bytes, storage_path, user_id)
            self.logger.info(
                "Cover letter PDF rendered and uploaded",
                user_id=user_id,
                job_id=job_id,
                path=storage_path,
            )
            return {"pdf_url": pdf_url}
        except Exception as exc:
            return self._error(str(exc), "RENDER_COVER_PDF_ERROR")

    async def get_download_url(
        self, storage_path: str, user_id: str
    ) -> dict[str, Any]:
        try:
            # Generate a fresh signed URL valid for 1 hour
            res = self._db.storage.from_("resumes").create_signed_url(
                storage_path, 3600
            )
            return {"signed_url": res["signedURL"]}
        except Exception as exc:
            return self._error(str(exc), "GET_DOWNLOAD_URL_ERROR")

    async def list_templates(self) -> dict[str, Any]:
        try:
            templates = []
            for tmpl_path in TEMPLATES_DIR.glob("resume_*.html"):
                tid = tmpl_path.stem.replace("resume_", "")
                templates.append({"id": tid, "name": tid.replace("_", " ").title()})
            return {"templates": templates}
        except Exception as exc:
            return self._error(str(exc), "LIST_TEMPLATES_ERROR")

    # ── Private helpers ───────────────────────────────────────────────────

    def _render_pdf(self, html: str) -> bytes:
        """Render HTML to PDF bytes using WeasyPrint."""
        try:
            from weasyprint import HTML
            with tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False
            ) as tmp:
                tmp_path = tmp.name
            HTML(string=html).write_pdf(tmp_path)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_path)
            return pdf_bytes
        except ImportError:
            # WeasyPrint not installed — return placeholder bytes for dev
            logger.warning("WeasyPrint not available — returning placeholder PDF")
            return b"%PDF-1.4 placeholder"

    async def _upload_pdf(
        self, pdf_bytes: bytes, storage_path: str, user_id: str
    ) -> str:
        """Upload PDF bytes to Supabase Storage and return the path."""
        bucket = "resumes"
        res = await self._db.storage.from_(bucket).upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        # Return the storage path — caller can get a signed URL separately
        return storage_path

    def _build_resume_html(
        self, resume_text: str, profile: dict, template: str = "classic"
    ) -> str:
        template_file = TEMPLATES_DIR / f"resume_{template}.html"
        if not template_file.exists():
            template_file = TEMPLATES_DIR / "resume.html"

        raw = template_file.read_text(encoding="utf-8")
        return (
            raw
            .replace("{{full_name}}", profile.get("full_name", ""))
            .replace("{{email}}", profile.get("email", ""))
            .replace("{{phone}}", profile.get("phone", ""))
            .replace("{{linkedin_url}}", profile.get("linkedin_url", ""))
            .replace("{{resume_body}}", self._md_to_html(resume_text))
        )

    def _build_cover_html(
        self, cover_text: str, profile: dict, company: str
    ) -> str:
        template_file = TEMPLATES_DIR / "cover_letter.html"
        raw = template_file.read_text(encoding="utf-8")
        return (
            raw
            .replace("{{full_name}}", profile.get("full_name", ""))
            .replace("{{email}}", profile.get("email", ""))
            .replace("{{company}}", company)
            .replace("{{cover_body}}", self._md_to_html(cover_text))
        )

    @staticmethod
    def _md_to_html(text: str) -> str:
        """Minimal Markdown-like conversion for resume text."""
        import re
        lines = text.split("\n")
        result = []
        for line in lines:
            line = line.rstrip()
            if line.startswith("## "):
                result.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                result.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("- ") or line.startswith("• "):
                result.append(f"<li>{line[2:]}</li>")
            elif line == "":
                result.append("<br>")
            else:
                # Bold **text**
                line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                result.append(f"<p>{line}</p>")
        return "\n".join(result)
