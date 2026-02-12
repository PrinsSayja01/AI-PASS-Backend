from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json
import time
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

INVOCATIONS_FILE = LOG_DIR / "invocations.jsonl"
WALLET_FILE = LOG_DIR / "wallet.json"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_invocation(event: Dict[str, Any]) -> None:
    event = dict(event)
    event["event_id"] = event.get("event_id") or str(uuid.uuid4())
    event["ts"] = event.get("ts") or now_iso()

    with INVOCATIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _load_wallet() -> Dict[str, Any]:
    if not WALLET_FILE.exists():
        return {"tenants": {}}
    try:
        return json.loads(WALLET_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"tenants": {}}


def _save_wallet(data: Dict[str, Any]) -> None:
    # Atomic save
    tmp = WALLET_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(WALLET_FILE)


def ensure_tenant_wallet(tenant_id: str, starting_credits: int = 1000) -> Dict[str, Any]:
    data = _load_wallet()
    tenants = data.setdefault("tenants", {})
    if tenant_id not in tenants:
        tenants[tenant_id] = {"credits_total": starting_credits, "credits_used": 0}
        _save_wallet(data)
    return tenants[tenant_id]


def spend_credits(tenant_id: str, credits: int) -> Dict[str, Any]:
    data = _load_wallet()
    tenants = data.setdefault("tenants", {})
    wallet = tenants.get(tenant_id) or {"credits_total": 1000, "credits_used": 0}

    wallet["credits_total"] = int(wallet.get("credits_total", 1000))
    wallet["credits_used"] = int(wallet.get("credits_used", 0))

    wallet["credits_used"] += int(credits)
    tenants[tenant_id] = wallet
    _save_wallet(data)
    return wallet
