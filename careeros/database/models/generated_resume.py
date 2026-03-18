"""GeneratedResume model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, Numeric, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from careeros.database.base import Base, TimestampMixin


class GeneratedResume(Base, TimestampMixin):
    __tablename__ = "generated_resumes"
    __table_args__ = (
        UniqueConstraint("session_id", "version_number", name="uq_resume_session_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    claim_evidence_map: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    critic_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    critic_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped["GenerationSession"] = relationship("GenerationSession", back_populates="resumes", foreign_keys=[session_id])
