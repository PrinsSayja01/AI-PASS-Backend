from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import jsonschema

@dataclass
class SkillMeta:
    skill_id: str
    version: str
    category: str
    risk_level: str
    plan_tier: str
    explainability: bool
    deterministic: bool

@dataclass
class SkillResult:
    ok: bool
    output: Dict[str, Any]
    confidence: float = 0.0
    evidence: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None

class SkillBase:
    meta: SkillMeta
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    def estimate_credits(self, inp: Dict[str, Any]) -> int:
        text = (inp.get("text") or "")
        return max(1, len(text) // 500)

    def check_permissions(self, ctx: Dict[str, Any], inp: Dict[str, Any]) -> None:
        required = ctx.get("required_scopes", [])
        have = set(ctx.get("scopes", []))
        missing = [s for s in required if s not in have]
        if missing:
            raise PermissionError(f"Missing scopes: {missing}")

    def validate_input(self, inp: Dict[str, Any]) -> None:
        jsonschema.validate(instance=inp, schema=self.input_schema)

    def validate_output(self, out: Dict[str, Any]) -> None:
        jsonschema.validate(instance=out, schema=self.output_schema)

    def run(self, ctx: Dict[str, Any], inp: Dict[str, Any]) -> SkillResult:
        start = time.time()
        try:
            self.validate_input(inp)
            self.check_permissions(ctx, inp)
            credits = self.estimate_credits(inp)

            out, conf, evidence = self.execute(ctx, inp)
            out = {**out, "_credits": credits}
            self.validate_output(out)

            latency = int((time.time() - start) * 1000)
            return SkillResult(ok=True, output=out, confidence=conf, evidence=evidence, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return SkillResult(ok=False, output={}, error=str(e), latency_ms=latency)

    def execute(self, ctx: Dict[str, Any], inp: Dict[str, Any]):
        raise NotImplementedError
