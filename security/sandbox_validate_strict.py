import subprocess, json, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "reports" / "sandbox_latest.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def docker_ok():
    r = subprocess.run(["docker","version"], capture_output=True, text=True)
    return r.returncode == 0

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip(), False
    except subprocess.TimeoutExpired:
        return -1, "", "timeout", True

def main():
    report = {"ts": time.time(), "ok": True, "tests": []}

    if not docker_ok():
        report["ok"] = False
        report["skipped"] = True
        report["reason"] = "Docker not available"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return report

    # 1) network must fail
    cmd_net = ["docker","run","--rm","--network","none","alpine","sh","-lc","ping -c 1 8.8.8.8"]
    code, out, err, to = run(cmd_net)
    net_ok = (code != 0)
    report["tests"].append({"name":"network_isolation","ok": net_ok, "code": code, "stderr": err[:200]})
    report["ok"] = report["ok"] and net_ok

    # 2) read-only fs should block write
    cmd_ro = ["docker","run","--rm","--read-only","alpine","sh","-lc","echo hi > /tmp/x"]
    code, out, err, to = run(cmd_ro)
    ro_ok = (code != 0)
    report["tests"].append({"name":"read_only_fs","ok": ro_ok, "code": code, "stderr": err[:200]})
    report["ok"] = report["ok"] and ro_ok

    # 3) timeout test
    cmd_sleep = ["docker","run","--rm","alpine","sh","-lc","sleep 30"]
    code, out, err, to = run(cmd_sleep, timeout=2)
    timeout_ok = to is True
    report["tests"].append({"name":"timeout_kill","ok": timeout_ok, "code": code, "stderr": err[:200]})
    report["ok"] = report["ok"] and timeout_ok

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not report["ok"]:
        raise SystemExit("❌ Sandbox strict validation failed")
    print("✅ Sandbox strict validation passed")
    return report

if __name__ == "__main__":
    main()
