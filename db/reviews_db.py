from __future__ import annotations
import uuid
import time
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Review

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def add_review_db(payload: Dict[str, Any]) -> Dict[str, Any]:
    skill_id = payload.get("skill_id")
    tenant_id = payload.get("tenant_id","t1")
    user_id = payload.get("user_id","u1")
    rating = int(payload.get("rating",0))
    text = (payload.get("text","") or "").strip()
    verified = bool(payload.get("verified", False))
    abuse_score = int(payload.get("abuse_score", 0))

    if not skill_id:
        raise ValueError("skill_id required")
    if rating < 1 or rating > 5:
        raise ValueError("rating must be 1..5")
    if len(text) < 3:
        raise ValueError("text too short")

    db: Session = SessionLocal()
    try:
        rid = str(uuid.uuid4())
        r = Review(
            review_id=rid, ts=now_iso(), skill_id=skill_id,
            tenant_id=tenant_id, user_id=user_id, rating=rating,
            text=text, verified=verified, abuse_score=abuse_score
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return {
            "review_id": r.review_id, "ts": r.ts, "skill_id": r.skill_id,
            "tenant_id": r.tenant_id, "user_id": r.user_id,
            "rating": r.rating, "text": r.text,
            "verified": r.verified, "abuse_score": r.abuse_score,
            "developer_response": r.developer_response
        }
    finally:
        db.close()

def list_reviews_db(skill_id: str | None = None) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        q = db.query(Review)
        if skill_id:
            q = q.filter(Review.skill_id == skill_id)
        rows = q.order_by(Review.ts.desc()).limit(200).all()
        return [{
            "review_id": r.review_id, "ts": r.ts, "skill_id": r.skill_id,
            "tenant_id": r.tenant_id, "user_id": r.user_id,
            "rating": r.rating, "text": r.text,
            "verified": r.verified, "abuse_score": r.abuse_score,
            "developer_response": r.developer_response
        } for r in rows]
    finally:
        db.close()
