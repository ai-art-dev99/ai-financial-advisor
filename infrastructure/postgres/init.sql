-- ═══════════════════════════════════════════════════════════════
--  robo_auth database schema
-- ═══════════════════════════════════════════════════════════════
\c robo_auth;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    full_name     VARCHAR(255) NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    is_verified   BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Refresh tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked    BOOLEAN DEFAULT FALSE
);

-- User risk profiles
CREATE TABLE IF NOT EXISTS risk_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    risk_score          SMALLINT CHECK (risk_score BETWEEN 1 AND 10),
    risk_category       VARCHAR(20) CHECK (risk_category IN ('conservative','moderate','aggressive')),
    investment_horizon  SMALLINT,   -- months
    monthly_income      NUMERIC(14,2),
    investable_assets   NUMERIC(14,2),
    questionnaire_data  JSONB DEFAULT '{}',
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ═══════════════════════════════════════════════════════════════
--  robo_portfolio database schema
-- ═══════════════════════════════════════════════════════════════
\c robo_portfolio;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    currency        VARCHAR(3) DEFAULT 'USD',
    target_return   NUMERIC(5,4),     -- e.g. 0.0850 = 8.5%
    max_drawdown    NUMERIC(5,4),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio holdings (current snapshot)
CREATE TABLE IF NOT EXISTS holdings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol          VARCHAR(20) NOT NULL,
    asset_type      VARCHAR(20) CHECK (asset_type IN ('stock','etf','crypto','bond','cash')),
    quantity        NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_cost        NUMERIC(14,4),
    target_weight   NUMERIC(5,4),    -- desired allocation e.g. 0.25 = 25%
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (portfolio_id, symbol)
);

-- Transactions log
CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol          VARCHAR(20) NOT NULL,
    tx_type         VARCHAR(10) CHECK (tx_type IN ('buy','sell','dividend','deposit','withdraw')),
    quantity        NUMERIC(20,8),
    price           NUMERIC(14,4),
    total_amount    NUMERIC(14,4),
    fee             NUMERIC(10,4) DEFAULT 0,
    notes           TEXT,
    executed_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Rebalancing history
CREATE TABLE IF NOT EXISTS rebalancing_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    trigger_type    VARCHAR(20) CHECK (trigger_type IN ('scheduled','threshold','manual')),
    status          VARCHAR(20) CHECK (status IN ('pending','completed','failed')),
    drift_before    JSONB,
    drift_after     JSONB,
    trades          JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Portfolio performance snapshots (daily)
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    total_value     NUMERIC(16,4),
    cash_value      NUMERIC(16,4),
    daily_return    NUMERIC(8,6),
    total_return    NUMERIC(8,6),
    UNIQUE (portfolio_id, snapshot_date)
);

CREATE INDEX idx_portfolios_user ON portfolios(user_id);
CREATE INDEX idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX idx_transactions_portfolio ON transactions(portfolio_id);
CREATE INDEX idx_transactions_executed ON transactions(executed_at DESC);
CREATE INDEX idx_performance_portfolio ON performance_snapshots(portfolio_id, snapshot_date DESC);
