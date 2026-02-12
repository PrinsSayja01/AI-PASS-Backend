from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Set

BASE = Path("data/rag")

def _tenant_dir(tenant_id: str) -> Path:
    d = BASE / tenant_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _acl_path(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "acl.json"

def load_acl(tenant_id: str) -> Dict[str, Any]:
    """
    ACL structure:
    {
      "mode": "strict",                 # strict | permissive
      "allow_all_if_empty": false,      # if true and no grants, allow all docs
      "workflows": {
         "*": ["doc1","doc2"],          # allowed for any workflow
         "wf-123": ["doc3"]             # allowed only for wf-123
      }
    }
    """
    p = _acl_path(tenant_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # default: strict deny unless granted
    return {"mode": "strict", "allow_all_if_empty": False, "workflows": {}}

def save_acl(tenant_id: str, acl: Dict[str, Any]) -> None:
    p = _acl_path(tenant_id)
    p.write_text(json.dumps(acl, indent=2), encoding="utf-8")

def allowed_docs(tenant_id: str, workflow_id: str) -> Set[str]:
    acl = load_acl(tenant_id)
    workflows = acl.get("workflows") or {}
    g_all = set(workflows.get("*", []) or [])
    g_wf = set(workflows.get(workflow_id, []) or [])
    return g_all | g_wf

def is_allowed(tenant_id: str, workflow_id: str, doc_id: str) -> bool:
    acl = load_acl(tenant_id)
    mode = acl.get("mode", "strict")
    workflows = acl.get("workflows") or {}

    # permissive mode = allow if no grants exist
    if mode == "permissive" and not workflows:
        return True

    allow_all_if_empty = bool(acl.get("allow_all_if_empty", False))
    if allow_all_if_empty and not workflows:
        return True

    return doc_id in allowed_docs(tenant_id, workflow_id)

def filter_hits_by_acl(tenant_id: str, workflow_id: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    acl = load_acl(tenant_id)
    mode = acl.get("mode", "strict")
    workflows = acl.get("workflows") or {}

    if mode == "permissive" and not workflows:
        return hits
    if acl.get("allow_all_if_empty", False) and not workflows:
        return hits

    allowed = allowed_docs(tenant_id, workflow_id)
    return [h for h in hits if h.get("doc_id") in allowed]
