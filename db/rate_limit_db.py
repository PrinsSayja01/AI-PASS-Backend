from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import RateCounter, Suspension

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_PATH = BASE_DIR / "registry" / "rate_limit_policy.json"

def now() -> int:
    return int(time.time())

def load_policy() -> Dict[str, Any]:
    if not POLICY_PATH.exists():
        return {
            "tenant": {"per_minute": 120, "per_hour": 2000},
            "device": {"per_minute": 60, "per_hour": 800},
            "route_costs": {},
            "auto_suspend": {"enabled": True, "minutes": 10, "threshold_429_per_5min": 20}
        }
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_suspended(db: Session, tenant_id: str, device_id: str) -> Tuple[bool, int, str]:
    ts = now()
    row = db.query(Suspension).filter(
        Suspension.tenant_id == tenant_id,
        Suspension.device_id == device_id,
        Suspension.until_ts > ts
    ).order_by(Suspension.until_ts.desc()).first()
    if not row:
        return False, 0, ""
    return True, row.until_ts, row.reason or ""

def suspend(db: Session, tenant_id: str, device_id: str, minutes: int, reason: str) -> str:
    until_ts = now() + minutes * 60
    sid = str(uuid.uuid4())
    row = Suspension(
        suspend_id=sid,
        tenant_id=tenant_id,
        device_id=device_id,
        until_ts=until_ts,
        reason=reason
    )
    db.add(row)
    db.commit()
    return sid

def _key(prefix: str, tenant_id: str, device_id: str, route: str, window_sec: int) -> str:
    # Keep keys stable and simple
    return f"{prefix}:{tenant_id}:{device_id}:{route}:{window_sec}"

def _touch_counter(db: Session, key: str, window_sec: int, cost: int) -> int:
    ts = now()
    window_start = ts - (ts % window_sec)

    row = db.query(RateCounter).filter(RateCounter.key == key).first()
    if not row:
        row = RateCounter(key=key, window_start=window_start, window_sec=window_sec, count=0)
        db.add(row)

    # reset if window changed
    if row.window_start != window_start:
        row.window_start = window_start
        row.count = 0

    row.count += cost
    db.commit()
    return row.count

def check_rate_limit(tenant_id: str, device_id: str, route: str, cost: int = 1) -> Dict[str, Any]:
    pol = load_policy()

    # normalize route buckets
    route_bucket = route
    if route.startswith("POST /skills/"):
        route_bucket = "POST /skills"
    if route.startswith("POST /rag/"):
        route_bucket = "POST /rag"

    # apply route cost override
    route_costs = pol.get("route_costs", {})
    cost = int(route_costs.get(route_bucket, cost))

    db = SessionLocal()
    try:
        # suspension check
        blocked, until_ts, reason = is_suspended(db, tenant_id, device_id)
        if blocked:
            return {"allowed": False, "retry_after": max(1, until_ts - now()), "reason": f"suspended: {reason}"}

        # thresholds
        t_min = int(pol["tenant"]["per_minute"])
        t_hr = int(pol["tenant"]["per_hour"])
        d_min = int(pol["device"]["per_minute"])
        d_hr = int(pol["device"]["per_hour"])

        # counters
        tenant_min_key = _key("tenant", tenant_id, "all", route_bucket, 60)
        tenant_hr_key  = _key("tenant", tenant_id, "all", route_bucket, 3600)
        dev_min_key    = _key("device", tenant_id, device_id, route_bucket, 60)
        dev_hr_key     = _key("device", tenant_id, device_id, route_bucket, 3600)

        tenant_min = _touch_counter(db, tenant_min_key, 60, cost)
        tenant_hr  = _touch_counter(db, tenant_hr_key, 3600, cost)
        dev_min    = _touch_counter(db, dev_min_key, 60, cost)
        dev_hr     = _touch_counter(db, dev_hr_key, 3600, cost)

        # enforce
        if tenant_min > t_min or tenant_hr > t_hr or dev_min > d_min or dev_hr > d_hr:
            # auto suspend if configured (quick protection)
            auto = pol.get("auto_suspend", {})
            if auto.get("enabled", True):
                mins = int(auto.get("minutes", 10))
                suspend(db, tenant_id, device_id, mins, "rate_limit_exceeded")
                return {"allowed": False, "retry_after": mins * 60, "reason": "rate_limited_and_suspended"}

            return {"allowed": False, "retry_after": 60, "reason": "rate_limited"}

        return {
            "allowed": True,
            "tenant_min": tenant_min,
            "tenant_hr": tenant_hr,
            "device_min": dev_min,
            "device_hr": dev_hr,
            "cost": cost
        }
    finally:
        db.close()

def list_suspensions(limit: int = 50) -> list[dict]:
    db = SessionLocal()
    try:
        ts = now()
        rows = db.query(Suspension).filter(Suspension.until_ts > ts).order_by(Suspension.until_ts.desc()).limit(min(limit, 200)).all()
        return [{
            "suspend_id": r.suspend_id,
            "tenant_id": r.tenant_id,
            "device_id": r.device_id,
            "until_ts": r.until_ts,
            "retry_after": max(1, r.until_ts - ts),
            "reason": r.reason
        } for r in rows]
    finally:
        db.close()

def clear_suspension(suspend_id: str) -> bool:
    db = SessionLocal()
    try:
        row = db.query(Suspension).filter(Suspension.suspend_id == suspend_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()
