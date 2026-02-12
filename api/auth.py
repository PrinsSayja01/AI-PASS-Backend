from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Header
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import User, Device
from pathlib import Path
import uuid
import time
import json

router = APIRouter(prefix="/auth", tags=["auth"])

BASE_DIR = Path(__file__).resolve().parent.parent
REG = BASE_DIR / "registry"
ADMIN_POLICY = REG / "admin_policy.json"

# ---- security settings (MVP) ----
from api.config import JWT_SECRET, JWT_ALG, ACCESS_TTL_SEC, DEVICE_TTL_SEC   # later: move to env var

pwd = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def now() -> int:
    return int(time.time())

def load_admin_token() -> str:
    if not ADMIN_POLICY.exists():
        ADMIN_POLICY.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_POLICY.write_text(json.dumps({"admin_token":"CHANGE_ME_ADMIN_TOKEN"}, indent=2), encoding="utf-8")
    return json.loads(ADMIN_POLICY.read_text(encoding="utf-8")).get("admin_token","CHANGE_ME_ADMIN_TOKEN")

def _bcrypt_safe(p: str) -> str:
    # bcrypt uses only first 72 bytes
    b = (p or "").encode("utf-8")
    if len(b) > 72:
        b = b[:72]
    return b.decode("utf-8", errors="ignore")

def hash_pw(p: str) -> str:
    return pwd.hash(p)

def verify_pw(p: str, h: str) -> bool:
    return pwd.verify(p, h)

def make_access_token(user: User) -> str:
    payload = {
        "type": "access",
        "sub": user.user_id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "exp": now() + ACCESS_TTL_SEC,
        "iat": now()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def make_device_token(device: Device) -> str:
    jti = str(uuid.uuid4())
    device.current_jti = jti
    payload = {
        "type": "device",
        "device_id": device.device_id,
        "tenant_id": device.tenant_id,
        "user_id": device.user_id,
        "jti": jti,
        "exp": now() + DEVICE_TTL_SEC,
        "iat": now()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

def require_access(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    data = decode_token(token)
    if data.get("type") != "access":
        raise HTTPException(status_code=401, detail="Not an access token")
    return data

def require_role(role: str):
    def _dep(claims: dict = Depends(require_access)) -> dict:
        if claims.get("role") != role:
            raise HTTPException(status_code=403, detail=f"Requires role={role}")
        return claims
    return _dep

def require_admin_or_dev(claims: dict = Depends(require_access)) -> dict:
    if claims.get("role") not in ("admin", "developer"):
        raise HTTPException(status_code=403, detail="Requires admin or developer role")
    return claims

# -------------------------
# Bootstrap Admin
# -------------------------
@router.post("/bootstrap_admin")
def bootstrap_admin(payload: dict, x_admin_token: str | None = Header(default=None), db: Session = Depends(db_session)):
    """
    One-time: create admin user. Requires X-Admin-Token header matching registry/admin_policy.json
    body: { "email": "...", "password": "..." }
    """
    if x_admin_token != load_admin_token():
        raise HTTPException(status_code=401, detail="Bad admin token")

    email = payload.get("email","").strip().lower()
    password = payload.get("password","")
    if not email or len(password) < 8:
        raise HTTPException(status_code=400, detail="email and password(min 8) required")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return {"ok": True, "user_id": existing.user_id, "note": "already exists"}

    u = User(
        user_id=str(uuid.uuid4()),
        tenant_id="platform",
        email=email,
        password_hash=hash_pw(password),
        role="admin",
        is_active=True
    )
    db.add(u)
    db.commit()
    return {"ok": True, "user_id": u.user_id}

# -------------------------
# Register + Login
# -------------------------
@router.post("/register")
def register(payload: dict, claims: dict = Depends(require_admin_or_dev), db: Session = Depends(db_session)):
    """
    Admin/Developer can create users.
    payload: { tenant_id, email, password, role }
    """
    tenant_id = payload.get("tenant_id","t1")
    email = payload.get("email","").strip().lower()
    password = payload.get("password","")
    role = payload.get("role","tenant")

    if role not in ("admin","developer","tenant"):
        raise HTTPException(status_code=400, detail="role must be admin|developer|tenant")
    if not email or len(password) < 8:
        raise HTTPException(status_code=400, detail="email and password(min 8) required")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="email already exists")

    u = User(
        user_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_pw(password),
        role=role,
        is_active=True
    )
    db.add(u)
    db.commit()
    return {"ok": True, "user_id": u.user_id, "tenant_id": tenant_id, "role": role}

@router.post("/login")
def login(payload: dict, db: Session = Depends(db_session)):
    """
    payload: { email, password }
    """
    email = payload.get("email","").strip().lower()
    password = payload.get("password","")
    u = db.query(User).filter(User.email == email).first()
    if not u or not u.is_active or not verify_pw(password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = make_access_token(u)
    return {"ok": True, "access_token": token, "role": u.role, "tenant_id": u.tenant_id, "user_id": u.user_id}

# -------------------------
# Device tokens (bind + rotate)
# -------------------------
@router.post("/device/register")
def register_device(payload: dict, claims: dict = Depends(require_access), db: Session = Depends(db_session)):
    """
    payload: { device_name }
    returns device_token
    """
    device_name = payload.get("device_name","My Device")
    device_id = str(uuid.uuid4())

    d = Device(
        device_id=device_id,
        tenant_id=claims["tenant_id"],
        user_id=claims["sub"],
        name=device_name,
        current_jti="",
        is_active=True
    )

    token = make_device_token(d)
    db.add(d)
    db.commit()

    return {"ok": True, "device_id": device_id, "device_token": token}

@router.post("/device/rotate")
def rotate_device(payload: dict, device_token: str | None = Header(default=None), db: Session = Depends(db_session)):
    """
    Header: Device-Token: <jwt>
    Returns new device_token and invalidates old by jti check.
    """
    if not device_token:
        raise HTTPException(status_code=401, detail="Missing Device-Token header")

    claims = decode_token(device_token)
    if claims.get("type") != "device":
        raise HTTPException(status_code=401, detail="Not a device token")

    device_id = claims.get("device_id")
    jti = claims.get("jti")

    d = db.query(Device).filter(Device.device_id == device_id).first()
    if not d or not d.is_active:
        raise HTTPException(status_code=401, detail="Device not found/inactive")

    # old token must match current_jti
    if d.current_jti != jti:
        raise HTTPException(status_code=401, detail="Device token already rotated/revoked")

    new_token = make_device_token(d)
    db.add(d)
    db.commit()
    return {"ok": True, "device_id": device_id, "device_token": new_token}
