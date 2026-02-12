from __future__ import annotations
import os, glob
from typing import Dict, Any, List
from datasets.config import RAW_DIR, PROCESSED_DIR, MAX_CHARS
from datasets.utils import ensure_dir, read_text_file, normalize_ws, stable_id, write_jsonl

def main():
    ensure_dir(PROCESSED_DIR)
    out_path = os.path.join(PROCESSED_DIR, "raw.jsonl")

    files = []
    files += glob.glob(os.path.join(RAW_DIR, "**/*.txt"), recursive=True)
    files += glob.glob(os.path.join(RAW_DIR, "**/*.md"), recursive=True)

    rows: List[Dict[str, Any]] = []
    for fp in sorted(files):
        text = read_text_file(fp)
        text = text[:MAX_CHARS]
        text = normalize_ws(text)
        if not text:
            continue
        rows.append({
            "id": stable_id(fp + ":" + text[:200]),
            "source_path": fp,
            "text": text
        })

    write_jsonl(out_path, rows)
    print(f"✅ Collected {len(rows)} files -> {out_path}")

if __name__ == "__main__":
    main()
