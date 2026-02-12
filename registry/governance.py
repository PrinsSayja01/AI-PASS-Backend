from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"

TENANT_INSTALLS = REG / "tenant_installs.json"
APPROVALS = REG / "approvals.json"
LOCKS = REG / "locks.json"

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def enforce(tenant_id: str, skill_id: str) -> Dict[str, Any]:
    """
    Minimal governance:
    - tenant must have installed skill
    - skill version must be approved
    - if locked version exists, must match installed version
    Returns: {"installed_version": "..."}
    """
    installs = _read(TENANT_INSTALLS, {"tenants": {}})
    t = installs.get("tenants", {}).get(tenant_id, {})
    installed = t.get("installed", {})
    version = installed.get(skill_id)
    if not version:
        raise ValueError(f"Skill not installed for tenant: {tenant_id} -> {skill_id}")

    approvals = _read(APPROVALS, {"approved": []})
    ok = any(a.get("skill_id") == skill_id and a.get("version") == version for a in approvals.get("approved", []))
    if not ok:
        raise ValueError(f"Skill version not approved: {skill_id}@{version}")

    locks = _read(LOCKS, {"locks": {}})
    locked = locks.get("locks", {}).get(skill_id, {}).get("locked_version")
    if locked and locked != version:
        raise ValueError(f"Skill locked to version {locked} (installed {version})")

    return {"installed_version": version}
