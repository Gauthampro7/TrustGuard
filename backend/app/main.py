"""
TrustGuard Core Application Entry Point
Track 01 PS-02: AI for Digital Trust
FastAPI server prepared for local execution (<150ms latency target).
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .api.routes import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up CORS middleware for browser extension and local web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"chrome-extension://[a-p]{32}",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
app.mount("/dashboard", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True), name="dashboard")


class BoundedBodyMiddleware:
    """Enforce the limit for chunked bodies before JSON materializes large sample arrays."""
    def __init__(self, app, maximum=8 * 1024 * 1024):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        parts, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > self.maximum:
                return await JSONResponse({"detail": "Request exceeds the 8 MiB transient sample limit"}, status_code=413)(scope, receive, send)
            parts.append(body)
            if not message.get("more_body", False):
                break
        body = b"".join(parts)
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, bounded_receive, send)


app.add_middleware(BoundedBodyMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, error):
    # Do not echo submitted media samples through validation error responses.
    details = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


@app.get("/", tags=["Root"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/dashboard/simple.html", status_code=307)
    return {
        "service": "TrustGuard Digital Trust Engine",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "dashboard": "/dashboard/simple.html",
        "workbench": "/dashboard/index.html",
        "status": "ready_for_inspection"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
