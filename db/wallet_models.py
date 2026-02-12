from sqlalchemy import Column, String, Integer, Boolean, Text, BigInteger
from db.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    tenant_id = Column(String, primary_key=True, index=True)
    balance = Column(Integer, default=0)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(String, primary_key=True, index=True)
    ts = Column(BigInteger, index=True)
    tenant_id = Column(String, index=True)
    user_id = Column(String, index=True)
    device_id = Column(String, index=True, nullable=True)

    action = Column(String, index=True)      # SKILL_RUN / RAG_QUERY / WORKFLOW_RUN / CHAT
    units = Column(Integer, default=1)
    credits = Column(Integer, default=0)
    ok = Column(Boolean, default=True)
    ref_id = Column(String, index=True, nullable=True)
    error = Column(Text, nullable=True)
