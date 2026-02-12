from __future__ import annotations
from pathlib import Path
import json
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"
WALLETS = REG / "wallets.json"

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def ensure_wallet(tenant_id: str, start_credits: int = 1000) -> Dict[str, Any]:
    data = _read(WALLETS, {"tenants": {}})
    if tenant_id not in data["tenants"]:
        data["tenants"][tenant_id] = {"credits": start_credits}
        _write(WALLETS, data)
    return data["tenants"][tenant_id]

def charge_wallet(tenant_id: str, credits: int):
    data = _read(WALLETS, {"tenants": {}})
    if tenant_id not in data["tenants"]:
        data["tenants"][tenant_id] = {"credits": 1000}
    bal = int(data["tenants"][tenant_id].get("credits", 0))
    if bal < credits:
        raise ValueError("Insufficient credits")
    data["tenants"][tenant_id]["credits"] = bal - credits
    _write(WALLETS, data)
