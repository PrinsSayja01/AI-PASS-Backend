from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import time

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = BASE_DIR / "registry"

INSTALLS_FILE = REGISTRY_DIR / "tenant_installs.json"
VISIBILITY_FILE = REGISTRY_DIR / "visibility.json"

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _read_json(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_visibility() -> Dict[str, Any]:
    return _read_json(VISIBILITY_FILE, {"skills": {}})

def can_tenant_see_skill(tenant_id: str, skill_id: str) -> bool:
    vis = get_visibility()
    rules = vis.get("skills", {}).get(skill_id, {"visibility": "public", "allowed_tenants": []})
    mode = rules.get("visibility", "public")
    allowed = set(rules.get("allowed_tenants", []))

    if mode == "public":
        return True
    if mode in ("private", "enterprise"):
        return tenant_id in allowed
    return False

def get_installs() -> Dict[str, Any]:
    return _read_json(INSTALLS_FILE, {"tenants": {}})

def get_tenant_install_state(tenant_id: str) -> Dict[str, Any]:
    data = get_installs()
    tenants = data.setdefault("tenants", {})
    return tenants.setdefault(tenant_id, {"installed": {}, "history": []})

def install_skill(tenant_id: str, skill_id: str, version: str, actor: str) -> Dict[str, Any]:
    if not can_tenant_see_skill(tenant_id, skill_id):
        raise PermissionError("Skill not visible for this tenant")

    data = get_installs()
    tenants = data.setdefault("tenants", {})
    state = tenants.setdefault(tenant_id, {"installed": {}, "history": []})

    current = state["installed"].get(skill_id)
    state["installed"][skill_id] = version

    state["history"].append({
        "ts": now_iso(),
        "action": "INSTALL",
        "tenant_id": tenant_id,
        "skill_id": skill_id,
        "from_version": current,
        "to_version": version,
        "actor": actor
    })

    _write_json(INSTALLS_FILE, data)
    return state

def rollback_skill(tenant_id: str, skill_id: str, actor: str) -> Dict[str, Any]:
    data = get_installs()
    tenants = data.setdefault("tenants", {})
    state = tenants.setdefault(tenant_id, {"installed": {}, "history": []})

    # find last versions from history
    hist = [h for h in state["history"] if h["skill_id"] == skill_id and h["action"] in ("INSTALL", "ROLLBACK")]
    if len(hist) < 2:
        raise ValueError("No previous version found to rollback")

    current_version = state["installed"].get(skill_id)
    prev = hist[-2].get("to_version")

    state["installed"][skill_id] = prev
    state["history"].append({
        "ts": now_iso(),
        "action": "ROLLBACK",
        "tenant_id": tenant_id,
        "skill_id": skill_id,
        "from_version": current_version,
        "to_version": prev,
        "actor": actor
    })

    _write_json(INSTALLS_FILE, data)
    return state
