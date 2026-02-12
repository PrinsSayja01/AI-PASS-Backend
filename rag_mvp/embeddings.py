import hashlib
import numpy as np

DIM = 384

def embed_text(text: str) -> np.ndarray:
    """
    Deterministic, offline embedding:
    Hash tokens into a fixed vector space. Not semantic, but stable + fast.
    Replace later with real embeddings (sentence-transformers/OpenAI/etc).
    """
    v = np.zeros((DIM,), dtype=np.float32)
    tokens = (text or "").lower().split()
    if not tokens:
        return v
    for t in tokens[:512]:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "big") % DIM
        sign = 1.0 if (h[2] % 2 == 0) else -1.0
        v[idx] += sign
    # normalize
    n = np.linalg.norm(v)
    if n > 0:
        v /= n
    return v
