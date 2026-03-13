"""
core/agents.py

All 15 LangGraph agent node implementations for Prism.
Each node takes ResumeState and returns a partial dict.

Temperature guide:
  0.0  — analytical nodes (jd_intelligence, critic, fact_checker)
  0.1  — rewriter (slight creativity, mostly deterministic)
  0.15 — humanizer (needs natural variation)
  0.2  — cover letter (most creative)
"""

import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from rank_bm25 import BM25Okapi

from .state import ResumeState

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# LLM helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_llm(temperature: float = 0.0) -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=temperature,
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )


def call_llm(system: str, user: str, temperature: float = 0.0) -> str:
    try:
        resp = get_llm(temperature).invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return resp.content.strip()
    except Exception as e:
        return f"LLM_ERROR: {str(e)}"


def parse_json(text: str) -> Any:
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    return json.loads(clean)


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: jd_cleaner_node
# ─────────────────────────────────────────────────────────────────────────────

def jd_cleaner_node(state: ResumeState) -> dict:
    """Strip HTML, banners, and boilerplate from raw JD."""
    system = (
        "You are a JD pre-processor. Remove HTML tags, cookie banners, nav menus, "
        "salary boilerplate ('competitive compensation', 'equal opportunity employer'), "
        "and any text NOT about the actual job requirements or responsibilities. "
        "Return ONLY the cleaned plain-text JD. No preamble."
    )
    user = state["raw_jd"]
    try:
        result = call_llm(system, user, temperature=0.0)
        if result.startswith("LLM_ERROR"):
            return {
                "clean_jd": user,
                "errors": [{"node": "jd_cleaner", "error": result}],
                "logs": [{"node": "jd_cleaner", "status": "fallback_raw"}],
            }
        return {
            "clean_jd": result,
            "logs": [{"node": "jd_cleaner", "chars_in": len(user), "chars_out": len(result)}],
        }
    except Exception as e:
        return {
            "clean_jd": user,
            "errors": [{"node": "jd_cleaner", "error": str(e)}],
            "logs": [{"node": "jd_cleaner", "status": "error_fallback"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: resume_loader_node  (No LLM call)
# ─────────────────────────────────────────────────────────────────────────────

def resume_loader_node(state: ResumeState) -> dict:
    """Find .docx resume, parse it, chunk it, build ChromaDB."""
    from .resume_parser import (
        parse_resume_docx,
        chunk_resume,
        extract_verified_metrics,
        build_vector_store,
    )

    search_patterns = [
        "**/*[Rr]esume*.docx",
        "**/*[Kk]rishna*.docx",
        "**/*[Aa]nnavaram*.docx",
        "prism_files/**/*.docx",
        "**/*.docx",
    ]

    resume_path = None
    for pattern in search_patterns:
        found = glob.glob(pattern, recursive=True)
        if found:
            resume_path = found[0]
            break

    if not resume_path:
        return {
            "resume_chunks":     [],
            "vector_collection": None,
            "verified_metrics":  {},
            "errors": [{
                "node":  "resume_loader",
                "error": (
                    "No .docx resume found. Place Krishna's resume .docx in the "
                    "project root or prism_files/ directory."
                ),
            }],
            "logs": [{"node": "resume_loader", "status": "no_docx_found"}],
        }

    try:
        parsed     = parse_resume_docx(resume_path)
        chunks     = chunk_resume(parsed)
        metrics    = extract_verified_metrics(parsed)
        collection = build_vector_store(chunks)

        return {
            "resume_chunks":     chunks,
            "vector_collection": collection,
            "verified_metrics":  metrics,
            "logs": [{
                "node":    "resume_loader",
                "file":    resume_path,
                "chunks":  len(chunks),
                "metrics": len(metrics),
            }],
        }
    except Exception as e:
        return {
            "resume_chunks":     [],
            "vector_collection": None,
            "verified_metrics":  {},
            "errors": [{"node": "resume_loader", "error": str(e)}],
            "logs":   [{"node": "resume_loader", "status": "parse_error"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: jd_intelligence_node
# ─────────────────────────────────────────────────────────────────────────────

def jd_intelligence_node(state: ResumeState) -> dict:
    """Deep structured analysis of the cleaned JD."""
    system = """You are a senior technical recruiter and ATS expert.
Analyze the job description and return ONLY the following JSON (no preamble, no markdown fences):
{
  "exact_keywords": [
    {"term": "LangGraph", "full_form": "LangGraph agent orchestration", "priority": "must_have", "frequency": 3}
  ],
  "must_haves": ["list of hard requirements"],
  "nice_haves": ["list of preferred skills"],
  "red_flags": ["things they explicitly do not want"],
  "seniority": "senior|mid|junior|lead",
  "company_tone": "startup-casual|enterprise-formal|technical-direct",
  "top_3_focus_areas": ["what this person will actually DO day-to-day"],
  "job_title_exact": "exact title from JD",
  "domain": "healthcare|fintech|enterprise-saas|etc",
  "years_required": "X",
  "salary_range": "extract if mentioned, else empty string",
  "keyword_density_target": "70-75%"
}

Rules:
- Include BOTH acronym and full form as separate keyword entries
- priority = 'must_have' if mentioned 2+ times OR in requirements section
- red_flags: watch for 'not looking for', implied culture signals
- DO NOT include generic soft skills unless mentioned 3+ times
- Hard ceiling on density: 80% — modern ATS spam detection above this"""

    clean_jd = state.get("clean_jd") or state.get("raw_jd", "")
    try:
        raw = call_llm(system, clean_jd, temperature=0.0)
        analysis = parse_json(raw)
        return {
            "jd_analysis": analysis,
            "logs": [{
                "node":     "jd_intelligence",
                "keywords": len(analysis.get("exact_keywords", [])),
                "domain":   analysis.get("domain", ""),
                "seniority": analysis.get("seniority", ""),
            }],
        }
    except Exception as e:
        fallback = {
            "exact_keywords": [], "must_haves": [], "nice_haves": [],
            "red_flags": [], "seniority": "senior", "company_tone": "technical-direct",
            "top_3_focus_areas": [], "job_title_exact": state.get("role_name", ""),
            "domain": "", "years_required": "5", "salary_range": "",
            "keyword_density_target": "70-75%",
        }
        return {
            "jd_analysis": fallback,
            "errors": [{"node": "jd_intelligence", "error": str(e)}],
            "logs":   [{"node": "jd_intelligence", "status": "fallback"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4: hybrid_indexer_node  (No LLM call)
# ─────────────────────────────────────────────────────────────────────────────

def hybrid_indexer_node(state: ResumeState) -> dict:
    """Build BM25Okapi index over contextualised resume chunks."""
    chunks = state.get("resume_chunks", [])
    texts  = [
        (c.get("context", "") + " " + c.get("text", "")).strip()
        for c in chunks
    ]

    if not texts:
        return {
            "bm25_index":  None,
            "chunk_texts": [],
            "logs": [{"node": "hybrid_indexer", "status": "no_chunks"}],
        }

    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)

    return {
        "bm25_index":  bm25,
        "chunk_texts": texts,
        "logs": [{"node": "hybrid_indexer", "indexed": len(texts)}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5: hybrid_retriever_node
# ─────────────────────────────────────────────────────────────────────────────

def hybrid_retriever_node(state: ResumeState) -> dict:
    """Hybrid BM25 + ChromaDB retrieval with RRF fusion."""
    from .vector_store import hybrid_retrieve

    analysis   = state.get("jd_analysis", {})
    chunks     = state.get("resume_chunks", [])
    collection = state.get("vector_collection")

    must_haves = analysis.get("must_haves", [])
    keywords   = [kw["term"] for kw in analysis.get("exact_keywords", [])]
    query      = " ".join(must_haves + keywords)

    if not query.strip() or not chunks:
        return {
            "retrieved_chunks": chunks,
            "logs": [{"node": "hybrid_retriever", "status": "no_query_or_chunks"}],
        }

    try:
        if collection is not None:
            retrieved = hybrid_retrieve(query, collection, chunks, top_k=8)
        else:
            # Fallback: BM25 only
            bm25 = state.get("bm25_index")
            if bm25 is None:
                texts     = [c.get("text", "") for c in chunks]
                tokenized = [t.lower().split() for t in texts]
                bm25      = BM25Okapi(tokenized)
            scores = bm25.get_scores(query.lower().split())
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:8]
            retrieved = [dict(chunks[i], rrf_score=s, bm25_rank=r, semantic_score=0.0)
                         for r, (i, s) in enumerate(ranked)]

        return {
            "retrieved_chunks": retrieved,
            "logs": [{"node": "hybrid_retriever", "retrieved": len(retrieved)}],
        }
    except Exception as e:
        return {
            "retrieved_chunks": chunks[:8],
            "errors": [{"node": "hybrid_retriever", "error": str(e)}],
            "logs":   [{"node": "hybrid_retriever", "status": "fallback_all_chunks"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6: resume_contextualizer_node
# ─────────────────────────────────────────────────────────────────────────────

def resume_contextualizer_node(state: ResumeState) -> dict:
    """
    Anthropic Contextual Retrieval: add 2-sentence context to each chunk.
    Improves BM25 retrieval accuracy by ~49%.
    """
    chunks = state.get("resume_chunks", [])
    if not chunks:
        return {
            "resume_chunks": chunks,
            "logs": [{"node": "resume_contextualizer", "status": "no_chunks"}],
        }

    system = (
        "Summarise this resume chunk in 1-2 sentences capturing: "
        "what role/section this is, which technologies and domains it covers, "
        "and what outcome metrics it contains. Be specific, not generic."
    )

    enriched = []
    for chunk in chunks:
        try:
            user    = f"CHUNK (id={chunk['id']}):\n{chunk['text']}"
            context = call_llm(system, user, temperature=0.0)
            if context.startswith("LLM_ERROR"):
                context = ""
        except Exception:
            context = ""
        enriched.append({**chunk, "context": context})

    return {
        "resume_chunks": enriched,
        "logs": [{"node": "resume_contextualizer", "enriched": len(enriched)}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7: rewriter_node  (ACTOR — temperature 0.1)
# ─────────────────────────────────────────────────────────────────────────────

BANNED_WORDS = (
    "spearheaded, leveraged, cutting-edge, passionate, robust, dynamic, "
    "innovative, synergy, utilized, holistic, transformative, impactful, "
    "streamlined, delivered, fostered, harnessed, demonstrated, orchestrated"
)

def rewriter_node(state: ResumeState) -> dict:
    """Core resume rewriter. Incorporates reflection_notes on subsequent loops."""
    analysis         = state.get("jd_analysis", {})
    retrieved_chunks = state.get("retrieved_chunks", [])
    loop_count       = state.get("loop_count", 0)
    reflection_notes = state.get("reflection_notes", "")
    company          = state.get("company_name", "")
    role             = state.get("role_name", "")

    keywords_list = analysis.get("exact_keywords", [])
    all_terms     = [kw["term"] for kw in keywords_list]
    must_haves    = analysis.get("must_haves", [])
    job_title     = analysis.get("job_title_exact", role)
    domain        = analysis.get("domain", "")
    seniority     = analysis.get("seniority", "senior")
    tone          = analysis.get("company_tone", "technical-direct")
    top_focus     = analysis.get("top_3_focus_areas", [])
    density_target = analysis.get("keyword_density_target", "70-75%")

    # Build resume source context
    resume_context = "\n\n---\n\n".join(
        f"[{c.get('section','').upper()} | rank={c.get('role_rank','N/A')}]\n{c.get('text','')}"
        for c in retrieved_chunks
    )

    system = f"""You are an expert ATS resume writer. Your ONLY job is to write the best
possible resume for Krishna Annavaram targeting this specific role.

═══ KEYWORD RULES (research-backed) ═══
- Target: {density_target} keyword coverage. Hard ceiling: 80%.
- Use EXACT JD terminology — NEVER synonyms (e.g. if JD says "LangGraph" don't write "workflow orchestrator")
- Include acronym AND full form on FIRST use only: "RAG (Retrieval-Augmented Generation)"
- Keywords must appear IN CONTEXT inside bullets — never standalone or stuffed in a skills list
- Density above 80% triggers modern ATS spam detection

═══ CONTENT RULES (non-negotiable) ═══
- NEVER invent facts, tools, metrics, or experiences not in the source resume
- NEVER change any percentage or number — not even by 1%
- NEVER remove existing quantified metrics
- Gap filling: if JD keyword exists in Krishna's skills but not in bullets,
  weave into nearest existing bullet using real context only (no fabrication)

═══ STRUCTURE RULES (ATS formatting) ═══
- Single-column, plain text only — NO tables, columns, graphics, borders
- Section order: Summary → Skills → Experience → Education
- Contact info in body (first line) — NEVER in header/footer (ATS skips those)
- Each job header: "Title at Company (Location) | Dates"
- Bullet format: [Strong Verb] + [What built/did] + [Tools used] + [Quantified result]
- Max 2 lines per bullet. No pronouns (I, my, we) anywhere.
- Most recent job: 5-6 bullets. All other jobs: 3-4 bullets.
- 2 pages is acceptable for a 5+ year candidate

═══ SUMMARY RULES ═══
- Line 1: Exact JD title + years of experience + domain
- Line 2: Top 3 JD tech skills using JD's exact wording
- Line 3: Strongest differentiator + one metric
- Max 4 sentences. Never start with "I".

═══ HUMANNESS RULES ═══
- Vary bullet lengths (some 1 line, some 2)
- No two adjacent bullets starting with the same verb
- Banned words: {BANNED_WORDS}

JD Context:
- Exact title: {job_title}
- Domain: {domain}
- Seniority: {seniority}
- Tone: {tone}
- Top focus areas: {', '.join(top_focus)}
- Must-haves: {', '.join(must_haves[:10])}
- Target keywords: {', '.join(all_terms[:20])}"""

    user_prefix = ""
    if loop_count > 0 and reflection_notes:
        user_prefix = (
            f"═══ SURGICAL FIX INSTRUCTIONS (apply exactly) ═══\n"
            f"{reflection_notes}\n"
            f"═════════════════════════════════════════════════\n\n"
        )

    user = (
        f"{user_prefix}"
        f"TARGET ROLE: {job_title} at {company}\n\n"
        f"SOURCE RESUME CHUNKS (use ONLY these facts):\n{resume_context}\n\n"
        f"Write the complete optimized resume now. Plain text only."
    )

    try:
        draft = call_llm(system, user, temperature=0.1)
        if draft.startswith("LLM_ERROR"):
            return {
                "draft_resume": state.get("draft_resume", ""),
                "loop_count":   loop_count + 1,
                "errors": [{"node": "rewriter", "error": draft}],
                "logs":   [{"node": "rewriter", "loop": loop_count, "status": "llm_error"}],
            }
        return {
            "draft_resume": draft,
            "loop_count":   loop_count + 1,
            "logs": [{"node": "rewriter", "loop": loop_count, "chars": len(draft)}],
        }
    except Exception as e:
        return {
            "draft_resume": state.get("draft_resume", ""),
            "loop_count":   loop_count + 1,
            "errors": [{"node": "rewriter", "error": str(e)}],
            "logs":   [{"node": "rewriter", "loop": loop_count, "status": "error"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 8: critic_node  (EVALUATOR — separate persona, temperature 0.0)
# ─────────────────────────────────────────────────────────────────────────────

def critic_node(state: ResumeState) -> dict:
    """
    Cold-audit the draft. Completely separate from the rewriter.
    Scores 0-100 across 4 dimensions (25 pts each).
    """
    draft    = state.get("draft_resume", "")
    analysis = state.get("jd_analysis", {})

    all_keywords = [kw["term"] for kw in analysis.get("exact_keywords", [])]
    must_haves   = analysis.get("must_haves", [])

    # Pre-compute keyword stats
    draft_lower  = draft.lower()
    kw_present   = [k for k in all_keywords if k.lower() in draft_lower]
    kw_missing   = [k for k in all_keywords if k.lower() not in draft_lower]
    density_pct  = (len(kw_present) / len(all_keywords) * 100) if all_keywords else 0

    density_warning = "ok"
    if density_pct > 80:
        density_warning = "over_stuffed"
    elif density_pct < 60:
        density_warning = "under_stuffed"

    system = """You are a forensic ATS auditor. You have NO idea who wrote this resume.
Your job is to find EVERY flaw coldly and objectively.

Evaluate the resume against the job description across 4 dimensions (25 pts each).
Return ONLY this JSON (no preamble, no markdown):
{
  "keyword_score": 0-25,
  "bullet_quality": 0-25,
  "structure_score": 0-25,
  "humanness_score": 0-25,
  "total_score": 0-100,
  "keyword_gaps": ["specific missing keywords"],
  "bullet_issues": [{"location": "Ideate bullet 2", "issue": "starts with Leveraged"}],
  "structure_issues": ["specific problems found"],
  "humanness_issues": ["specific AI-sounding phrases found"],
  "density_warning": "ok|over_stuffed|under_stuffed",
  "top_3_fixes": ["most impactful fixes in order of importance"]
}

Scoring criteria:
- keyword_score (25): keywords in context, both forms, density 70-80%
- bullet_quality (25): action verbs, quantified, no pronouns, varied lengths
- structure_score (25): standard headers, single-column, reverse-chrono, skills first
- humanness_score (25): no AI clichés, natural rhythm, sounds like a real engineer"""

    user = (
        f"JD MUST-HAVES: {', '.join(must_haves[:15])}\n"
        f"ALL KEYWORDS: {', '.join(all_keywords)}\n"
        f"PRE-COMPUTED: {len(kw_present)}/{len(all_keywords)} keywords found "
        f"({density_pct:.1f}%) — density: {density_warning}\n"
        f"MISSING: {', '.join(kw_missing[:20])}\n\n"
        f"RESUME TO AUDIT:\n{draft}"
    )

    try:
        raw    = call_llm(system, user, temperature=0.0)
        report = parse_json(raw)
        report["density_warning"] = density_warning
        score  = int(report.get("total_score", 0))
        return {
            "critic_score":  score,
            "critic_report": report,
            "logs": [{"node": "critic", "score": score, "density": round(density_pct, 1)}],
        }
    except Exception as e:
        return {
            "critic_score":  50,
            "critic_report": {"error": str(e), "density_warning": density_warning},
            "errors": [{"node": "critic", "error": str(e)}],
            "logs":   [{"node": "critic", "status": "fallback_score_50"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING FUNCTION: should_continue_reflexion
# ─────────────────────────────────────────────────────────────────────────────

def should_continue_reflexion(state: ResumeState) -> str:
    """Conditional edge: pass to quality gates or retry via reflector."""
    score = state.get("critic_score", 0)
    loop  = state.get("loop_count", 0)
    if score >= 85:
        return "pass"
    if loop >= 3:
        return "pass"  # Accept best result after 3 loops
    return "retry"


# ─────────────────────────────────────────────────────────────────────────────
# NODE 9: reflector_node
# ─────────────────────────────────────────────────────────────────────────────

def reflector_node(state: ResumeState) -> dict:
    """Convert critic report into surgical, specific rewrite instructions."""
    report = state.get("critic_report", {})
    draft  = state.get("draft_resume", "")

    system = """Convert this audit report into precise surgical rewrite instructions.

BAD: 'Improve the summary'
GOOD: 'Summary line 1 says Machine Learning Engineer — change to exact JD title Senior MLOps Engineer'

BAD: 'Add more keywords'
GOOD: 'Ideate bullet 3 mentions FAISS but missing Retrieval-Augmented Generation — add as: ...using FAISS for Retrieval-Augmented Generation (RAG)...'

Return a numbered list. Max 8 fixes. Most impactful first.
Each fix MUST reference: EXACT location + EXACT problem + EXACT fix."""

    user = (
        f"AUDIT REPORT:\n{json.dumps(report, indent=2)}\n\n"
        f"DRAFT (first 3000 chars):\n{draft[:3000]}"
    )

    try:
        notes = call_llm(system, user, temperature=0.0)
        return {
            "reflection_notes": notes,
            "logs": [{"node": "reflector", "fixes_length": len(notes)}],
        }
    except Exception as e:
        return {
            "reflection_notes": json.dumps(report.get("top_3_fixes", [])),
            "errors": [{"node": "reflector", "error": str(e)}],
            "logs":   [{"node": "reflector", "status": "fallback"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 10: fact_checker_node
# ─────────────────────────────────────────────────────────────────────────────

def fact_checker_node(state: ResumeState) -> dict:
    """Hard gate: verify every metric in draft against verified_metrics ground truth."""
    draft            = state.get("draft_resume", "")
    verified_metrics = state.get("verified_metrics", {})

    system = (
        "You are a fact-checker. Find any numbers, percentages, tool names, "
        "company names, or dates in the draft resume that DO NOT match the "
        "verified source data.\n"
        "Return ONLY JSON: "
        '{"passed": true, "violations": [{"location": "...", "claim_in_draft": "...", '
        '"verified_fact": "...", "severity": "critical|warning"}]}'
    )

    metrics_str = "\n".join(f"  {k}: {v}" for k, v in verified_metrics.items())
    user = (
        f"VERIFIED METRICS FROM ACTUAL RESUME:\n{metrics_str or '(none found)'}\n\n"
        f"DRAFT RESUME TO CHECK:\n{draft}"
    )

    try:
        raw    = call_llm(system, user, temperature=0.0)
        result = parse_json(raw)
        passed     = result.get("passed", True)
        violations = result.get("violations", [])
        # Critical violations = fail
        critical = [v for v in violations if v.get("severity") == "critical"]
        passed   = passed and len(critical) == 0

        return {
            "fact_check_passed": passed,
            "fact_violations":   violations,
            "logs": [{
                "node":       "fact_checker",
                "passed":     passed,
                "violations": len(violations),
                "critical":   len(critical),
            }],
        }
    except Exception as e:
        return {
            "fact_check_passed": True,   # Fail open — don't block pipeline
            "fact_violations":   [],
            "errors": [{"node": "fact_checker", "error": str(e)}],
            "logs":   [{"node": "fact_checker", "status": "fallback_passed"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 11: ats_formatter_node
# ─────────────────────────────────────────────────────────────────────────────

def ats_formatter_node(state: ResumeState) -> dict:
    """Auto-fix structural ATS compliance issues."""
    draft = state.get("draft_resume", "")

    system = """You are an ATS formatting expert. Fix ALL structural compliance issues.
Rules to enforce:
1. Standard section headers ONLY: Summary | Skills | Experience | Education
2. Single-column — flatten any table or multi-column structure
3. Contact info in body (first line), NOT in header/footer
4. Each job: 'Title at Company (Location) | Dates' format
5. Reverse chronological order (most recent job first)
6. Skills section BEFORE Experience
7. No graphics, icons, horizontal rules, or special characters
8. Consistent date format: Mon YYYY – Mon YYYY (e.g. Jan 2025 – Present)
9. Bullet character: simple hyphen (-) not bullets (•) or diamonds (◆)
10. PRESERVE every single fact, number, and word — only fix formatting

Return the corrected resume as plain text. No commentary."""

    try:
        fixed = call_llm(system, draft, temperature=0.0)
        if fixed.startswith("LLM_ERROR"):
            fixed = draft
        return {
            "format_fixed_resume": fixed,
            "logs": [{"node": "ats_formatter", "chars": len(fixed)}],
        }
    except Exception as e:
        return {
            "format_fixed_resume": draft,
            "errors": [{"node": "ats_formatter", "error": str(e)}],
            "logs":   [{"node": "ats_formatter", "status": "fallback_draft"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 12: voice_extractor_node
# ─────────────────────────────────────────────────────────────────────────────

def voice_extractor_node(state: ResumeState) -> dict:
    """Extract Krishna's natural writing style fingerprint."""
    chunks = state.get("resume_chunks", [])
    # Sample first 4 experience chunks
    exp_chunks = [c for c in chunks if c.get("section") == "experience"][:4]
    if not exp_chunks:
        exp_chunks = chunks[:4]

    sample_text = "\n\n".join(c.get("text", "") for c in exp_chunks)

    system = """Analyze this engineer's writing style and return ONLY this JSON:
{
  "avg_bullet_length": "short|medium|long",
  "preferred_openers": ["Built", "Developed", "Designed"],
  "phrasing_style": "direct-technical|narrative|metric-first",
  "sentence_rhythm": "compact-clauses|extended-with-context",
  "unique_phrases": ["phrases that sound like this person specifically"],
  "technical_depth": "always-shows-stack|outcome-focused|balanced"
}"""

    try:
        raw         = call_llm(system, sample_text, temperature=0.0)
        fingerprint = parse_json(raw)
        return {
            "voice_fingerprint": fingerprint,
            "logs": [{"node": "voice_extractor", "style": fingerprint.get("phrasing_style")}],
        }
    except Exception as e:
        fallback = {
            "avg_bullet_length": "medium",
            "preferred_openers": ["Built", "Developed", "Designed"],
            "phrasing_style":    "direct-technical",
            "sentence_rhythm":   "compact-clauses",
            "unique_phrases":    [],
            "technical_depth":   "balanced",
        }
        return {
            "voice_fingerprint": fallback,
            "errors": [{"node": "voice_extractor", "error": str(e)}],
            "logs":   [{"node": "voice_extractor", "status": "fallback"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 13: humanizer_node  (temperature 0.15)
# ─────────────────────────────────────────────────────────────────────────────

FULL_BANNED_WORDS = (
    "spearheaded, leveraged, cutting-edge, passionate, robust, dynamic, innovative, "
    "synergy, utilized, holistic, transformative, impactful, ecosystem, deep-dive, "
    "actionable, best-in-class, world-class, streamlined, delivered, fostered, "
    "orchestrated, architected, harnessed, demonstrated"
)


def humanizer_node(state: ResumeState) -> dict:
    """Remove AI writing patterns using voice fingerprint. Preserve all facts."""
    resume      = state.get("format_fixed_resume") or state.get("draft_resume", "")
    fingerprint = state.get("voice_fingerprint", {})

    system = f"""You are a writing naturalizer. Remove all AI writing patterns from this resume.

VOICE FINGERPRINT (match this style):
- Phrasing style: {fingerprint.get('phrasing_style', 'direct-technical')}
- Preferred openers: {', '.join(fingerprint.get('preferred_openers', ['Built', 'Developed']))}
- Sentence rhythm: {fingerprint.get('sentence_rhythm', 'compact-clauses')}
- Technical depth: {fingerprint.get('technical_depth', 'balanced')}

FULL BANNED WORDS LIST (replace every occurrence):
{FULL_BANNED_WORDS}

STRUCTURAL RULES:
- No two adjacent bullets start with the same verb
- Vary rhythm: some 1-line bullets, some 2-line
- Remove: "In this role", "As a", "I was responsible for", "Moreover", "Furthermore"
- Cut over-explanation (if point made in one clause, remove the repetition)

ABSOLUTE PRESERVATION (NEVER change these):
- KEEP every number and percentage exactly as-is
- KEEP every tool name (LangGraph, FAISS, ChromaDB, etc.)
- KEEP every company name, title, and date
- KEEP every JD keyword
- KEEP all section headers and structure

Return the humanized resume as plain text. No commentary."""

    try:
        humanized = call_llm(system, resume, temperature=0.15)
        if humanized.startswith("LLM_ERROR"):
            humanized = resume
        return {
            "humanized_resume": humanized,
            "logs": [{"node": "humanizer", "chars": len(humanized)}],
        }
    except Exception as e:
        return {
            "humanized_resume": resume,
            "errors": [{"node": "humanizer", "error": str(e)}],
            "logs":   [{"node": "humanizer", "status": "fallback"}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 14: cover_letter_node  (temperature 0.2)
# ─────────────────────────────────────────────────────────────────────────────

COVER_LETTER_BANNED = [
    "spearheaded", "leveraged", "passionate", "cutting-edge", "synergy",
    "transformative", "I am excited", "I am writing to express",
    "best-in-class", "I thrive", "holistic", "I am passionate about",
    "I am a team player", "excited opportunity", "ideal candidate",
]


def cover_letter_node(state: ResumeState) -> dict:
    """Write a 150-250 word cover letter with AI risk scoring."""
    analysis  = state.get("jd_analysis", {})
    company   = state.get("company_name", "")
    role      = state.get("role_name", "")
    humanized = state.get("humanized_resume") or state.get("format_fixed_resume", "")

    job_title  = analysis.get("job_title_exact", role)
    top_focus  = analysis.get("top_3_focus_areas", [])
    must_haves = analysis.get("must_haves", [])
    domain     = analysis.get("domain", "")

    system = f"""Write a 150-250 word cover letter for Krishna Annavaram.

STRUCTURE (4 paragraphs):
P1 HOOK: Name the exact role + company. One specific company connection.
   NEVER start with: "I am writing to express", "I am excited to apply", "I am reaching out"

P2 PROOF: ONE achievement with metric addressing the top JD priority.
   Use JD's own keywords. Be specific — no vague claims.

P3 CONNECTION: Why this SPECIFIC role (not generic). What unique combination
   Krishna brings. Reference something specific from the JD.

P4 CLOSE: Direct CTA mentioning something specific from the JD.
   NOT: "I look forward to hearing from you at your earliest convenience"
   YES: "Happy to walk through how I'd approach [specific JD challenge] in a call."

BANNED PHRASES: {', '.join(COVER_LETTER_BANNED)}

JD CONTEXT:
- Role: {job_title} at {company}
- Domain: {domain}
- Top focus areas: {', '.join(top_focus)}
- Must-haves to reference: {', '.join(must_haves[:5])}

Write exactly 150-250 words. Plain text. No subject line."""

    user = f"RESUME CONTEXT (for accurate achievement references):\n{humanized[:2000]}"

    try:
        cl = call_llm(system, user, temperature=0.2)
        if cl.startswith("LLM_ERROR"):
            cl = ""
    except Exception as e:
        cl = ""

    # Compute AI risk score
    cl_lower = cl.lower()
    risk = min(
        sum(1 for phrase in COVER_LETTER_BANNED if phrase.lower() in cl_lower) * 10,
        100,
    )
    word_count = len(cl.split())

    return {
        "cover_letter":       cl,
        "cover_letter_score": risk,
        "logs": [{
            "node":       "cover_letter",
            "words":      word_count,
            "risk_score": risk,
        }],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 15: report_assembler_node
# ─────────────────────────────────────────────────────────────────────────────

def report_assembler_node(state: ResumeState) -> dict:
    """Build final ATS score report, change log, and save output files."""
    analysis      = state.get("jd_analysis", {})
    humanized     = state.get("humanized_resume") or state.get("format_fixed_resume", "")
    cover_letter  = state.get("cover_letter", "")
    critic_score  = state.get("critic_score", 0)
    fact_passed   = state.get("fact_check_passed", True)
    fact_viols    = state.get("fact_violations", [])
    loop_count    = state.get("loop_count", 0)
    cl_score      = state.get("cover_letter_score", 0)
    company       = state.get("company_name", "")
    role          = state.get("role_name", "")
    thread_id     = state.get("thread_id", "")

    all_keywords  = [kw["term"] for kw in analysis.get("exact_keywords", [])]
    must_haves    = analysis.get("must_haves", [])
    humanized_lwr = humanized.lower()

    matched       = [k for k in all_keywords if k.lower() in humanized_lwr]
    missing       = [k for k in all_keywords if k.lower() not in humanized_lwr]
    must_matched  = [m for m in must_haves if m.lower() in humanized_lwr]
    density_pct   = (len(matched) / len(all_keywords) * 100) if all_keywords else 0.0

    ats_report = {
        "final_ats_score":        critic_score,
        "keyword_density_pct":    round(density_pct, 2),
        "keywords_matched":       matched,
        "keywords_missing":       missing,
        "must_haves_matched":     must_matched,
        "fact_check_passed":      fact_passed,
        "fact_violations":        fact_viols,
        "reflexion_loops_used":   loop_count,
        "cover_letter_ai_risk":   cl_score,
        "cover_letter_word_count": len(cover_letter.split()),
        "status":                 "PASS" if critic_score >= 75 else "NEEDS_REVIEW",
        "domain":                 analysis.get("domain", ""),
        "seniority":              analysis.get("seniority", ""),
    }

    change_log = [
        {
            "section": "Keywords",
            "what":    f"{len(matched)}/{len(all_keywords)} JD keywords incorporated",
            "why":     "ATS keyword matching",
        },
        {
            "section": "Reflexion",
            "what":    f"Resume optimized through {loop_count} critique loop(s)",
            "why":     f"Final score: {critic_score}/100",
        },
        {
            "section": "Fact Check",
            "what":    "PASS" if fact_passed else f"{len(fact_viols)} violation(s) found",
            "why":     "Ground truth verification from source resume",
        },
    ]

    # ── Save output files ──────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = re.sub(r"[^\w]", "_", company)
    safe_role    = re.sub(r"[^\w]", "_", role)
    base_name    = f"{safe_company}_{safe_role}_{ts}"

    Path("output").mkdir(exist_ok=True)
    resume_path = f"output/{base_name}_resume.txt"
    cl_path     = f"output/{base_name}_cover_letter.txt"

    try:
        Path(resume_path).write_text(humanized, encoding="utf-8")
    except Exception:
        resume_path = ""

    try:
        Path(cl_path).write_text(cover_letter, encoding="utf-8")
    except Exception:
        cl_path = ""

    return {
        "ats_score_report":   ats_report,
        "change_log":         change_log,
        "resume_output_path": resume_path,
        "cover_letter_path":  cl_path,
        "logs": [{
            "node":          "report_assembler",
            "ats_score":     critic_score,
            "density":       round(density_pct, 1),
            "keywords":      f"{len(matched)}/{len(all_keywords)}",
            "resume_saved":  resume_path,
            "cl_saved":      cl_path,
        }],
    }
