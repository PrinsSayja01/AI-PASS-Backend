from __future__ import annotations
import uuid
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import BillingEvent

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def record_billing_db(event: Dict[str, Any]) -> Dict[str, Any]:
    db: Session = SessionLocal()
    try:
        eid = str(uuid.uuid4())
        row = BillingEvent(
            event_id=eid,
            ts=event.get("ts", now_iso()),
            tenant_id=event["tenant_id"],
            skill_id=event["skill_id"],
            version=event.get("version","unknown"),
            credits=int(event.get("credits", 0)),
            gross_usd=float(event.get("gross_usd", 0.0)),
            platform_fee_usd=float(event.get("platform_fee_usd", 0.0)),
            developer_net_usd=float(event.get("developer_net_usd", 0.0)),
            developer_id=event.get("developer_id","unknown_dev"),
            latency_ms=event.get("latency_ms")
        )
        db.add(row)
        db.commit()
        return {"ok": True, "event_id": eid}
    finally:
        db.close()

def list_billing_db(tenant_id: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        q = db.query(BillingEvent)
        if tenant_id:
            q = q.filter(BillingEvent.tenant_id == tenant_id)
        rows = q.order_by(BillingEvent.ts.desc()).limit(limit).all()
        return [{
            "event_id": r.event_id, "ts": r.ts, "tenant_id": r.tenant_id,
            "skill_id": r.skill_id, "version": r.version, "credits": r.credits,
            "gross_usd": r.gross_usd, "platform_fee_usd": r.platform_fee_usd,
            "developer_net_usd": r.developer_net_usd, "developer_id": r.developer_id,
            "latency_ms": r.latency_ms
        } for r in rows]
    finally:
        db.close()
