"""Tracker API schemas."""
from datetime import date
from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    company: str
    role_title: str
    applied_date: date
    session_id: str | None = None
    source_platform: str | None = None
    job_url: str | None = None
    notes: str | None = None


class StatusUpdateRequest(BaseModel):
    new_status: str
    note: str | None = None


class NoteRequest(BaseModel):
    content: str


class EventResponse(BaseModel):
    id: str
    event_type: str
    old_value: str | None
    new_value: str | None
    note: str | None
    occurred_at: str


class ApplicationResponse(BaseModel):
    id: str
    company: str
    role_title: str
    status: str
    applied_date: str
    source_platform: str | None
    job_url: str | None
    notes: str | None
    created_at: str
