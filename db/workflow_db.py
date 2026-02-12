from __future__ import annotations
import json, time, uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from db.models import WorkflowVersion, Submission, VersionLock

def now() -> int:
    return int(time.time())

def new_id() -> str:
    return str(uuid.uuid4())

def create_draft(db: Session, developer_id: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = workflow.get("workflow_id") or new_id()
    version = workflow.get("version") or "1.0.0"

    row = WorkflowVersion(
        wf_ver_id=new_id(),
        workflow_id=workflow_id,
        version=version,
        developer_id=developer_id,
        tenant_scope=workflow.get("tenant_scope","public"),
        visibility=workflow.get("visibility","public"),
        status="DRAFT",
        created_ts=now(),
        payload_json=json.dumps({**workflow, "workflow_id": workflow_id, "version": version})
    )
    db.add(row)
    db.commit()
    return {"workflow_id": workflow_id, "version": version, "status": row.status}

def submit_workflow(db: Session, developer_id: str, workflow_id: str, version: str) -> Dict[str, Any]:
    wf = db.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow_id,
        WorkflowVersion.version == version,
        WorkflowVersion.developer_id == developer_id
    ).first()
    if not wf:
        raise ValueError("workflow version not found")
    if wf.status not in ("DRAFT","REJECTED"):
        raise ValueError(f"cannot submit from status={wf.status}")

    sub = Submission(
        submission_id=new_id(),
        workflow_id=workflow_id,
        version=version,
        developer_id=developer_id,
        status="SUBMITTED",
        created_ts=now(),
        updated_ts=now(),
        scan_report_json="",
        reviewer_notes="",
        decision_by=""
    )
    db.add(sub)
    db.commit()
    return {"submission_id": sub.submission_id, "status": sub.status}

def dev_list_workflows(db: Session, developer_id: str) -> List[Dict[str, Any]]:
    rows = db.query(WorkflowVersion).filter(WorkflowVersion.developer_id == developer_id).order_by(WorkflowVersion.created_ts.desc()).all()
    out = []
    for r in rows:
        out.append({
            "workflow_id": r.workflow_id, "version": r.version, "status": r.status,
            "tenant_scope": r.tenant_scope, "visibility": r.visibility, "created_ts": r.created_ts
        })
    return out

def dev_list_submissions(db: Session, developer_id: str) -> List[Dict[str, Any]]:
    rows = db.query(Submission).filter(Submission.developer_id == developer_id).order_by(Submission.updated_ts.desc()).all()
    return [{
        "submission_id": r.submission_id,
        "workflow_id": r.workflow_id,
        "version": r.version,
        "status": r.status,
        "created_ts": r.created_ts,
        "updated_ts": r.updated_ts,
        "reviewer_notes": r.reviewer_notes
    } for r in rows]

def admin_queue(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = db.query(Submission).filter(Submission.status.in_(["SUBMITTED","SECURITY_SCAN","HUMAN_REVIEW"])).order_by(Submission.updated_ts.asc()).limit(min(limit,200)).all()
    return [{
        "submission_id": r.submission_id,
        "workflow_id": r.workflow_id,
        "version": r.version,
        "developer_id": r.developer_id,
        "status": r.status,
        "updated_ts": r.updated_ts
    } for r in rows]

def admin_set_status(db: Session, submission_id: str, status: str, admin_user_id: str, notes: str = "", scan_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    sub = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not sub:
        raise ValueError("submission not found")

    allowed = {"SECURITY_SCAN","HUMAN_REVIEW","APPROVED","REJECTED"}
    if status not in allowed:
        raise ValueError("bad status")

    sub.status = status
    sub.updated_ts = now()
    sub.decision_by = admin_user_id
    if notes:
        sub.reviewer_notes = notes
    if scan_report is not None:
        sub.scan_report_json = json.dumps(scan_report)

    # If approved, mark workflow version approved too
    if status == "APPROVED":
        wf = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == sub.workflow_id,
            WorkflowVersion.version == sub.version
        ).first()
        if wf:
            wf.status = "APPROVED"

    if status == "REJECTED":
        wf = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == sub.workflow_id,
            WorkflowVersion.version == sub.version
        ).first()
        if wf and wf.status == "DRAFT":
            wf.status = "REJECTED"

    db.commit()
    return {"submission_id": sub.submission_id, "status": sub.status}

def lock_version(db: Session, tenant_id: str, workflow_id: str, version: str, reason: str = "") -> Dict[str, Any]:
    row = db.query(VersionLock).filter(
        VersionLock.tenant_id == tenant_id,
        VersionLock.workflow_id == workflow_id
    ).first()
    if not row:
        row = VersionLock(
            lock_id=new_id(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            locked_version=version,
            is_locked=True,
            reason=reason,
            updated_ts=now()
        )
        db.add(row)
    else:
        row.locked_version = version
        row.is_locked = True
        row.reason = reason
        row.updated_ts = now()

    db.commit()
    return {"tenant_id": tenant_id, "workflow_id": workflow_id, "locked_version": version, "is_locked": True}

def unlock_version(db: Session, tenant_id: str, workflow_id: str) -> Dict[str, Any]:
    row = db.query(VersionLock).filter(
        VersionLock.tenant_id == tenant_id,
        VersionLock.workflow_id == workflow_id
    ).first()
    if not row:
        return {"ok": True, "note": "no lock found"}
    row.is_locked = False
    row.updated_ts = now()
    db.commit()
    return {"tenant_id": tenant_id, "workflow_id": workflow_id, "is_locked": False}

def get_lock(db: Session, tenant_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
    row = db.query(VersionLock).filter(
        VersionLock.tenant_id == tenant_id,
        VersionLock.workflow_id == workflow_id
    ).first()
    if not row:
        return None
    return {"tenant_id": row.tenant_id, "workflow_id": row.workflow_id, "locked_version": row.locked_version, "is_locked": row.is_locked}
