"""
agents/ats_analyzer.py — Claude Opus ATS analysis node.

Responsibilities:
1. Fetch user profile via profile-mcp
2. Call Claude Opus to extract JD keywords and compute initial ATS score
3. Validate Claude's output via guardrails
4. Save job + gap JSON via storage-mcp
5. Update state with ats_score, jd_keywords, ats_gap, job_id
"""

from backend.agents.state import ResumeState
from backend.core.guardrails import (
    validate_ats_score,
    validate_gap_json,
    validate_keywords_dict,
)
from backend.core.logger import get_logger
from backend.llm.claude_client import analyze_jd
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)


async def ats_analyzer_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """
    LangGraph node: ATS analysis.
    Returns partial state update dict.
    """
    user_id = state["user_id"]
    jd_text = state["jd_text"]
    company_name = state.get("company_name", "")
    job_title = state.get("job_title", "")

    logger.info("ATS analyzer started", user_id=user_id)

    # 1. Fetch user profile
    profile_result = await mcp.call_tool(
        server="profile-mcp", tool="get_profile", user_id=user_id
    )
    if "error" in profile_result:
        logger.error("Failed to fetch profile", user_id=user_id, error=profile_result)
        return {"error_message": f"Profile fetch failed: {profile_result['error']}"}

    profile = profile_result

    # 2. Call Claude Opus — deep JD analysis
    try:
        analysis = await analyze_jd(jd_text=jd_text, profile=profile)
    except Exception as exc:
        logger.error("Claude ATS analysis failed", error=str(exc))
        return {"error_message": f"ATS analysis failed: {exc}"}

    # 3. Validate LLM outputs
    jd_keywords = validate_keywords_dict(analysis.get("jd_keywords", {}))
    ats_score = validate_ats_score(analysis.get("ats_score", 0))

    gap_json = validate_gap_json({
        "missing_keywords": analysis.get("missing_keywords", []),
        "experience_gaps": analysis.get("experience_gaps", []),
        "section_scores": analysis.get("section_scores", {}),
        "matched_keywords": analysis.get("matched_keywords", []),
        "rewrite_hints": analysis.get("rewrite_hints", []),
    })

    # 4. Save job to DB via storage-mcp
    save_result = await mcp.call_tool(
        server="storage-mcp",
        tool="save_job",
        user_id=user_id,
        company_name=company_name,
        job_title=job_title,
        jd_text=jd_text,
        keywords_json=jd_keywords,
        ats_score=ats_score,
        gap_json=gap_json,
    )
    if "error" in save_result:
        logger.error("Failed to save job", error=save_result)
        return {"error_message": f"Job save failed: {save_result['error']}"}

    job_id = save_result["job_id"]

    logger.info(
        "ATS analysis complete",
        user_id=user_id,
        job_id=job_id,
        ats_score=ats_score,
        missing_keywords=len(gap_json.get("missing_keywords", [])),
    )

    return {
        "job_id": job_id,
        "ats_score": ats_score,
        "jd_keywords": jd_keywords,
        "ats_gap": gap_json,
        "user_confirmed": False,   # reset gate for fresh run
        "retry_count": 0,
        "resume_version": 0,
    }
