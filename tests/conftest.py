import hashlib
import re

import numpy as np
import pytest


def fake_embed(texts):
    """Deterministic bag-of-words embedding so tests don't download a model."""
    vecs = []
    for t in texts:
        v = np.zeros(128)
        for w in re.findall(r"[a-z0-9+#]+", t.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 128] += 1
        n = np.linalg.norm(v)
        vecs.append(v / n if n else v)
    return np.array(vecs)


@pytest.fixture(autouse=True)
def patch_embed(monkeypatch):
    from app.matching import embedder

    monkeypatch.setattr(embedder, "embed", fake_embed)