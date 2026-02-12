from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from api.security_deps import require_role
from db.rate_limit_db import list_suspensions, clear_suspension

router = APIRouter(prefix="/admin/rate", tags=["rate-admin"])

@router.get("/suspensions")
def susp(limit: int = 50, claims: dict = Depends(require_role("admin"))):
    rows = list_suspensions(limit=limit)
    return {"count": len(rows), "suspensions": rows}

@router.post("/suspensions/clear")
def clear(payload: dict, claims: dict = Depends(require_role("admin"))):
    sid = payload.get("suspend_id","")
    if not sid:
        raise HTTPException(status_code=400, detail="suspend_id required")
    ok = clear_suspension(sid)
    return {"ok": ok}
