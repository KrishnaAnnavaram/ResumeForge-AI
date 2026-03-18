"""Gap Analyzer Agent — compare JD requirements against evidence."""
import time
from sqlalchemy.ext.asyncio import AsyncSession

from careeros.agents.state import CareerOSState
from careeros.core.logging import get_logger
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.gap_analyzer_prompts import GAP_NUANCE_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()


def _skill_in_evidence(skill: str, evidence_set: list[dict]) -> tuple[bool, list[str]]:
    """Check if skill appears in any bullet's skills_used."""
    matching_ids = []
    skill_lower = skill.lower()
    for bullet in evidence_set:
        skills_used_lower = [s.lower() for s in (bullet.get("skills_used") or [])]
        if skill_lower in skills_used_lower:
            matching_ids.append(bullet["bullet_id"])
    return len(matching_ids) > 0, matching_ids


async def run_gap_analyzer_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Compare JD requirements against retrieved evidence and produce gap report."""
    start = time.time()
    log.info("agent.start", agent="Gap_Analyzer_Agent", session_id=state["session_id"], user_id=state["user_id"])

    jd = state["jd_structured"] or {}
    evidence_set = state.get("evidence_set") or []
    profile = state.get("profile") or {}
    profile_skill_names = [s.lower() for s in profile.get("skill_names", [])]

    required_skills = jd.get("required_skills", [])
    preferred_skills = jd.get("preferred_skills", [])
    llm = get_llm_client()

    matched = []
    partial = []
    missing = []

    # Step 1: Deterministic pre-check
    candidate_gaps = []
    for skill in required_skills:
        in_profile = skill.lower() in profile_skill_names
        in_evidence, evidence_ids = _skill_in_evidence(skill, evidence_set)

        if in_profile and in_evidence:
            matched.append({
                "skill": skill,
                "evidence_bullet_ids": evidence_ids,
                "confidence": "high",
            })
        elif in_profile or in_evidence:
            matched.append({
                "skill": skill,
                "evidence_bullet_ids": evidence_ids,
                "confidence": "medium",
            })
        else:
            candidate_gaps.append(skill)

    # Step 2: LLM nuance pass for candidate gaps
    top_bullets_text = "\n".join([
        f"[{b['bullet_id'][:8]}] {b['content']} (skills: {', '.join(b.get('skills_used', []))})"
        for b in evidence_set[:8]
    ])

    for skill in candidate_gaps:
        try:
            prompt = GAP_NUANCE_PROMPT.format(
                skill=skill,
                jd_role_title=jd.get("role_title", ""),
                jd_company=jd.get("company", ""),
                evidence_bullets=top_bullets_text,
            )
            result = llm.complete_json(prompt, model=settings.haiku_model)

            if result.get("demonstrates_skill"):
                partial.append({
                    "skill": skill,
                    "reason": result.get("reasoning", ""),
                    "evidence_bullet_ids": result.get("relevant_bullet_ids", []),
                    "suggestion": f"Highlight {skill} context in relevant bullets",
                    "confidence": result.get("confidence", "low"),
                })
            else:
                missing.append({
                    "skill": skill,
                    "severity": "critical",
                    "is_required": True,
                })
        except Exception as exc:
            log.warning("gap_analyzer.llm_failed", skill=skill, error=str(exc))
            missing.append({
                "skill": skill,
                "severity": "critical",
                "is_required": True,
            })

    # Add preferred skills gaps as minor
    for skill in preferred_skills:
        in_evidence, evidence_ids = _skill_in_evidence(skill, evidence_set)
        if not in_evidence and skill.lower() not in profile_skill_names:
            missing.append({
                "skill": skill,
                "severity": "minor",
                "is_required": False,
            })

    # Gap severity score
    total = max(len(required_skills), 1)
    unmatched = len(missing) + (len(partial) * 0.5)
    gap_severity_score = round(max(0, 100 - (unmatched / total) * 100), 1)

    gap_analysis = {
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "gap_severity_score": gap_severity_score,
    }

    # Surface warnings for critical missing required skills
    new_warnings = list(state.get("layer1_warnings", []))
    for item in missing:
        if item.get("severity") == "critical" and item.get("is_required"):
            new_warnings.append(
                f"No evidence found for critical required skill: {item['skill']}. "
                "This will not appear in the generated resume."
            )

    elapsed = int((time.time() - start) * 1000)
    log.info(
        "agent.complete",
        agent="Gap_Analyzer_Agent",
        session_id=state["session_id"],
        duration_ms=elapsed,
        matched=len(matched),
        partial=len(partial),
        missing=len(missing),
        gap_score=gap_severity_score,
    )

    return {
        **state,
        "gap_analysis": gap_analysis,
        "layer1_warnings": new_warnings,
    }
