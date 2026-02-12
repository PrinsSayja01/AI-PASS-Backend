from __future__ import annotations
import os, random
from typing import Dict, Any, List
from datasets.config import SPLITS_DIR, EXPORT_DIR
from datasets.utils import ensure_dir, load_jsonl, write_jsonl

def make_tasks(text: str) -> List[Dict[str, Any]]:
    """
    Weak-supervision tasks (MVP):
    - Summarize: use first N words as pseudo summary
    - Keywords: top unique words by simple frequency
    - Clean text: normalize whitespace (already clean, but keep task)
    You can replace these with human-labeled data later.
    """
    words = [w.strip(".,!?;:()[]{}\"'").lower() for w in text.split()]
    words = [w for w in words if w and len(w) >= 4]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:8]
    keywords = [k for k,_ in top]

    pseudo_summary = " ".join(text.split()[:40])

    tasks = []
    tasks.append({
        "instruction": "Summarize the text in 40 words or less.",
        "input": text,
        "output": pseudo_summary
    })
    tasks.append({
        "instruction": "Extract up to 8 keywords from the text.",
        "input": text,
        "output": ", ".join(keywords)
    })
    tasks.append({
        "instruction": "Clean the text: remove extra spaces and keep it readable.",
        "input": text,
        "output": " ".join(text.split())
    })
    return tasks

def convert(split_name: str, out_name: str, limit: int = 0):
    inp = os.path.join(SPLITS_DIR, f"{split_name}.jsonl")
    rows = load_jsonl(inp)
    if limit and limit > 0:
        rows = rows[:limit]

    out_rows = []
    for r in rows:
        text = r.get("text","").strip()
        if len(text) < 50:
            continue
        out_rows.extend(make_tasks(text))

    out_path = os.path.join(EXPORT_DIR, out_name)
    write_jsonl(out_path, out_rows)
    print(f"✅ Exported {len(out_rows)} instruct rows -> {out_path}")

def main():
    ensure_dir(EXPORT_DIR)
    convert("train", "train_instruct.jsonl")
    convert("val", "val_instruct.jsonl")

if __name__ == "__main__":
    main()
