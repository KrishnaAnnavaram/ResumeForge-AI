"""
api/routes.py — All FastAPI route handlers.

Routes:
  POST   /api/graph/run              Start new LangGraph run
  GET    /api/graph/status/{run_id}  Poll graph status
  POST   /api/graph/resume/{run_id}  Resume after interrupt
  GET    /api/resume/{resume_id}     Get resume text + PDF URL
  GET    /api/logs                   Get all logs for current user
  POST   /api/profile                Create/update profile
  GET    /api/profile                Get current user profile

All routes require valid Supabase JWT.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from backend.api.auth import get_current_user_id
from backend.core.exceptions import NotFoundError, RunNotFound, ValidationError
from backend.core.guardrails import (
    validate_company_name,
    validate_feedback_rating,
    validate_jd_text,
    validate_job_title,
)
from backend.core.logger import get_logger
from backend.core.rate_limit import check_global_limit, check_graph_run_limit, check_profile_update_limit

logger = get_logger(__name__)
router = APIRouter(prefix="/api")


# ── Request / Response models ─────────────────────────────────────────────────

class GraphRunRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    job_title: str = Field(..., min_length=1, max_length=200)
    jd_text: str = Field(..., min_length=50, max_length=10_000)


class GraphResumeRequest(BaseModel):
    user_confirmed: Optional[bool] = None
    is_confirmed: Optional[bool] = None
    wants_cover_letter: Optional[bool] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_notes: Optional[str] = Field(None, max_length=2000)
    applied: Optional[bool] = None
    applied_on: Optional[str] = None


class ProfileUpsertRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    raw_resume_text: Optional[str] = Field(None, max_length=8_000)
    skills_json: Optional[list] = None
    soft_skills_json: Optional[list] = None
    experience_json: Optional[list] = None
    education_json: Optional[list] = None
    certifications_json: Optional[list] = None


# ── Graph routes ──────────────────────────────────────────────────────────────

@router.post("/graph/run")
async def start_graph_run(
    body: GraphRunRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Start a new LangGraph run for a job description."""
    await check_global_limit(user_id)
    await check_graph_run_limit(user_id)

    # Validate inputs
    jd_text = validate_jd_text(body.jd_text)
    company_name = validate_company_name(body.company_name)
    job_title = validate_job_title(body.job_title)

    graph_app = request.app.state.graph
    run_id = str(uuid.uuid4())

    initial_state = {
        "user_id": user_id,
        "job_id": "",
        "jd_text": jd_text,
        "company_name": company_name,
        "job_title": job_title,
        "ats_score": 0.0,
        "ats_gap": {},
        "jd_keywords": {},
        "resume_text": "",
        "resume_version": 0,
        "retry_count": 0,
        "user_confirmed": False,
        "is_confirmed": False,
        "wants_cover_letter": False,
        "resume_id": "",
        "cover_letter_text": "",
        "cover_letter_id": "",
        "resume_pdf_url": "",
        "cover_pdf_url": "",
        "applied": False,
        "applied_on": None,
        "feedback_rating": None,
        "feedback_notes": "",
        "error_message": None,
        "run_id": run_id,
    }

    config = {"configurable": {"thread_id": run_id}}

    # Start graph in background (non-blocking)
    import asyncio
    asyncio.create_task(
        _run_graph(graph_app, initial_state, config)
    )

    logger.info(
        "Graph run started",
        user_id=user_id,
        run_id=run_id,
        company_name=company_name,
        job_title=job_title,
    )

    return {"run_id": run_id, "status": "running"}


async def _run_graph(graph_app, initial_state: dict, config: dict) -> None:
    """Execute graph in background. Runs until first interrupt or completion."""
    try:
        async for _ in graph_app.astream(initial_state, config=config):
            pass
    except Exception as exc:
        logger.error("Graph run failed", error=str(exc), config=config)


@router.get("/graph/status/{run_id}")
async def get_graph_status(
    run_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Poll graph status for a run. Returns current state snapshot."""
    await check_global_limit(user_id)

    graph_app = request.app.state.graph
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph_app.aget_state(config)
    except Exception as exc:
        raise RunNotFound(f"Run {run_id} not found")

    if state is None:
        raise RunNotFound(f"Run {run_id} not found")

    # Determine status
    values = state.values if hasattr(state, "values") else {}

    # Check ownership
    if values.get("user_id") and values["user_id"] != user_id:
        from backend.core.exceptions import AuthorizationError
        raise AuthorizationError("You do not own this run")

    # Determine interrupt node
    next_nodes = state.next if hasattr(state, "next") else []
    interrupt_node = next_nodes[0] if next_nodes else None

    if not next_nodes:
        status = "complete"
    elif interrupt_node in {"show_ats", "show_resume", "cover_letter_ask", "show_cover_letter"}:
        status = "interrupted"
    else:
        status = "running"

    return {
        "run_id": run_id,
        "status": status,
        "interrupt_node": interrupt_node,
        "state": {
            "ats_score": values.get("ats_score"),
            "ats_gap": values.get("ats_gap"),
            "jd_keywords": values.get("jd_keywords"),
            "resume_text": values.get("resume_text"),
            "resume_version": values.get("resume_version"),
            "resume_id": values.get("resume_id"),
            "cover_letter_text": values.get("cover_letter_text"),
            "cover_letter_id": values.get("cover_letter_id"),
            "job_id": values.get("job_id"),
            "error_message": values.get("error_message"),
        },
    }


@router.post("/graph/resume/{run_id}")
async def resume_graph(
    run_id: str,
    body: GraphResumeRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Resume a paused graph after a human-in-the-loop interrupt."""
    await check_global_limit(user_id)

    graph_app = request.app.state.graph
    config = {"configurable": {"thread_id": run_id}}

    # Build state update from non-None fields
    state_update = {}
    if body.user_confirmed is not None:
        state_update["user_confirmed"] = body.user_confirmed
    if body.is_confirmed is not None:
        state_update["is_confirmed"] = body.is_confirmed
        if body.is_confirmed:
            # Confirm resume in DB
            state_result = await graph_app.aget_state(config)
            resume_id = (state_result.values or {}).get("resume_id")
            if resume_id:
                mcp = request.app.state.mcp
                await mcp.call_tool(
                    server="storage-mcp",
                    tool="confirm_resume",
                    resume_id=resume_id,
                    user_id=user_id,
                )
    if body.wants_cover_letter is not None:
        state_update["wants_cover_letter"] = body.wants_cover_letter
    if body.feedback_rating is not None:
        state_update["feedback_rating"] = validate_feedback_rating(body.feedback_rating)
    if body.feedback_notes is not None:
        state_update["feedback_notes"] = body.feedback_notes
    if body.applied is not None:
        state_update["applied"] = body.applied
    if body.applied_on is not None:
        state_update["applied_on"] = body.applied_on

    if state_update:
        await graph_app.aupdate_state(config, state_update)

    # Continue graph execution
    import asyncio
    asyncio.create_task(_run_graph(graph_app, None, config))

    return {"run_id": run_id, "status": "running"}


# ── Resume routes ─────────────────────────────────────────────────────────────

@router.get("/resume/{resume_id}")
async def get_resume(
    resume_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get resume text and PDF URL for a given resume_id."""
    await check_global_limit(user_id)

    mcp = request.app.state.mcp
    result = await mcp.call_tool(
        server="storage-mcp",
        tool="get_resume_by_id",
        resume_id=resume_id,
        user_id=user_id,
    )
    if "error" in result:
        from backend.core.exceptions import ResumeNotFound
        raise ResumeNotFound(f"Resume {resume_id} not found")

    return result["resume"]


# ── Log routes ────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    limit: int = 20,
    offset: int = 0,
):
    """Get paginated application logs for the current user."""
    await check_global_limit(user_id)

    mcp = request.app.state.mcp
    result = await mcp.call_tool(
        server="log-mcp",
        tool="get_all_logs",
        user_id=user_id,
        limit=min(limit, 100),
        offset=offset,
    )
    stats = await mcp.call_tool(
        server="log-mcp",
        tool="get_stats",
        user_id=user_id,
    )
    return {"logs": result.get("logs", []), "stats": stats}


# ── Profile routes ────────────────────────────────────────────────────────────

@router.post("/profile")
async def upsert_profile(
    body: ProfileUpsertRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Create or update user profile."""
    await check_global_limit(user_id)
    await check_profile_update_limit(user_id)

    mcp = request.app.state.mcp
    fields = body.model_dump(exclude_none=True)

    result = await mcp.call_tool(
        server="profile-mcp",
        tool="upsert_profile",
        user_id=user_id,
        fields=fields,
    )
    if "error" in result:
        raise ValidationError(f"Profile update failed: {result['error']}")

    return result["profile"]


@router.get("/profile")
async def get_profile(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get current user profile."""
    await check_global_limit(user_id)

    mcp = request.app.state.mcp
    result = await mcp.call_tool(
        server="profile-mcp",
        tool="get_profile",
        user_id=user_id,
    )
    if "error" in result:
        from backend.core.exceptions import ProfileNotFound
        raise ProfileNotFound("Profile not found — please create one first")

    return result
