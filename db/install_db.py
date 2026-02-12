from __future__ import annotations
import time, uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from db.models import WorkflowVersion, VersionLock, TenantInstall, InstallEvent

def now() -> int:
    return int(time.time())

def new_id() -> str:
    return str(uuid.uuid4())

def _get_lock(db: Session, tenant_id: str, workflow_id: str) -> Optional[VersionLock]:
    return db.query(VersionLock).filter(
        VersionLock.tenant_id == tenant_id,
        VersionLock.workflow_id == workflow_id
    ).first()

def _get_wf(db: Session, workflow_id: str, version: str) -> Optional[WorkflowVersion]:
    return db.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow_id,
        WorkflowVersion.version == version
    ).first()

def _ensure_approved(wf: WorkflowVersion) -> None:
    if wf.status != "APPROVED":
        raise ValueError(f"workflow version not approved (status={wf.status})")

def get_current(db: Session, tenant_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
    row = db.query(TenantInstall).filter(
        TenantInstall.tenant_id == tenant_id,
        TenantInstall.workflow_id == workflow_id
    ).first()
    if not row:
        return None
    return {"tenant_id": tenant_id, "workflow_id": workflow_id, "current_version": row.current_version, "updated_ts": row.updated_ts}

def install_version(
    db: Session,
    tenant_id: str,
    workflow_id: str,
    version: str,
    by_user_id: str,
    device_id: str,
    reason: str = ""
) -> Dict[str, Any]:

    wf = _get_wf(db, workflow_id, version)
    if not wf:
        raise ValueError("workflow version not found")
    _ensure_approved(wf)

    lock = _get_lock(db, tenant_id, workflow_id)
    if lock and lock.is_locked and lock.locked_version != version:
        raise ValueError(f"version locked to {lock.locked_version}")

    row = db.query(TenantInstall).filter(
        TenantInstall.tenant_id == tenant_id,
        TenantInstall.workflow_id == workflow_id
    ).first()

    if not row:
        row = TenantInstall(
            install_id=new_id(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            current_version=version,
            updated_ts=now()
        )
        db.add(row)
    else:
        row.current_version = version
        row.updated_ts = now()

    ev = InstallEvent(
        event_id=new_id(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        version=version,
        action="INSTALL",
        by_user_id=by_user_id,
        device_id=device_id,
        reason=reason,
        created_ts=now()
    )
    db.add(ev)
    db.commit()

    return {"tenant_id": tenant_id, "workflow_id": workflow_id, "current_version": version}

def history(db: Session, tenant_id: str, workflow_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    rows = db.query(InstallEvent).filter(
        InstallEvent.tenant_id == tenant_id,
        InstallEvent.workflow_id == workflow_id
    ).order_by(InstallEvent.created_ts.desc()).limit(min(limit, 200)).all()

    return [{
        "event_id": r.event_id,
        "action": r.action,
        "version": r.version,
        "by_user_id": r.by_user_id,
        "device_id": r.device_id,
        "reason": r.reason,
        "created_ts": r.created_ts
    } for r in rows]

def rollback(
    db: Session,
    tenant_id: str,
    workflow_id: str,
    to_version: str,
    by_user_id: str,
    device_id: str,
    reason: str = "rollback"
) -> Dict[str, Any]:

    wf = _get_wf(db, workflow_id, to_version)
    if not wf:
        raise ValueError("workflow version not found")
    _ensure_approved(wf)

    lock = _get_lock(db, tenant_id, workflow_id)
    if lock and lock.is_locked and lock.locked_version != to_version:
        raise ValueError(f"version locked to {lock.locked_version}")

    row = db.query(TenantInstall).filter(
        TenantInstall.tenant_id == tenant_id,
        TenantInstall.workflow_id == workflow_id
    ).first()
    if not row:
        raise ValueError("no current install found (install first)")

    row.current_version = to_version
    row.updated_ts = now()

    ev = InstallEvent(
        event_id=new_id(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        version=to_version,
        action="ROLLBACK",
        by_user_id=by_user_id,
        device_id=device_id,
        reason=reason,
        created_ts=now()
    )
    db.add(ev)
    db.commit()

    return {"tenant_id": tenant_id, "workflow_id": workflow_id, "current_version": to_version}
