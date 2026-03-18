"""Generation API schemas."""
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    jd_id: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    jd_id: str
    iteration_count: int
    gap_analysis: dict | None
    resume_version_id: str | None
    cl_version_id: str | None


class FeedbackRequest(BaseModel):
    type: str
    content: str


class VersionResponse(BaseModel):
    id: str
    version_number: int
    critic_score: float | None
    is_approved: bool
    created_at: str
