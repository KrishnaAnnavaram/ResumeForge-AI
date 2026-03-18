"""User model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from careeros.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    profiles: Mapped[list["Profile"]] = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
    experiences: Mapped[list["Experience"]] = relationship("Experience", back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship("Skill", back_populates="user", cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship("Education", back_populates="user", cascade="all, delete-orphan")
    certifications: Mapped[list["Certification"]] = relationship("Certification", back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    job_descriptions: Mapped[list["JobDescription"]] = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    generation_sessions: Mapped[list["GenerationSession"]] = relationship("GenerationSession", back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
