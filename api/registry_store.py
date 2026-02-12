from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import json
import uuid
import time

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = BASE_DIR / "registry"

SUBMISSIONS_FILE = REGISTRY_DIR / "submissions.json"
APPROVALS_FILE = REGISTRY_DIR / "approvals.json"
LOCKS_FILE = REGISTRY_DIR / "locks.json"
ADMIN_FILE = REGISTRY_DIR / "admin_policy.json"

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

def get_admin_token() -> str:
    pol = _read_json(ADMIN_FILE, {"admin_token": "CHANGE_ME_ADMIN_TOKEN"})
    return pol.get("admin_token", "CHANGE_ME_ADMIN_TOKEN")

# -------------------------
# Submissions
# -------------------------
def list_submissions() -> List[Dict[str, Any]]:
    return _read_json(SUBMISSIONS_FILE, [])

def create_submission(payload: Dict[str, Any]) -> Dict[str, Any]:
    submissions = list_submissions()
    sub = {
        "submission_id": str(uuid.uuid4()),
        "ts": now_iso(),
        "status": "PENDING",  # PENDING / APPROVED / REJECTED
        "reason": None,
        "skill_id": payload.get("skill_id"),
        "version": payload.get("version"),
        "developer_id": payload.get("developer_id", "unknown"),
        "notes": payload.get("notes", "")
    }
    submissions.append(sub)
    _write_json(SUBMISSIONS_FILE, submissions)
    return sub

def update_submission(submission_id: str, status: str, reason: str | None = None) -> Dict[str, Any]:
    submissions = list_submissions()
    for s in submissions:
        if s["submission_id"] == submission_id:
            s["status"] = status
            s["reason"] = reason
            s["updated_ts"] = now_iso()
            _write_json(SUBMISSIONS_FILE, submissions)
            return s
    raise KeyError("Submission not found")

# -------------------------
# Approvals
# -------------------------
def get_approvals() -> Dict[str, Any]:
    return _read_json(APPROVALS_FILE, {"approved": []})

def add_approval(skill_id: str, version: str, submission_id: str) -> Dict[str, Any]:
    data = get_approvals()
    approved = data.setdefault("approved", [])
    approved.append({
        "skill_id": skill_id,
        "version": version,
        "submission_id": submission_id,
        "approved_ts": now_iso()
    })
    _write_json(APPROVALS_FILE, data)
    return data

# -------------------------
# Version Locks
# -------------------------
def get_locks() -> Dict[str, Any]:
    return _read_json(LOCKS_FILE, {"locks": {}})

def lock_version(skill_id: str, version: str) -> Dict[str, Any]:
    data = get_locks()
    locks = data.setdefault("locks", {})
    locks[skill_id] = {
        "locked_version": version,
        "locked_ts": now_iso()
    }
    _write_json(LOCKS_FILE, data)
    return data

def is_version_locked(skill_id: str, version: str) -> bool:
    data = get_locks()
    locks = data.get("locks", {})
    lock = locks.get(skill_id)
    if not lock:
        return False
    return lock.get("locked_version") == version
