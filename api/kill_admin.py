from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from api.security_deps import require_role
from api.kill_switch import get_rules, add_block, remove_block

router = APIRouter(prefix="/admin/kill", tags=["kill-switch"])

@router.get("/list")
def list_rules(claims: dict = Depends(require_role("admin"))):
    return {"ok": True, "rules": get_rules()}

@router.post("/block")
def block(payload: dict, claims: dict = Depends(require_role("admin"))):
    kind = payload.get("kind","")
    value = payload.get("value","")
    if not kind or not value:
        raise HTTPException(status_code=400, detail="kind and value required")
    data = add_block(kind, value)
    return {"ok": True, "rules": data}

@router.post("/unblock")
def unblock(payload: dict, claims: dict = Depends(require_role("admin"))):
    kind = payload.get("kind","")
    value = payload.get("value","")
    if not kind or not value:
        raise HTTPException(status_code=400, detail="kind and value required")
    data = remove_block(kind, value)
    return {"ok": True, "rules": data}
