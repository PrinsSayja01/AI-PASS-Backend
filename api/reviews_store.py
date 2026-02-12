from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import time
import uuid
from collections import defaultdict
from api.billing_ledger import tenant_dashboard

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"
REVIEWS_FILE = REG / "reviews.json"
FEATURED_FILE = REG / "featured.json"
LEDGER_FILE = REG / "billing_ledger.json"

def _read(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def list_reviews(skill_id: str | None = None) -> List[Dict[str, Any]]:
    data = _read(REVIEWS_FILE, {"reviews": []})
    rev = data.get("reviews", [])
    if skill_id:
        rev = [r for r in rev if r.get("skill_id") == skill_id]
    return rev

def _is_abuse(text: str) -> bool:
    t = (text or "").lower()
    if len(t.strip()) < 3:
        return True
    # very basic spam
    if t.count("http://") + t.count("https://") >= 2:
        return True
    if t.count("buy") >= 3:
        return True
    return False



# -----------------------
# Fraud detection helpers
# -----------------------
def _abuse_score(user_id: str, reviews):
    # simple heuristic
    user_reviews = [r for r in reviews if r.get("user_id")==user_id]
    score = 0
    if len(user_reviews) > 5:
        score += 2
    if any(len(r.get("text","")) < 5 for r in user_reviews):
        score += 1
    if len(set(r.get("rating") for r in user_reviews)) == 1 and len(user_reviews) >= 3:
        score += 1
    return score

def _is_verified_user(tenant_id: str):
    # verified if tenant has real billing usage
    dash = tenant_dashboard(tenant_id)
    return dash.get("total_events",0) >= 1


def add_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    skill_id = payload.get("skill_id")
    tenant_id = payload.get("tenant_id", "t1")
    user_id = payload.get("user_id", "u1")
    rating = int(payload.get("rating", 0))
    text = payload.get("text", "").strip()

    if not skill_id:
        raise ValueError("skill_id required")
    if rating < 1 or rating > 5:
        raise ValueError("rating must be 1..5")
    if _is_abuse(text):
        raise ValueError("Review rejected (possible abuse/spam)")

    data = _read(REVIEWS_FILE, {"reviews": []})

    review = {
        "review_id": str(uuid.uuid4()),
        "ts": now_iso(),
        "skill_id": skill_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "rating": rating,
        "text": text,
        "verified": bool(payload.get("verified", False)),
        "developer_response": None
    }
    data["reviews"].append(review)
    _write(REVIEWS_FILE, data)
    return review

def developer_reply(review_id: str, developer_id: str, text: str) -> Dict[str, Any]:
    data = _read(REVIEWS_FILE, {"reviews": []})
    for r in data["reviews"]:
        if r["review_id"] == review_id:
            r["developer_response"] = {
                "developer_id": developer_id,
                "ts": now_iso(),
                "text": text[:800]
            }
            _write(REVIEWS_FILE, data)
            return r
    raise ValueError("review not found")

def rating_summary(skill_id: str) -> Dict[str, Any]:
    rev = list_reviews(skill_id)
    if not rev:
        return {"skill_id": skill_id, "count": 0, "avg": 0.0, "stars": {}}

    stars = defaultdict(int)
    total = 0
    for r in rev:
        stars[int(r["rating"])] += 1
        total += int(r["rating"])

    avg = total / len(rev)
    return {"skill_id": skill_id, "count": len(rev), "avg": round(avg, 2), "stars": dict(stars)}

def usage_counts() -> Dict[str, int]:
    led = _read(LEDGER_FILE, {"events": []})
    cnt = defaultdict(int)
    for e in led.get("events", []):
        cnt[e.get("skill_id")] += 1
    return dict(cnt)

def featured_skills() -> List[str]:
    f = _read(FEATURED_FILE, {"featured_skills": []})
    return f.get("featured_skills", [])

def search_and_rank(skills: List[Dict[str, Any]], q: str = "") -> List[Dict[str, Any]]:
    q = (q or "").lower().strip()
    featured = set(featured_skills())
    usage = usage_counts()

    # rating cache
    rating_cache = {}
    for s in skills:
        sid = s.get("skill_id")
        rating_cache[sid] = rating_summary(sid)

    def score(skill):
        sid = skill.get("skill_id")
        r = rating_cache.get(sid, {"avg": 0.0, "count": 0})
        avg = float(r.get("avg", 0.0))
        cnt = int(r.get("count", 0))
        use = int(usage.get(sid, 0))
        feat = 1 if sid in featured else 0
        # weighted score
        return (feat * 1000) + (avg * 100) + (cnt * 2) + (use * 1)

    # search filter
    if q:
        skills = [s for s in skills if q in s.get("skill_id","").lower() or q in s.get("category","").lower()]

    out = []
    for s in skills:
        sid = s.get("skill_id")
        s2 = dict(s)
        s2["rating"] = rating_cache.get(sid)
        s2["usage_count"] = usage.get(sid, 0)
        s2["featured"] = sid in featured
        s2["_rank_score"] = score(s)
        out.append(s2)

    out.sort(key=lambda x: x["_rank_score"], reverse=True)
    return out
