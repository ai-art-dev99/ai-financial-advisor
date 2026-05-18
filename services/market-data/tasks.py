"""
Market Data Celery Tasks
Fetches OHLCV data, quotes, and asset info via yfinance.
"""
import logging
from datetime import datetime, timezone
from typing import List

import pandas as pd
import psycopg2
import os

from celery_app import app

logger = logging.getLogger(__name__)

DB_URL = os.getenv("TIMESCALE_URL", "postgresql://robo_user:password@timescale:5432/robo_market")


def get_conn():
    # Convert SQLAlchemy URL to psycopg2 format
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)


# ─── Tasks ─────────────────────────────────────────────────────


@app.task(name="tasks.fetch_quotes", bind=True, max_retries=3)
def fetch_quotes(self, symbols: List[str]):
    """Fetch latest quotes and update latest_quotes table"""
    import yfinance as yf

    try:
        logger.info(f"Fetching quotes for {symbols}")
        tickers = yf.Tickers(" ".join(symbols))

        conn = get_conn()
        cur = conn.cursor()

        for symbol in symbols:
            try:
                ticker = tickers.tickers.get(symbol)
                if not ticker:
                    continue

                info = ticker.fast_info
                price = getattr(info, "last_price", None)
                prev_close = getattr(info, "previous_close", None)

                if not price:
                    continue

                change_abs = round(price - prev_close, 4) if prev_close else None
                change_pct = round((change_abs / prev_close) * 100, 4) if prev_close and change_abs else None

                cur.execute("""
                    INSERT INTO latest_quotes
                        (symbol, price, change_abs, change_pct, volume, fetched_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        price = EXCLUDED.price,
                        change_abs = EXCLUDED.change_abs,
                        change_pct = EXCLUDED.change_pct,
                        volume = EXCLUDED.volume,
                        fetched_at = EXCLUDED.fetched_at
                """, (symbol, price, change_abs, change_pct,
                      getattr(info, "three_month_average_volume", None),
                      datetime.now(timezone.utc)))

            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Updated quotes for {len(symbols)} symbols")

    except Exception as exc:
        logger.error(f"fetch_quotes failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@app.task(name="tasks.fetch_daily_bars", bind=True, max_retries=3)
def fetch_daily_bars(self, symbols: List[str], period: str = "1mo"):
    """Fetch daily OHLCV bars and insert into price_bars hypertable"""
    import yfinance as yf

    try:
        logger.info(f"Fetching daily bars for {symbols}")

        conn = get_conn()
        cur = conn.cursor()
        rows_inserted = 0

        for symbol in symbols:
            try:
                df = yf.download(symbol, period=period, interval="1d",
                                 auto_adjust=True, progress=False)

                if df.empty:
                    continue

                for ts, row in df.iterrows():
                    cur.execute("""
                        INSERT INTO price_bars (time, symbol, open, high, low, close, volume, interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, '1d')
                        ON CONFLICT DO NOTHING
                    """, (
                        ts.to_pydatetime().replace(tzinfo=timezone.utc),
                        symbol,
                        float(row["Open"]) if not pd.isna(row["Open"]) else None,
                        float(row["High"]) if not pd.isna(row["High"]) else None,
                        float(row["Low"]) if not pd.isna(row["Low"]) else None,
                        float(row["Close"]) if not pd.isna(row["Close"]) else None,
                        int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
                    ))
                    rows_inserted += 1

            except Exception as e:
                logger.warning(f"Failed to fetch bars for {symbol}: {e}")

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Inserted {rows_inserted} price bars")

    except Exception as exc:
        logger.error(f"fetch_daily_bars failed: {exc}")
        raise self.retry(exc=exc, countdown=120)


@app.task(name="tasks.update_asset_info", bind=True, max_retries=2)
def update_asset_info(self, symbols: List[str]):
    """Update static asset metadata"""
    import yfinance as yf

    try:
        conn = get_conn()
        cur = conn.cursor()

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                cur.execute("""
                    INSERT INTO asset_info
                        (symbol, name, sector, industry, asset_type, exchange, currency, country, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        name = EXCLUDED.name,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        updated_at = EXCLUDED.updated_at
                """, (
                    symbol,
                    info.get("longName") or info.get("shortName"),
                    info.get("sector"),
                    info.get("industry"),
                    info.get("quoteType", "").lower(),
                    info.get("exchange"),
                    info.get("currency", "USD"),
                    info.get("country"),
                    datetime.now(timezone.utc),
                ))

            except Exception as e:
                logger.warning(f"Failed to update info for {symbol}: {e}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)
