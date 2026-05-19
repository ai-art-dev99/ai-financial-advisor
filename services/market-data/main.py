from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras
import os


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


app = FastAPI(title="Robo-Advisor — Market Data Service", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(StripPrefixMiddleware, prefix="/api/v1/market")

DB_URL = os.getenv("TIMESCALE_URL", "postgresql://robo_user:password@timescale:5432/robo_market")


def get_conn():
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


class QuoteResponse(BaseModel):
    symbol: str
    price: Optional[float]
    change_abs: Optional[float]
    change_pct: Optional[float]
    volume: Optional[int]
    fetched_at: Optional[datetime]


class PriceBar(BaseModel):
    time: datetime
    symbol: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]


@app.get("/health")
def health():
    return {"status": "ok", "service": "market-data"}


@app.get("/quotes", response_model=List[QuoteResponse])
def get_quotes(symbols: str = Query(...)):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM latest_quotes WHERE symbol = ANY(%s)", (symbol_list,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [QuoteResponse(**row) for row in rows]


@app.get("/quotes/{symbol}", response_model=QuoteResponse)
def get_quote(symbol: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM latest_quotes WHERE symbol = %s", (symbol.upper(),))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(404, f"No quote for {symbol}")
    return QuoteResponse(**row)


@app.get("/bars/{symbol}", response_model=List[PriceBar])
def get_bars(symbol: str, interval: str = Query("1d"), limit: int = Query(100, le=1000)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT time, symbol, open, high, low, close, volume FROM price_bars WHERE symbol = %s AND interval = %s ORDER BY time DESC LIMIT %s",
        (symbol.upper(), interval, limit)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [PriceBar(**row) for row in rows]


@app.post("/fetch/{symbol}")
def trigger_fetch(symbol: str):
    from tasks import fetch_quotes
    task = fetch_quotes.delay([symbol.upper()])
    return {"task_id": task.id, "symbol": symbol.upper(), "status": "queued"}