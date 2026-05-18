from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from database import engine, Base
from routers import portfolios, holdings, transactions, performance
from config import settings


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

Instrumentator().instrument(app).expose(app)

app.include_router(portfolios.router,   prefix="/portfolios",   tags=["Portfolios"])
app.include_router(holdings.router,     prefix="/holdings",     tags=["Holdings"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(performance.router,  prefix="/performance",  tags=["Performance"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portfolio"}