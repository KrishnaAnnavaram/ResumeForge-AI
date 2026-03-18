"""Structured search — exact skill intersection and skill table queries."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from careeros.core.logging import get_logger

log = get_logger(__name__)


async def structured_search(
    required_skills: list[str],
    user_id: str,
    db: AsyncSession,
    limit: int = 15,
) -> list[dict]:
    """
    Exact skill intersection search using PostgreSQL array overlap operator.
    Also fetches matching skills directly from skills table.
    """
    if not required_skills:
        return []

    sql = text("""
        SELECT
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
            e.domain
        FROM experience_bullets eb
        JOIN experiences e ON eb.experience_id = e.id
        WHERE eb.user_id = CAST(:user_id AS uuid)
            AND eb.is_canonical = true
            AND eb.skills_used && CAST(:required_skills AS varchar[])
        ORDER BY
            CASE eb.impact_level WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            eb.usage_count DESC
        LIMIT :limit
    """)

    result = await db.execute(sql, {
        "user_id": user_id,
        "required_skills": required_skills,
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
            "source": "structured",
        })

    log.debug("structured_search.complete", user_id=user_id, results=len(results), skills=len(required_skills))
    return results
