"""
core/guardrails.py — Input and output validation guardrails.

Input guardrails: run BEFORE hitting any LLM or DB.
Output guardrails: run AFTER receiving LLM output to catch hallucinations.
"""

import re
from typing import Any

from backend.core.config import get_settings
from backend.core.exceptions import (
    InputTooLong,
    InputTooShort,
    MissingField,
    ValidationError,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Input guardrails ─────────────────────────────────────────────────────────


def validate_jd_text(jd_text: str) -> str:
    """Validate job description text length and basic content."""
    if not jd_text or not jd_text.strip():
        raise MissingField("jd_text is required")
    text = jd_text.strip()
    if len(text) < settings.jd_text_min_chars:
        raise InputTooShort(
            f"Job description must be at least {settings.jd_text_min_chars} characters"
        )
    if len(text) > settings.jd_text_max_chars:
        raise InputTooLong(
            f"Job description must not exceed {settings.jd_text_max_chars} characters"
        )
    return text


def validate_company_name(name: str) -> str:
    if not name or not name.strip():
        raise MissingField("company_name is required")
    name = name.strip()
    if len(name) > settings.company_name_max_chars:
        raise InputTooLong(
            f"Company name must not exceed {settings.company_name_max_chars} characters"
        )
    return name


def validate_job_title(title: str) -> str:
    if not title or not title.strip():
        raise MissingField("job_title is required")
    title = title.strip()
    if len(title) > settings.job_title_max_chars:
        raise InputTooLong(
            f"Job title must not exceed {settings.job_title_max_chars} characters"
        )
    return title


def validate_resume_text(text: str) -> str:
    if not text or not text.strip():
        raise MissingField("resume_text is required")
    text = text.strip()
    if len(text) < settings.resume_text_min_chars:
        raise InputTooShort(
            f"Resume text must be at least {settings.resume_text_min_chars} characters"
        )
    if len(text) > settings.resume_text_max_chars:
        raise InputTooLong(
            f"Resume text must not exceed {settings.resume_text_max_chars} characters"
        )
    return text


def validate_feedback_rating(rating: Any) -> int:
    try:
        r = int(rating)
    except (TypeError, ValueError):
        raise ValidationError("feedback_rating must be an integer 1–5")
    if r < 1 or r > 5:
        raise ValidationError("feedback_rating must be between 1 and 5")
    return r


def validate_user_id(user_id: str) -> str:
    """Basic UUID format check."""
    if not user_id:
        raise MissingField("user_id is required")
    uuid_re = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    if not uuid_re.match(user_id):
        raise ValidationError("user_id must be a valid UUID")
    return user_id


# ── Output guardrails ────────────────────────────────────────────────────────


def validate_ats_score(score: Any, field: str = "ats_score") -> float:
    """Ensure LLM-produced score is within [0, 100]."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        logger.warning("LLM returned non-numeric ATS score", raw_score=score)
        raise ValidationError(f"{field} must be a number between 0 and 100")
    if not (0.0 <= s <= 100.0):
        logger.warning("LLM returned out-of-range ATS score", score=s)
        # Clamp rather than hard-fail — resume generation can continue
        s = max(0.0, min(100.0, s))
    return round(s, 2)


def validate_gap_json(gap: Any) -> dict:
    """Ensure Claude's gap JSON has the required top-level keys."""
    required_keys = {
        "missing_keywords",
        "experience_gaps",
        "section_scores",
        "rewrite_hints",
    }
    if not isinstance(gap, dict):
        raise ValidationError("ats_gap_json must be a JSON object")
    missing = required_keys - gap.keys()
    if missing:
        logger.warning("gap JSON missing keys — backfilling defaults", missing=missing)
        for key in missing:
            gap[key] = [] if key != "section_scores" else {
                "summary": 0, "skills": 0, "experience": 0,
                "education": 0, "certifications": 0,
            }
    return gap


def validate_bullet_list(bullets: Any) -> list[str]:
    """Ensure GPT-4o returned a non-empty list of strings."""
    if not isinstance(bullets, list):
        raise ValidationError("GPT-4o must return a JSON array of bullets")
    validated = []
    for i, b in enumerate(bullets):
        if not isinstance(b, str):
            logger.warning("Non-string bullet skipped", index=i, value=b)
            continue
        b = b.strip()
        if b:
            validated.append(b)
    if not validated:
        raise ValidationError("GPT-4o returned no usable bullets")
    return validated


def validate_keywords_dict(keywords: Any) -> dict:
    """Ensure keyword extraction result has required structure."""
    required = ["hard_skills", "soft_skills", "tools", "certifications",
                "action_verbs", "min_years"]
    if not isinstance(keywords, dict):
        raise ValidationError("jd_keywords must be a JSON object")
    for key in required:
        if key not in keywords:
            keywords[key] = [] if key != "min_years" else 0
    return keywords
