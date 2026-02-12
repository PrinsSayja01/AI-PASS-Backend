from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import uuid
import time

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"

WF_FILE = REG / "workflows.json"
SUB_FILE = REG / "workflow_submissions.json"
APP_FILE = REG / "workflow_approvals.json"
LOCK_FILE = REG / "workflow_locks.json"
TENANT_WF_FILE = REG / "tenant_workflow_installs.json"
ADMIN_FILE = REG / "admin_policy.json"

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def admin_token() -> str:
    pol = _read(ADMIN_FILE, {"admin_token":"CHANGE_ME_ADMIN_TOKEN"})
    return pol.get("admin_token","CHANGE_ME_ADMIN_TOKEN")

# -------------------------
# Workflows (draft storage)
# -------------------------
def list_workflows() -> List[Dict[str, Any]]:
    return _read(WF_FILE, {"workflows": []}).get("workflows", [])

def get_workflow(workflow_id: str) -> Dict[str, Any] | None:
    for w in list_workflows():
        if w.get("workflow_id") == workflow_id:
            return w
    return None

def create_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload:
    {
      "name": "...",
      "version": "1.0.0",
      "developer_id": "dev_x",
      "steps": [{"skill_id":"pii_redactor","input":{"text":"{text}"}}]
    }
    """
    if not payload.get("name") or not payload.get("version") or not payload.get("steps"):
        raise ValueError("name, version, steps required")

    w = {
        "workflow_id": str(uuid.uuid4()),
        "name": payload["name"],
        "version": payload["version"],
        "developer_id": payload.get("developer_id","unknown_dev"),
        "status": "DRAFT",  # DRAFT / SUBMITTED / APPROVED / REJECTED
        "steps": payload["steps"],
        "created_ts": now_iso(),
        "updated_ts": now_iso()
    }

    data = _read(WF_FILE, {"workflows": []})
    data["workflows"].append(w)
    _write(WF_FILE, data)
    return w

def submit_workflow(workflow_id: str) -> Dict[str, Any]:
    data = _read(WF_FILE, {"workflows": []})
    for w in data["workflows"]:
        if w["workflow_id"] == workflow_id:
            if w["status"] not in ("DRAFT","REJECTED"):
                raise ValueError(f"Cannot submit from status {w['status']}")
            w["status"] = "SUBMITTED"
            w["updated_ts"] = now_iso()
            _write(WF_FILE, data)

            subs = _read(SUB_FILE, [])
            sub = {
                "submission_id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "ts": now_iso(),
                "status": "PENDING",
                "reason": None
            }
            subs.append(sub)
            _write(SUB_FILE, subs)
            return {"workflow": w, "submission": sub}
    raise ValueError("workflow not found")

# -------------------------
# Approval + Locks
# -------------------------
def approvals() -> Dict[str, Any]:
    return _read(APP_FILE, {"approved": []})

def locks() -> Dict[str, Any]:
    return _read(LOCK_FILE, {"locks": {}})

def approve_workflow(submission_id: str) -> Dict[str, Any]:
    subs = _read(SUB_FILE, [])
    wf_data = _read(WF_FILE, {"workflows": []})

    sub = next((s for s in subs if s["submission_id"] == submission_id), None)
    if not sub:
        raise ValueError("submission not found")

    wf = next((w for w in wf_data["workflows"] if w["workflow_id"] == sub["workflow_id"]), None)
    if not wf:
        raise ValueError("workflow not found")

    sub["status"] = "APPROVED"
    sub["reason"] = None

    wf["status"] = "APPROVED"
    wf["updated_ts"] = now_iso()

    app = approvals()
    app["approved"].append({
        "workflow_id": wf["workflow_id"],
        "version": wf["version"],
        "approved_ts": now_iso()
    })
    _write(APP_FILE, app)

    lock = locks()
    lock["locks"][wf["workflow_id"]] = {"locked_version": wf["version"], "locked_ts": now_iso()}
    _write(LOCK_FILE, lock)

    _write(SUB_FILE, subs)
    _write(WF_FILE, wf_data)
    return {"workflow": wf, "submission": sub, "lock": lock["locks"][wf["workflow_id"]]}

def reject_workflow(submission_id: str, reason: str) -> Dict[str, Any]:
    subs = _read(SUB_FILE, [])
    wf_data = _read(WF_FILE, {"workflows": []})

    sub = next((s for s in subs if s["submission_id"] == submission_id), None)
    if not sub:
        raise ValueError("submission not found")

    wf = next((w for w in wf_data["workflows"] if w["workflow_id"] == sub["workflow_id"]), None)
    if wf:
        wf["status"] = "REJECTED"
        wf["updated_ts"] = now_iso()

    sub["status"] = "REJECTED"
    sub["reason"] = reason

    _write(SUB_FILE, subs)
    _write(WF_FILE, wf_data)
    return {"workflow": wf, "submission": sub}

def is_workflow_approved(workflow_id: str, version: str) -> bool:
    app = approvals()
    return any(a["workflow_id"] == workflow_id and a["version"] == version for a in app.get("approved", []))

def locked_workflow_version(workflow_id: str) -> str | None:
    lock = locks()
    item = lock.get("locks", {}).get(workflow_id)
    return item.get("locked_version") if item else None

# -------------------------
# Tenant install workflow
# -------------------------
def tenant_install_workflow(tenant_id: str, workflow_id: str, version: str):
    data = _read(TENANT_WF_FILE, {"tenants": {}})
    t = data["tenants"].setdefault(tenant_id, {"installed": {}, "history": []})
    prev = t["installed"].get(workflow_id)

    t["installed"][workflow_id] = version
    t["history"].append({
        "ts": now_iso(),
        "action": "INSTALL",
        "workflow_id": workflow_id,
        "from_version": prev,
        "to_version": version
    })
    _write(TENANT_WF_FILE, data)
    return t

def tenant_workflow_version(tenant_id: str, workflow_id: str) -> str | None:
    data = _read(TENANT_WF_FILE, {"tenants": {}})
    return data.get("tenants", {}).get(tenant_id, {}).get("installed", {}).get(workflow_id)
