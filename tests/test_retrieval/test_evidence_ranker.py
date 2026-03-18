"""Tests for evidence ranker."""
import pytest
from careeros.retrieval.evidence_ranker import rank_evidence


def make_bullet(bullet_id: str, impact: str = "medium", metrics: list = None, usage: int = 0) -> dict:
    return {
        "bullet_id": bullet_id,
        "content": f"Test bullet {bullet_id}",
        "metrics": metrics or [],
        "skills_used": ["Python"],
        "impact_level": impact,
        "usage_count": usage,
        "company": "ACME",
        "title": "Engineer",
        "start_date": "2023-01-01",
        "domain": "AI",
    }


def test_rank_deduplicates():
    b1 = make_bullet("aaa", impact="high")
    b1_copy = {**b1}  # same bullet in multiple layers

    l1 = [{**b1, "l1_distance": 0.2}]
    l2 = [b1_copy]
    l3 = []

    ranked, low_warning = rank_evidence(l1, l2, l3)
    assert len([r for r in ranked if r["bullet_id"] == "aaa"]) == 1


def test_rank_scores_by_layer():
    # Bullet in L2 (structured) should score higher than L1 only
    b_l2_only = make_bullet("l2only")
    b_l1_only = {**make_bullet("l1only"), "l1_distance": 0.4}

    ranked, _ = rank_evidence(
        l1_results=[b_l1_only],
        l2_results=[b_l2_only],
        l3_results=[],
    )

    l2_bullet = next(r for r in ranked if r["bullet_id"] == "l2only")
    l1_bullet = next(r for r in ranked if r["bullet_id"] == "l1only")
    assert l2_bullet["rank_score"] > l1_bullet["rank_score"]


def test_low_evidence_warning():
    bullets = [make_bullet(f"b{i}") for i in range(3)]
    _, low_warning = rank_evidence(bullets, [], [])
    assert low_warning is True


def test_no_low_warning_with_enough():
    bullets = [make_bullet(f"b{i}") for i in range(8)]
    _, low_warning = rank_evidence(bullets, [], [])
    assert low_warning is False


def test_metric_bonus():
    b_with_metrics = make_bullet("with_m", metrics=["40% improvement"])
    b_no_metrics = make_bullet("no_m")

    ranked, _ = rank_evidence([b_with_metrics, b_no_metrics], [], [])

    bm = next(r for r in ranked if r["bullet_id"] == "with_m")
    nm = next(r for r in ranked if r["bullet_id"] == "no_m")
    assert bm["rank_score"] > nm["rank_score"]


def test_high_impact_bonus():
    b_high = make_bullet("high_impact", impact="high")
    b_low = make_bullet("low_impact", impact="low")

    ranked, _ = rank_evidence([b_high, b_low], [], [])
    bh = next(r for r in ranked if r["bullet_id"] == "high_impact")
    bl = next(r for r in ranked if r["bullet_id"] == "low_impact")
    assert bh["rank_score"] > bl["rank_score"]


def test_top_k_limit():
    bullets = [make_bullet(f"b{i}") for i in range(30)]
    ranked, _ = rank_evidence(bullets, [], [], top_k=10)
    assert len(ranked) <= 10
