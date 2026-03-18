"""Session search — find bullets used in approved past generations for similar roles."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from careeros.core.logging import get_logger

log = get_logger(__name__)


async def session_search(
    user_id: str,
    current_domain: str | None,
    current_required_skills: list[str],
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """
    Find approved bullets used in similar past generation sessions.
    Similarity = same domain OR overlapping required skills.
    """
    sql = text("""
        SELECT DISTINCT
            eb.id::text AS bullet_id,
            eb.content,
            eb.metrics,
            eb.skills_used,
            eb.impact_level,
            eb.usage_count,
            eb.experience_id::text,
            e.company,
            e.title,
            e.start_date::text,
            e.domain,
            MAX(gr.approved_at) AS last_approved
        FROM experience_bullets eb
        JOIN experiences e ON eb.experience_id = e.id
        JOIN generated_resumes gr ON eb.id::text = ANY(gr.evidence_ids)
        JOIN generation_sessions gs ON gr.session_id = gs.id
        JOIN job_descriptions jd ON gs.jd_id = jd.id
        WHERE gs.user_id = CAST(:user_id AS uuid)
            AND gr.is_approved = true
            AND (
                jd.domain = :current_domain
                OR jd.required_skills && CAST(:current_skills AS varchar[])
            )
        GROUP BY
            eb.id, eb.content, eb.metrics, eb.skills_used,
            eb.impact_level, eb.usage_count, eb.experience_id,
            e.company, e.title, e.start_date, e.domain
        ORDER BY last_approved DESC
        LIMIT :limit
    """)

    result = await db.execute(sql, {
        "user_id": user_id,
        "current_domain": current_domain or "",
        "current_skills": current_required_skills,
        "limit": limit,
    })

    rows = result.mappings().all()
    results = []
    for row in rows:
        results.append({
            "bullet_id": row["bullet_id"],
            "content": row["content"],
            "metrics": row["metrics"] or [],
            "skills_used": row["skills_used"] or [],
            "impact_level": row["impact_level"],
            "usage_count": row["usage_count"],
            "experience_id": row["experience_id"],
            "company": row["company"],
            "title": row["title"],
            "start_date": row["start_date"],
            "domain": row["domain"],
            "source": "session",
        })

    log.debug("session_search.complete", user_id=user_id, results=len(results))
    return results
