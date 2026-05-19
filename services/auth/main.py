from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.types import ASGIApp, Receive, Scope, Send
from prometheus_fastapi_instrumentator import Instrumentator

from database import engine, Base, create_databases_if_not_exist
from routers import users, auth_router
from config import settings


class StripPrefixMiddleware:
    """Strips ALB path prefix before routing — ALB doesn't strip paths like nginx does."""
    def __init__(self, app: ASGIApp, prefix: str):
        self.app = app
        self.prefix = prefix.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path.startswith(self.prefix):
                new_path = path[len(self.prefix):] or "/"
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode()
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_databases_if_not_exist()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Robo-Advisor — Auth Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Strip /api/v1/auth prefix that ALB forwards
app.add_middleware(StripPrefixMiddleware, prefix="/api/v1/auth")

Instrumentator().instrument(app).expose(app)

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router,      prefix="/users", tags=["Users"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}