import os, json, time
import sys
from pathlib import Path
import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
ACCESS = os.getenv("ACCESS", "")
DEVICE = os.getenv("DEVICE", "")
OUT = Path("reports/battle_latest.json")
CASES = Path("tests/battle/cases.json")

def fmt_headers(h: dict) -> dict:
    hh = {}
    for k,v in (h or {}).items():
        v = v.replace("{ACCESS}", ACCESS).replace("{DEVICE}", DEVICE)
        hh[k] = v
    return hh

def run_case(c):
    method = c["method"].upper()
    url = BASE_URL + c["path"]
    headers = fmt_headers(c.get("headers", {}))
    payload = c.get("json", None)

    t0 = time.time()
    try:
        r = requests.request(method, url, headers=headers, json=payload, timeout=15)
        latency_ms = int((time.time() - t0) * 1000)

        ok_status = (r.status_code == c["expect_status"])
        ok_json = True
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text}

        expect_contains = c.get("expect_json_contains")
        if expect_contains is not None:
            for kk,vv in expect_contains.items():
                if body.get(kk) != vv:
                    ok_json = False

        return {"name": c["name"], "passed": (ok_status and ok_json), "status": r.status_code,
                "expected_status": c["expect_status"], "latency_ms": latency_ms, "body": body}
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        return {"name": c["name"], "passed": False, "status": None, "expected_status": c["expect_status"],
                "latency_ms": latency_ms, "error": str(e)}

def main():
    data = json.loads(CASES.read_text(encoding="utf-8"))
    results, passed = [], 0

    for c in data:
        res = run_case(c)
        results.append(res)
        passed += 1 if res["passed"] else 0
        print(("✅" if res["passed"] else "❌"), res["name"], "status=", res["status"])

    report = {"base_url": BASE_URL, "total": len(results), "passed": passed,
              "failed": len(results) - passed, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n🧾 report saved: {OUT}")
    if report["failed"] > 0:
        return 1
    return 0

if __name__ == "__main__":
    code = main()
    sys.exit(code if isinstance(code,int) else 0)
