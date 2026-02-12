from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss

from rag_mvp.embed import embed_text

BASE = Path("data/rag")
BASE.mkdir(parents=True, exist_ok=True)

def _tenant_dir(tenant_id: str) -> Path:
    d = BASE / tenant_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _paths(tenant_id: str):
    d = _tenant_dir(tenant_id)
    return d / "index.faiss", d / "meta.json"

def _load_meta(meta_path: Path) -> List[Dict[str, Any]]:
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return []

def _save_meta(meta_path: Path, meta: List[Dict[str, Any]]):
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

def _load_index(index_path: Path, dim: int) -> faiss.Index:
    if index_path.exists():
        return faiss.read_index(str(index_path))
    return faiss.IndexFlatIP(dim)  # cosine-ish because embeddings are normalized

def _save_index(index_path: Path, index: faiss.Index):
    faiss.write_index(index, str(index_path))

def ingest_document(tenant_id: str, doc_id: str, text_chunks: List[str], dim: int = 384) -> Dict[str, Any]:
    index_path, meta_path = _paths(tenant_id)
    meta = _load_meta(meta_path)
    index = _load_index(index_path, dim)

    vectors = []
    for i, ch in enumerate(text_chunks):
        v = embed_text(ch, dim=dim)
        vectors.append(v)
        meta.append({
            "tenant_id": tenant_id,
            "doc_id": doc_id,
            "chunk_id": i,
            "text": ch
        })

    if vectors:
        X = np.stack(vectors).astype("float32")
        index.add(X)

    _save_index(index_path, index)
    _save_meta(meta_path, meta)

    return {"tenant_id": tenant_id, "doc_id": doc_id, "chunks_added": len(text_chunks), "total_vectors": int(index.ntotal)}

def query(tenant_id: str, q: str, top_k: int = 5, dim: int = 384) -> Dict[str, Any]:
    index_path, meta_path = _paths(tenant_id)
    meta = _load_meta(meta_path)
    index = _load_index(index_path, dim)

    if index.ntotal == 0:
        return {"hits": [], "note": "empty index for tenant"}

    v = embed_text(q, dim=dim).reshape(1, -1).astype("float32")
    k = min(max(1, int(top_k)), 20)
    scores, ids = index.search(v, k)

    hits = []
    for score, idx in zip(scores[0].tolist(), ids[0].tolist()):
        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        # extra guard (should always match because index is tenant-scoped)
        if m.get("tenant_id") != tenant_id:
            continue
        hits.append({
            "score": float(score),
            "doc_id": m.get("doc_id"),
            "chunk_id": m.get("chunk_id"),
            "text": (m.get("text") or "")[:500]
        })

    return {"hits": hits}


def list_docs(tenant_id: str) -> Dict[str, Any]:
    index_path, meta_path = _paths(tenant_id)
    meta = _load_meta(meta_path)
    docs = {}
    for m in meta:
        did = m.get("doc_id")
        if not did:
            continue
        docs.setdefault(did, 0)
        docs[did] += 1
    out = [{"doc_id": k, "chunks": v} for k, v in sorted(docs.items(), key=lambda x: x[0])]
    return {"tenant_id": tenant_id, "count": len(out), "docs": out}

