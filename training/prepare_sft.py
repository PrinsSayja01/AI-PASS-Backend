import json
from pathlib import Path

def read_jsonl(path: str):
    rows=[]
    p=Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def main():
    inp = read_jsonl("data/splits/train.jsonl")
    out = []
    for r in inp:
        text = r.get("text","")
        out.append({
            "instruction": "Summarize the text in 3 sentences.",
            "input": text,
            "output": "PLACEHOLDER_SUMMARY"
        })
    Path("training/sft_train.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ wrote training/sft_train.json", len(out))

if __name__ == "__main__":
    main()
