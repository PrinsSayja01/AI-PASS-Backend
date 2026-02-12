from __future__ import annotations
from typing import Dict, Any, List, Tuple

# We will call your existing runtime function from api/app.py:
# _run_and_log(skill_id, inp, tenant_id)
# To avoid circular imports, we will import at runtime inside functions.

DEFAULT_WORKFLOWS = {
    "sanitize_and_summarize": [
        ("pii_redactor", {"text": "{text}"}),
        ("summarize", {"text": "{redacted}", "max_words": 60})
    ],
    "rag_then_summarize": [
        ("rag_query", {"query": "{query}", "k": 3}),
        ("summarize", {"text": "{answer}", "max_words": 80})
    ],
    "doc_safety_analysis": [
        ("decision_classifier", {"text": "{text}"}),
        ("pii_redactor", {"text": "{text}"}),
        ("summarize", {"text": "{redacted}", "max_words": 80})
    ]
}

def _render(template: Any, memory: Dict[str, Any]) -> Any:
    # Replace "{key}" in strings using memory dict.
    if isinstance(template, str):
        out = template
        for k, v in memory.items():
            if isinstance(v, (str, int, float)):
                out = out.replace("{"+k+"}", str(v))
        return out
    if isinstance(template, dict):
        return {k: _render(v, memory) for k, v in template.items()}
    if isinstance(template, list):
        return [_render(x, memory) for x in template]
    return template

def run_workflow(workflow_id: str, tenant_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    if workflow_id not in DEFAULT_WORKFLOWS:
        raise ValueError(f"Unknown workflow: {workflow_id}")

    # memory holds intermediate outputs
    memory: Dict[str, Any] = dict(inputs)
    trace: List[Dict[str, Any]] = []

    # Import runtime lazily to avoid circular import
    from api.app import _run_and_log

    for step_idx, (skill_id, payload_template) in enumerate(DEFAULT_WORKFLOWS[workflow_id], start=1):
        # Render input with memory
        payload = _render(payload_template, memory)
        if not isinstance(payload, dict):
            payload = {"value": payload}

        # Always attach tenant_id
        payload["tenant_id"] = tenant_id

        # Execute the skill (this enforces install/approval/lock + charges wallet + records billing)
        result = _run_and_log(skill_id, payload, tenant_id=tenant_id)

        trace.append({
            "step": step_idx,
            "skill_id": skill_id,
            "input": payload,
            "result_ok": result.get("ok"),
            "charged_credits": result.get("charged_credits", 0),
            "error": result.get("error"),
        })

        if not result.get("ok"):
            return {
                "ok": False,
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "trace": trace,
                "final": None,
                "error": f"Step failed: {skill_id} :: {result.get('error')}"
            }

        out = result.get("output", {})

        # Put outputs into memory for next steps
        if isinstance(out, dict):
            memory.update(out)

        # Special mapping for common keys
        # pii_redactor -> redacted
        if "redacted" in out:
            memory["redacted"] = out["redacted"]
        # rag_query -> answer
        if "answer" in out:
            memory["answer"] = out["answer"]

    return {
        "ok": True,
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "trace": trace,
        "final": memory
    }
