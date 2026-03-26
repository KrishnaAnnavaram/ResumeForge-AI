"""
agents/feedback_log.py — Application log write node.

Final node in the graph. Writes to application_logs via log-mcp.
cover_letter_id is nullable — user may have skipped cover letter.
"""

from backend.agents.state import ResumeState
from backend.core.logger import get_logger
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)


async def feedback_log_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """
    LangGraph node: persist application log.
    Returns partial state update dict.
    """
    user_id = state["user_id"]
    job_id = state["job_id"]
    resume_id = state.get("resume_id", "")
    cover_letter_id = state.get("cover_letter_id") or None  # nullable

    feedback_rating = state.get("feedback_rating")
    feedback_notes = state.get("feedback_notes", "")
    applied = state.get("applied", False)
    applied_on = state.get("applied_on")

    logger.info(
        "Feedback log node started",
        user_id=user_id,
        job_id=job_id,
        resume_id=resume_id,
        has_cover_letter=cover_letter_id is not None,
    )

    result = await mcp.call_tool(
        server="log-mcp",
        tool="append_log",
        user_id=user_id,
        job_id=job_id,
        resume_id=resume_id,
        cover_letter_id=cover_letter_id,
        applied=applied,
        applied_on=applied_on,
        feedback_rating=feedback_rating,
        feedback_notes=feedback_notes,
    )

    if "error" in result:
        logger.error("Failed to append application log", error=result)
        # Non-fatal — don't block the user flow
        return {}

    log_id = result["log_id"]
    logger.info("Application log appended", user_id=user_id, log_id=log_id)

    return {}
