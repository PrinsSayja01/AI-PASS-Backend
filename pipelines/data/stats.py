import json
from pathlib import Path
from collections import Counter

def read_jsonl(path: str):
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def main():
    train = read_jsonl("data/splits/train.jsonl")
    val = read_jsonl("data/splits/val.jsonl")
    test = read_jsonl("data/splits/test.jsonl")

    def length_bucket(text: str):
        n = len(text.split())
        if n < 20: return "<20"
        if n < 50: return "20-49"
        if n < 100: return "50-99"
        return "100+"

    buckets = Counter()
    for r in train + val + test:
        t = str(r.get("text",""))
        buckets[length_bucket(t)] += 1

    report = {
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "length_buckets": dict(buckets)
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
