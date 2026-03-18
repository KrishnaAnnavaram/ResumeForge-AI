"""Evidence ranker — merges and scores results from all three retrieval layers."""
from careeros.core.logging import get_logger

log = get_logger(__name__)


def rank_evidence(
    l1_results: list[dict],
    l2_results: list[dict],
    l3_results: list[dict],
    top_k: int = 25,
) -> tuple[list[dict], bool]:
    """
    Merge, deduplicate, and score evidence from all three retrieval layers.

    Scoring:
    - (1 - L1_distance) * 0.4 if in semantic results
    - +0.5 if in structured results (exact skill match)
    - +0.3 if in session results (prior approval signal)
    - +0.2 if has quantified metrics
    - +0.1 if impact_level == 'high'
    - +0.05 per usage_count (capped at 0.15)

    Returns (ranked_evidence, low_evidence_warning).
    """
    # Build lookup maps
    l1_map = {r["bullet_id"]: r for r in l1_results}
    l2_ids = {r["bullet_id"] for r in l2_results}
    l3_ids = {r["bullet_id"] for r in l3_results}

    # Merge all unique bullets
    all_bullets: dict[str, dict] = {}
    for r in l1_results + l2_results + l3_results:
        bid = r["bullet_id"]
        if bid not in all_bullets:
            all_bullets[bid] = r

    # Score each bullet
    scored = []
    for bid, bullet in all_bullets.items():
        score = 0.0

        # Layer 1 contribution
        if bid in l1_map:
            dist = l1_map[bid].get("l1_distance", 0.5)
            score += (1.0 - dist) * 0.4

        # Layer 2 contribution
        if bid in l2_ids:
            score += 0.5

        # Layer 3 contribution
        if bid in l3_ids:
            score += 0.3

        # Metric bonus
        if bullet.get("metrics"):
            score += 0.2

        # Impact bonus
        if bullet.get("impact_level") == "high":
            score += 0.1

        # Usage bonus (capped)
        usage = min(bullet.get("usage_count", 0), 3)
        score += usage * 0.05

        scored.append({**bullet, "rank_score": round(score, 4)})

    scored.sort(key=lambda x: x["rank_score"], reverse=True)
    top = scored[:top_k]

    low_evidence_warning = len(top) < 5
    if low_evidence_warning:
        log.warning("evidence_ranker.low_evidence", total_found=len(top))

    log.info(
        "evidence_ranker.complete",
        l1=len(l1_results),
        l2=len(l2_results),
        l3=len(l3_results),
        unique=len(all_bullets),
        top_k=len(top),
        low_evidence=low_evidence_warning,
    )

    return top, low_evidence_warning
