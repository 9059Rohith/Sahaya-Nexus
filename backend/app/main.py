from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import engine
from .routes import (
    auth,
    discovery,
    messages,
    notifications,
    operations,
    organizations,
    requests,
    safety,
    speech,
    volunteers,
)
from .services.rate_limit import (
    InvalidProxyIdentity,
    RateLimitUnavailable,
    permitted,
    shared_limiter_status,
)

app = FastAPI(
    title="Sahaya Nexus API",
    version="1.0.0",
    description="Open public need to verified action and measurable impact",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(discovery.router)
app.include_router(notifications.router)
app.include_router(safety.router)
app.include_router(speech.router)
app.include_router(volunteers.router)
app.include_router(requests.router)
app.include_router(messages.router)
app.include_router(organizations.router)
app.include_router(operations.router)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    codes = {
        400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
        404: "NOT_FOUND", 409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR", 429: "RATE_LIMITED", 503: "SERVICE_UNAVAILABLE",
    }
    message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": codes.get(exc.status_code, f"HTTP_{exc.status_code}"), "message": message}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Check the submitted fields",
                "details": errors,
            }
        },
    )


@app.middleware("http")
async def headers(request: Request, call_next):
    try:
        allowed = permitted(request)
    except InvalidProxyIdentity:
        return JSONResponse(status_code=403, content={"error": {"code": "FORBIDDEN", "message": "Request must come through the secure web proxy."}})
    except RateLimitUnavailable:
        return JSONResponse(status_code=503, content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Request protection is temporarily unavailable. Please try again shortly."}}, headers={"Retry-After": "30"})
    if not allowed:
        return JSONResponse(status_code=429, content={"error": {"code": "RATE_LIMITED", "message": "Too many requests. Please try again shortly."}}, headers={"Retry-After": "60"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )
    return response


@app.get("/api/v1/health", tags=["health"])
def health():
    try:
        with Session(engine) as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "unavailable",
                "ai_provider": "rule_based",
            },
        )
    limiter = shared_limiter_status()
    status = "degraded" if limiter == "unavailable" else "ok"
    payload = {"status": status, "database": "available", "rate_limit": limiter, "ai_provider": "rule_based", "mode": settings.app_mode}
    return JSONResponse(status_code=503 if status == "degraded" else 200, content=payload)
