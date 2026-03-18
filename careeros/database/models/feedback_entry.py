"""FeedbackEntry model."""
import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from careeros.database.base import Base, TimestampMixin


class FeedbackEntry(Base, TimestampMixin):
    __tablename__ = "feedback_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("generated_resumes.id", ondelete="SET NULL"), nullable=True)
    cl_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("generated_cover_letters.id", ondelete="SET NULL"), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    feedback_raw: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_parsed: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    acted_on: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    session: Mapped["GenerationSession"] = relationship("GenerationSession", back_populates="feedback_entries")
