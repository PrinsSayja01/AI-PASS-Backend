from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
PATH = BASE_DIR / "registry" / "kill_switch.json"

def _load() -> Dict[str, Any]:
    if not PATH.exists():
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps({"skills":[],"workflows":[],"tenants":[],"devices":[]}, indent=2), encoding="utf-8")
    return json.loads(PATH.read_text(encoding="utf-8"))

def _save(data: Dict[str, Any]) -> None:
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_rules() -> Dict[str, Any]:
    return _load()

def is_blocked(tenant_id: str, device_id: str, route: str) -> str | None:
    """
    Returns a string reason if blocked, else None.
    route example: "POST /skills/summarize" or "/skills/summarize"
    """
    data = _load()

    if tenant_id in set(data.get("tenants", [])):
        return "tenant_killed"
    if device_id in set(data.get("devices", [])):
        return "device_killed"

    # Skill route: /skills/<skill_id>
    if "/skills/" in route:
        skill_id = route.split("/skills/", 1)[1].split("/", 1)[0].strip()
        if skill_id in set(data.get("skills", [])):
            return f"skill_killed:{skill_id}"

    # Workflow route: /workflows/run with workflow_id in query/body (middleware can’t read body safely)
    # We'll block workflows by route only when route contains workflow id, or use admin endpoint check in workflow runner too.
    # Here: allow /workflows/<id> or /workflows/run/<id> patterns
    if "/workflows/" in route:
        tail = route.split("/workflows/", 1)[1]
        wf_id = tail.split("/", 1)[0].strip()
        if wf_id in set(data.get("workflows", [])):
            return f"workflow_killed:{wf_id}"

    return None

def add_block(kind: str, value: str) -> Dict[str, Any]:
    data = _load()
    if kind not in data:
        raise ValueError("kind must be skills|workflows|tenants|devices")
    if value not in data[kind]:
        data[kind].append(value)
    _save(data)
    return data

def remove_block(kind: str, value: str) -> Dict[str, Any]:
    data = _load()
    if kind not in data:
        raise ValueError("kind must be skills|workflows|tenants|devices")
    data[kind] = [x for x in data[kind] if x != value]
    _save(data)
    return data
