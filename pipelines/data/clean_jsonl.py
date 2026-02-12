import json
from pathlib import Path

def clean(infile: str, outfile: str):
    seen = set()
    out = []
    inp = Path(infile)
    for line in inp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        text = str(row.get("text","")).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append({"text": text})

    Path(outfile).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8")
    print(f"✅ cleaned rows: {len(out)} -> {outfile}")

if __name__ == "__main__":
    clean("data/raw/data.jsonl", "data/clean/clean.jsonl")
