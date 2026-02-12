from __future__ import annotations
import os, re, json, hashlib
from typing import Dict, Any, Iterable, List

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def stable_id(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

_ws = re.compile(r"\s+")
def normalize_ws(text: str) -> str:
    return _ws.sub(" ", (text or "").strip())

# simple PII patterns (not perfect, good MVP)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
APIKEY = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{20,})\b")

def mask_pii(text: str) -> str:
    t = text or ""
    t = EMAIL.sub("[EMAIL]", t)
    t = PHONE.sub("[PHONE]", t)
    t = APIKEY.sub("[SECRET]", t)
    return t
