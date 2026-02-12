from __future__ import annotations
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Device
from api.security_deps import require_access

JWT_SECRET = "CHANGE_ME_SUPER_SECRET"
JWT_ALG = "HS256"

def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_device_token(
    claims: dict = Depends(require_access),
    device_token: str | None = Header(default=None, alias="Device-Token"),
    db: Session = Depends(_db)
) -> dict:
    try:
        if not device_token:
            raise HTTPException(status_code=401, detail="Missing Device-Token header")

        # Decode device JWT
        try:
            dclaims = jwt.decode(device_token, JWT_SECRET, algorithms=[JWT_ALG])
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid device token: {e}")

        if dclaims.get("type") != "device":
            raise HTTPException(status_code=401, detail="Not a device token")

        device_id = dclaims.get("device_id")
        tenant_id = dclaims.get("tenant_id")
        jti = dclaims.get("jti")

        if not device_id or not tenant_id or not jti:
            raise HTTPException(status_code=401, detail="Malformed device token")

        # tenant must match access token
        if tenant_id != claims.get("tenant_id"):
            raise HTTPException(status_code=403, detail="Device tenant mismatch")

        # Load device from DB
        d = db.query(Device).filter(Device.device_id == device_id).first()
        if not d or not d.is_active:
            raise HTTPException(status_code=401, detail="Device not found/inactive")

        # Rotation check
        if d.current_jti != jti:
            raise HTTPException(status_code=401, detail="Device token rotated/revoked")

        return {"device_id": device_id, "tenant_id": tenant_id, "user_id": dclaims.get("user_id")}

    except HTTPException:
        raise
    except Exception as e:
        # This is the key: no hidden 500 anymore
        raise HTTPException(status_code=500, detail=f"Device guard error: {type(e).__name__}: {e}")
