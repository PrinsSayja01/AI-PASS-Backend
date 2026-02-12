import json, time
from pathlib import Path
from security.scan import build_report, save_report

BASE = Path(__file__).resolve().parent.parent
REPORTS = BASE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

def main():
    report = build_report(".")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"security_{ts}.json"
    save_report(report, str(out))
    print(json.dumps({"ok": True, "saved": str(out), "secret_count": report.get("secret_count",0)}, indent=2))

if __name__ == "__main__":
    main()
