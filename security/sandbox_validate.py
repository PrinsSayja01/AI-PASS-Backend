import subprocess
import json

def docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "version"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def main():
    if not docker_available():
        report = {"ok": False, "skipped": True, "reason": "Docker not available/running"}
        print(json.dumps(report, indent=2))
        return report

    # This container tries to reach network (ping). It MUST FAIL because --network none.
    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--pids-limit", "128",
        "--cpus", "0.5",
        "--memory", "128m",
        "alpine",
        "sh", "-lc",
        "ping -c 1 8.8.8.8"
    ]

    code, out, err = run(cmd)

    # Expected: ping fails (non-zero code)
    ok = code != 0

    report = {
        "ok": ok,
        "skipped": False,
        "test": "network_isolation",
        "returncode": code,
        "stdout": out,
        "stderr": err
    }

    print(json.dumps(report, indent=2))

    if not ok:
        raise SystemExit("❌ Sandbox validation failed: container had network access")

    return report

if __name__ == "__main__":
    main()
