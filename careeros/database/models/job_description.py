"""JobDescription model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, DateTime, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from careeros.database.base import Base, TimestampMixin


class JobDescription(Base, TimestampMixin):
    __tablename__ = "job_descriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "raw_text_hash", name="uq_jd_user_hash"),
        Index("ix_jd_required_skills_gin", "required_skills", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_policy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    preferred_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    soft_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    ats_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    responsibilities: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False, server_default="{}")
    seniority_signals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    culture_signals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    hiring_signals: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    match_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    parse_confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    parse_warnings: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False, server_default="{}")
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_descriptions")
    generation_sessions: Mapped[list["GenerationSession"]] = relationship("GenerationSession", back_populates="jd")
