from __future__ import annotations
import os
from datasets.config import PROCESSED_DIR, MASK_PII
from datasets.utils import load_jsonl, write_jsonl, normalize_ws, mask_pii

def main():
    inp = os.path.join(PROCESSED_DIR, "raw.jsonl")
    out = os.path.join(PROCESSED_DIR, "clean.jsonl")

    rows = load_jsonl(inp)
    cleaned = []
    for r in rows:
        text = normalize_ws(r.get("text",""))
        if MASK_PII:
            text = mask_pii(text)
        if len(text) < 20:
            continue
        r2 = dict(r)
        r2["text"] = text
        cleaned.append(r2)

    write_jsonl(out, cleaned)
    print(f"✅ Cleaned {len(cleaned)} samples -> {out}")

if __name__ == "__main__":
    main()
