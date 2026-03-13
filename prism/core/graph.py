"""
core/graph.py

LangGraph pipeline builder for Prism.

Topology:
  START → jd_cleaner + resume_loader (PARALLEL)
        → jd_intelligence + resume_contextualizer (PARALLEL)
        → hybrid_indexer
        → hybrid_retriever
        → rewriter → critic → [pass → fact_checker | retry → reflector → rewriter]
        → fact_checker  ← HITL interrupt here
        → ats_formatter → voice_extractor → humanizer
        → cover_letter → report_assembler → END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ResumeState
from .agents import (
    jd_cleaner_node,
    resume_loader_node,
    jd_intelligence_node,
    resume_contextualizer_node,
    hybrid_indexer_node,
    hybrid_retriever_node,
    rewriter_node,
    critic_node,
    reflector_node,
    should_continue_reflexion,
    fact_checker_node,
    ats_formatter_node,
    voice_extractor_node,
    humanizer_node,
    cover_letter_node,
    report_assembler_node,
)


def build_graph() -> StateGraph:
    builder = StateGraph(ResumeState)

    # Register all 15 nodes
    for name, fn in [
        ("jd_cleaner",            jd_cleaner_node),
        ("resume_loader",         resume_loader_node),
        ("jd_intelligence",       jd_intelligence_node),
        ("resume_contextualizer", resume_contextualizer_node),
        ("hybrid_indexer",        hybrid_indexer_node),
        ("hybrid_retriever",      hybrid_retriever_node),
        ("rewriter",              rewriter_node),
        ("critic",                critic_node),
        ("reflector",             reflector_node),
        ("fact_checker",          fact_checker_node),
        ("ats_formatter",         ats_formatter_node),
        ("voice_extractor",       voice_extractor_node),
        ("humanizer",             humanizer_node),
        ("cover_letter",          cover_letter_node),
        ("report_assembler",      report_assembler_node),
    ]:
        builder.add_node(name, fn)

    # ── LAYER 0: Parallel pre-processing (both start from START) ──────────
    builder.add_edge(START, "jd_cleaner")
    builder.add_edge(START, "resume_loader")

    # ── LAYER 1: Parallel intelligence ────────────────────────────────────
    builder.add_edge("jd_cleaner",            "jd_intelligence")
    builder.add_edge("resume_loader",         "resume_contextualizer")

    # ── LAYER 1b: BM25 indexing (after contextualization) ─────────────────
    builder.add_edge("resume_contextualizer", "hybrid_indexer")

    # ── LAYER 2: Hybrid retrieval (waits for both jd_intelligence + hybrid_indexer) ──
    builder.add_edge("jd_intelligence",       "hybrid_retriever")
    builder.add_edge("hybrid_indexer",        "hybrid_retriever")

    # ── LAYER 3: Reflexion loop ────────────────────────────────────────────
    builder.add_edge("hybrid_retriever", "rewriter")
    builder.add_edge("rewriter",         "critic")

    # Conditional: score >= 85 → pass to fact_checker, else → reflector
    builder.add_conditional_edges(
        "critic",
        should_continue_reflexion,
        {"pass": "fact_checker", "retry": "reflector"},
    )
    builder.add_edge("reflector", "rewriter")   # Close the Reflexion loop

    # ── LAYER 4: Quality gates ─────────────────────────────────────────────
    # fact_checker is the HITL interrupt point (configured in compile_graph)
    builder.add_edge("fact_checker",   "ats_formatter")

    # ── LAYER 5+6: Voice → Humanize → Cover Letter → Report ───────────────
    builder.add_edge("ats_formatter",  "voice_extractor")
    builder.add_edge("voice_extractor","humanizer")
    builder.add_edge("humanizer",      "cover_letter")
    builder.add_edge("cover_letter",   "report_assembler")
    builder.add_edge("report_assembler", END)

    return builder


def compile_graph(hitl: bool = True):
    """
    Compile the graph with optional HITL interrupt.

    hitl=True  → pauses BEFORE fact_checker so Krishna can review the draft
    hitl=False → runs end-to-end without stopping
    """
    builder      = build_graph()
    checkpointer = MemorySaver()
    interrupt_nodes = ["fact_checker"] if hitl else []
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_nodes,
    )


def run_optimizer(
    jd_text:     str,
    company_name: str,
    role_name:   str,
    thread_id:   str = "default",
    job_url:     str = "",
    salary_range: str = "",
    hitl:        bool = True,
) -> dict:
    """
    Phase 1 runner. Runs until the HITL interrupt point (before fact_checker).
    Returns the state dict at the interrupt.

    Prints: target role, running status, ATS critic score, first 2000 chars of draft.
    """
    graph = compile_graph(hitl=hitl)

    initial_state = {
        "raw_jd":         jd_text,
        "company_name":   company_name,
        "role_name":      role_name,
        "job_url":        job_url,
        "salary_range":   salary_range,
        "loop_count":     0,
        "human_approved": False,
        "human_feedback": "",
        "thread_id":      thread_id,
        "logs":           [],
        "errors":         [],
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(initial_state, config=config)

    print(f"\n[Prism] Target: {role_name} @ {company_name}")
    print(f"[Prism] Critic score: {result.get('critic_score', 'N/A')}/100")
    print(f"[Prism] Draft preview:\n{result.get('draft_resume', '')[:2000]}\n")

    return result


def resume_after_approval(
    thread_id: str,
    feedback:  str = "",
    hitl:      bool = True,
) -> dict:
    """
    Phase 2 runner. Resumes from checkpoint after human approval.

    If feedback provided: injects it as reflection_notes and resets critic_score
    to 0 to force one more rewriter pass before quality gates run.
    """
    graph  = compile_graph(hitl=hitl)
    config = {"configurable": {"thread_id": thread_id}}

    update: dict = {"human_approved": True}
    if feedback.strip():
        update["human_feedback"]   = feedback
        update["reflection_notes"] = f"HUMAN FEEDBACK:\n{feedback}"
        update["critic_score"]     = 0   # Force one more rewriter pass

    result = graph.invoke(update, config=config)

    report = result.get("ats_score_report", {})
    print(f"\n[Prism] Final ATS score:    {report.get('final_ats_score', 'N/A')}/100")
    print(f"[Prism] Keyword density:     {report.get('keyword_density_pct', 'N/A')}%")
    print(f"[Prism] Fact check:          {'PASS' if report.get('fact_check_passed') else 'FAIL'}")
    print(f"[Prism] Cover letter risk:   {report.get('cover_letter_ai_risk', 'N/A')}/100")
    print(f"[Prism] Resume saved to:     {result.get('resume_output_path', '')}")
    print(f"[Prism] Cover letter saved:  {result.get('cover_letter_path', '')}")

    return result
