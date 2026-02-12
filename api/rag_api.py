import json, time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import require_access  # your existing auth dependency
from api.device_deps import require_device_token  # device token dependency
from rag_mvp.store import ingest_document, query as rag_query

REPORT = Path("reports/rag_latest.json")
REPORT.parent.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/ingest")
def ingest(req: Request, payload: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    role = claims.get("role")
    if role not in ("tenant", "developer", "admin"):
        raise HTTPException(status_code=403, detail="forbidden")

    tenant_id = claims.get("tenant_id")
    user_id = claims.get("sub")

    title = payload.get("title", "Untitled")
    text = payload.get("text", "")
    acl = payload.get("acl", {"mode":"tenant"})
    mode = acl.get("mode", "tenant")
    workflow_ids = acl.get("workflow_ids", [])

    out = ingest_document(tenant_id=tenant_id, user_id=user_id, title=title, text=text, acl_mode=mode, workflow_ids=workflow_ids)

    report = {"ts": int(time.time()), "action": "ingest", "tenant_id": tenant_id, "user_id": user_id, "device_id": device.get("device_id"), "result": out}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return out

@router.post("/query")
def query(req: Request, payload: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    tenant_id = claims.get("tenant_id")
    user_id = claims.get("sub")

    q = payload.get("query", "")
    top_k = int(payload.get("top_k", 5))
    workflow_id = payload.get("workflow_id")  # optional for ACL workflow mode

    if not q:
        raise HTTPException(status_code=400, detail="query required")

    out = rag_query(tenant_id=tenant_id, user_id=user_id, query_text=q, top_k=top_k, workflow_id=workflow_id)

    report = {"ts": int(time.time()), "action": "query", "tenant_id": tenant_id, "user_id": user_id, "device_id": device.get("device_id"), "result_count": len(out.get("matches", []))}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return out
