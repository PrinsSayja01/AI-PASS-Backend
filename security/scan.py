import re
import os
import json
from pathlib import Path
from typing import Dict, Any, List

PATTERNS = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "generic_api_key": re.compile(r"\b(api[_-]?key|secret|token)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]", re.IGNORECASE),
}

MALICIOUS_URL = re.compile(
    r"(http|https)://"
    r"(?:(?:\d{1,3}\.){3}\d{1,3}|[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    r"(?::\d+)?"
    r"(?:/[^\s'\"<>]*)?",
    re.IGNORECASE
)

DANGEROUS = {
    "python_eval_exec": re.compile(r"\b(eval|exec)\s*\("),
    "node_child_process": re.compile(r"\b(child_process|execSync|spawn)\b"),
}

SKIP_EXT = {".png", ".jpg", ".jpeg", ".webp", ".zip", ".pdf", ".exe", ".dylib", ".so", ".bin"}


def scan_repo(root: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    root_path = Path(root)

    for p in root_path.rglob("*"):
        if p.is_dir():
            continue
        if p.suffix.lower() in SKIP_EXT:
            continue
        # skip venv and node_modules
        if any(part in {".venv", "node_modules", ".git"} for part in p.parts):
            continue

        try:
            content = p.read_text(errors="ignore")
        except Exception:
            continue

        for name, rx in PATTERNS.items():
            for m in rx.finditer(content):
                findings.append({"type": "secret", "rule": name, "file": str(p), "match": m.group(0)[:80]})

        for m in MALICIOUS_URL.finditer(content):
            url = m.group(0)
            # basic allowlist (customize later)
            if any(url.startswith(x) for x in ["https://docs.", "https://github.com", "https://npmjs.com"]):
                continue
            findings.append({"type": "url", "rule": "url_detected", "file": str(p), "match": url[:120]})

        for name, rx in DANGEROUS.items():
            if rx.search(content):
                findings.append({"type": "danger", "rule": name, "file": str(p), "match": "pattern_found"})

    return findings


def build_report(root: str) -> Dict[str, Any]:
    findings = scan_repo(root)
    secret_count = sum(1 for f in findings if f["type"] == "secret")
    danger_count = sum(1 for f in findings if f["type"] == "danger")
    url_count = sum(1 for f in findings if f["type"] == "url")

    return {
        "scan_path": str(Path(root).resolve()),
        "count": len(findings),
        "secret_count": secret_count,
        "danger_count": danger_count,
        "url_count": url_count,
        "findings": findings,
        "ok": secret_count == 0,
    }


def save_report(report: Dict[str, Any], out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    repo = os.environ.get("SCAN_PATH", ".")
    report = build_report(repo)
    print(json.dumps(report, indent=2))

    # CI fail condition: secrets -> fail
    if report["secret_count"] > 0:
        raise SystemExit("❌ Secret leak detected. Blocking build.")
