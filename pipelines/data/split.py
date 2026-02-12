import json, random
from pathlib import Path

def load_jsonl(path: str):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def save_jsonl(path: str, rows):
    Path(path).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows), encoding="utf-8")

def split(infile: str):
    data = load_jsonl(infile)
    random.shuffle(data)
    n = len(data)
    train = data[:int(n*0.8)]
    val = data[int(n*0.8):int(n*0.9)]
    test = data[int(n*0.9):]
    save_jsonl("data/splits/train.jsonl", train)
    save_jsonl("data/splits/val.jsonl", val)
    save_jsonl("data/splits/test.jsonl", test)
    print(f"✅ split done: train={len(train)} val={len(val)} test={len(test)}")

if __name__ == "__main__":
    split("data/clean/clean.jsonl")
