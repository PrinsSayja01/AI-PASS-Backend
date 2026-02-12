from __future__ import annotations
import re
import numpy as np

_word = re.compile(r"[A-Za-z0-9_]+")

def embed_text(text: str, dim: int = 384) -> np.ndarray:
    """
    Deterministic lightweight embedding:
    - tokenize words
    - hash into fixed vector
    - L2 normalize
    """
    v = np.zeros((dim,), dtype="float32")
    words = _word.findall((text or "").lower())
    if not words:
        return v
    for w in words:
        h = hash(w) % dim
        v[h] += 1.0
    # normalize
    n = float(np.linalg.norm(v))
    if n > 0:
        v /= n
    return v
