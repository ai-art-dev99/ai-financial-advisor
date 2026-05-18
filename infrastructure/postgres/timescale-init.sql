-- TimescaleDB market data schema
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- OHLCV price data
CREATE TABLE IF NOT EXISTS price_bars (
    time        TIMESTAMPTZ NOT NULL,
    symbol      VARCHAR(20) NOT NULL,
    open        NUMERIC(14,4),
    high        NUMERIC(14,4),
    low         NUMERIC(14,4),
    close       NUMERIC(14,4),
    volume      BIGINT,
    interval    VARCHAR(5) NOT NULL DEFAULT '1d'  -- 1m,5m,1h,1d
);

SELECT create_hypertable('price_bars', 'time', if_not_exists => TRUE);

-- Latest quotes cache
CREATE TABLE IF NOT EXISTS latest_quotes (
    symbol          VARCHAR(20) PRIMARY KEY,
    price           NUMERIC(14,4),
    change_abs      NUMERIC(10,4),
    change_pct      NUMERIC(8,4),
    volume          BIGINT,
    market_cap      BIGINT,
    pe_ratio        NUMERIC(8,2),
    week_52_high    NUMERIC(14,4),
    week_52_low     NUMERIC(14,4),
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Asset metadata
CREATE TABLE IF NOT EXISTS asset_info (
    symbol          VARCHAR(20) PRIMARY KEY,
    name            VARCHAR(200),
    sector          VARCHAR(100),
    industry        VARCHAR(100),
    asset_type      VARCHAR(20),
    exchange        VARCHAR(20),
    currency        VARCHAR(3) DEFAULT 'USD',
    country         VARCHAR(50),
    description     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_price_bars_symbol ON price_bars(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_price_bars_interval ON price_bars(interval, time DESC);

-- Continuous aggregate: daily summary
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_ohlcv
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    symbol,
    first(open, time)   AS open,
    max(high)           AS high,
    min(low)            AS low,
    last(close, time)   AS close,
    sum(volume)         AS volume
FROM price_bars
WHERE interval = '1h'
GROUP BY day, symbol
WITH NO DATA;
