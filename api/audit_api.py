from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import AuditLog
from api.security_deps import require_role

router = APIRouter(prefix="/audit", tags=["audit"])

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/recent")
def recent(limit: int = 50, claims: dict = Depends(require_role("admin")), db: Session = Depends(_db)):
    rows = db.query(AuditLog).order_by(AuditLog.ts.desc()).limit(min(limit, 200)).all()
    return {"count": len(rows), "logs": [{
        "audit_id": r.audit_id, "ts": r.ts,
        "tenant_id": r.tenant_id, "user_id": r.user_id, "device_id": r.device_id,
        "ip": r.ip, "route": r.route, "action": r.action, "target_id": r.target_id,
        "ok": r.ok, "credits": r.credits, "error": r.error
    } for r in rows]}
