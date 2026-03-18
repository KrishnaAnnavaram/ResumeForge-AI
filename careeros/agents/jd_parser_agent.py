"""JD Parser Agent — transforms raw JD text into structured data."""
import hashlib
import re
import time
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from careeros.agents.state import CareerOSState
from careeros.core.exceptions import JDParseError, LanguageNotSupportedError
from careeros.core.logging import get_logger
from careeros.database.models.job_description import JobDescription
from careeros.database.models.skill_alias import SkillAlias
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.jd_parser_prompts import JD_CORE_EXTRACTION_PROMPT, JD_SIGNAL_EXTRACTION_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()

# EEO / benefits patterns to strip
_EEO_PATTERNS = [
    r"equal opportunity employer.*",
    r"eoe.*",
    r"we are committed to diversity.*",
    r"we do not discriminate.*",
    r"disability.*accommodation.*",
]
_BENEFITS_HEADERS = [
    "benefits:", "perks:", "what we offer:", "compensation:", "salary range:",
    "our benefits:", "employee benefits:", "what you'll get:",
]


def _preprocess_jd(raw: str) -> str:
    """Strip HTML, EEO text, benefits sections, normalize whitespace."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", raw)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")

    lines = text.split("\n")
    filtered: list[str] = []
    skip_mode = False

    for line in lines:
        lower = line.lower().strip()
        # Detect benefits/EEO section headers → skip until next section
        if any(lower.startswith(h) for h in _BENEFITS_HEADERS):
            skip_mode = True
            continue
        # Detect EEO inline paragraphs
        if any(re.search(p, lower) for p in _EEO_PATTERNS):
            continue
        # Reset skip mode on blank line (section break)
        if skip_mode and lower == "":
            skip_mode = False
            continue
        if skip_mode:
            continue
        filtered.append(line)

    # Normalize whitespace
    result = "\n".join(filtered)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r"[ \t]+", " ", result)
    return result.strip()


def _detect_language(text: str) -> str:
    """Very lightweight English detection — checks for common English words."""
    english_words = {"the", "and", "for", "are", "with", "you", "will", "have", "this", "that"}
    words = set(text.lower().split()[:200])
    overlap = english_words & words
    return "en" if len(overlap) >= 3 else "unknown"


def _score_confidence(structured: dict) -> tuple[float, list[str]]:
    """Score parse confidence 0.0–1.0 and collect warnings."""
    score = 0.0
    warnings = []

    if structured.get("role_title"):
        score += 0.15
    if structured.get("required_skills"):
        score += 0.15
    else:
        warnings.append("No required skills extracted — confidence capped at 0.4")
    if structured.get("domain"):
        score += 0.15
    if structured.get("company"):
        score += 0.10
    if structured.get("responsibilities"):
        score += 0.10
    if structured.get("seniority"):
        score += 0.10
    if structured.get("location") or structured.get("remote_policy"):
        score += 0.05

    # Cap if no required skills
    if not structured.get("required_skills"):
        score = min(score, 0.40)

    return round(score, 2), warnings


async def _normalize_skills(skills: list[str], db: AsyncSession) -> list[str]:
    """Map skill names through alias table to canonical form."""
    if not skills:
        return skills

    result = await db.execute(select(SkillAlias).where(SkillAlias.alias.in_([s.lower() for s in skills])))
    aliases = {row.alias: row.canonical for row in result.scalars().all()}

    normalized = []
    for skill in skills:
        canonical = aliases.get(skill.lower())
        if canonical:
            normalized.append(canonical)
        else:
            normalized.append(skill)
    return normalized


async def run_jd_parser_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Parse JD: preprocess → cache check → LLM extraction → persist."""
    start = time.time()
    log.info("agent.start", agent="JD_Parser_Agent", session_id=state["session_id"], user_id=state["user_id"])

    try:
        raw_text = state["jd_raw"]

        # Step 1: Preprocessing
        processed = _preprocess_jd(raw_text)
        word_count = len(processed.split())
        warnings: list[str] = []

        if word_count < 80:
            warnings.append(f"JD is very short ({word_count} words) — parse confidence will be low")

        # Language detection
        lang = _detect_language(processed)
        if lang != "en":
            raise LanguageNotSupportedError("Job description must be in English")

        # Step 2: Cache check
        text_hash = hashlib.sha256(processed.encode()).hexdigest()
        result = await db.execute(
            select(JobDescription).where(
                JobDescription.user_id == state["user_id"],
                JobDescription.raw_text_hash == text_hash,
            )
        )
        cached_jd = result.scalar_one_or_none()

        if cached_jd:
            log.info("jd_parser.cache_hit", session_id=state["session_id"], hash=text_hash)
            return {
                **state,
                "jd_id": str(cached_jd.id),
                "jd_structured": _jd_to_dict(cached_jd),
                "layer1_warnings": state.get("layer1_warnings", []),
            }

        # Step 3: Core extraction
        llm = get_llm_client()
        core_prompt = JD_CORE_EXTRACTION_PROMPT.format(raw_jd_text=processed)
        core_data = llm.complete_json(core_prompt, model=settings.haiku_model)

        # Step 4: Signal extraction
        signal_prompt = JD_SIGNAL_EXTRACTION_PROMPT.format(raw_jd_text=processed)
        signal_data = llm.complete_json(signal_prompt, model=settings.haiku_model)

        # Step 5: Skills normalization
        required_skills = await _normalize_skills(core_data.get("required_skills", []), db)
        preferred_skills = await _normalize_skills(core_data.get("preferred_skills", []), db)

        # Step 6: Confidence scoring
        merged = {**core_data, "required_skills": required_skills}
        confidence, parse_warnings = _score_confidence(merged)
        all_warnings = warnings + parse_warnings

        # Step 7: Persist
        jd = JobDescription(
            user_id=state["user_id"],
            raw_text=raw_text,
            raw_text_hash=text_hash,
            company=core_data.get("company"),
            role_title=core_data.get("role_title"),
            seniority=core_data.get("seniority"),
            employment_type=core_data.get("employment_type"),
            location=core_data.get("location"),
            remote_policy=core_data.get("remote_policy"),
            required_skills=required_skills or [],
            preferred_skills=preferred_skills or [],
            soft_skills=core_data.get("soft_skills", []),
            responsibilities=core_data.get("responsibilities", []),
            domain=core_data.get("domain"),
            industry=core_data.get("industry"),
            team_context=core_data.get("team_context"),
            seniority_signals=signal_data.get("seniority_signals", []),
            tone=signal_data.get("tone"),
            company_stage=signal_data.get("company_stage"),
            culture_signals=signal_data.get("culture_signals", []),
            hiring_signals=signal_data.get("hiring_signals", {}),
            ats_keywords=signal_data.get("ats_keywords", []),
            parse_confidence=confidence,
            parse_warnings=all_warnings,
            parsed_at=datetime.now(timezone.utc),
        )
        db.add(jd)
        await db.flush()

        elapsed = int((time.time() - start) * 1000)
        log.info(
            "agent.complete",
            agent="JD_Parser_Agent",
            session_id=state["session_id"],
            duration_ms=elapsed,
            parse_confidence=confidence,
            required_skills_found=len(required_skills),
        )

        new_warnings = state.get("layer1_warnings", []) + all_warnings
        return {
            **state,
            "jd_id": str(jd.id),
            "jd_structured": _jd_to_dict(jd),
            "layer1_warnings": new_warnings,
        }

    except LanguageNotSupportedError:
        raise
    except Exception as exc:
        log.error("agent.failed", agent="JD_Parser_Agent", session_id=state["session_id"], error=str(exc), error_type=type(exc).__name__)
        raise JDParseError(f"Failed to parse job description: {exc}") from exc


def _jd_to_dict(jd: JobDescription) -> dict:
    return {
        "id": str(jd.id),
        "company": jd.company,
        "role_title": jd.role_title,
        "seniority": jd.seniority,
        "employment_type": jd.employment_type,
        "location": jd.location,
        "remote_policy": jd.remote_policy,
        "required_skills": jd.required_skills or [],
        "preferred_skills": jd.preferred_skills or [],
        "soft_skills": jd.soft_skills or [],
        "responsibilities": jd.responsibilities or [],
        "domain": jd.domain,
        "industry": jd.industry,
        "team_context": jd.team_context,
        "seniority_signals": jd.seniority_signals or [],
        "tone": jd.tone,
        "company_stage": jd.company_stage,
        "culture_signals": jd.culture_signals or [],
        "hiring_signals": jd.hiring_signals or {},
        "ats_keywords": jd.ats_keywords or [],
        "parse_confidence": float(jd.parse_confidence) if jd.parse_confidence else 0.0,
        "parse_warnings": jd.parse_warnings or [],
    }
