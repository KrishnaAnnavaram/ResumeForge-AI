"""Retrieval Agent — three-layer hybrid retrieval."""
import time
from sqlalchemy.ext.asyncio import AsyncSession

from careeros.agents.state import CareerOSState
from careeros.core.exceptions import RetrievalError, InsufficientEvidenceError
from careeros.core.logging import get_logger
from careeros.retrieval.semantic_search import semantic_search
from careeros.retrieval.structured_search import structured_search
from careeros.retrieval.session_search import session_search
from careeros.retrieval.evidence_ranker import rank_evidence
from careeros.ingestion.embedder import embed

log = get_logger(__name__)


async def run_retrieval_agent(state: CareerOSState, db: AsyncSession) -> CareerOSState:
    """Execute three-layer hybrid retrieval and return ranked evidence set."""
    start = time.time()
    log.info("agent.start", agent="Retrieval_Agent", session_id=state["session_id"], user_id=state["user_id"])

    try:
        jd = state["jd_structured"]
        if not jd:
            raise RetrievalError("No structured JD in state — run JD parser first")

        user_id = state["user_id"]
        required_skills = jd.get("required_skills", [])
        domain = jd.get("domain")

        # Build JD signal for embedding
        jd_signal = " ".join(filter(None, [
            jd.get("role_title", ""),
            domain or "",
            " ".join(required_skills[:10]),
        ]))

        # Layer 1: Semantic search
        query_embedding = await embed(jd_signal)
        l1_results = await semantic_search(
            query_embedding=query_embedding,
            user_id=user_id,
            db=db,
        )

        # Layer 2: Structured skill match
        l2_results = await structured_search(
            required_skills=required_skills,
            user_id=user_id,
            db=db,
        )

        # Layer 3: Prior session search
        l3_results = await session_search(
            user_id=user_id,
            current_domain=domain,
            current_required_skills=required_skills,
            db=db,
        )

        # Rank and merge
        ranked_evidence, low_evidence_warning = rank_evidence(l1_results, l2_results, l3_results)

        if low_evidence_warning:
            state["layer1_warnings"] = state.get("layer1_warnings", []) + [
                f"Low evidence found ({len(ranked_evidence)} bullets). Generation quality may be limited."
            ]

        elapsed = int((time.time() - start) * 1000)
        log.info(
            "agent.complete",
            agent="Retrieval_Agent",
            session_id=state["session_id"],
            duration_ms=elapsed,
            l1=len(l1_results),
            l2=len(l2_results),
            l3=len(l3_results),
            top_evidence=len(ranked_evidence),
        )

        return {
            **state,
            "evidence_set": ranked_evidence,
            "low_evidence_warning": low_evidence_warning,
        }

    except Exception as exc:
        log.error("agent.failed", agent="Retrieval_Agent", session_id=state["session_id"], error=str(exc), error_type=type(exc).__name__)
        raise RetrievalError(f"Evidence retrieval failed: {exc}") from exc
