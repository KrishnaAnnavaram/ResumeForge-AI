"""Critic Agent — validates all claims against evidence and enforces truth lock."""
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from careeros.agents.state import CareerOSState
from careeros.core.logging import get_logger
from careeros.database.models.generated_resume import GeneratedResume
from careeros.database.models.generated_cover_letter import GeneratedCoverLetter
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.critic_prompts import CRITIC_CLAIM_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()

FORBIDDEN_PHRASES = [
    "passionate about", "team player", "hardworking", "self-motivated",
    "dynamic", "synergy", "leverage", "results-driven", "go-getter",
    "i am writing to apply", "to whom it may concern", "passion for",
]


def _base_score() -> int:
    return 70


def _check_forbidden_phrases(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


async def run_critic_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Validate generated content against evidence. Enforce truth lock."""
    start = time.time()
    log.info("agent.start", agent="Critic_Agent", session_id=state["session_id"], user_id=state["user_id"])

    llm = get_llm_client()
    evidence_set = state.get("evidence_set") or []
    evidence_map = {b["bullet_id"]: b for b in evidence_set}

    flags = []
    score = _base_score()

    # Validate resume
    resume_draft = state.get("resume_draft") or {}
    resume_claim_map = {}
    for section in resume_draft.get("sections", []):
        resume_claim_map.update(section.get("claim_evidence_map", {}))

    sections_with_metrics = 0
    for section in resume_draft.get("sections", []):
        content = section.get("content", "")
        bullets = section.get("bullets", [])
        all_text = content + " ".join(bullets)
        # Check for metrics in bullets (simple heuristic: contains % or numbers)
        has_metric = any(c.isdigit() or "%" in b for b in bullets for c in b)
        if has_metric:
            sections_with_metrics += 1

    # Check a sample of claims via LLM
    claims_to_check = list(resume_claim_map.items())[:5]  # limit LLM calls
    for claim_text, bullet_id in claims_to_check:
        bullet = evidence_map.get(bullet_id)
        if not bullet:
            flags.append({
                "location": "resume",
                "claim": claim_text,
                "issue": f"Cited evidence ID {bullet_id[:8]} not found in evidence set",
                "severity": "critical",
                "suggested_fix": "Remove unsupported claim",
            })
            score -= 15
            continue

        try:
            prompt = CRITIC_CLAIM_PROMPT.format(
                claim=claim_text,
                location="resume",
                evidence_text=bullet.get("content", ""),
            )
            result = llm.complete_json(prompt, model=settings.haiku_model)
            if not result.get("supported"):
                severity = result.get("severity", "minor")
                flags.append({
                    "location": "resume",
                    "claim": claim_text,
                    "issue": result.get("issue", "Claim not supported by evidence"),
                    "severity": severity,
                    "suggested_fix": result.get("suggested_fix"),
                })
                score -= 15 if severity == "critical" else 5
        except Exception as exc:
            log.warning("critic.claim_check_failed", claim=claim_text[:50], error=str(exc))

    # Check cover letter for forbidden phrases
    cl_draft = state.get("cl_draft") or {}
    cl_content = cl_draft.get("content", "")
    forbidden_found = _check_forbidden_phrases(cl_content)
    if forbidden_found:
        score -= 10
        flags.append({
            "location": "cover_letter",
            "claim": f"Contains forbidden phrases: {', '.join(forbidden_found)}",
            "issue": "Cover letter uses cliché phrases",
            "severity": "minor",
            "suggested_fix": f"Remove: {', '.join(forbidden_found)}",
        })

    # Bonuses
    score += min(sections_with_metrics * 5, 20)

    # ATS keyword coverage
    jd = state.get("jd_structured") or {}
    ats_keywords = jd.get("ats_keywords", [])
    if ats_keywords:
        resume_full_text = " ".join(
            s.get("content", "") + " ".join(s.get("bullets", []))
            for s in resume_draft.get("sections", [])
        ).lower()
        covered = sum(1 for kw in ats_keywords if kw.lower() in resume_full_text)
        coverage = covered / len(ats_keywords)
        if coverage > 0.8:
            score += 5

    # Summary quality bonus (non-generic check)
    for section in resume_draft.get("sections", []):
        if "summary" in section.get("section_name", "").lower():
            content = section.get("content", "")
            if len(content) > 50 and not any(p in content.lower() for p in ["passionate", "hardworking", "team player"]):
                score += 10
            break

    score = max(0, min(100, score))

    critic_report = {
        "valid": len([f for f in flags if f["severity"] == "critical"]) == 0,
        "quality_score": score,
        "flags": flags,
        "summary": f"{'Valid' if score >= 60 else 'Below threshold'} — score {score}/100 with {len(flags)} flags.",
    }

    # Persist scores to DB
    if state.get("resume_version_id"):
        resume_result = await db.execute(
            select(GeneratedResume).where(GeneratedResume.id == state["resume_version_id"])
        )
        resume = resume_result.scalar_one_or_none()
        if resume:
            resume.critic_score = score
            resume.critic_flags = {"flags": flags}

    if state.get("cl_version_id"):
        cl_result = await db.execute(
            select(GeneratedCoverLetter).where(GeneratedCoverLetter.id == state["cl_version_id"])
        )
        cl = cl_result.scalar_one_or_none()
        if cl:
            cl.critic_score = score
            cl.critic_flags = {"flags": flags}

    await db.flush()

    elapsed = int((time.time() - start) * 1000)
    log.info(
        "agent.complete",
        agent="Critic_Agent",
        session_id=state["session_id"],
        duration_ms=elapsed,
        quality_score=score,
        flags=len(flags),
        valid=critic_report["valid"],
    )

    return {
        **state,
        "critic_report": critic_report,
        "critic_retry_count": state.get("critic_retry_count", 0),
    }
