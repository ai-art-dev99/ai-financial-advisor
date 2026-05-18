from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from config import settings
from rag.ingestor import DocumentIngestor
from routers import chat, ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise ChromaDB collections
    ingestor = DocumentIngestor()
    await ingestor.ensure_collections()
    yield


app = FastAPI(
    title="Robo-Advisor — AI Advisor Service",
    description="LLM + RAG powered financial advisor using Anthropic Claude",
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

Instrumentator().instrument(app).expose(app)

app.include_router(chat.router,   prefix="/chat",   tags=["Chat"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-advisor", "model": settings.anthropic_model}