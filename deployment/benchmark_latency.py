import time
import requests

BASE = "http://localhost:8000"

def bench(endpoint: str, payload: dict, runs: int = 20):
    times=[]
    for _ in range(runs):
        t0=time.time()
        r=requests.post(BASE+endpoint, json=payload, timeout=10)
        dt=(time.time()-t0)*1000
        times.append(dt)
    times.sort()
    return {
        "p50": times[len(times)//2],
        "p90": times[int(len(times)*0.9)-1],
        "min": times[0],
        "max": times[-1],
    }

if __name__ == "__main__":
    print("summarize:", bench("/skills/summarize", {"text":"hello world "*50, "max_words": 20}))
    print("pii_redactor:", bench("/skills/pii_redactor", {"text":"Email is a@b.com phone +49 123 456 789"}))
