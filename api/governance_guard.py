from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json
import time

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"

SKILLS_FILE = REG / "skills.json"
LOCKS_FILE = REG / "locks.json"
APPROVALS_FILE = REG / "approvals.json"
INSTALLS_FILE = REG / "tenant_installs.json"
WALLETS_FILE = REG / "tenant_wallets.json"
RATE_LIMITS_FILE = REG / "rate_limits.json"
RATE_STATE_FILE = REG / "rate_state.json"

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_skill_meta(skill_id: str) -> Dict[str, Any] | None:
    skills = _read(SKILLS_FILE, [])
    for s in skills:
        if s.get("skill_id") == skill_id:
            return s
    return None

def tenant_installed_version(tenant_id: str, skill_id: str) -> str | None:
    data = _read(INSTALLS_FILE, {"tenants": {}})
    t = data.get("tenants", {}).get(tenant_id, {})
    return t.get("installed", {}).get(skill_id)

def is_approved(skill_id: str, version: str) -> bool:
    appr = _read(APPROVALS_FILE, {"approved": []})
    return any(a.get("skill_id") == skill_id and a.get("version") == version for a in appr.get("approved", []))

def locked_version(skill_id: str) -> str | None:
    locks = _read(LOCKS_FILE, {"locks": {}})
    item = locks.get("locks", {}).get(skill_id)
    return item.get("locked_version") if item else None

def charge_wallet(tenant_id: str, credits: int) -> None:
    wallets = _read(WALLETS_FILE, {"tenants": {}})
    t = wallets.setdefault("tenants", {}).setdefault(tenant_id, {"credits": 0})
    if t["credits"] < credits:
        raise ValueError(f"Insufficient credits. Have {t['credits']}, need {credits}.")
    t["credits"] -= credits
    _write(WALLETS_FILE, wallets)

def rate_limit_check(tenant_id: str, skill_id: str) -> None:
    limits = _read(RATE_LIMITS_FILE, {"default_per_minute": 60, "overrides": {}})
    state = _read(RATE_STATE_FILE, {"state": {}})

    key = f"{tenant_id}:{skill_id}"
    limit = int(limits.get("overrides", {}).get(key, limits.get("default_per_minute", 60)))

    now = int(time.time())
    window = now // 60  # per-minute bucket

    s = state.setdefault("state", {}).setdefault(key, {"window": window, "count": 0})
    if s["window"] != window:
        s["window"] = window
        s["count"] = 0

    if s["count"] >= limit:
        _write(RATE_STATE_FILE, state)
        raise ValueError(f"Rate limit exceeded ({limit}/min) for {key}")

    s["count"] += 1
    _write(RATE_STATE_FILE, state)

def enforce(tenant_id: str, skill_id: str) -> Dict[str, Any]:
    # 1) tenant must install skill
    installed_version = tenant_installed_version(tenant_id, skill_id)
    if not installed_version:
        raise ValueError(f"Skill not installed for tenant: {tenant_id}. Install it first.")

    # 2) if locked, must match
    lv = locked_version(skill_id)
    if lv and installed_version != lv:
        raise ValueError(f"Skill version not allowed. Locked={lv}, installed={installed_version}")

    # 3) must be approved
    if not is_approved(skill_id, installed_version):
        raise ValueError(f"Skill version not approved: {skill_id}@{installed_version}")

    # 4) rate limit
    rate_limit_check(tenant_id, skill_id)

    return {"installed_version": installed_version, "locked_version": lv}
