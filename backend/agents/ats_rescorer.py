"""
agents/ats_rescorer.py — Claude Opus re-scoring node.

After resume assembly, re-score the new resume against the JD.
If score >= 95 or retry_count >= 3 → proceed to show_resume.
Otherwise → back to resume_writer for another pass.
"""

from backend.agents.state import ResumeState
from backend.core.config import get_settings
from backend.core.guardrails import validate_ats_score
from backend.core.logger import get_logger
from backend.llm.claude_client import rescore_resume
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)
settings = get_settings()


async def ats_rescorer_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """
    LangGraph node: ATS re-scoring.
    Returns partial state update dict.
    """
    user_id = state["user_id"]
    resume_text = state.get("resume_text", "")
    jd_text = state.get("jd_text", "")
    jd_keywords = state.get("jd_keywords", {})
    resume_id = state.get("resume_id", "")
    retry_count = state.get("retry_count", 0)

    logger.info(
        "ATS rescorer started",
        user_id=user_id,
        resume_id=resume_id,
        attempt=retry_count + 1,
    )

    # 1. Call Claude Opus to re-score
    try:
        result = await rescore_resume(
            resume_text=resume_text,
            jd_text=jd_text,
            jd_keywords=jd_keywords,
        )
    except Exception as exc:
        logger.error("ATS rescore failed", error=str(exc))
        # On failure, increment retry_count — graph will route to show_resume
        # if we hit the limit, rather than looping forever
        return {
            "ats_score": state.get("ats_score", 0.0),
            "retry_count": retry_count + 1,
            "error_message": f"Rescore failed: {exc}",
        }

    new_score = validate_ats_score(result.get("ats_score", 0), "rescore_ats_score")
    section_scores = result.get("section_scores", {})

    # 2. Update resume record with final ATS score via storage-mcp
    if resume_id:
        # Update ats_score_final on the resume row
        try:
            await mcp.call_tool(
                server="storage-mcp",
                tool="update_resume_pdf_url",   # reuse update path
                resume_id=resume_id,
                user_id=user_id,
                pdf_url=state.get("resume_pdf_url", ""),
            )
        except Exception:
            pass  # Non-fatal — score is still returned

        # Direct DB update for ats_score_final
        try:
            db = mcp.storage._db
            await db.table("resumes").update(
                {"ats_score_final": new_score}
            ).eq("id", resume_id).eq("user_id", user_id).execute()
        except Exception as exc:
            logger.warning("Could not update ats_score_final", error=str(exc))

    logger.info(
        "ATS rescore complete",
        user_id=user_id,
        resume_id=resume_id,
        new_score=new_score,
        retry_count=retry_count + 1,
        will_retry=new_score < settings.ats_pass_threshold
            and retry_count + 1 < settings.ats_max_retries,
    )

    # Update gap JSON with new section scores
    ats_gap = dict(state.get("ats_gap", {}))
    ats_gap["section_scores"] = section_scores
    ats_gap["rescore_feedback"] = result.get("feedback", "")

    return {
        "ats_score": new_score,
        "ats_gap": ats_gap,
        "retry_count": retry_count + 1,
    }
