"""Generation API router — manages generation sessions and streaming."""
import asyncio
import json
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from careeros.api.generation.schemas import CreateSessionRequest, SessionResponse, FeedbackRequest, VersionResponse
from careeros.database.models.generation_session import GenerationSession
from careeros.database.models.job_description import JobDescription
from careeros.database.models.generated_resume import GeneratedResume
from careeros.database.models.generated_cover_letter import GeneratedCoverLetter
from careeros.database.models.feedback_entry import FeedbackEntry
from careeros.dependencies import CurrentUser, DB
from careeros.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/generation", tags=["generation"])


def _session_to_response(session: GenerationSession) -> SessionResponse:
    return SessionResponse(
        session_id=str(session.id),
        status=session.status,
        jd_id=str(session.jd_id),
        iteration_count=session.iteration_count,
        gap_analysis=session.gap_analysis,
        resume_version_id=str(session.current_resume_version_id) if session.current_resume_version_id else None,
        cl_version_id=str(session.current_cl_version_id) if session.current_cl_version_id else None,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest, current_user: CurrentUser, db: DB):
    # Verify JD exists and belongs to user
    jd_result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == uuid.UUID(request.jd_id),
            JobDescription.user_id == current_user.id,
        )
    )
    jd = jd_result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

    session = GenerationSession(
        user_id=current_user.id,
        jd_id=jd.id,
        status="active",
    )
    db.add(session)
    await db.flush()
    return _session_to_response(session)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _session_to_response(session)


@router.get("/sessions/{session_id}/stream")
async def stream_generation(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """SSE endpoint for live agent pipeline status."""
    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == session.jd_id))
    jd = jd_result.scalar_one_or_none()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Run the generation pipeline and stream SSE events."""
        from careeros.agents.state import CareerOSState

        initial_state: CareerOSState = {
            "session_id": str(session_id),
            "user_id": str(current_user.id),
            "jd_raw": jd.raw_text if jd else "",
            "jd_id": str(session.jd_id),
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
            "status": "generating",
            "error": None,
            "should_stream": True,
        }

        agent_sequence = [
            ("load_profile", "Loading career profile"),
            ("parse_jd", "Parsing job description"),
            ("retrieve_evidence", "Retrieving evidence"),
            ("analyze_gaps", "Analyzing skill gaps"),
            ("plan_rewrite", "Planning resume strategy"),
            ("generate_resume", "Writing resume"),
            ("generate_cl", "Writing cover letter"),
            ("critic_validate", "Validating content"),
        ]

        try:
            from careeros.agents.profile_loader_agent import run_profile_loader_agent
            from careeros.agents.jd_parser_agent import run_jd_parser_agent
            from careeros.agents.retrieval_agent import run_retrieval_agent
            from careeros.agents.gap_analyzer_agent import run_gap_analyzer_agent
            from careeros.agents.rewrite_planner_agent import run_rewrite_planner_agent
            from careeros.agents.resume_writer_agent import run_resume_writer_agent
            from careeros.agents.cover_letter_writer_agent import run_cover_letter_writer_agent
            from careeros.agents.critic_agent import run_critic_agent
            from careeros.database.connection import AsyncSessionLocal

            state = initial_state
            for agent_key, agent_label in agent_sequence:
                yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent_key, 'label': agent_label})}\n\n"
                await asyncio.sleep(0.05)

                try:
                    async with AsyncSessionLocal() as agent_db:
                        if agent_key == "load_profile":
                            state = await run_profile_loader_agent(state, agent_db)
                        elif agent_key == "parse_jd":
                            state = await run_jd_parser_agent(state, agent_db)
                            await agent_db.commit()
                        elif agent_key == "retrieve_evidence":
                            state = await run_retrieval_agent(state, agent_db)
                        elif agent_key == "analyze_gaps":
                            state = await run_gap_analyzer_agent(state, agent_db)
                        elif agent_key == "plan_rewrite":
                            state = await run_rewrite_planner_agent(state, agent_db)
                        elif agent_key == "generate_resume":
                            state = await run_resume_writer_agent(state, agent_db)
                            await agent_db.commit()
                        elif agent_key == "generate_cl":
                            state = await run_cover_letter_writer_agent(state, agent_db)
                            await agent_db.commit()
                        elif agent_key == "critic_validate":
                            state = await run_critic_agent(state, agent_db)
                            await agent_db.commit()

                    yield f"data: {json.dumps({'type': 'agent_complete', 'agent': agent_key})}\n\n"

                except Exception as exc:
                    log.error("stream.agent_failed", agent=agent_key, error=str(exc))
                    yield f"data: {json.dumps({'type': 'agent_error', 'agent': agent_key, 'error': str(exc)})}\n\n"

            # Update session with results
            async with AsyncSessionLocal() as final_db:
                final_result = await final_db.execute(select(GenerationSession).where(GenerationSession.id == session_id))
                gen_session = final_result.scalar_one_or_none()
                if gen_session:
                    gen_session.status = "awaiting_feedback"
                    gen_session.gap_analysis = state.get("gap_analysis")
                    gen_session.rewrite_plan = state.get("rewrite_plan")
                    gen_session.retrieved_evidence = {"count": len(state.get("evidence_set") or [])}
                    if state.get("resume_version_id"):
                        gen_session.current_resume_version_id = uuid.UUID(state["resume_version_id"])
                    if state.get("cl_version_id"):
                        gen_session.current_cl_version_id = uuid.UUID(state["cl_version_id"])
                await final_db.commit()

            yield f"data: {json.dumps({'type': 'complete', 'session_id': str(session_id), 'resume_version_id': state.get('resume_version_id'), 'cl_version_id': state.get('cl_version_id'), 'gap_analysis': state.get('gap_analysis'), 'critic_report': state.get('critic_report'), 'warnings': state.get('layer1_warnings', [])})}\n\n"

        except Exception as exc:
            log.error("stream.pipeline_failed", session_id=str(session_id), error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/feedback")
async def submit_feedback(session_id: uuid.UUID, request: FeedbackRequest, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    entry = FeedbackEntry(
        session_id=session_id,
        user_id=current_user.id,
        resume_version_id=session.current_resume_version_id,
        cl_version_id=session.current_cl_version_id,
        feedback_type=request.type,
        feedback_raw=request.content,
    )
    db.add(entry)
    await db.flush()
    return {"feedback_id": str(entry.id), "status": "received"}


@router.post("/sessions/{session_id}/approve")
async def approve_session(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    from datetime import datetime, timezone

    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.current_resume_version_id:
        resume_result = await db.execute(select(GeneratedResume).where(GeneratedResume.id == session.current_resume_version_id))
        resume = resume_result.scalar_one_or_none()
        if resume:
            resume.is_approved = True
            resume.approved_at = datetime.now(timezone.utc)

    if session.current_cl_version_id:
        cl_result = await db.execute(select(GeneratedCoverLetter).where(GeneratedCoverLetter.id == session.current_cl_version_id))
        cl = cl_result.scalar_one_or_none()
        if cl:
            cl.is_approved = True
            cl.approved_at = datetime.now(timezone.utc)

    session.status = "approved"
    return {"status": "approved", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/abandon")
async def abandon_session(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.status = "abandoned"
    return {"status": "abandoned"}


@router.get("/sessions/{session_id}/versions")
async def list_versions(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    resumes = await db.execute(
        select(GeneratedResume)
        .where(GeneratedResume.session_id == session_id, GeneratedResume.user_id == current_user.id)
        .order_by(GeneratedResume.version_number.desc())
    )
    cls = await db.execute(
        select(GeneratedCoverLetter)
        .where(GeneratedCoverLetter.session_id == session_id, GeneratedCoverLetter.user_id == current_user.id)
        .order_by(GeneratedCoverLetter.version_number.desc())
    )
    return {
        "resumes": [
            VersionResponse(
                id=str(r.id),
                version_number=r.version_number,
                critic_score=float(r.critic_score) if r.critic_score else None,
                is_approved=r.is_approved,
                created_at=str(r.created_at),
            )
            for r in resumes.scalars().all()
        ],
        "cover_letters": [
            VersionResponse(
                id=str(cl.id),
                version_number=cl.version_number,
                critic_score=float(cl.critic_score) if cl.critic_score else None,
                is_approved=cl.is_approved,
                created_at=str(cl.created_at),
            )
            for cl in cls.scalars().all()
        ],
    }


@router.get("/sessions/{session_id}/evidence")
async def get_evidence(session_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(GenerationSession).where(
            GenerationSession.id == session_id,
            GenerationSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"evidence": session.retrieved_evidence or {}}
