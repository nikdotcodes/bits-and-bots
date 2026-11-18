from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers.auth import router as auth_router
from .routers.public import router as public_router
from .routers.volunteers import router as volunteers_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Bits and Bots Code Club", docs_url=None, redoc_url=None, lifespan=lifespan
)
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)
app.include_router(auth_router)
app.include_router(volunteers_router)
app.include_router(public_router)
