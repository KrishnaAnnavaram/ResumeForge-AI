"""Rewrite Planner Agent — produces section-by-section resume writing plan."""
import json
import time
from sqlalchemy.ext.asyncio import AsyncSession

from careeros.agents.state import CareerOSState
from careeros.core.logging import get_logger
from careeros.llm.client import get_llm_client
from careeros.llm.prompts.planner_prompts import REWRITE_PLAN_PROMPT
from careeros.config import get_settings

log = get_logger(__name__)
settings = get_settings()


def _format_evidence(evidence_set: list[dict]) -> str:
    """Format evidence set for prompt inclusion."""
    lines = []
    for i, bullet in enumerate(evidence_set[:20], 1):
        lines.append(
            f"[{i}] ID:{bullet['bullet_id'][:8]} | {bullet['company']} — {bullet['title']}\n"
            f"    {bullet['content']}\n"
            f"    Skills: {', '.join(bullet.get('skills_used', []))}\n"
            f"    Metrics: {', '.join(bullet.get('metrics', []))} | Impact: {bullet.get('impact_level', 'medium')}\n"
            f"    Score: {bullet.get('rank_score', 0):.3f}"
        )
    return "\n".join(lines)


async def run_rewrite_planner_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Generate section-by-section resume plan with evidence assignments."""
    start = time.time()
    log.info("agent.start", agent="Rewrite_Planner_Agent", session_id=state["session_id"], user_id=state["user_id"])

    jd = state["jd_structured"] or {}
    gap = state.get("gap_analysis") or {}
    evidence_set = state.get("evidence_set") or []
    profile = state.get("profile") or {}
    tone_preferences = profile.get("profile", {}) and profile.get("profile", {}).get("tone_preferences") or {}

    matched_skills = [m["skill"] for m in gap.get("matched", [])]
    missing_skills = [m["skill"] for m in gap.get("missing", []) if m.get("severity") == "critical"]
    partial_skills = [p["skill"] for p in gap.get("partial", [])]

    prompt = REWRITE_PLAN_PROMPT.format(
        company=jd.get("company", "the company"),
        role_title=jd.get("role_title", ""),
        seniority=jd.get("seniority", ""),
        domain=jd.get("domain", ""),
        required_skills=", ".join(jd.get("required_skills", [])),
        ats_keywords=", ".join(jd.get("ats_keywords", [])),
        tone=jd.get("tone", "professional"),
        responsibilities=json.dumps(jd.get("responsibilities", []), indent=2),
        formatted_evidence_set=_format_evidence(evidence_set),
        matched_skills=", ".join(matched_skills),
        missing_skills=", ".join(missing_skills),
        partial_skills=", ".join(partial_skills),
        tone_preferences=json.dumps(tone_preferences, indent=2),
    )

    llm = get_llm_client()
    plan = llm.complete_json(prompt, model=settings.sonnet_model, max_tokens=6000)

    elapsed = int((time.time() - start) * 1000)
    log.info(
        "agent.complete",
        agent="Rewrite_Planner_Agent",
        session_id=state["session_id"],
        duration_ms=elapsed,
        sections=len(plan.get("sections", [])),
    )

    return {
        **state,
        "rewrite_plan": plan,
    }
