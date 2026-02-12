from __future__ import annotations
import os, random
from datasets.config import PROCESSED_DIR, SPLITS_DIR, SPLIT
from datasets.utils import ensure_dir, load_jsonl, write_jsonl

def main(seed: int = 42):
    random.seed(seed)
    ensure_dir(SPLITS_DIR)

    inp = os.path.join(PROCESSED_DIR, "clean.jsonl")
    rows = load_jsonl(inp)
    random.shuffle(rows)

    n = len(rows)
    n_train = int(n * SPLIT["train"])
    n_val = int(n * SPLIT["val"])
    train = rows[:n_train]
    val = rows[n_train:n_train+n_val]
    test = rows[n_train+n_val:]

    write_jsonl(os.path.join(SPLITS_DIR, "train.jsonl"), train)
    write_jsonl(os.path.join(SPLITS_DIR, "val.jsonl"), val)
    write_jsonl(os.path.join(SPLITS_DIR, "test.jsonl"), test)

    print("✅ Split complete")
    print("train:", len(train), "val:", len(val), "test:", len(test))

if __name__ == "__main__":
    main()
