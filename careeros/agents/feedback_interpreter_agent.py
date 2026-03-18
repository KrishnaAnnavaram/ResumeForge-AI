"""Feedback Interpreter Agent — parses user feedback into structured instructions."""
import time
from sqlalchemy.ext.asyncio import AsyncSession

from careeros.agents.state import CareerOSState
from careeros.core.logging import get_logger
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.feedback_prompts import FEEDBACK_INTERPRETATION_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()


async def run_feedback_interpreter_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Parse user natural language feedback into structured instructions."""
    start = time.time()
    log.info("agent.start", agent="Feedback_Interpreter_Agent", session_id=state["session_id"], user_id=state["user_id"])

    feedback_raw = state.get("user_feedback_raw", "")
    resume_draft = state.get("resume_draft") or {}

    # Build available sections list
    available_sections = [s.get("section_name", "") for s in resume_draft.get("sections", [])]
    available_sections.append("cover_letter")

    prompt = FEEDBACK_INTERPRETATION_PROMPT.format(
        resume_version=state.get("resume_version_id", "current"),
        cl_version=state.get("cl_version_id", "current"),
        available_sections=", ".join(available_sections),
        feedback_raw=feedback_raw,
    )

    llm = get_llm_client()
    result = llm.complete_json(prompt, model=settings.haiku_model, max_tokens=1024)

    elapsed = int((time.time() - start) * 1000)
    log.info(
        "agent.complete",
        agent="Feedback_Interpreter_Agent",
        session_id=state["session_id"],
        duration_ms=elapsed,
        action=result.get("action"),
        targets=len(result.get("targets", [])),
        clarification_needed=result.get("clarification_needed", False),
    )

    return {
        **state,
        "feedback_parsed": result,
        "status": "awaiting_action" if result.get("clarification_needed") else "feedback_interpreted",
    }
