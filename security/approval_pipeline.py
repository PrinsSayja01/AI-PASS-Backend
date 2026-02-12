
from pathlib import Path
Path("reports").mkdir(exist_ok=True)
REPORT_OUTPUT = Path("reports") / "approval_latest.json"

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import subprocess
import sys
import time

from security.scan import build_report as static_scan_report
from security.sandbox_validate import main as sandbox_validate

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_FILE = BASE_DIR / "registry" / "skills.json"
POLICY_FILE = BASE_DIR / "registry" / "approval_policy.json"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def run_pip_audit() -> Dict[str, Any]:
    """
    Runs pip-audit and returns a structured result.
    pip-audit returns non-zero if vulnerabilities found.
    """
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-f", "json"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )

        vulns = []
        try:
            vulns = json.loads(res.stdout or "[]")
        except Exception:
            vulns = []

        ok = (res.returncode == 0)
        return {"ok": ok, "vulns": vulns, "stderr": res.stderr, "returncode": res.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e), "vulns": []}

def risk_gate(skills: List[Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
    approved = set(policy.get("approved_skill_ids", []))
    block_high = bool(policy.get("block_high_risk_without_approval", True))

    blocked: List[Dict[str, Any]] = []
    for s in skills:
        risk = (s.get("risk_level") or "").lower()
        sid = s.get("skill_id")
        if block_high and risk == "high" and sid not in approved:
            blocked.append(s)

    return {"ok": len(blocked) == 0, "blocked_skills": blocked}

def main(scan_path: str = ".") -> Dict[str, Any]:
    skills = load_json(REGISTRY_FILE, default=[])
    policy = load_json(POLICY_FILE, default={})

    # 1) Static security scan
    static_report = static_scan_report(scan_path)

    # 2) Dependency vulnerability scan
    dep_report = run_pip_audit()

    # 3) Sandbox validation (Docker isolation check)
    # If Docker not available, sandbox_validate returns {"skipped": True}
    sandbox_report = sandbox_validate()

    # 4) Risk gate
    risk_report = risk_gate(skills, policy)

    # Policy controls
    fail_on_secrets = bool(policy.get("fail_on_secrets", True))
    fail_on_deps = bool(policy.get("fail_on_dependency_vulns", True))
    fail_on_sandbox = bool(policy.get("fail_on_sandbox_validation", False))  # default False (CI may not have docker)

    secrets_ok = (static_report.get("secret_count", 0) == 0) or (not fail_on_secrets)
    deps_ok = bool(dep_report.get("ok", False)) or (not fail_on_deps)

    sandbox_ok = True
    if sandbox_report.get("skipped") is True:
        sandbox_ok = (not fail_on_sandbox)
    else:
        sandbox_ok = bool(sandbox_report.get("ok", False)) or (not fail_on_sandbox)

    approved = bool(secrets_ok and deps_ok and sandbox_ok and risk_report["ok"])

    report = {
        "ts": now_iso(),
        "approved": approved,
        "static_scan": {
            "ok": static_report.get("ok", False),
            "secret_count": static_report.get("secret_count", 0),
            "danger_count": static_report.get("danger_count", 0),
            "url_count": static_report.get("url_count", 0),
            "count": static_report.get("count", 0),
        },
        "dependency_scan": {
            "ok": dep_report.get("ok", False),
            "vuln_count": len(dep_report.get("vulns", []) or []),
        },
        "sandbox_validation": sandbox_report,
        "risk_gate": risk_report,
        "policy": policy,
        "details": {
            "static_report": static_report,
            "dependency_report": dep_report,
        }
    }

    out = REPORT_DIR / "approval_latest.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not approved:
        raise SystemExit("❌ App Approval Pipeline failed. See reports/approval_latest.json")

    print("✅ App Approval Pipeline PASSED.")
    return report

if __name__ == "__main__":
    scan_path = sys.argv[1] if len(sys.argv) > 1 else "."
    main(scan_path)
