import json, time, os, re
from pathlib import Path
from typing import Any, Dict, List, Callable

def _now_ts() -> int:
    return int(time.time())

def _ensure_reports():
    Path("reports").mkdir(parents=True, exist_ok=True)

def _write_status(obj: Dict[str, Any]):
    _ensure_reports()
    Path("reports/workflow_latest.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _template_apply(value: Any, vars: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        def repl(m):
            k = m.group(1)
            v = vars.get(k, "")
            if isinstance(v, (dict, list)):
                return json.dumps(v)
            return str(v)
        return re.sub(r"\{([a-zA-Z0-9_]+)\}", repl, value)
    if isinstance(value, dict):
        return {k: _template_apply(v, vars) for k, v in value.items()}
    if isinstance(value, list):
        return [_template_apply(v, vars) for v in value]
    return value

def _rag_query_internal(tenant_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    We try a few import paths because your repo evolved.
    This keeps it stable even if module names change.
    """
    last_err = None

    # Option A: rag_mvp module
    try:
        from rag_mvp.retrieve import search_index  # type: ignore
        return {"ok": True, "matches": search_index(tenant_id, query, top_k)}
    except Exception as e:
        last_err = e

    # Option B: rag package (if you used python/rag)
    try:
        from rag.retrieve import search_index  # type: ignore
        return {"ok": True, "matches": search_index(tenant_id, query, top_k)}
    except Exception as e:
        last_err = e

    # Option C: call the same helper used by api.rag_api (if exists)
    try:
        from api.rag_api import _query_impl  # type: ignore
        matches = _query_impl(tenant_id=tenant_id, query=query, top_k=top_k)
        return {"ok": True, "matches": matches}
    except Exception as e:
        last_err = e

    return {"ok": False, "matches": [], "error": f"RAG backend not found: {type(last_err).__name__}: {last_err}"}

def run_marketplace_workflow(
    tenant_id: str,
    user_id: str,
    device_id: str,
    workflow_id: str,
    version: str,
    steps: List[Dict[str, Any]],
    skill_call_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    initial_vars: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    start = time.time()
    vars: Dict[str, Any] = dict(initial_vars or {})
    results: List[Dict[str, Any]] = []

    status = {
        "ts": _now_ts(),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "device_id": device_id,
        "workflow_id": workflow_id,
        "version": version,
        "ok": True,
        "steps_total": len(steps),
        "steps_done": 0,
        "last_step": None,
    }
    _write_status(status)

    for idx, step in enumerate(steps):
        step_start = time.time()
        step_type = step.get("type")
        skill_id = step.get("skill_id")
        inp = step.get("input", {}) or {}

        # Apply {var} templates
        inp = _template_apply(inp, vars)

        step_out: Dict[str, Any]
        if step_type == "rag_query":
            query = inp.get("query", "")
            top_k = int(inp.get("top_k", 3))
            rag = _rag_query_internal(tenant_id=tenant_id, query=str(query), top_k=top_k)

            matches = rag.get("matches", []) or []
            context = "\n".join([m.get("text", "") for m in matches if isinstance(m, dict)]).strip()

            vars["rag_matches"] = matches
            vars["rag_context"] = context
            step_out = {"ok": rag.get("ok", False), "output": {"matches": matches, "context": context}, "error": rag.get("error")}
        else:
            if not skill_id:
                step_out = {"ok": False, "output": {}, "error": "step must include type=rag_query OR skill_id"}
            else:
                step_out = skill_call_fn(skill_id, inp)
                if step_out.get("ok"):
                    out_obj = step_out.get("output") or {}
                    if isinstance(out_obj, dict):
                        for k, v in out_obj.items():
                            vars[k] = v

        latency_ms = int((time.time() - step_start) * 1000)
        results.append({
            "index": idx,
            "type": step_type or "skill",
            "skill_id": skill_id,
            "ok": bool(step_out.get("ok", False)),
            "latency_ms": latency_ms,
            "output": step_out.get("output", {}),
            "error": step_out.get("error"),
        })

        status["steps_done"] = idx + 1
        status["last_step"] = {"index": idx, "type": step_type or "skill", "skill_id": skill_id, "ok": bool(step_out.get("ok", False))}
        status["ok"] = status["ok"] and bool(step_out.get("ok", False))
        _write_status(status)

        # Stop early on failure
        if not step_out.get("ok", False):
            break

    total_ms = int((time.time() - start) * 1000)
    final = {
        "ok": bool(status["ok"]),
        "workflow_id": workflow_id,
        "version": version,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "device_id": device_id,
        "results": results,
        "vars": {k: vars[k] for k in list(vars.keys())[:200]},
        "latency_ms": total_ms,
    }
    _write_status({**status, "finished": True, "latency_ms": total_ms})
    return final
