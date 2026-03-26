"""
agents/cover_letter.py — Claude Sonnet cover letter generation node.

Only runs after Gate 3 (wants_cover_letter = True).
Never auto-generates — always waits for user confirmation.
"""

from backend.agents.state import ResumeState
from backend.core.logger import get_logger
from backend.llm.claude_client import generate_cover_letter
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)


async def cover_letter_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """
    LangGraph node: cover letter generation.
    Returns partial state update dict.
    """
    user_id = state["user_id"]
    job_id = state["job_id"]
    resume_id = state["resume_id"]
    job_title = state.get("job_title", "")
    company_name = state.get("company_name", "")
    jd_text = state.get("jd_text", "")

    logger.info("Cover letter node started", user_id=user_id, job_id=job_id)

    # 1. Fetch soft skills from profile
    soft_skills_result = await mcp.call_tool(
        server="profile-mcp",
        tool="get_soft_skills",
        user_id=user_id,
    )
    soft_skills = []
    if not mcp.profile._is_error(soft_skills_result):
        soft_skills = soft_skills_result.get("soft_skills", [])

    # 2. Fetch full profile for contact details
    profile_result = await mcp.call_tool(
        server="profile-mcp",
        tool="get_profile",
        user_id=user_id,
    )
    if "error" in profile_result:
        return {"error_message": f"Profile fetch failed: {profile_result['error']}"}

    profile = profile_result

    # 3. Generate cover letter with Claude Sonnet
    try:
        cover_text = await generate_cover_letter(
            profile=profile,
            job_title=job_title,
            company_name=company_name,
            jd_text=jd_text,
            soft_skills=soft_skills,
        )
    except Exception as exc:
        logger.error("Cover letter generation failed", error=str(exc))
        return {"error_message": f"Cover letter generation failed: {exc}"}

    # 4. Save cover letter via storage-mcp
    save_result = await mcp.call_tool(
        server="storage-mcp",
        tool="save_cover_letter",
        user_id=user_id,
        resume_id=resume_id,
        job_id=job_id,
        generated_text=cover_text,
        soft_skills_used=soft_skills,
        pdf_url=None,   # PDF generated on demand via docgen-mcp
    )
    if "error" in save_result:
        return {"error_message": f"Cover letter save failed: {save_result['error']}"}

    cover_letter_id = save_result["cover_letter_id"]

    logger.info(
        "Cover letter complete",
        user_id=user_id,
        cover_letter_id=cover_letter_id,
        soft_skills_used=soft_skills,
    )

    return {
        "cover_letter_text": cover_text,
        "cover_letter_id": cover_letter_id,
    }
