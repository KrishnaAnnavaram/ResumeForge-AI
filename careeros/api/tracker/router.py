"""Tracker API router — application tracking with event log."""
import uuid
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from careeros.api.tracker.schemas import (
    ApplicationCreate, StatusUpdateRequest, NoteRequest,
    EventResponse, ApplicationResponse,
)
from careeros.database.models.application import Application, ApplicationEvent
from careeros.dependencies import CurrentUser, DB

router = APIRouter(prefix="/tracker", tags=["tracker"])


def _app_to_response(a: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=str(a.id),
        company=a.company,
        role_title=a.role_title,
        status=a.status,
        applied_date=str(a.applied_date),
        source_platform=a.source_platform,
        job_url=a.job_url,
        notes=a.notes,
        created_at=str(a.created_at),
    )


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(request: ApplicationCreate, current_user: CurrentUser, db: DB):
    app = Application(
        user_id=current_user.id,
        company=request.company,
        role_title=request.role_title,
        applied_date=request.applied_date,
        session_id=uuid.UUID(request.session_id) if request.session_id else None,
        source_platform=request.source_platform,
        job_url=request.job_url,
        notes=request.notes,
    )
    db.add(app)
    await db.flush()

    # Append initial event
    event = ApplicationEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="status_change",
        old_value=None,
        new_value="applied",
        note="Application created",
    )
    db.add(event)
    return _app_to_response(app)


@router.get("/applications", response_model=list[ApplicationResponse])
async def list_applications(
    current_user: CurrentUser,
    db: DB,
    application_status: str | None = Query(None, alias="status"),
    company: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    query = select(Application).where(Application.user_id == current_user.id)
    if application_status:
        query = query.where(Application.status == application_status)
    if company:
        query = query.where(Application.company.ilike(f"%{company}%"))
    query = query.order_by(Application.applied_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return [_app_to_response(a) for a in result.scalars().all()]


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == current_user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _app_to_response(app)


@router.patch("/applications/{application_id}/status")
async def update_status(application_id: uuid.UUID, request: StatusUpdateRequest, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == current_user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    old_status = app.status
    app.status = request.new_status

    # APPEND-ONLY event
    event = ApplicationEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="status_change",
        old_value=old_status,
        new_value=request.new_status,
        note=request.note,
    )
    db.add(event)
    return {"status": request.new_status, "application_id": str(application_id)}


@router.post("/applications/{application_id}/notes")
async def add_note(application_id: uuid.UUID, request: NoteRequest, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == current_user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    event = ApplicationEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="note_added",
        note=request.content,
    )
    db.add(event)
    return {"status": "note_added"}


@router.get("/applications/{application_id}/events", response_model=list[EventResponse])
async def get_events(application_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id, ApplicationEvent.user_id == current_user.id)
        .order_by(ApplicationEvent.occurred_at.asc())
    )
    return [
        EventResponse(
            id=str(e.id),
            event_type=e.event_type,
            old_value=e.old_value,
            new_value=e.new_value,
            note=e.note,
            occurred_at=str(e.occurred_at),
        )
        for e in result.scalars().all()
    ]


@router.get("/applications/{application_id}/documents")
async def get_application_documents(application_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == current_user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return {
        "resume_version_id": str(app.resume_version_id) if app.resume_version_id else None,
        "cl_version_id": str(app.cl_version_id) if app.cl_version_id else None,
    }
