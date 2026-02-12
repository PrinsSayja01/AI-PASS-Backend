from fastapi import APIRouter, Depends, HTTPException
from db.database import SessionLocal
from db.wallet_models import Wallet, UsageEvent
from api.security_deps import require_access, require_role
from api.metering import ensure_wallet

router = APIRouter(prefix="/wallet", tags=["wallet"])
admin_router = APIRouter(prefix="/admin/usage", tags=["admin-usage"])

@router.get("/balance")
def wallet_balance(claims=Depends(require_access)):
    tenant_id = claims["tenant_id"]
    ensure_wallet(tenant_id, starter=100)
    db = SessionLocal()
    w = db.query(Wallet).filter(Wallet.tenant_id == tenant_id).first()
    db.close()
    return {"tenant_id": tenant_id, "balance": (w.balance if w else 0)}

@admin_router.get("/recent")
def usage_recent(limit: int = 50, claims=Depends(require_role("admin"))):
    db = SessionLocal()
    rows = db.query(UsageEvent).order_by(UsageEvent.ts.desc()).limit(limit).all()
    out = []
    for r in rows:
        d = r.__dict__.copy()
        d.pop("_sa_instance_state", None)
        out.append(d)
    db.close()
    return {"count": len(out), "events": out}
