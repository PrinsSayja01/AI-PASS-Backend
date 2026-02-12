from __future__ import annotations
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from api.config import JWT_SECRET, JWT_ALG

def require_access(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    if data.get("type") != "access":
        raise HTTPException(status_code=401, detail="Not an access token")
    return data

def require_role(role: str):
    def _dep(claims: dict = Depends(require_access)) -> dict:
        if claims.get("role") != role:
            raise HTTPException(status_code=403, detail=f"Requires role={role}")
        return claims
    return _dep
