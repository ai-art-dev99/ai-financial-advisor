from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.types import ASGIApp, Receive, Scope, Send
from prometheus_fastapi_instrumentator import Instrumentator

from database import engine, Base
from routers import portfolios, holdings, transactions, performance
from config import settings


class StripPrefixMiddleware:
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Robo-Advisor — Portfolio Service",
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

app.add_middleware(StripPrefixMiddleware, prefix="/api/v1/portfolio")

Instrumentator().instrument(app).expose(app)

app.include_router(portfolios.router,   prefix="/portfolios",   tags=["Portfolios"])
app.include_router(holdings.router,     prefix="/holdings",     tags=["Holdings"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(performance.router,  prefix="/performance",  tags=["Performance"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portfolio"}