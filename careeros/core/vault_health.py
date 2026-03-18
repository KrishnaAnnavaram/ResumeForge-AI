"""Vault health computation — evaluates completeness of user's career data."""
from dataclasses import dataclass, field


@dataclass
class VaultHealth:
    has_summary: bool = False
    experiences_count: int = 0
    bullets_with_metrics: float = 0.0
    skills_count: int = 0
    has_master_resume: bool = False
    has_certifications: bool = False
    has_preferences: bool = False
    completeness_score: float = 0.0
    warnings: list[str] = field(default_factory=list)


def compute_vault_health(
    profile,
    experiences: list,
    all_bullets: list,
    skills: list,
    certifications: list,
    documents: list,
) -> VaultHealth:
    health = VaultHealth()

    # Individual metrics
    health.has_summary = profile is not None and bool(profile.summary)
    health.experiences_count = len(experiences)
    health.skills_count = len(skills)
    health.has_certifications = len(certifications) > 0
    health.has_master_resume = any(d.is_master for d in documents if d.parse_status == "done")
    health.has_preferences = (
        profile is not None and bool(profile.tone_preferences)
    )

    # Bullets with metrics ratio
    if all_bullets:
        bullets_with_metrics = sum(1 for b in all_bullets if b.metrics and len(b.metrics) > 0)
        health.bullets_with_metrics = bullets_with_metrics / len(all_bullets)
    else:
        health.bullets_with_metrics = 0.0

    # Compute score
    score = 0.0
    score += 0.10 if health.has_summary else 0.0
    score += 0.20 if health.experiences_count >= 3 else (health.experiences_count / 3) * 0.20
    score += health.bullets_with_metrics * 0.25
    score += 0.15 if health.skills_count >= 10 else (health.skills_count / 10) * 0.15
    score += 0.10 if health.has_master_resume else 0.0
    score += 0.10 if health.has_certifications else 0.0
    score += 0.10 if health.has_preferences else 0.0
    health.completeness_score = round(min(score, 1.0), 2)

    # Warnings
    if health.completeness_score < 0.4:
        health.warnings.append("Vault too thin to generate quality output")
    if health.bullets_with_metrics < 0.5:
        health.warnings.append("Many bullets lack quantified metrics — add numbers and percentages")
    if health.experiences_count < 2:
        health.warnings.append("Add more work experience to improve match quality")
    if not health.has_master_resume:
        health.warnings.append("Upload a master resume for better parsing and embedding coverage")

    return health
