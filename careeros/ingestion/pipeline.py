"""Resume ingestion pipeline — parse, extract, confirm, embed, store."""
import os
import uuid
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from careeros.core.logging import get_logger
from careeros.core.exceptions import DocumentParseError
from careeros.database.models.document import Document
from careeros.database.models.document_chunk import DocumentChunk
from careeros.database.models.profile import Profile
from careeros.database.models.experience import Experience
from careeros.database.models.experience_bullet import ExperienceBullet
from careeros.database.models.skill import Skill
from careeros.database.models.education import Education
from careeros.database.models.certification import Certification
from careeros.ingestion.pdf_parser import parse_pdf
from careeros.ingestion.docx_parser import parse_docx
from careeros.ingestion.resume_extractor import extract_resume_data
from careeros.ingestion.embedder import embed_batch

log = get_logger(__name__)


def _parse_file(file_path: str) -> str:
    """Parse raw text from PDF or DOCX."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return parse_docx(file_path)
    else:
        raise DocumentParseError(f"Unsupported file type: {ext}")


def _safe_date(date_str: str | None):
    """Parse a date string safely."""
    if not date_str:
        return None
    try:
        return parse_date(date_str).date()
    except Exception:
        return None


async def ingest_document(
    file_path: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    is_master: bool = True,
    interactive: bool = True,
) -> Document:
    """
    Full ingestion pipeline:
    1. Parse raw text
    2. Extract structured career data via LLM
    3. CLI confirmation (if interactive)
    4. Store all entities as canonical
    5. Generate and store embeddings
    """
    log.info("ingestion.start", file_path=file_path, user_id=str(user_id))

    # Step 1: Parse file
    try:
        raw_text = _parse_file(file_path)
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse {file_path}: {exc}") from exc

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    mime_type = "application/pdf" if file_path.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Create document record
    doc = Document(
        user_id=user_id,
        type="resume",
        title=f"Master Resume — {file_name}",
        raw_text=raw_text,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        parse_status="processing",
        is_master=is_master,
    )
    db.add(doc)
    await db.flush()

    # Step 2: Extract structured data
    try:
        extracted = extract_resume_data(raw_text)
    except Exception as exc:
        doc.parse_status = "failed"
        doc.parse_errors = {"error": str(exc)}
        await db.flush()
        raise DocumentParseError(f"LLM extraction failed: {exc}") from exc

    # Step 3: CLI confirmation
    total_bullets = sum(len(e.get("bullets", [])) for e in extracted.get("experiences", []))
    print("\n" + "=" * 50)
    print("=== EXTRACTED RESUME DATA ===")
    profile_data = extracted.get("profile", {})
    print(f"Profile: {profile_data.get('full_name', 'Unknown')} — {profile_data.get('headline', '')}")
    print(f"Experiences: {len(extracted.get('experiences', []))}")
    print(f"Total Bullets: {total_bullets}")
    print(f"Skills: {len(extracted.get('skills', []))}")
    print(f"Education: {len(extracted.get('education', []))}")
    print(f"Certifications: {len(extracted.get('certifications', []))}")
    print("=" * 50)

    if interactive:
        confirm = input("\nPlease review the extracted data above. Type 'confirm' to mark as canonical and generate embeddings: ").strip().lower()
        if confirm != "confirm":
            doc.parse_status = "failed"
            doc.parse_errors = {"error": "User cancelled ingestion"}
            await db.flush()
            log.info("ingestion.cancelled", user_id=str(user_id))
            return doc

    # Step 4: Store all entities
    # Profile
    prof_data = extracted.get("profile", {})
    existing_profile = await db.execute(select(Profile).where(Profile.user_id == user_id, Profile.is_active == True))
    existing = existing_profile.scalar_one_or_none()
    if not existing:
        profile = Profile(
            user_id=user_id,
            full_name=prof_data.get("full_name", ""),
            headline=prof_data.get("headline"),
            summary=prof_data.get("summary"),
            location=prof_data.get("location"),
            linkedin_url=prof_data.get("linkedin"),
            github_url=prof_data.get("github"),
        )
        db.add(profile)

    # Experiences + bullets
    bullet_records = []  # For embedding later
    for exp_data in extracted.get("experiences", []):
        start_date = _safe_date(exp_data.get("start_date"))
        if not start_date:
            continue

        exp = Experience(
            user_id=user_id,
            source_doc_id=doc.id,
            company=exp_data.get("company", "Unknown"),
            title=exp_data.get("title", "Unknown"),
            employment_type=exp_data.get("employment_type"),
            start_date=start_date,
            end_date=_safe_date(exp_data.get("end_date")),
            is_current=exp_data.get("is_current", False),
            location=exp_data.get("location"),
            domain=exp_data.get("domain"),
            description=exp_data.get("description"),
            is_canonical=True,
        )
        db.add(exp)
        await db.flush()

        for b_data in exp_data.get("bullets", []):
            if not b_data.get("content"):
                continue
            bullet = ExperienceBullet(
                experience_id=exp.id,
                user_id=user_id,
                content=b_data["content"],
                metrics=b_data.get("metrics", []),
                skills_used=b_data.get("skills_used", []),
                impact_level=_infer_impact(b_data),
                is_canonical=True,
            )
            db.add(bullet)
            await db.flush()
            bullet_records.append(bullet)

    # Skills
    for s_data in extracted.get("skills", []):
        if not s_data.get("name"):
            continue
        existing_skill = await db.execute(
            select(Skill).where(Skill.user_id == user_id, Skill.name == s_data["name"])
        )
        if not existing_skill.scalar_one_or_none():
            skill = Skill(
                user_id=user_id,
                source_doc_id=doc.id,
                name=s_data["name"],
                category=s_data.get("category"),
                proficiency=s_data.get("proficiency", "proficient"),
                years_used=s_data.get("years_used"),
                is_canonical=True,
            )
            db.add(skill)

    # Education
    for e_data in extracted.get("education", []):
        edu = Education(
            user_id=user_id,
            institution=e_data.get("institution", ""),
            degree=e_data.get("degree", ""),
            field=e_data.get("field"),
            start_date=_safe_date(e_data.get("start_date")),
            end_date=_safe_date(e_data.get("end_date")),
            gpa=e_data.get("gpa"),
            is_canonical=True,
        )
        db.add(edu)

    # Certifications
    for c_data in extracted.get("certifications", []):
        cert = Certification(
            user_id=user_id,
            name=c_data.get("name", ""),
            issuer=c_data.get("issuer"),
            issued_date=_safe_date(c_data.get("issued_date")),
            credential_id=c_data.get("credential_id"),
            is_canonical=True,
        )
        db.add(cert)

    await db.flush()

    # Step 5: Generate and store embeddings
    if bullet_records:
        print(f"\nGenerating embeddings for {len(bullet_records)} bullets...")
        texts = [b.content for b in bullet_records]
        embeddings = await embed_batch(texts)

        for bullet, embedding in zip(bullet_records, embeddings):
            chunk = DocumentChunk(
                document_id=doc.id,
                user_id=user_id,
                source_type="bullet",
                source_id=bullet.id,
                content=bullet.content,
                embedding=embedding,
                metadata_={"company": bullet.experience.company if hasattr(bullet, 'experience') else "", "impact_level": bullet.impact_level},
            )
            db.add(chunk)

    # Mark document as done
    doc.parse_status = "done"
    doc.parsed_at = datetime.now(timezone.utc)
    await db.flush()

    log.info(
        "ingestion.complete",
        user_id=str(user_id),
        doc_id=str(doc.id),
        bullets=len(bullet_records),
    )
    print(f"\n✓ Ingestion complete. Document ID: {doc.id}")
    return doc


def _infer_impact(bullet_data: dict) -> str:
    """Infer impact level from bullet content heuristics."""
    content = bullet_data.get("content", "")
    metrics = bullet_data.get("metrics", [])

    if metrics and len(metrics) >= 2:
        return "high"
    if metrics:
        return "medium"

    high_keywords = ["led", "architected", "founded", "launched", "reduced by", "increased by", "saved"]
    if any(kw in content.lower() for kw in high_keywords):
        return "high"

    return "medium"
