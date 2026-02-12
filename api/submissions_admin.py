from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import SessionLocal
from api.security_deps import require_role
from db.workflow_db import admin_queue, admin_set_status, lock_version, unlock_version

router = APIRouter(prefix="/admin", tags=["admin-review"])

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/review-queue")
def queue(limit: int = 50, claims: dict = Depends(require_role("admin")), db: Session = Depends(_db)):
    return {"count": 0, "queue": admin_queue(db, limit=limit)}

@router.post("/submissions/set_status")
def set_status(payload: dict, claims: dict = Depends(require_role("admin")), db: Session = Depends(_db)):
    submission_id = payload.get("submission_id","")
    status = payload.get("status","")
    notes = payload.get("notes","")
    scan_report = payload.get("scan_report", None)
    if not submission_id or not status:
        raise HTTPException(status_code=400, detail="submission_id and status required")
    try:
        out = admin_set_status(db, submission_id, status, admin_user_id=claims["sub"], notes=notes, scan_report=scan_report)
        return {"ok": True, **out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/workflows/lock")
def lock(payload: dict, claims: dict = Depends(require_role("admin")), db: Session = Depends(_db)):
    tenant_id = payload.get("tenant_id","")
    workflow_id = payload.get("workflow_id","")
    version = payload.get("version","")
    reason = payload.get("reason","")
    if not tenant_id or not workflow_id or not version:
        raise HTTPException(status_code=400, detail="tenant_id, workflow_id, version required")
    return {"ok": True, "lock": lock_version(db, tenant_id, workflow_id, version, reason=reason)}

@router.post("/workflows/unlock")
def unlock(payload: dict, claims: dict = Depends(require_role("admin")), db: Session = Depends(_db)):
    tenant_id = payload.get("tenant_id","")
    workflow_id = payload.get("workflow_id","")
    if not tenant_id or not workflow_id:
        raise HTTPException(status_code=400, detail="tenant_id, workflow_id required")
    return {"ok": True, "lock": unlock_version(db, tenant_id, workflow_id)}
