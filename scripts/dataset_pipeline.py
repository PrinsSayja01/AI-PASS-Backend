import json, re, random, time, hashlib
from pathlib import Path

RAW = Path("datasets/raw")
CLEAN = Path("datasets/clean")
SPLITS = Path("datasets/splits")
REPORT = Path("reports/dataset_latest.json")

random.seed(42)

def clean_text(t: str) -> str:
    t = (t or "").replace("\r", " ").replace("\n", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def stable_id(obj: dict) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:16]

def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def ensure_sample_raw():
    RAW.mkdir(parents=True, exist_ok=True)
    sample = RAW / "skills_prompts.jsonl"
    if sample.exists():
        return str(sample)

    rows = [
        {
            "task":"summarize",
            "input":"AI-Pass Marketplace supports reusable AI agent skills with governance and sandboxing.",
            "output":"AI-Pass is a governed marketplace for reusable agent skills."
        },
        {
            "task":"translate",
            "input":"Hello, how are you?",
            "output":"Hallo, wie geht es dir?"
        },
        {
            "task":"pii_redactor",
            "input":"Email is test@mail.com phone +49 123 456 789",
            "output":"Email is <EMAIL> phone <PHONE>"
        },
        {
            "task":"security_scan",
            "input":"Find leaked keys: sk-1234567890abcdef and URL http://evil.example.com",
            "output":"Detected possible secret + suspicious URL."
        }
    ]
    write_jsonl(sample, rows)
    return str(sample)

def main():
    t0 = time.time()
    RAW.mkdir(parents=True, exist_ok=True)
    CLEAN.mkdir(parents=True, exist_ok=True)
    SPLITS.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    created_sample = ensure_sample_raw()

    all_clean = []
    per_file = []

    for f in sorted(RAW.glob("*.jsonl")):
        cleaned = []
        for r in load_jsonl(f):
            task = clean_text(r.get("task", "unknown"))
            inp = clean_text(r.get("input", ""))
            out = clean_text(r.get("output", ""))
            if not inp or not out:
                continue
            row = {"id": stable_id({"task":task,"input":inp,"output":out}), "task": task, "input": inp, "output": out}
            cleaned.append(row)

        # de-dup by id inside file
        seen = set()
        uniq = []
        for r in cleaned:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            uniq.append(r)

        clean_path = CLEAN / f.name
        write_jsonl(clean_path, uniq)

        all_clean.extend(uniq)
        per_file.append({"file": str(f), "rows": len(uniq), "cleaned_file": str(clean_path)})

    # global de-dup
    seen = set()
    uniq_all = []
    for r in all_clean:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        uniq_all.append(r)

    random.shuffle(uniq_all)
    n = len(uniq_all)
    n_train = int(n * 0.8)
    n_valid = int(n * 0.1)

    train = uniq_all[:n_train]
    valid = uniq_all[n_train:n_train+n_valid]
    test  = uniq_all[n_train+n_valid:]

    write_jsonl(SPLITS / "train.jsonl", train)
    write_jsonl(SPLITS / "valid.jsonl", valid)
    write_jsonl(SPLITS / "test.jsonl", test)

    report = {
        "ok": True,
        "ts": int(time.time()),
        "created_sample_raw": created_sample,
        "raw_files": len(list(RAW.glob("*.jsonl"))),
        "clean_files": len(list(CLEAN.glob("*.jsonl"))),
        "total_rows": n,
        "split": {"train": len(train), "valid": len(valid), "test": len(test)},
        "per_file": per_file,
        "output": {
            "train": str(SPLITS / "train.jsonl"),
            "valid": str(SPLITS / "valid.jsonl"),
            "test": str(SPLITS / "test.jsonl")
        },
        "latency_ms": int((time.time() - t0) * 1000)
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("✅ dataset pipeline done")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
