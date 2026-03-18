"""Resume Writer Agent — generates each resume section from the plan and evidence."""
import json
import time
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from careeros.agents.state import CareerOSState
from careeros.core.exceptions import GenerationError
from careeros.core.logging import get_logger
from careeros.database.models.generation_session import GenerationSession
from careeros.database.models.generated_resume import GeneratedResume
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.resume_writer_prompts import RESUME_SECTION_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()


def _format_evidence_chunks(evidence_ids: list[str], evidence_set: list[dict]) -> str:
    """Format evidence bullets assigned to a section for prompt."""
    bullet_map = {b["bullet_id"]: b for b in evidence_set}
    chunks = []
    for eid in evidence_ids:
        # Try full ID then prefix match
        bullet = bullet_map.get(eid)
        if not bullet:
            for bid, b in bullet_map.items():
                if bid.startswith(eid[:8]):
                    bullet = b
                    break
        if bullet:
            chunks.append(
                f"[{bullet['bullet_id'][:8]}] {bullet['content']}\n"
                f"  Metrics: {', '.join(bullet.get('metrics', []) or [])}\n"
                f"  Skills: {', '.join(bullet.get('skills_used', []) or [])}"
            )
    return "\n\n".join(chunks) if chunks else "No specific evidence assigned — use profile summary."


def _resume_to_markdown(sections: list[dict], profile: dict, jd: dict) -> str:
    """Render resume sections to clean markdown."""
    lines = []
    p = profile.get("profile") or {}
    if p.get("full_name"):
        lines.append(f"# {p['full_name']}")
    if p.get("headline"):
        lines.append(f"*{p['headline']}*")
    if p.get("location"):
        links = []
        if p.get("linkedin_url"):
            links.append(f"[LinkedIn]({p['linkedin_url']})")
        if p.get("github_url"):
            links.append(f"[GitHub]({p['github_url']})")
        links_str = " | ".join(links)
        lines.append(f"{p['location']}{' | ' + links_str if links_str else ''}")
    lines.append("")

    for section in sections:
        name = section.get("section_name", "")
        content = section.get("content", "")
        bullets = section.get("bullets", [])

        if "summary" in name.lower():
            lines.append("## Summary")
            lines.append(content)
        elif "experience" in name.lower():
            company = section.get("company", name.replace("experience_", ""))
            lines.append(f"## {company}")
            if content:
                lines.append(content)
            for b in bullets:
                lines.append(f"- {b}")
        elif "skills" in name.lower():
            lines.append("## Skills")
            lines.append(content)
        elif "education" in name.lower():
            lines.append("## Education")
            lines.append(content)
        elif "certification" in name.lower():
            lines.append("## Certifications")
            lines.append(content)
        else:
            lines.append(f"## {name.title()}")
            lines.append(content)
        lines.append("")

    return "\n".join(lines)


async def run_resume_writer_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Generate each resume section from the plan and assembled evidence."""
    start = time.time()
    log.info("agent.start", agent="Resume_Writer_Agent", session_id=state["session_id"], user_id=state["user_id"])

    try:
        jd = state["jd_structured"] or {}
        plan = state.get("rewrite_plan") or {}
        evidence_set = state.get("evidence_set") or []
        profile = state.get("profile") or {}
        llm = get_llm_client()

        sections_plan = sorted(plan.get("sections", []), key=lambda s: s.get("priority", 99))
        generated_sections = []
        all_evidence_ids = []
        full_claim_evidence_map = {}

        for section in sections_plan:
            section_evidence_ids = section.get("evidence_ids", [])
            evidence_chunks = _format_evidence_chunks(section_evidence_ids, evidence_set)

            prompt = RESUME_SECTION_PROMPT.format(
                section_name=section.get("section_name", ""),
                section_purpose=section.get("purpose", ""),
                word_limit=section.get("word_limit", 150),
                tone_instruction=section.get("tone_instruction", plan.get("tone_instruction", "Professional")),
                ats_keywords=", ".join(section.get("ats_keywords_to_include", [])),
                evidence_chunks=evidence_chunks,
                role_title=jd.get("role_title", ""),
                company=jd.get("company", ""),
                domain=jd.get("domain", ""),
            )

            try:
                section_result = llm.complete_json(
                    prompt,
                    model=settings.sonnet_model,
                    max_tokens=2048,
                )
                generated_sections.append({**section_result, "company": section.get("company")})
                claim_map = section_result.get("claim_evidence_map", {})
                full_claim_evidence_map.update(claim_map)
                all_evidence_ids.extend(section_evidence_ids)
            except Exception as exc:
                log.warning("resume_writer.section_failed", section=section.get("section_name"), error=str(exc))
                generated_sections.append({
                    "section_name": section.get("section_name"),
                    "content": f"[Section generation failed: {exc}]",
                    "bullets": [],
                    "claim_evidence_map": {},
                })

        # Build content JSONB
        content = {"sections": generated_sections, "plan": plan}
        content_md = _resume_to_markdown(generated_sections, profile, jd)

        # Get next version number
        session_result = await db.execute(
            select(GenerationSession).where(GenerationSession.id == state["session_id"])
        )
        gen_session = session_result.scalar_one_or_none()
        version_number = (gen_session.iteration_count if gen_session else 0) + 1

        resume = GeneratedResume(
            session_id=state["session_id"],
            user_id=state["user_id"],
            version_number=version_number,
            content=content,
            content_md=content_md,
            evidence_ids=[str(eid) for eid in set(all_evidence_ids)],
            claim_evidence_map=full_claim_evidence_map,
            generation_metadata={
                "model": settings.sonnet_model,
                "sections_count": len(generated_sections),
                "duration_ms": int((time.time() - start) * 1000),
            },
        )
        db.add(resume)
        await db.flush()

        elapsed = int((time.time() - start) * 1000)
        log.info(
            "agent.complete",
            agent="Resume_Writer_Agent",
            session_id=state["session_id"],
            duration_ms=elapsed,
            sections=len(generated_sections),
            version=version_number,
        )

        return {
            **state,
            "resume_draft": content,
            "resume_version_id": str(resume.id),
        }

    except Exception as exc:
        log.error("agent.failed", agent="Resume_Writer_Agent", session_id=state["session_id"], error=str(exc), error_type=type(exc).__name__)
        raise GenerationError(f"Resume generation failed: {exc}") from exc
