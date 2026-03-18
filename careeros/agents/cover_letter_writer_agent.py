"""Cover Letter Writer Agent — generates tailored cover letter from evidence and JD signals."""
import time
from sqlalchemy.ext.asyncio import AsyncSession

from careeros.agents.state import CareerOSState
from careeros.core.exceptions import GenerationError
from careeros.core.logging import get_logger
from careeros.database.models.generated_cover_letter import GeneratedCoverLetter
from careeros.database.models.generation_session import GenerationSession
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.cover_letter_prompts import COVER_LETTER_PROMPT
from careeros.config import get_settings
from sqlalchemy import select

log = get_logger(__name__)
settings = get_settings()


def _format_evidence_for_cl(evidence_set: list[dict], top_k: int = 8) -> str:
    """Format top evidence bullets for cover letter context."""
    chunks = []
    for bullet in evidence_set[:top_k]:
        chunks.append(
            f"[{bullet['bullet_id'][:8]}] {bullet['content']}\n"
            f"  Metrics: {', '.join(bullet.get('metrics', []) or [])}"
        )
    return "\n\n".join(chunks)


async def run_cover_letter_writer_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Generate a tailored cover letter from evidence and JD signals."""
    start = time.time()
    log.info("agent.start", agent="CoverLetter_Writer_Agent", session_id=state["session_id"], user_id=state["user_id"])

    try:
        jd = state["jd_structured"] or {}
        evidence_set = state.get("evidence_set") or []
        plan = state.get("rewrite_plan") or {}

        prompt = COVER_LETTER_PROMPT.format(
            tone_instruction=plan.get("tone_instruction", jd.get("tone", "professional")),
            company=jd.get("company", "the company"),
            role_title=jd.get("role_title", ""),
            team_context=jd.get("team_context", ""),
            required_skills=", ".join(jd.get("required_skills", [])[:8]),
            culture_signals=", ".join(jd.get("culture_signals", [])),
            cover_letter_angle=plan.get("cover_letter_angle", "Highlight technical expertise and measurable impact"),
            evidence_chunks=_format_evidence_for_cl(evidence_set),
        )

        llm = get_llm_client()
        result = llm.complete_json(prompt, model=settings.sonnet_model, max_tokens=2048)

        # Get version number
        from sqlalchemy import select
        session_result = await db.execute(
            select(GenerationSession).where(GenerationSession.id == state["session_id"])
        )
        gen_session = session_result.scalar_one_or_none()
        version_number = (gen_session.iteration_count if gen_session else 0) + 1

        cl = GeneratedCoverLetter(
            session_id=state["session_id"],
            user_id=state["user_id"],
            version_number=version_number,
            content=result.get("content", ""),
            evidence_ids=[b["bullet_id"] for b in evidence_set[:8]],
            claim_evidence_map=result.get("claim_evidence_map", {}),
            generation_metadata={
                "model": settings.sonnet_model,
                "duration_ms": int((time.time() - start) * 1000),
            },
        )
        db.add(cl)
        await db.flush()

        elapsed = int((time.time() - start) * 1000)
        log.info(
            "agent.complete",
            agent="CoverLetter_Writer_Agent",
            session_id=state["session_id"],
            duration_ms=elapsed,
            version=version_number,
        )

        return {
            **state,
            "cl_draft": {"content": result.get("content", ""), "claim_evidence_map": result.get("claim_evidence_map", {})},
            "cl_version_id": str(cl.id),
        }

    except Exception as exc:
        log.error("agent.failed", agent="CoverLetter_Writer_Agent", session_id=state["session_id"], error=str(exc), error_type=type(exc).__name__)
        raise GenerationError(f"Cover letter generation failed: {exc}") from exc
