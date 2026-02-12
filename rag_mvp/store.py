import os, json, time, uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import faiss

from rag_mvp.embeddings import embed_text, DIM
from rag_mvp.chunk import chunk_text

DATA_DIR = Path(os.getenv("RAG_DATA_DIR", "rag_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _tenant_dir(tenant_id: str) -> Path:
    d = DATA_DIR / tenant_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _index_path(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "index.faiss"

def _meta_path(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "meta.jsonl"

def _load_index(tenant_id: str) -> faiss.IndexFlatIP:
    p = _index_path(tenant_id)
    if p.exists():
        return faiss.read_index(str(p))
    return faiss.IndexFlatIP(DIM)

def _save_index(tenant_id: str, index: faiss.IndexFlatIP):
    faiss.write_index(index, str(_index_path(tenant_id)))

def _append_meta(tenant_id: str, rows: List[Dict[str, Any]]):
    mp = _meta_path(tenant_id)
    with mp.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _read_meta(tenant_id: str) -> List[Dict[str, Any]]:
    mp = _meta_path(tenant_id)
    if not mp.exists():
        return []
    out = []
    with mp.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out

def _acl_allows(meta: Dict[str, Any], user_id: str, tenant_id: str, workflow_id: Optional[str]) -> bool:
    acl = meta.get("acl", {})
    mode = acl.get("mode", "tenant")  # default tenant
    if mode == "tenant":
        return meta.get("tenant_id") == tenant_id
    if mode == "private":
        return meta.get("owner_user_id") == user_id
    if mode == "workflow":
        allowed = set(acl.get("workflow_ids", []))
        return (workflow_id is not None) and (workflow_id in allowed)
    return False

def ingest_document(
    tenant_id: str,
    user_id: str,
    title: str,
    text: str,
    acl_mode: str = "tenant",
    workflow_ids: Optional[List[str]] = None,
    chunk_size: int = 800,
    overlap: int = 120
) -> Dict[str, Any]:
    doc_id = str(uuid.uuid4())
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    index = _load_index(tenant_id)
    metas = []

    vectors = []
    for i, ch in enumerate(chunks):
        vec = embed_text(ch)
        vectors.append(vec)

        meta = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "doc_id": doc_id,
            "chunk_id": i,
            "title": title,
            "text": ch,
            "owner_user_id": user_id,
            "created_ts": int(time.time()),
            "acl": {
                "mode": acl_mode,
                "workflow_ids": workflow_ids or []
            }
        }
        metas.append(meta)

    if vectors:
        X = np.stack(vectors).astype(np.float32)
        index.add(X)
        _save_index(tenant_id, index)
        _append_meta(tenant_id, metas)

    return {"ok": True, "doc_id": doc_id, "chunks": len(chunks)}

def query(
    tenant_id: str,
    user_id: str,
    query_text: str,
    top_k: int = 5,
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    index = _load_index(tenant_id)
    metas = _read_meta(tenant_id)

    if index.ntotal == 0 or not metas:
        return {"ok": True, "matches": []}

    q = embed_text(query_text).astype(np.float32).reshape(1, -1)
    k = min(top_k * 5, index.ntotal)  # retrieve more then filter by ACL
    scores, ids = index.search(q, k)

    # FAISS index is flat; ids are in insertion order -> match metas by row index
    matches = []
    for rank, idx in enumerate(ids[0].tolist()):
        if idx < 0 or idx >= len(metas):
            continue
        m = metas[idx]
        if not _acl_allows(m, user_id=user_id, tenant_id=tenant_id, workflow_id=workflow_id):
            continue
        matches.append({
            "score": float(scores[0][rank]),
            "doc_id": m["doc_id"],
            "title": m["title"],
            "chunk_id": m["chunk_id"],
            "text": m["text"][:1200]
        })
        if len(matches) >= top_k:
            break

    return {"ok": True, "matches": matches}
