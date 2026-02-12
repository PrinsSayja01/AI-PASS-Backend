from __future__ import annotations
from sqlalchemy import Column, String, Integer, Float, Boolean, Text
from db.database import Base

class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(String, primary_key=True, index=True)
    ts = Column(String, index=True)
    skill_id = Column(String, index=True)
    tenant_id = Column(String, index=True)
    user_id = Column(String, index=True)
    rating = Column(Integer)
    text = Column(Text)
    verified = Column(Boolean, default=False)
    abuse_score = Column(Integer, default=0)
    developer_response = Column(Text, nullable=True)

class BillingEvent(Base):
    __tablename__ = "billing_events"
    event_id = Column(String, primary_key=True, index=True)
    ts = Column(String, index=True)
    tenant_id = Column(String, index=True)
    skill_id = Column(String, index=True)
    version = Column(String)
    credits = Column(Integer)
    gross_usd = Column(Float)
    platform_fee_usd = Column(Float)
    developer_net_usd = Column(Float)
    developer_id = Column(String, index=True)
    latency_ms = Column(Integer, nullable=True)

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)   # e.g. "t1"
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, index=True)        # "admin" | "developer" | "tenant"
    is_active = Column(Boolean, default=True)

class Device(Base):
    __tablename__ = "devices"
    device_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    user_id = Column(String, index=True)
    name = Column(String)
    current_jti = Column(String)             # rotation: only latest jti is valid
    is_active = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id = Column(String, primary_key=True, index=True)
    ts = Column(String, index=True)
    tenant_id = Column(String, index=True)
    user_id = Column(String, index=True)
    device_id = Column(String, index=True)
    ip = Column(String, index=True)
    route = Column(String, index=True)
    action = Column(String, index=True)   # e.g. SKILL_RUN / WORKFLOW_RUN / AGENT_RUN
    target_id = Column(String, index=True)  # skill_id or workflow_id
    ok = Column(Boolean, default=False)
    credits = Column(Integer, default=0)
    error = Column(Text, nullable=True)

class RateCounter(Base):
    __tablename__ = "rate_counters"
    key = Column(String, primary_key=True, index=True)     # tenant/device/route/window
    window_start = Column(Integer, index=True)             # unix seconds
    window_sec = Column(Integer)
    count = Column(Integer, default=0)

class Suspension(Base):
    __tablename__ = "suspensions"
    suspend_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    device_id = Column(String, index=True)
    until_ts = Column(Integer, index=True)                 # unix seconds
    reason = Column(Text)

class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    wf_ver_id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, index=True)          # stable id
    version = Column(String, index=True)              # "1.0.0"
    developer_id = Column(String, index=True)
    tenant_scope = Column(String, default="public")   # public|enterprise|private
    visibility = Column(Text, default="public")       # simple string rules
    status = Column(String, index=True)               # DRAFT|APPROVED|REJECTED|LOCKED
    created_ts = Column(Integer, index=True)
    payload_json = Column(Text)                       # full workflow definition JSON

class Submission(Base):
    __tablename__ = "submissions"
    submission_id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, index=True)
    version = Column(String, index=True)
    developer_id = Column(String, index=True)
    status = Column(String, index=True)               # SUBMITTED|SECURITY_SCAN|HUMAN_REVIEW|APPROVED|REJECTED
    created_ts = Column(Integer, index=True)
    updated_ts = Column(Integer, index=True)
    scan_report_json = Column(Text, default="")       # from security scan
    reviewer_notes = Column(Text, default="")
    decision_by = Column(String, default="")          # admin user id

class VersionLock(Base):
    __tablename__ = "version_locks"
    lock_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    workflow_id = Column(String, index=True)
    locked_version = Column(String, index=True)
    is_locked = Column(Boolean, default=True)
    reason = Column(Text, default="")
    updated_ts = Column(Integer, index=True)

class TenantInstall(Base):
    __tablename__ = "tenant_installs"
    install_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    workflow_id = Column(String, index=True)
    current_version = Column(String, index=True)
    updated_ts = Column(Integer, index=True)

class InstallEvent(Base):
    __tablename__ = "install_events"
    event_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    workflow_id = Column(String, index=True)
    version = Column(String, index=True)
    action = Column(String, index=True)          # INSTALL | ROLLBACK
    by_user_id = Column(String, index=True)
    device_id = Column(String, index=True)
    reason = Column(Text, default="")
    created_ts = Column(Integer, index=True)
