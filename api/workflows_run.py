from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any

from api.deps import require_access
from api.device_deps import require_device_token
from api.workflow_runner import run_marketplace_workflow

from skills.summarization.skill import SummarizeSkill
from skills.translation.skill import TranslateSkill

router = APIRouter(prefix="/workflows", tags=["workflows"])

def _skill_registry():
    return {
        "summarize": SummarizeSkill(),
        "translate": TranslateSkill(),
    }

def _call_skill(skill_id: str, inp: Dict[str, Any]) -> Dict[str, Any]:
    reg = _skill_registry()
    s = reg.get(skill_id)
    if not s:
        return {"ok": False, "output": {}, "confidence": 0.0, "evidence": None, "error": f"Skill not registered for workflows: {skill_id}", "latency_ms": 0}

    res = s.run({"mode": "workflow"}, inp)
    return {
        "ok": bool(getattr(res, "ok", False)),
        "output": getattr(res, "output", {}) or {},
        "confidence": float(getattr(res, "confidence", 0.0) or 0.0),
        "evidence": getattr(res, "evidence", None),
        "error": getattr(res, "error", None),
        "latency_ms": int(getattr(res, "latency_ms", 0) or 0),
    }

@router.post("/run")
def run_workflow(
    request: Request,
    payload: Dict[str, Any],
    claims: dict = Depends(require_access),
    device: dict = Depends(require_device_token),
):
    if claims.get("role") != "tenant":
        raise HTTPException(status_code=403, detail="tenant only")

    tenant_id = claims.get("tenant_id")
    user_id = claims.get("sub")
    device_id = device.get("device_id")

    steps = payload.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="steps[] required")

    out = run_marketplace_workflow(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id=device_id,
        workflow_id=payload.get("workflow_id", "adhoc"),
        version=payload.get("version", "1.0.0"),
        steps=steps,
        skill_call_fn=_call_skill,
        initial_vars=(payload.get("input", {}) or {}),
    )
    return out
