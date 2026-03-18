"""GenerationSession model."""
import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from careeros.database.base import Base, TimestampMixin


class GenerationSession(Base, TimestampMixin):
    __tablename__ = "generation_sessions"
    __table_args__ = (
        Index("ix_gen_sessions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jd_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    current_resume_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("generated_resumes.id", ondelete="SET NULL"), nullable=True)
    current_cl_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("generated_cover_letters.id", ondelete="SET NULL"), nullable=True)
    retrieved_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gap_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rewrite_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generation_sessions")
    jd: Mapped["JobDescription"] = relationship("JobDescription", back_populates="generation_sessions")
    resumes: Mapped[list["GeneratedResume"]] = relationship(
        "GeneratedResume",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="GeneratedResume.session_id",
    )
    cover_letters: Mapped[list["GeneratedCoverLetter"]] = relationship(
        "GeneratedCoverLetter",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="GeneratedCoverLetter.session_id",
    )
    feedback_entries: Mapped[list["FeedbackEntry"]] = relationship("FeedbackEntry", back_populates="session", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="generation_session")
