from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import SessionLocal
from api.security_deps import require_role
from api.device_deps import require_device_token
from db.install_db import install_version, history, rollback, get_current

router = APIRouter(prefix="/tenant/workflows", tags=["tenant-installs"])

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/install")
def install(payload: dict,
            claims: dict = Depends(require_role("tenant")),
            device: dict = Depends(require_device_token),
            db: Session = Depends(_db)):
    workflow_id = payload.get("workflow_id","")
    version = payload.get("version","")
    reason = payload.get("reason","")
    if not workflow_id or not version:
        raise HTTPException(status_code=400, detail="workflow_id and version required")
    try:
        out = install_version(
            db,
            tenant_id=claims["tenant_id"],
            workflow_id=workflow_id,
            version=version,
            by_user_id=claims["sub"],
            device_id=device.get("device_id","unknown"),
            reason=reason
        )
        return {"ok": True, "install": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/current")
def current(workflow_id: str,
            claims: dict = Depends(require_role("tenant")),
            device: dict = Depends(require_device_token),
            db: Session = Depends(_db)):
    cur = get_current(db, claims["tenant_id"], workflow_id)
    return {"ok": True, "current": cur}

@router.get("/history")
def get_history(workflow_id: str,
                limit: int = 50,
                claims: dict = Depends(require_role("tenant")),
                device: dict = Depends(require_device_token),
                db: Session = Depends(_db)):
    return {"ok": True, "workflow_id": workflow_id, "events": history(db, claims["tenant_id"], workflow_id, limit=limit)}

@router.post("/rollback")
def do_rollback(payload: dict,
                claims: dict = Depends(require_role("tenant")),
                device: dict = Depends(require_device_token),
                db: Session = Depends(_db)):
    workflow_id = payload.get("workflow_id","")
    to_version = payload.get("to_version","")
    reason = payload.get("reason","rollback")
    if not workflow_id or not to_version:
        raise HTTPException(status_code=400, detail="workflow_id and to_version required")
    try:
        out = rollback(
            db,
            tenant_id=claims["tenant_id"],
            workflow_id=workflow_id,
            to_version=to_version,
            by_user_id=claims["sub"],
            device_id=device.get("device_id","unknown"),
            reason=reason
        )
        return {"ok": True, "install": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
