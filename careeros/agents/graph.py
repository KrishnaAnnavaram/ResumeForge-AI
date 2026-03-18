"""CareerOS LangGraph multi-agent graph assembly."""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from careeros.agents.state import CareerOSState
from careeros.core.logging import get_logger

log = get_logger(__name__)


def _route_after_critic(state: CareerOSState) -> Literal["present_to_user", "generate_resume", "present_with_flags"]:
    """Route based on critic score and retry count."""
    critic = state.get("critic_report") or {}
    score = critic.get("quality_score", 0)
    retry_count = state.get("critic_retry_count", 0)

    if score >= 60:
        return "present_to_user"
    if retry_count < 1:
        return "generate_resume"
    return "present_with_flags"


def _route_after_feedback(state: CareerOSState) -> Literal["plan_rewrite", "generate_resume", "present_to_user", "end"]:
    """Route based on interpreted feedback action."""
    parsed = state.get("feedback_parsed") or {}
    action = parsed.get("action", "")

    if action == "approve":
        return "approve_versions"
    if action == "full_regen":
        return "plan_rewrite"
    if action == "refine_section":
        return "generate_resume"
    if action == "reject":
        return "end"
    # Default: loop back to user
    return "present_to_user"


def _route_after_gap(state: CareerOSState) -> Literal["surface_gaps", "plan_rewrite"]:
    """Surface gaps to user if there are critical missing skills."""
    gap = state.get("gap_analysis") or {}
    critical_missing = [m for m in gap.get("missing", []) if m.get("severity") == "critical" and m.get("is_required")]
    if critical_missing:
        return "surface_gaps"
    return "plan_rewrite"


def _check_iteration_limit(state: CareerOSState) -> bool:
    return state.get("iteration", 0) >= state.get("max_iterations", 5)


async def load_profile_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.profile_loader_agent import run_profile_loader_agent
    async with AsyncSessionLocal() as db:
        return await run_profile_loader_agent(state, db)


async def parse_jd_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.jd_parser_agent import run_jd_parser_agent
    async with AsyncSessionLocal() as db:
        result = await run_jd_parser_agent(state, db)
        await db.commit()
        return result


async def retrieve_evidence_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.retrieval_agent import run_retrieval_agent
    async with AsyncSessionLocal() as db:
        return await run_retrieval_agent(state, db)


async def analyze_gaps_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.gap_analyzer_agent import run_gap_analyzer_agent
    async with AsyncSessionLocal() as db:
        return await run_gap_analyzer_agent(state, db)


async def surface_gaps_node(state: CareerOSState) -> CareerOSState:
    """Human-in-the-loop interrupt: surface gap warnings to user."""
    log.info("graph.interrupt", node="surface_gaps", session_id=state["session_id"])
    return {**state, "status": "awaiting_gap_review"}


async def plan_rewrite_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.rewrite_planner_agent import run_rewrite_planner_agent
    if _check_iteration_limit(state):
        return {**state, "status": "max_iterations_reached"}
    async with AsyncSessionLocal() as db:
        return await run_rewrite_planner_agent(state, db)


async def generate_resume_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.resume_writer_agent import run_resume_writer_agent
    async with AsyncSessionLocal() as db:
        result = await run_resume_writer_agent(state, db)
        await db.commit()
        return result


async def generate_cl_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.cover_letter_writer_agent import run_cover_letter_writer_agent
    async with AsyncSessionLocal() as db:
        result = await run_cover_letter_writer_agent(state, db)
        await db.commit()
        return result


async def critic_validate_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.critic_agent import run_critic_agent
    async with AsyncSessionLocal() as db:
        result = await run_critic_agent(state, db)
        await db.commit()
        return result


async def present_to_user_node(state: CareerOSState) -> CareerOSState:
    """Human-in-the-loop interrupt: present results to user for approval."""
    log.info("graph.interrupt", node="present_to_user", session_id=state["session_id"])
    return {**state, "status": "awaiting_feedback"}


async def present_with_flags_node(state: CareerOSState) -> CareerOSState:
    """Present to user with critic flags visible."""
    log.info("graph.interrupt", node="present_with_flags", session_id=state["session_id"])
    return {**state, "status": "awaiting_feedback_with_flags"}


async def interpret_feedback_node(state: CareerOSState) -> CareerOSState:
    from careeros.database.connection import AsyncSessionLocal
    from careeros.agents.feedback_interpreter_agent import run_feedback_interpreter_agent
    async with AsyncSessionLocal() as db:
        return await run_feedback_interpreter_agent(state, db)


async def approve_versions_node(state: CareerOSState) -> CareerOSState:
    """Deterministic: mark current versions as approved in DB."""
    from careeros.database.connection import AsyncSessionLocal
    from sqlalchemy import select
    from careeros.database.models.generated_resume import GeneratedResume
    from careeros.database.models.generated_cover_letter import GeneratedCoverLetter
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        if state.get("resume_version_id"):
            result = await db.execute(select(GeneratedResume).where(GeneratedResume.id == state["resume_version_id"]))
            resume = result.scalar_one_or_none()
            if resume:
                resume.is_approved = True
                resume.approved_at = datetime.now(timezone.utc)

        if state.get("cl_version_id"):
            result = await db.execute(select(GeneratedCoverLetter).where(GeneratedCoverLetter.id == state["cl_version_id"]))
            cl = result.scalar_one_or_none()
            if cl:
                cl.is_approved = True
                cl.approved_at = datetime.now(timezone.utc)

        await db.commit()

    log.info("graph.approved", session_id=state["session_id"])
    return {**state, "status": "approved"}


async def error_handler_node(state: CareerOSState) -> CareerOSState:
    """Log error and update session status."""
    log.error("graph.error", session_id=state["session_id"], error=state.get("error"))
    from careeros.database.connection import AsyncSessionLocal
    from sqlalchemy import select
    from careeros.database.models.generation_session import GenerationSession

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GenerationSession).where(GenerationSession.id == state["session_id"]))
        session = result.scalar_one_or_none()
        if session:
            session.status = "error"
            session.error_message = state.get("error", "Unknown error")
        await db.commit()

    return {**state, "status": "error"}


def build_graph() -> StateGraph:
    """Build and compile the CareerOS LangGraph."""
    builder = StateGraph(CareerOSState)

    # Add all nodes
    builder.add_node("load_profile", load_profile_node)
    builder.add_node("parse_jd", parse_jd_node)
    builder.add_node("retrieve_evidence", retrieve_evidence_node)
    builder.add_node("analyze_gaps", analyze_gaps_node)
    builder.add_node("surface_gaps", surface_gaps_node)
    builder.add_node("plan_rewrite", plan_rewrite_node)
    builder.add_node("generate_resume", generate_resume_node)
    builder.add_node("generate_cl", generate_cl_node)
    builder.add_node("critic_validate", critic_validate_node)
    builder.add_node("present_to_user", present_to_user_node)
    builder.add_node("present_with_flags", present_with_flags_node)
    builder.add_node("interpret_feedback", interpret_feedback_node)
    builder.add_node("approve_versions", approve_versions_node)
    builder.add_node("error_handler", error_handler_node)

    # Edges
    builder.add_edge(START, "load_profile")
    builder.add_edge("load_profile", "parse_jd")
    builder.add_edge("parse_jd", "retrieve_evidence")
    builder.add_edge("retrieve_evidence", "analyze_gaps")

    builder.add_conditional_edges(
        "analyze_gaps",
        _route_after_gap,
        {"surface_gaps": "surface_gaps", "plan_rewrite": "plan_rewrite"},
    )

    builder.add_edge("surface_gaps", "plan_rewrite")
    builder.add_edge("plan_rewrite", "generate_resume")
    builder.add_edge("plan_rewrite", "generate_cl")
    builder.add_edge("generate_resume", "critic_validate")
    builder.add_edge("generate_cl", "critic_validate")

    builder.add_conditional_edges(
        "critic_validate",
        _route_after_critic,
        {
            "present_to_user": "present_to_user",
            "generate_resume": "generate_resume",
            "present_with_flags": "present_with_flags",
        },
    )

    builder.add_edge("present_to_user", "interpret_feedback")
    builder.add_edge("present_with_flags", "interpret_feedback")

    builder.add_conditional_edges(
        "interpret_feedback",
        _route_after_feedback,
        {
            "plan_rewrite": "plan_rewrite",
            "generate_resume": "generate_resume",
            "approve_versions": "approve_versions",
            "present_to_user": "present_to_user",
            "end": END,
        },
    )

    builder.add_edge("approve_versions", END)
    builder.add_edge("error_handler", END)

    return builder.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
