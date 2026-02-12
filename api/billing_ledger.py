from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import time
from collections import defaultdict
from db.billing_db import record_billing_db

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"
LEDGER = REG / "billing_ledger.json"
POLICY = REG / "billing_policy.json"
WALLETS = REG / "tenant_wallets.json"

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def get_policy() -> Dict[str, Any]:
    return _read(POLICY, {
        "platform_fee_percent": 25,
        "default_credit_value_usd": 0.01,
        "skill_developers": {}
    })

def get_wallets() -> Dict[str, Any]:
    return _read(WALLETS, {"tenants": {}})

def record_event(tenant_id: str, skill_id: str, version: str, credits: int, latency_ms: int | None = None):
    data = _read(LEDGER, {"events": []})
    pol = get_policy()

    dev = pol.get("skill_developers", {}).get(skill_id, "unknown_dev")
    credit_usd = float(pol.get("default_credit_value_usd", 0.01))
    gross_usd = float(credits) * credit_usd

    fee_pct = float(pol.get("platform_fee_percent", 25)) / 100.0
    platform_fee = gross_usd * fee_pct
    developer_net = gross_usd - platform_fee

    event = {
        "ts": now_iso(),
        "tenant_id": tenant_id,
        "skill_id": skill_id,
        "version": version,
        "credits": int(credits),
        "gross_usd": round(gross_usd, 6),
        "platform_fee_usd": round(platform_fee, 6),
        "developer_net_usd": round(developer_net, 6),
        "developer_id": dev,
        "latency_ms": latency_ms
    }
    data["events"].append(event)
    _write(LEDGER, data)
    try:
        record_billing_db(event)
    except Exception:
        pass
    return event

def tenant_dashboard(tenant_id: str) -> Dict[str, Any]:
    data = _read(LEDGER, {"events": []})
    wallets = get_wallets()
    remaining = wallets.get("tenants", {}).get(tenant_id, {}).get("credits", 0)

    ev = [e for e in data["events"] if e["tenant_id"] == tenant_id]

    by_skill = defaultdict(lambda: {"credits": 0, "gross_usd": 0.0})
    total_credits = 0
    total_usd = 0.0
    for e in ev:
        total_credits += e["credits"]
        total_usd += e["gross_usd"]
        s = by_skill[e["skill_id"]]
        s["credits"] += e["credits"]
        s["gross_usd"] += e["gross_usd"]

    by_skill_out = {k: {"credits": v["credits"], "gross_usd": round(v["gross_usd"], 6)} for k, v in by_skill.items()}

    return {
        "tenant_id": tenant_id,
        "remaining_credits": remaining,
        "total_events": len(ev),
        "total_credits_used": total_credits,
        "total_spend_usd": round(total_usd, 6),
        "by_skill": by_skill_out
    }

def developer_dashboard(developer_id: str) -> Dict[str, Any]:
    data = _read(LEDGER, {"events": []})
    ev = [e for e in data["events"] if e["developer_id"] == developer_id]

    by_skill = defaultdict(lambda: {"credits": 0, "gross_usd": 0.0, "net_usd": 0.0})
    gross = 0.0
    net = 0.0
    fee = 0.0
    for e in ev:
        gross += e["gross_usd"]
        net += e["developer_net_usd"]
        fee += e["platform_fee_usd"]
        s = by_skill[e["skill_id"]]
        s["credits"] += e["credits"]
        s["gross_usd"] += e["gross_usd"]
        s["net_usd"] += e["developer_net_usd"]

    by_skill_out = {k: {
        "credits": v["credits"],
        "gross_usd": round(v["gross_usd"], 6),
        "net_usd": round(v["net_usd"], 6)
    } for k, v in by_skill.items()}

    return {
        "developer_id": developer_id,
        "total_events": len(ev),
        "gross_usd": round(gross, 6),
        "platform_fee_usd": round(fee, 6),
        "net_usd": round(net, 6),
        "by_skill": by_skill_out
    }

def platform_dashboard() -> Dict[str, Any]:
    data = _read(LEDGER, {"events": []})
    gross = sum(e["gross_usd"] for e in data["events"])
    fee = sum(e["platform_fee_usd"] for e in data["events"])
    net = sum(e["developer_net_usd"] for e in data["events"])
    return {
        "total_events": len(data["events"]),
        "gross_usd": round(gross, 6),
        "platform_fee_usd": round(fee, 6),
        "developer_net_usd": round(net, 6),
    }
