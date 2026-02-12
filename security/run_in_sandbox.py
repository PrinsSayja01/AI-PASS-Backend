import subprocess, json, time

def run_sandbox(image: str, cmd: str, timeout: int = 10):
    docker_cmd = [
        "docker","run","--rm",
        "--network","none",
        "--read-only",
        "--pids-limit","128",
        "--cpus","0.5",
        "--memory","256m",
        image,
        "sh","-lc", cmd
    ]
    t0 = time.time()
    try:
        r = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:5000],
            "latency_ms": int((time.time()-t0)*1000)
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "latency_ms": int((time.time()-t0)*1000)}

if __name__ == "__main__":
    # demo: this should fail network
    out = run_sandbox("alpine", "ping -c 1 8.8.8.8", timeout=5)
    print(json.dumps(out, indent=2))
