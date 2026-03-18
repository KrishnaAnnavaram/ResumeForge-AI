"""Initial schema — all CareerOS tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768  # sentence-transformers/all-mpnet-base-v2


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # profiles
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("headline", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("target_roles", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("target_domains", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("tone_preferences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_profiles_active_user"),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])

    # documents (needed before experiences for FK)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("parse_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("parse_errors", postgresql.JSONB(), nullable=True),
        sa.Column("is_master", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    # experiences
    op.create_table(
        "experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("employment_type", sa.String(50), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_doc_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_user_id", "experiences", ["user_id"])
    op.create_index("ix_experiences_user_canonical", "experiences", ["user_id", "is_canonical"])

    # experience_bullets
    op.create_table(
        "experience_bullets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("experience_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("skills_used", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("impact_level", sa.String(20), server_default="medium", nullable=False),
        sa.Column("is_canonical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bullets_experience_id", "experience_bullets", ["experience_id"])
    op.create_index("ix_bullets_user_id", "experience_bullets", ["user_id"])
    op.create_index("ix_bullets_user_canonical_impact", "experience_bullets", ["user_id", "is_canonical", "impact_level"])
    op.execute("CREATE INDEX ix_bullets_skills_used_gin ON experience_bullets USING GIN (skills_used)")

    # skills
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("proficiency", sa.String(50), server_default="proficient", nullable=False),
        sa.Column("years_used", sa.Numeric(4, 1), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_doc_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_skills_user_name"),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"])

    # skill_aliases
    op.create_table(
        "skill_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False, unique=True),
        sa.Column("canonical", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # education
    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("degree", sa.String(255), nullable=False),
        sa.Column("field", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("gpa", sa.String(20), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_education_user_id", "education", ["user_id"])

    # certifications
    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("credential_id", sa.String(255), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_certifications_user_id", "certifications", ["user_id"])

    # document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),  # placeholder; real vector below
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Replace placeholder text column with actual vector column
    op.execute("ALTER TABLE document_chunks DROP COLUMN embedding")
    op.execute(f"ALTER TABLE document_chunks ADD COLUMN embedding vector({EMBEDDING_DIM})")
    op.create_index("ix_document_chunks_user_source_type", "document_chunks", ["user_id", "source_type"])
    op.execute(
        "CREATE INDEX ix_document_chunks_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # job_descriptions
    op.create_table(
        "job_descriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_text_hash", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("role_title", sa.String(255), nullable=True),
        sa.Column("seniority", sa.String(50), nullable=True),
        sa.Column("employment_type", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote_policy", sa.String(50), nullable=True),
        sa.Column("required_skills", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("preferred_skills", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("soft_skills", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("ats_keywords", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("responsibilities", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("seniority_signals", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("team_context", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(100), nullable=True),
        sa.Column("company_stage", sa.String(100), nullable=True),
        sa.Column("culture_signals", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("hiring_signals", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("match_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("parse_confidence", sa.Numeric(3, 2), server_default="0.0", nullable=False),
        sa.Column("parse_warnings", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "raw_text_hash", name="uq_jd_user_hash"),
    )
    op.create_index("ix_jd_user_id", "job_descriptions", ["user_id"])
    op.execute("CREATE INDEX ix_jd_required_skills_gin ON job_descriptions USING GIN (required_skills)")

    # generation_sessions — must come before generated_resumes/cover_letters (circular FK handled with deferred)
    op.create_table(
        "generation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jd_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("current_resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_cl_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retrieved_evidence", postgresql.JSONB(), nullable=True),
        sa.Column("gap_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("rewrite_plan", postgresql.JSONB(), nullable=True),
        sa.Column("iteration_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_iterations", sa.Integer(), server_default="5", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gen_sessions_user_id", "generation_sessions", ["user_id"])
    op.create_index("ix_gen_sessions_user_status", "generation_sessions", ["user_id", "status"])

    # generated_resumes
    op.create_table(
        "generated_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("evidence_ids", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("claim_evidence_map", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("critic_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("critic_flags", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("generation_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["generation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "version_number", name="uq_resume_session_version"),
    )
    op.create_index("ix_generated_resumes_session_id", "generated_resumes", ["session_id"])
    op.create_index("ix_generated_resumes_user_id", "generated_resumes", ["user_id"])

    # generated_cover_letters
    op.create_table(
        "generated_cover_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("claim_evidence_map", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("critic_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("critic_flags", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("generation_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["generation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "version_number", name="uq_cl_session_version"),
    )
    op.create_index("ix_generated_cls_session_id", "generated_cover_letters", ["session_id"])
    op.create_index("ix_generated_cls_user_id", "generated_cover_letters", ["user_id"])

    # Add circular FKs to generation_sessions now that resumes/cls tables exist
    op.create_foreign_key(
        "fk_sessions_current_resume",
        "generation_sessions", "generated_resumes",
        ["current_resume_version_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sessions_current_cl",
        "generation_sessions", "generated_cover_letters",
        ["current_cl_version_id"], ["id"],
        ondelete="SET NULL",
    )

    # feedback_entries
    op.create_table(
        "feedback_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cl_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("feedback_raw", sa.Text(), nullable=False),
        sa.Column("feedback_parsed", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("acted_on", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["generation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["generated_resumes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cl_version_id"], ["generated_cover_letters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_entries_session_id", "feedback_entries", ["session_id"])

    # applications
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("jd_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cl_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="applied", nullable=False),
        sa.Column("applied_date", sa.Date(), nullable=False),
        sa.Column("source_platform", sa.String(100), nullable=True),
        sa.Column("job_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["generation_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["generated_resumes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cl_version_id"], ["generated_cover_letters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_user_status", "applications", ["user_id", "status"])
    op.create_index("ix_applications_user_date", "applications", ["user_id", "applied_date"])

    # application_events
    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("old_value", sa.String(255), nullable=True),
        sa.Column("new_value", sa.String(255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_events_application_id", "application_events", ["application_id"])
    op.create_index("ix_app_events_application_time", "application_events", ["application_id", "occurred_at"])

    # chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_session_id"], ["generation_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["chat_session_id"])
    op.create_index("ix_chat_messages_session_time", "chat_messages", ["chat_session_id", "created_at"])

    # Seed skill_aliases
    from careeros.database.models.skill_alias import SKILL_ALIAS_SEEDS
    for alias, canonical, category in SKILL_ALIAS_SEEDS:
        op.execute(
            f"INSERT INTO skill_aliases (alias, canonical, category) "
            f"VALUES ('{alias}', '{canonical}', '{category}') "
            f"ON CONFLICT (alias) DO NOTHING"
        )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("application_events")
    op.drop_table("applications")
    op.drop_table("feedback_entries")
    op.drop_constraint("fk_sessions_current_cl", "generation_sessions", type_="foreignkey")
    op.drop_constraint("fk_sessions_current_resume", "generation_sessions", type_="foreignkey")
    op.drop_table("generated_cover_letters")
    op.drop_table("generated_resumes")
    op.drop_table("generation_sessions")
    op.drop_table("job_descriptions")
    op.drop_table("document_chunks")
    op.drop_table("certifications")
    op.drop_table("education")
    op.drop_table("skill_aliases")
    op.drop_table("skills")
    op.drop_table("experience_bullets")
    op.drop_table("experiences")
    op.drop_table("documents")
    op.drop_table("profiles")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
