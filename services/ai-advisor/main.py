from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.types import ASGIApp, Receive, Scope, Send
from prometheus_fastapi_instrumentator import Instrumentator

from config import settings
from rag.ingestor import DocumentIngestor
from routers import chat, ingest


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
    ingestor = DocumentIngestor()
    await ingestor.ensure_collections()
    yield


app = FastAPI(
    title="Robo-Advisor — AI Advisor Service",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(StripPrefixMiddleware, prefix="/api/v1/ai")

Instrumentator().instrument(app).expose(app)

app.include_router(chat.router,   prefix="/chat",   tags=["Chat"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-advisor", "model": settings.anthropic_model}