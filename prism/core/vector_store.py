"""
core/vector_store.py

Hybrid retrieval: BM25 (exact keyword) + ChromaDB (semantic) + RRF fusion.

Why hybrid?
- BM25 catches exact tool names: "LangGraph", "FAISS", "GPT-4o"
- ChromaDB catches semantic equivalents: "agent orchestration" ↔ "multi-agent system"
- RRF (k=60) ensures neither dominates — balanced, research-validated fusion
"""

from rank_bm25 import BM25Okapi


def hybrid_retrieve(
    query: str,
    collection,
    chunks: list,
    top_k: int = 8,
    k_rrf: int = 60,
) -> list:
    """
    Three-stage hybrid retrieval with RRF fusion.

    Args:
        query:      Query string (JD keywords + must-haves joined)
        collection: ChromaDB collection object
        chunks:     List of resume chunk dicts
        top_k:      Number of top results to return
        k_rrf:      RRF smoothing constant (60 is standard in literature)

    Returns:
        List of chunk dicts enriched with {rrf_score, bm25_rank, semantic_score}
    """
    if not chunks:
        return []

    # ── Stage 1: BM25 exact keyword matching ─────────────────────────────
    texts = [c["text"] for c in chunks]
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_ranked = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)

    # ── Stage 2: ChromaDB semantic similarity ─────────────────────────────
    n_results = min(top_k, collection.count()) if collection.count() > 0 else 1
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances", "ids"],
    )

    # Map ChromaDB IDs back to chunk indices
    semantic_ranked = []
    result_ids       = results["ids"][0]       if results["ids"]       else []
    result_distances = results["distances"][0] if results["distances"] else []

    for chroma_id, dist in zip(result_ids, result_distances):
        chunk_idx = next(
            (i for i, c in enumerate(chunks) if c["id"] == chroma_id), None
        )
        if chunk_idx is not None:
            # Convert cosine distance (0=identical) to similarity score
            semantic_score = 1 - dist
            semantic_ranked.append((chunk_idx, semantic_score))

    # ── Stage 3: RRF Fusion ───────────────────────────────────────────────
    # Formula: 1 / (k + rank)  — higher rank = lower score
    rrf_scores: dict = {}
    for rank, (idx, _) in enumerate(bm25_ranked):
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k_rrf + rank + 1)
    for rank, (idx, _) in enumerate(semantic_ranked):
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k_rrf + rank + 1)

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    # ── Build output ──────────────────────────────────────────────────────
    output = []
    for idx, rrf_score in fused:
        chunk = dict(chunks[idx])  # shallow copy
        bm25_rank = next(r for r, (i, _) in enumerate(bm25_ranked) if i == idx)
        semantic_score = next(
            (s for i, s in semantic_ranked if i == idx), 0.0
        )
        chunk.update({
            "rrf_score":      round(rrf_score, 5),
            "bm25_rank":      bm25_rank,
            "semantic_score": round(semantic_score, 4),
        })
        output.append(chunk)

    return output
