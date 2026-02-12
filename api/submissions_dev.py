from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import SessionLocal
from api.security_deps import require_role
from db.workflow_db import create_draft, submit_workflow, dev_list_workflows, dev_list_submissions

router = APIRouter(prefix="/dev", tags=["developer-submissions"])

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/workflows")
def list_my_workflows(claims: dict = Depends(require_role("developer")), db: Session = Depends(_db)):
    return {"count": 0, "workflows": dev_list_workflows(db, claims["sub"])}

@router.post("/workflows/create")
def create_workflow(payload: dict, claims: dict = Depends(require_role("developer")), db: Session = Depends(_db)):
    # payload is full workflow json {name, version, steps...}
    try:
        out = create_draft(db, claims["sub"], payload)
        return {"ok": True, **out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/workflows/submit")
def submit(payload: dict, claims: dict = Depends(require_role("developer")), db: Session = Depends(_db)):
    workflow_id = payload.get("workflow_id","")
    version = payload.get("version","")
    if not workflow_id or not version:
        raise HTTPException(status_code=400, detail="workflow_id and version required")
    try:
        out = submit_workflow(db, claims["sub"], workflow_id, version)
        return {"ok": True, **out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/submissions")
def my_submissions(claims: dict = Depends(require_role("developer")), db: Session = Depends(_db)):
    return {"count": 0, "submissions": dev_list_submissions(db, claims["sub"])}
