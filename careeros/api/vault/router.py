"""Vault API router — manage career data."""
import os
import uuid
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from careeros.api.vault.schemas import (
    ProfileUpdate, ProfileResponse, ExperienceCreate, ExperienceResponse,
    BulletCreate, BulletResponse, SkillCreate, SkillResponse, VaultHealthResponse,
)
from careeros.core.exceptions import DocumentParseError
from careeros.core.vault_health import compute_vault_health
from careeros.database.models.profile import Profile
from careeros.database.models.experience import Experience
from careeros.database.models.experience_bullet import ExperienceBullet
from careeros.database.models.skill import Skill
from careeros.database.models.document import Document
from careeros.database.models.education import Education
from careeros.database.models.certification import Certification
from careeros.dependencies import CurrentUser, DB
from careeros.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/health", response_model=VaultHealthResponse)
async def vault_health(current_user: CurrentUser, db: DB):
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id, Profile.is_active == True))
    profile = profile_result.scalar_one_or_none()

    exp_result = await db.execute(select(Experience).options(selectinload(Experience.bullets)).where(Experience.user_id == current_user.id, Experience.is_canonical == True))
    experiences = exp_result.scalars().all()
    all_bullets = [b for e in experiences for b in e.bullets if b.is_canonical]

    skill_result = await db.execute(select(Skill).where(Skill.user_id == current_user.id, Skill.is_canonical == True))
    skills = skill_result.scalars().all()

    cert_result = await db.execute(select(Certification).where(Certification.user_id == current_user.id))
    certifications = cert_result.scalars().all()

    doc_result = await db.execute(select(Document).where(Document.user_id == current_user.id, Document.parse_status == "done"))
    documents = doc_result.scalars().all()

    health = compute_vault_health(profile, experiences, all_bullets, skills, certifications, documents)
    return VaultHealthResponse(**{
        "completeness_score": health.completeness_score,
        "warnings": health.warnings,
        "has_summary": health.has_summary,
        "experiences_count": health.experiences_count,
        "skills_count": health.skills_count,
        "has_master_resume": health.has_master_resume,
    })


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: CurrentUser, db: DB):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id, Profile.is_active == True))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse(
        id=str(profile.id),
        full_name=profile.full_name,
        headline=profile.headline,
        summary=profile.summary,
        location=profile.location,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
        target_roles=profile.target_roles or [],
        target_domains=profile.target_domains or [],
        tone_preferences=profile.tone_preferences or {},
    )


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(request: ProfileUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id, Profile.is_active == True))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=current_user.id, full_name=request.full_name or "")
        db.add(profile)

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.flush()
    return ProfileResponse(
        id=str(profile.id),
        full_name=profile.full_name,
        headline=profile.headline,
        summary=profile.summary,
        location=profile.location,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
        target_roles=profile.target_roles or [],
        target_domains=profile.target_domains or [],
        tone_preferences=profile.tone_preferences or {},
    )


@router.get("/experiences", response_model=list[ExperienceResponse])
async def list_experiences(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Experience)
        .where(Experience.user_id == current_user.id, Experience.is_canonical == True)
        .order_by(Experience.start_date.desc())
    )
    return [_exp_to_response(e) for e in result.scalars().all()]


@router.post("/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def create_experience(request: ExperienceCreate, current_user: CurrentUser, db: DB):
    exp = Experience(user_id=current_user.id, **request.model_dump())
    db.add(exp)
    await db.flush()
    return _exp_to_response(exp)


@router.patch("/experiences/{experience_id}", response_model=ExperienceResponse)
async def update_experience(experience_id: uuid.UUID, request: ExperienceCreate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Experience).where(Experience.id == experience_id, Experience.user_id == current_user.id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    for field, value in request.model_dump(exclude_none=True).items():
        setattr(exp, field, value)
    await db.flush()
    return _exp_to_response(exp)


@router.delete("/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(experience_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Experience).where(Experience.id == experience_id, Experience.user_id == current_user.id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
    exp.is_canonical = False


@router.get("/experiences/{experience_id}/bullets", response_model=list[BulletResponse])
async def list_bullets(experience_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ExperienceBullet)
        .where(ExperienceBullet.experience_id == experience_id, ExperienceBullet.user_id == current_user.id, ExperienceBullet.is_canonical == True)
        .order_by(ExperienceBullet.impact_level.desc())
    )
    return [_bullet_to_response(b) for b in result.scalars().all()]


@router.post("/experiences/{experience_id}/bullets", response_model=BulletResponse, status_code=status.HTTP_201_CREATED)
async def create_bullet(experience_id: uuid.UUID, request: BulletCreate, current_user: CurrentUser, db: DB):
    bullet = ExperienceBullet(
        experience_id=experience_id,
        user_id=current_user.id,
        **request.model_dump(),
    )
    db.add(bullet)
    await db.flush()
    return _bullet_to_response(bullet)


@router.patch("/bullets/{bullet_id}", response_model=BulletResponse)
async def update_bullet(bullet_id: uuid.UUID, request: BulletCreate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(ExperienceBullet).where(ExperienceBullet.id == bullet_id, ExperienceBullet.user_id == current_user.id))
    bullet = result.scalar_one_or_none()
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found")
    for field, value in request.model_dump(exclude_none=True).items():
        setattr(bullet, field, value)
    await db.flush()
    return _bullet_to_response(bullet)


@router.delete("/bullets/{bullet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bullet(bullet_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(ExperienceBullet).where(ExperienceBullet.id == bullet_id, ExperienceBullet.user_id == current_user.id))
    bullet = result.scalar_one_or_none()
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found")
    bullet.is_canonical = False


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills(current_user: CurrentUser, db: DB):
    result = await db.execute(select(Skill).where(Skill.user_id == current_user.id, Skill.is_canonical == True))
    return [_skill_to_response(s) for s in result.scalars().all()]


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(request: SkillCreate, current_user: CurrentUser, db: DB):
    skill = Skill(user_id=current_user.id, **request.model_dump())
    db.add(skill)
    await db.flush()
    return _skill_to_response(skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(skill_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == current_user.id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill.is_canonical = False


@router.post("/documents/upload")
async def upload_document(current_user: CurrentUser, db: DB, file: UploadFile = File(...)):
    """Upload and queue a document for parsing."""
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File exceeds {settings.max_file_size_mb}MB limit")

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, f"{current_user.id}_{file.filename}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = Document(
        user_id=current_user.id,
        type="resume",
        title=file.filename,
        file_path=file_path,
        file_name=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        parse_status="pending",
    )
    db.add(doc)
    await db.flush()

    # Trigger async parse (in production: use a task queue)
    # For MVP: parse inline
    try:
        from careeros.ingestion.pipeline import ingest_document
        await ingest_document(file_path, current_user.id, db, interactive=False)
    except Exception as exc:
        doc.parse_status = "failed"

    return {"document_id": str(doc.id), "parse_status": doc.parse_status}


@router.get("/documents/{document_id}/parse-status")
async def document_parse_status(document_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"document_id": str(doc.id), "parse_status": doc.parse_status, "parsed_at": doc.parsed_at}


def _exp_to_response(e: Experience) -> ExperienceResponse:
    return ExperienceResponse(
        id=str(e.id),
        company=e.company,
        title=e.title,
        employment_type=e.employment_type,
        start_date=str(e.start_date),
        end_date=str(e.end_date) if e.end_date else None,
        is_current=e.is_current,
        location=e.location,
        domain=e.domain,
        description=e.description,
    )


def _bullet_to_response(b: ExperienceBullet) -> BulletResponse:
    return BulletResponse(
        id=str(b.id),
        content=b.content,
        metrics=b.metrics or [],
        skills_used=b.skills_used or [],
        impact_level=b.impact_level,
        usage_count=b.usage_count,
    )


def _skill_to_response(s: Skill) -> SkillResponse:
    return SkillResponse(
        id=str(s.id),
        name=s.name,
        category=s.category,
        proficiency=s.proficiency,
        years_used=float(s.years_used) if s.years_used else None,
    )
