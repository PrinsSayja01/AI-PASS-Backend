from fastapi import FastAPI, HTTPException, Depends
from api.device_deps import require_device_token
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from fastapi import Request
from db.audit_db import write_audit
from db.rate_limit_db import check_rate_limit
from api.kill_switch import is_blocked
import traceback
from api.auth import router as auth_router
from api.audit_api import router as audit_router
from api.rate_admin import router as rate_admin_router
from api.kill_admin import router as kill_admin_router
from api.submissions_dev import router as submissions_dev_router
from api.submissions_admin import router as submissions_admin_router
from api.tenant_install import router as tenant_install_router
from api.workflows_run import router as workflows_run_router
from api.rag_api import router as rag_router
from api.security_deps import require_access
from api.workflow_store import create_workflow, submit_workflow, list_workflows
from api.billing_ledger import record_event
from api.reviews_store import add_review, list_reviews, rating_summary
from sdk.skill_registry import SKILL_IMPLS
from registry.governance import enforce
from registry.wallet import charge_wallet
from api.wallet_api import router as wallet_router, admin_router as usage_admin_router
from api.rag_api import router as rag_router
app = FastAPI(title="AI-Pass Skills API")
app.include_router(rag_router)

app.include_router(wallet_router)
app.include_router(usage_admin_router)

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    # Return full traceback for debugging (MVP only)
    return HTTPException(status_code=500, detail=traceback.format_exc())


app.include_router(auth_router)
app.include_router(kill_admin_router)
app.include_router(submissions_dev_router)
app.include_router(submissions_admin_router)
app.include_router(tenant_install_router)
app.include_router(workflows_run_router)
# -----------------------
# Audit Middleware (logs ALL requests)
# -----------------------
JWT_SECRET = "CHANGE_ME_SUPER_SECRET"
JWT_ALG = "HS256"

# ===============================
# Audit + Rate Limit Middleware (CLEAN VERSION)
# ===============================
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from db.audit_db import write_audit
from db.rate_limit_db import check_rate_limit
from api.kill_switch import is_blocked

JWT_SECRET = "CHANGE_ME_SUPER_SECRET"
JWT_ALG = "HS256"

@app.middleware("http")
async def audit_middleware(request: Request, call_next):

    # Skip docs/static
    if request.url.path in ("/docs", "/openapi.json", "/favicon.ico"):
        return await call_next(request)

    tenant_id = "unknown"
    user_id = "unknown"
    device_id = "unknown"

    # Parse access token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            if claims.get("type") == "access":
                tenant_id = claims.get("tenant_id", tenant_id)
                user_id = claims.get("sub", user_id)
        except JWTError:
            pass

    # Parse device token
    dtok = request.headers.get("device-token", "")
    if dtok:
        try:
            dclaims = jwt.decode(dtok, JWT_SECRET, algorithms=[JWT_ALG])
            if dclaims.get("type") == "device":
                device_id = dclaims.get("device_id", device_id)
        except JWTError:
            pass

    ip = request.client.host if request.client else "unknown"
    route = request.url.path
    method = request.method

    # ===== KILL SWITCH (Emergency block) =====
    block_reason = is_blocked(tenant_id, device_id, route)
    if block_reason:
        return JSONResponse(status_code=403, content={"detail": "Blocked by kill switch", "reason": block_reason})

# ===== RATE LIMIT =====
    runtime_paths = ("/skills/", "/agents/run", "/workflows/run", "/rag/")
    if route.startswith(runtime_paths) or route in runtime_paths:
        rl = check_rate_limit(tenant_id, device_id, f"{method} {route}", cost=1)
        if not rl.get("allowed", False):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limited",
                    "reason": rl.get("reason"),
                    "retry_after": rl.get("retry_after")
                }
            )

    # ===== CALL ENDPOINT =====
    err = None
    try:
        resp = await call_next(request)
        ok = 200 <= resp.status_code < 400
        status_code = resp.status_code
        return resp
    except Exception as e:
        ok = False
        status_code = 500
        err = f"{type(e).__name__}: {e}"
        raise
    finally:
        # ===== AUDIT LOG =====
        try:
            write_audit({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "device_id": device_id,
                "ip": ip,
                "route": f"{method} {route}",
                "action": "HTTP_REQUEST",
                "target_id": route,
                "ok": ok,
                "credits": 0,
                "error": err
            })
        except Exception:
            pass

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Always return JSON for unknown 500 errors
            return JSONResponse(
        status_code=500,
        content={"detail": f"UNHANDLED: {type(exc).__name__}: {exc}"}
    )


# -----------------------
# SAFE runtime wrapper
# -----------------------
def _run_and_log_safe(skill_id: str, inp: dict, tenant_id: str):
    import time
    skill_cls = SKILL_IMPLS.get(skill_id)
    if not skill_cls:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    try:
        gov = enforce(tenant_id, skill_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    ctx = {"tenant_id": tenant_id, "version": gov.get("installed_version")}
    skill = skill_cls()

    start = time.time()
    result = skill.run(ctx, inp)
    data = result.to_dict() if hasattr(result, 'to_dict') else (result.dict() if hasattr(result, 'dict') else result.__dict__)
    data["latency_ms"] = int((time.time() - start) * 1000)

    if data.get("ok"):
        credits = int(data.get("output", {}).get("_credits", 1))
        charge_wallet(tenant_id, credits)
        data["charged_credits"] = credits
        try:
            record_event(tenant_id, skill_id, ctx.get("version","unknown"), credits, latency_ms=data["latency_ms"])
        except Exception:
            pass

    # Audit log (best-effort)
    try:
        ip = request.client.host if request and request.client else 'unknown'
        write_audit({
            'tenant_id': (claims or {}).get('tenant_id', tenant_id),
            'user_id': (claims or {}).get('sub', 'unknown'),
            'device_id': (device or {}).get('device_id', 'unknown'),
            'ip': ip,
            'route': str(request.url.path) if request else '',
            'action': 'SKILL_RUN',
            'target_id': skill_id,
            'ok': bool(data.get('ok', False)),
            'credits': int(data.get('charged_credits', 0)),
            'error': data.get('error')
        })
    except Exception:
        pass
    return data

# -----------------------
# Health
# -----------------------
@app.get("/health")
def health():
    return {"ok": True}

# -----------------------
# Skills (Tenant only)
# -----------------------
@app.post("/skills/summarize")
def summarize(inp: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    inp["tenant_id"] = claims["tenant_id"]
    return _run_and_log_safe("summarize", inp, tenant_id=claims["tenant_id"])

@app.post("/skills/translate")
def translate(inp: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    return _run_and_log_safe("translate", inp, tenant_id=claims["tenant_id"])

@app.post("/skills/clean_text")
def clean_text(inp: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    return _run_and_log_safe("clean_text", inp, tenant_id=claims["tenant_id"])

@app.post("/skills/pii_redactor")
def pii_redactor(inp: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    return _run_and_log_safe("pii_redactor", inp, tenant_id=claims["tenant_id"])

# -----------------------
# Workflows
# -----------------------
@app.post("/workflows/run")
def workflows_run(payload: dict, claims: dict = Depends(require_access), device: dict = Depends(require_device_token)):
    tenant_id = claims["tenant_id"]
    return run_marketplace_workflow(tenant_id, payload.get("workflow_id"), payload.get("inputs", {}))

# -----------------------
# Root
# -----------------------
@app.get("/")
def root():
    return {"name":"AI-Pass Skills API","status":"running","docs":"/docs"}



@app.post("/debug/summarize")
def debug_summarize(inp: dict, claims: dict = Depends(require_access)):
    try:
        inp["tenant_id"] = claims["tenant_id"]
        return _run_and_log_safe("summarize", inp, tenant_id=claims["tenant_id"])
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=False)