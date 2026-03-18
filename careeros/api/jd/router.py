"""JD API router."""
import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from careeros.api.jd.schemas import JDAnalyzeRequest, JDResponse
from careeros.agents.jd_parser_agent import run_jd_parser_agent
from careeros.database.models.job_description import JobDescription
from careeros.dependencies import CurrentUser, DB

router = APIRouter(prefix="/jd", tags=["job-descriptions"])


@router.post("/analyze", response_model=JDResponse)
async def analyze_jd(request: JDAnalyzeRequest, current_user: CurrentUser, db: DB):
    state = {
        "session_id": "api_direct",
        "user_id": str(current_user.id),
        "jd_raw": request.raw_text,
        "jd_id": None,
        "jd_structured": None,
        "profile": None,
        "match_score": None,
        "layer1_warnings": [],
        "evidence_set": None,
        "gap_analysis": None,
        "low_evidence_warning": False,
        "rewrite_plan": None,
        "resume_draft": None,
        "cl_draft": None,
        "resume_version_id": None,
        "cl_version_id": None,
        "critic_report": None,
        "critic_retry_count": 0,
        "user_feedback_raw": None,
        "feedback_parsed": None,
        "iteration": 0,
        "status": "active",
        "error": None,
        "should_stream": False,
    }
    result = await run_jd_parser_agent(state, db)
    jd_structured = result["jd_structured"]

    if request.source_url:
        jd_result = await db.execute(select(JobDescription).where(JobDescription.id == uuid.UUID(result["jd_id"])))
        jd_obj = jd_result.scalar_one_or_none()
        if jd_obj:
            jd_obj.source_url = request.source_url

    return JDResponse(
        jd_id=result["jd_id"],
        company=jd_structured.get("company"),
        role_title=jd_structured.get("role_title"),
        seniority=jd_structured.get("seniority"),
        required_skills=jd_structured.get("required_skills", []),
        preferred_skills=jd_structured.get("preferred_skills", []),
        ats_keywords=jd_structured.get("ats_keywords", []),
        domain=jd_structured.get("domain"),
        parse_confidence=jd_structured.get("parse_confidence", 0.0),
        parse_warnings=jd_structured.get("parse_warnings", []),
        match_score=None,
    )


@router.get("/{jd_id}", response_model=JDResponse)
async def get_jd(jd_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id, JobDescription.user_id == current_user.id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="JD not found")
    return JDResponse(
        jd_id=str(jd.id),
        company=jd.company,
        role_title=jd.role_title,
        seniority=jd.seniority,
        required_skills=jd.required_skills or [],
        preferred_skills=jd.preferred_skills or [],
        ats_keywords=jd.ats_keywords or [],
        domain=jd.domain,
        parse_confidence=float(jd.parse_confidence) if jd.parse_confidence else 0.0,
        parse_warnings=jd.parse_warnings or [],
        match_score=float(jd.match_score) if jd.match_score else None,
    )


@router.get("", response_model=list[JDResponse])
async def list_jds(current_user: CurrentUser, db: DB, limit: int = 20, offset: int = 0):
    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .limit(limit).offset(offset)
    )
    return [
        JDResponse(
            jd_id=str(jd.id),
            company=jd.company,
            role_title=jd.role_title,
            seniority=jd.seniority,
            required_skills=jd.required_skills or [],
            preferred_skills=jd.preferred_skills or [],
            ats_keywords=jd.ats_keywords or [],
            domain=jd.domain,
            parse_confidence=float(jd.parse_confidence) if jd.parse_confidence else 0.0,
            parse_warnings=jd.parse_warnings or [],
            match_score=float(jd.match_score) if jd.match_score else None,
        )
        for jd in result.scalars().all()
    ]
