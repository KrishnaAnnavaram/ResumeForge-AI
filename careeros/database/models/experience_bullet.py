"""ExperienceBullet model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from careeros.database.base import Base, TimestampMixin


class ExperienceBullet(Base, TimestampMixin):
    __tablename__ = "experience_bullets"
    __table_args__ = (
        Index("ix_bullets_user_canonical_impact", "user_id", "is_canonical", "impact_level"),
        Index("ix_bullets_skills_used_gin", "skills_used", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    experience_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    skills_used: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False, server_default="{}")
    impact_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    experience: Mapped["Experience"] = relationship("Experience", back_populates="bullets")
