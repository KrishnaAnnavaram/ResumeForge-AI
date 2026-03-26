"""
agents/graph.py — LangGraph StateGraph wiring.

Compiles the complete resume generation workflow with:
- PostgresSaver checkpointer (Supabase DB)
- human-in-the-loop interrupt_before gates
- conditional edges for ATS retry loop and cover letter gate
"""

import os
import functools
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.agents.ats_analyzer import ats_analyzer_node
from backend.agents.ats_rescorer import ats_rescorer_node
from backend.agents.cover_letter import cover_letter_node
from backend.agents.feedback_log import feedback_log_node
from backend.agents.resume_writer import resume_writer_node
from backend.agents.state import ResumeState
from backend.core.config import get_settings
from backend.core.logger import get_logger
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)
settings = get_settings()


# ── Interrupt (human-in-the-loop) passthrough nodes ─────────────────────────

async def show_ats_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """Interrupt node — pauses graph; frontend reads ATS results."""
    logger.info("Graph interrupted at show_ats", user_id=state["user_id"])
    return {}


async def show_resume_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """Interrupt node — pauses graph; frontend shows resume preview."""
    logger.info("Graph interrupted at show_resume", user_id=state["user_id"])
    return {}


async def cover_letter_ask_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """Interrupt node — pauses graph; frontend asks Gate 3."""
    logger.info("Graph interrupted at cover_letter_ask", user_id=state["user_id"])
    return {}


async def show_cover_letter_node(state: ResumeState, mcp: MCPRegistry) -> dict:
    """Interrupt node — pauses graph; frontend shows cover letter."""
    logger.info("Graph interrupted at show_cover_letter", user_id=state["user_id"])
    return {}


# ── Conditional edges ────────────────────────────────────────────────────────

def route_after_ats(state: ResumeState) -> Literal["resume_writer", "__end__"]:
    """Gate 1: did user confirm they want a resume?"""
    if state.get("user_confirmed"):
        return "resume_writer"
    return END


def route_after_rescore(
    state: ResumeState,
) -> Literal["show_resume", "resume_writer"]:
    """
    Gate: ATS score >= 95 OR max retries reached → show resume.
    Otherwise → retry resume_writer.
    """
    score = state.get("ats_score", 0.0)
    retries = state.get("retry_count", 0)

    if score >= settings.ats_pass_threshold or retries >= settings.ats_max_retries:
        logger.info(
            "Rescore routing → show_resume",
            score=score,
            retries=retries,
            threshold=settings.ats_pass_threshold,
        )
        return "show_resume"

    logger.info(
        "Rescore routing → resume_writer (retry)",
        score=score,
        retries=retries,
    )
    return "resume_writer"


def route_after_resume_confirm(
    state: ResumeState,
) -> Literal["cover_letter", "feedback_log"]:
    """Gate 3: does the user want a cover letter?"""
    if state.get("wants_cover_letter"):
        return "cover_letter"
    return "feedback_log"


# ── Graph factory ────────────────────────────────────────────────────────────

def _bind(node_fn, mcp: MCPRegistry):
    """Partially apply the MCP registry to a node function."""
    return functools.partial(node_fn, mcp=mcp)


async def build_graph(mcp: MCPRegistry):
    """
    Build and compile the LangGraph StateGraph.

    Returns the compiled graph app with PostgresSaver checkpointer.
    Call once at application startup and cache the result.
    """
    db_url = settings.supabase_db_url

    # Async PostgresSaver for non-blocking checkpoint writes
    checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    await checkpointer.setup()  # creates langgraph_checkpoints table if needed

    graph = StateGraph(ResumeState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    graph.add_node("ats_analyzer",       _bind(ats_analyzer_node, mcp))
    graph.add_node("show_ats",           _bind(show_ats_node, mcp))
    graph.add_node("resume_writer",      _bind(resume_writer_node, mcp))
    graph.add_node("ats_rescorer",       _bind(ats_rescorer_node, mcp))
    graph.add_node("show_resume",        _bind(show_resume_node, mcp))
    graph.add_node("cover_letter_ask",   _bind(cover_letter_ask_node, mcp))
    graph.add_node("cover_letter",       _bind(cover_letter_node, mcp))
    graph.add_node("show_cover_letter",  _bind(show_cover_letter_node, mcp))
    graph.add_node("feedback_log",       _bind(feedback_log_node, mcp))

    # ── Entry point ───────────────────────────────────────────────────────
    graph.set_entry_point("ats_analyzer")

    # ── Edges ─────────────────────────────────────────────────────────────
    graph.add_edge("ats_analyzer", "show_ats")

    graph.add_conditional_edges(
        "show_ats",
        route_after_ats,
        {"resume_writer": "resume_writer", END: END},
    )

    graph.add_edge("resume_writer", "ats_rescorer")

    graph.add_conditional_edges(
        "ats_rescorer",
        route_after_rescore,
        {"show_resume": "show_resume", "resume_writer": "resume_writer"},
    )

    graph.add_edge("show_resume", "cover_letter_ask")

    graph.add_conditional_edges(
        "cover_letter_ask",
        route_after_resume_confirm,
        {"cover_letter": "cover_letter", "feedback_log": "feedback_log"},
    )

    graph.add_edge("cover_letter", "show_cover_letter")
    graph.add_edge("show_cover_letter", "feedback_log")
    graph.add_edge("feedback_log", END)

    # ── Compile with interrupt_before gates ───────────────────────────────
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "show_ats",
            "show_resume",
            "cover_letter_ask",
            "show_cover_letter",
        ],
    )

    logger.info("LangGraph compiled successfully")
    return app
