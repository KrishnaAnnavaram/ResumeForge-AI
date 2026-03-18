"""Profile Loader Agent — pure DB service, zero LLM calls."""
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from careeros.agents.state import CareerOSState
from careeros.core.exceptions import VaultTooThinError
from careeros.core.logging import get_logger
from careeros.core.vault_health import compute_vault_health
from careeros.database.models.profile import Profile
from careeros.database.models.experience import Experience
from careeros.database.models.experience_bullet import ExperienceBullet
from careeros.database.models.skill import Skill
from careeros.database.models.education import Education
from careeros.database.models.certification import Certification
from careeros.database.models.document import Document

log = get_logger(__name__)


async def run_profile_loader_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Load complete canonical career profile from PostgreSQL."""
    start = time.time()
    log.info("agent.start", agent="Profile_Loader_Agent", session_id=state["session_id"], user_id=state["user_id"])

    user_id = state["user_id"]

    # Load profile
    profile_result = await db.execute(
        select(Profile).where(Profile.user_id == user_id, Profile.is_active == True)
    )
    profile = profile_result.scalar_one_or_none()

    # Load experiences with bullets
    exp_result = await db.execute(
        select(Experience)
        .options(selectinload(Experience.bullets))
        .where(Experience.user_id == user_id, Experience.is_canonical == True)
        .order_by(Experience.start_date.desc())
    )
    experiences = exp_result.scalars().all()

    # Collect all bullets
    all_bullets = []
    for exp in experiences:
        all_bullets.extend([b for b in exp.bullets if b.is_canonical])

    # Load skills
    skill_result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user_id, Skill.is_canonical == True)
        .order_by(Skill.proficiency.desc())
    )
    skills = skill_result.scalars().all()

    # Load education
    edu_result = await db.execute(
        select(Education).where(Education.user_id == user_id, Education.is_canonical == True)
    )
    education = edu_result.scalars().all()

    # Load certifications
    cert_result = await db.execute(
        select(Certification).where(Certification.user_id == user_id, Certification.is_canonical == True)
    )
    certifications = cert_result.scalars().all()

    # Load documents
    doc_result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id, Document.parse_status == "done")
        .order_by(Document.is_master.desc(), Document.uploaded_at.desc())
    )
    documents = doc_result.scalars().all()

    # Compute vault health
    health = compute_vault_health(profile, experiences, all_bullets, skills, certifications, documents)

    if health.completeness_score < 0.3:
        raise VaultTooThinError(
            f"Vault has insufficient data for generation (score: {health.completeness_score:.0%}). "
            "Please add more experience and skills.",
            details={"completeness_score": health.completeness_score, "warnings": health.warnings},
        )

    profile_dict = {
        "profile": _profile_to_dict(profile) if profile else None,
        "experiences": [_experience_to_dict(e) for e in experiences],
        "skills": [_skill_to_dict(s) for s in skills],
        "skill_names": [s.name for s in skills],
        "education": [_education_to_dict(e) for e in education],
        "certifications": [_certification_to_dict(c) for c in certifications],
        "vault_health": {
            "completeness_score": health.completeness_score,
            "warnings": health.warnings,
            "has_summary": health.has_summary,
            "experiences_count": health.experiences_count,
            "skills_count": health.skills_count,
            "has_master_resume": health.has_master_resume,
        },
    }

    elapsed = int((time.time() - start) * 1000)
    log.info(
        "agent.complete",
        agent="Profile_Loader_Agent",
        session_id=state["session_id"],
        duration_ms=elapsed,
        experiences=len(experiences),
        bullets=len(all_bullets),
        skills=len(skills),
        vault_score=health.completeness_score,
    )

    return {
        **state,
        "profile": profile_dict,
        "layer1_warnings": state.get("layer1_warnings", []) + health.warnings,
    }


def _profile_to_dict(p: Profile) -> dict:
    return {
        "full_name": p.full_name,
        "headline": p.headline,
        "summary": p.summary,
        "location": p.location,
        "linkedin_url": p.linkedin_url,
        "github_url": p.github_url,
        "portfolio_url": p.portfolio_url,
        "target_roles": p.target_roles or [],
        "target_domains": p.target_domains or [],
        "tone_preferences": p.tone_preferences or {},
    }


def _experience_to_dict(e: Experience) -> dict:
    return {
        "id": str(e.id),
        "company": e.company,
        "title": e.title,
        "employment_type": e.employment_type,
        "start_date": str(e.start_date),
        "end_date": str(e.end_date) if e.end_date else None,
        "is_current": e.is_current,
        "location": e.location,
        "domain": e.domain,
        "description": e.description,
        "bullets": [_bullet_to_dict(b) for b in e.bullets if b.is_canonical],
    }


def _bullet_to_dict(b: ExperienceBullet) -> dict:
    return {
        "id": str(b.id),
        "experience_id": str(b.experience_id),
        "content": b.content,
        "metrics": b.metrics or [],
        "skills_used": b.skills_used or [],
        "impact_level": b.impact_level,
        "usage_count": b.usage_count,
    }


def _skill_to_dict(s: Skill) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "category": s.category,
        "proficiency": s.proficiency,
        "years_used": float(s.years_used) if s.years_used else None,
    }


def _education_to_dict(e: Education) -> dict:
    return {
        "id": str(e.id),
        "institution": e.institution,
        "degree": e.degree,
        "field": e.field,
        "start_date": str(e.start_date) if e.start_date else None,
        "end_date": str(e.end_date) if e.end_date else None,
        "gpa": e.gpa,
    }


def _certification_to_dict(c: Certification) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "issuer": c.issuer,
        "issued_date": str(c.issued_date) if c.issued_date else None,
        "credential_id": c.credential_id,
        "url": c.url,
    }
