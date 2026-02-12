from dataclasses import dataclass
from typing import List, Dict
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

@dataclass
class Chunk:
    doc_id: str
    tenant_id: str
    text: str
    meta: Dict

def fake_embed(text: str, dim=384) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    v = rng.normal(size=(dim,)).astype("float32")
    v /= (np.linalg.norm(v) + 1e-9)
    return v

class RAGIndex:
    def __init__(self, dim=384):
        if faiss is None:
            raise RuntimeError("faiss not installed. pip install faiss-cpu")
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: List[Chunk] = []
        self.vectors: List[np.ndarray] = []

    def add_chunks(self, chunks: List[Chunk]):
        for c in chunks:
            vec = fake_embed(c.text, self.dim)
            self.vectors.append(vec)
            self.chunks.append(c)
        mat = np.vstack(self.vectors)
        self.index.add(mat)

    def search(self, tenant_id: str, query: str, k=5):
        qv = fake_embed(query, self.dim).reshape(1, -1)
        scores, ids = self.index.search(qv, k*3)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            ch = self.chunks[idx]
            if ch.tenant_id != tenant_id:
                continue
            results.append({"score": float(score), "text": ch.text, "meta": ch.meta})
            if len(results) >= k:
                break
        return results
