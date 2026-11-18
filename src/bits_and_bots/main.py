"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import os
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import BASE_URL, IS_PRODUCTION, validate_config
from .csrf import CSRFSecurityMiddleware
from .routers.auth import router as auth_router
from .routers.public import router as public_router
from .routers.volunteers import router as volunteers_router

logger = logging.getLogger("bits_and_bots")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if IS_PRODUCTION:
        validate_config()
    yield


app = FastAPI(
    title="Bits and Bots Code Club",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(CSRFSecurityMiddleware)
if IS_PRODUCTION:
    from urllib.parse import urlparse
    host = urlparse(BASE_URL).hostname
    allowed = [host] if host else []
    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if render_host:
        allowed.append(render_host)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed or ["localhost"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_id)
        else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if request.url.path.startswith("/volunteers"):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    from .database import db
    try:
        with db() as client:
            client.table("volunteers").select("id").limit(1).execute()
        return {"status": "ready"}
    except Exception:
        logger.exception("Readiness check failed")
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "not_ready"}, status_code=503)


app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)
app.include_router(auth_router)
app.include_router(volunteers_router)
app.include_router(public_router)
