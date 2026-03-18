"""Database models package — imports all models for Alembic discovery."""
from careeros.database.models.user import User
from careeros.database.models.profile import Profile
from careeros.database.models.experience import Experience
from careeros.database.models.experience_bullet import ExperienceBullet
from careeros.database.models.skill import Skill
from careeros.database.models.skill_alias import SkillAlias
from careeros.database.models.education import Education
from careeros.database.models.certification import Certification
from careeros.database.models.document import Document
from careeros.database.models.document_chunk import DocumentChunk
from careeros.database.models.job_description import JobDescription
from careeros.database.models.generation_session import GenerationSession
from careeros.database.models.generated_resume import GeneratedResume
from careeros.database.models.generated_cover_letter import GeneratedCoverLetter
from careeros.database.models.feedback_entry import FeedbackEntry
from careeros.database.models.application import Application, ApplicationEvent
from careeros.database.models.chat_session import ChatSession, ChatMessage

__all__ = [
    "User",
    "Profile",
    "Experience",
    "ExperienceBullet",
    "Skill",
    "SkillAlias",
    "Education",
    "Certification",
    "Document",
    "DocumentChunk",
    "JobDescription",
    "GenerationSession",
    "GeneratedResume",
    "GeneratedCoverLetter",
    "FeedbackEntry",
    "Application",
    "ApplicationEvent",
    "ChatSession",
    "ChatMessage",
]
