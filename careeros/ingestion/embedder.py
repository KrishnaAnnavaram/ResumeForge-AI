"""Embedding generation using sentence-transformers."""
from functools import lru_cache
from careeros.config import get_settings
from careeros.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load the embedding model (cached after first call)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.embedding_model)
        log.info("embedder.model_loaded", model=settings.embedding_model)
        return model
    except Exception as exc:
        log.error("embedder.model_load_failed", error=str(exc))
        raise


async def embed(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    model = _load_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []
    model = _load_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [e.tolist() for e in embeddings]
