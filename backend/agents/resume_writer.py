"""
agents/resume_writer.py — GPT-4o bullet rewriting → Claude Sonnet assembly.

Step 1: Extract all experience bullets from the user's profile.
Step 2: Match each bullet to a rewrite hint from Claude's gap JSON.
Step 3: Call GPT-4o to rewrite bullets (ONLY GPT-4o writes bullets).
Step 4: Call Claude Sonnet to assemble the full resume from the rewritten bullets.
Step 5: Save the resume via storage-mcp.
"""

from backend.agents.state import ResumeState
from backend.core.logger import get_logger
from backend.llm.claude_client import assemble_resume
from backend.llm.gpt_client import rewrite_bullets
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)


async def resume_writer_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """
    LangGraph node: resume generation.
    Returns partial state update dict.
    """
    user_id = state["user_id"]
    job_id = state["job_id"]
    job_title = state.get("job_title", "")
    company_name = state.get("company_name", "")
    jd_keywords = state.get("jd_keywords", {})
    ats_gap = state.get("ats_gap", {})
    retry_count = state.get("retry_count", 0)
    resume_version = state.get("resume_version", 0) + 1

    logger.info(
        "Resume writer started",
        user_id=user_id,
        job_id=job_id,
        version=resume_version,
        retry=retry_count,
    )

    # 1. Fetch full profile
    profile_result = await mcp.call_tool(
        server="profile-mcp", tool="get_profile", user_id=user_id
    )
    if "error" in profile_result:
        return {"error_message": f"Profile fetch failed: {profile_result['error']}"}

    profile = profile_result

    # 2. Extract bullets from experience_json + match with rewrite hints
    experience_json = profile.get("experience_json", [])
    rewrite_hints = ats_gap.get("rewrite_hints", [])

    # Build a lookup of section → hint
    hint_by_section: dict[str, str] = {}
    for rh in rewrite_hints:
        if isinstance(rh, dict):
            hint_by_section[rh.get("section", "")] = rh.get("hint", "")

    bullets_to_rewrite = []
    for exp in experience_json:
        if not isinstance(exp, dict):
            continue
        for bullet in exp.get("bullets", []):
            if isinstance(bullet, str) and bullet.strip():
                bullets_to_rewrite.append({
                    "original": bullet,
                    "hint": hint_by_section.get("experience", ""),
                })

    # 3. GPT-4o rewrites bullets (GPT-4o responsibility — never changes)
    if bullets_to_rewrite:
        try:
            rewritten = await rewrite_bullets(
                bullets=bullets_to_rewrite,
                job_title=job_title,
            )
        except Exception as exc:
            logger.error("GPT-4o bullet rewrite failed", error=str(exc))
            # Fall back to original bullets on GPT failure
            rewritten = [b["original"] for b in bullets_to_rewrite]
            logger.warning("Falling back to original bullets")
    else:
        rewritten = []

    # 4. Claude Sonnet assembles full resume
    try:
        resume_text = await assemble_resume(
            profile=profile,
            rewritten_bullets=rewritten,
            jd_keywords=jd_keywords,
            gap_json=ats_gap,
            job_title=job_title,
            company_name=company_name,
        )
    except Exception as exc:
        logger.error("Claude resume assembly failed", error=str(exc))
        return {"error_message": f"Resume assembly failed: {exc}"}

    # 5. Save resume via storage-mcp
    save_result = await mcp.call_tool(
        server="storage-mcp",
        tool="save_resume",
        user_id=user_id,
        job_id=job_id,
        version=resume_version,
        resume_text=resume_text,
        ats_score_final=0.0,   # will be updated by ats_rescorer
    )
    if "error" in save_result:
        return {"error_message": f"Resume save failed: {save_result['error']}"}

    resume_id = save_result["resume_id"]

    logger.info(
        "Resume writer complete",
        user_id=user_id,
        job_id=job_id,
        resume_id=resume_id,
        version=resume_version,
        bullet_count=len(rewritten),
    )

    return {
        "resume_text": resume_text,
        "resume_id": resume_id,
        "resume_version": resume_version,
        "retry_count": retry_count,
    }
