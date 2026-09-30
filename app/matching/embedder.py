from functools import lru_cache

import numpy as np

from app import config


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBEDDING_MODEL)


def embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized embeddings, so a dot product equals cosine similarity."""
    if not texts:
        return np.zeros((0, 1))
    return np.asarray(_model().encode(texts, normalize_embeddings=True, show_progress_bar=False))