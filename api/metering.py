import time, uuid
from db.database import SessionLocal
from db.wallet_models import Wallet, UsageEvent

DEFAULT_COSTS = {
    "SKILL_RUN": 1,
    "RAG_QUERY": 2,
    "WORKFLOW_RUN": 3,
    "CHAT": 1,
}

def ensure_wallet(tenant_id: str, starter: int = 100):
    db = SessionLocal()
    w = db.query(Wallet).filter(Wallet.tenant_id == tenant_id).first()
    if not w:
        w = Wallet(tenant_id=tenant_id, balance=starter)
        db.add(w); db.commit()
    db.close()

def charge(tenant_id: str, credits: int) -> bool:
    db = SessionLocal()
    w = db.query(Wallet).filter(Wallet.tenant_id == tenant_id).first()
    if not w:
        w = Wallet(tenant_id=tenant_id, balance=0)
        db.add(w); db.commit()

    if w.balance < credits:
        db.close()
        return False

    w.balance -= credits
    db.commit()
    db.close()
    return True

def log_usage(*, tenant_id: str, user_id: str, device_id: str|None,
              action: str, credits: int, ok: bool, ref_id: str|None=None,
              error: str|None=None, units: int = 1):
    db = SessionLocal()
    ev = UsageEvent(
        id=str(uuid.uuid4()),
        ts=int(time.time()),
        tenant_id=tenant_id,
        user_id=user_id,
        device_id=device_id,
        action=action,
        units=units,
        credits=credits,
        ok=ok,
        ref_id=ref_id,
        error=error
    )
    db.add(ev); db.commit(); db.close()
