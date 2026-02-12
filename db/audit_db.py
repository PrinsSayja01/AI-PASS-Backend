from __future__ import annotations
import uuid
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import AuditLog

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def write_audit(event: Dict[str, Any]) -> str:
    """
    event keys:
    tenant_id,user_id,device_id,ip,route,action,target_id,ok,credits,error
    """
    db: Session = SessionLocal()
    try:
        aid = str(uuid.uuid4())
        row = AuditLog(
            audit_id=aid,
            ts=event.get("ts", now_iso()),
            tenant_id=event.get("tenant_id","unknown"),
            user_id=event.get("user_id","unknown"),
            device_id=event.get("device_id","unknown"),
            ip=event.get("ip","unknown"),
            route=event.get("route",""),
            action=event.get("action",""),
            target_id=event.get("target_id",""),
            ok=bool(event.get("ok", False)),
            credits=int(event.get("credits", 0)),
            error=(event.get("error") or "")[:800]
        )
        db.add(row)
        db.commit()
        return aid
    finally:
        db.close()
