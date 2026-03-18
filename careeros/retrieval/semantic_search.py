"""Semantic search via pgvector HNSW index."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from careeros.core.logging import get_logger

log = get_logger(__name__)


async def semantic_search(
    query_embedding: list[float],
    user_id: str,
    db: AsyncSession,
    limit: int = 15,
    distance_threshold: float = 0.55,
) -> list[dict]:
    """
    Semantic similarity search over experience bullets via pgvector.
    Returns ranked results with distance scores.
    """
    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    sql = text("""
        SELECT
            eb.id::text AS bullet_id,
            eb.content,
            eb.metrics,
            eb.skills_used,
            eb.impact_level,
            eb.usage_count,
            eb.experience_id::text,
            dc.embedding <-> CAST(:query_vec AS vector) AS distance,
            e.company,
            e.title,
            e.start_date::text,
            e.domain
        FROM experience_bullets eb
        JOIN document_chunks dc ON dc.source_id = eb.id
            AND dc.source_type = 'bullet'
        JOIN experiences e ON eb.experience_id = e.id
        WHERE eb.user_id = CAST(:user_id AS uuid)
            AND eb.is_canonical = true
            AND dc.embedding <-> CAST(:query_vec AS vector) < :threshold
        ORDER BY distance ASC
        LIMIT :limit
    """)

    result = await db.execute(sql, {
        "query_vec": embedding_str,
        "user_id": user_id,
        "threshold": distance_threshold,
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
            "l1_distance": float(row["distance"]),
            "source": "semantic",
        })

    log.debug("semantic_search.complete", user_id=user_id, results=len(results))
    return results
