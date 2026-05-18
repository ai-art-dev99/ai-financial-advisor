# 🤖 Argo — AI Financial Advisor (Robo-Advisory)

> Phase 1: Core infrastructure — Auth, Portfolio, Market Data, Dashboard

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Docker Compose                        │
│                                                             │
│  Browser / Mobile                                           │
│       ↓                                                     │
│  [ Nginx — Port 80 ]  ←── API Gateway + Load Balancer       │
│       ↓           ↓                    ↓                    │
│  [Auth:8000]  [Portfolio:8001]  [Market:8002]               │
│       ↓              ↓               ↓                      │
│  [PostgreSQL]  [PostgreSQL]   [TimescaleDB]                 │
│                                    ↑                        │
│  [Redis] ←────── [Celery Worker + Beat]                     │
│                                                             │
│  [Prometheus] → [Grafana:3001]                              │
│  [Frontend:3000]                                            │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose v2
- 4GB RAM minimum
- Ports 80, 3000, 3001, 9090 free

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_ORG/robo-advisor
cd robo-advisor
cp .env.example .env
# Edit .env with your secrets
```

### 2. Start Everything

```bash
docker compose up -d
```

Wait ~30 seconds for all services to be healthy:

```bash
docker compose ps
```

### 3. Verify

| Service        | URL                              |
|----------------|----------------------------------|
| Frontend       | http://localhost:3000            |
| Auth API docs  | http://localhost/api/v1/auth/docs|
| Portfolio docs | http://localhost/api/v1/portfolio/docs |
| Market API     | http://localhost/api/v1/market/docs |
| Grafana        | http://localhost:3001 (admin/admin123) |
| Prometheus     | http://localhost:9090            |

### 4. Seed Market Data

```bash
# Trigger first fetch manually
docker compose exec market-data \
  python -c "from tasks import fetch_quotes; fetch_quotes(['AAPL','MSFT','SPY','QQQ'])"
```

---

## 📁 Project Structure

```
robo-advisor/
├── docker-compose.yml              # Full orchestration
├── .env.example                    # Environment template
│
├── services/
│   ├── api-gateway/                # Nginx config
│   ├── auth/                       # FastAPI — JWT auth, users, risk profiles
│   │   ├── main.py
│   │   ├── models.py               # SQLAlchemy ORM
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── security.py             # JWT utilities
│   │   └── routers/
│   │       ├── auth_router.py      # /register /login /refresh /logout
│   │       └── users.py            # /me /me/risk-profile
│   │
│   ├── portfolio/                  # FastAPI — portfolios, holdings, transactions
│   │   ├── risk_engine.py          # MPT + HHI concentration analysis
│   │   └── routers/
│   │       ├── portfolios.py       # CRUD
│   │       ├── holdings.py         # Holdings + portfolio analysis
│   │       ├── transactions.py     # Transaction log
│   │       └── performance.py      # Snapshots + summary
│   │
│   ├── market-data/                # Celery + FastAPI
│   │   ├── celery_app.py           # Scheduled tasks (beat)
│   │   ├── tasks.py                # fetch_quotes, fetch_daily_bars
│   │   └── main.py                 # Quote/bar REST API
│   │
│   └── frontend/                   # React + Vite + Tailwind
│       └── src/
│           ├── pages/              # Dashboard, Portfolio, Market, RiskProfile
│           ├── components/         # Layout, shared UI
│           └── store/              # Zustand auth store
│
└── infrastructure/
    ├── postgres/                   # DB schemas + init scripts
    ├── prometheus/                 # Metrics config
    └── aws/                        # ECS task definitions
```

---

## 🔌 API Reference

### Auth Service (`/api/v1/auth/`)

```http
POST /auth/register        Register new user
POST /auth/login           Login → access + refresh tokens
POST /auth/refresh         Rotate refresh token
POST /auth/logout          Revoke refresh token
GET  /users/me             Get current user
POST /users/me/risk-profile Save risk questionnaire
GET  /users/me/risk-profile Get risk profile
```

### Portfolio Service (`/api/v1/portfolio/`)

```http
GET  /portfolios/                  List user portfolios
POST /portfolios/                  Create portfolio
GET  /portfolios/{id}              Get portfolio
GET  /holdings/{id}/holdings       List holdings
POST /holdings/{id}/holdings       Add/update holding
GET  /holdings/{id}/analysis       Risk analysis + rebalancing signals
GET  /transactions/{id}/transactions  Transaction history
POST /transactions/{id}/transactions  Record transaction
GET  /performance/{id}/summary     Performance summary
GET  /performance/{id}/snapshots   Daily snapshots
```

### Market Data Service (`/api/v1/market/`)

```http
GET  /quotes?symbols=AAPL,MSFT    Latest quotes (batch)
GET  /quotes/{symbol}              Single quote
GET  /bars/{symbol}?interval=1d   OHLCV bars
POST /fetch/{symbol}               Trigger manual fetch
```

---

## ⚙️ Development

### Run a single service locally

```bash
# Auth service
cd services/auth
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd services/frontend
npm install
npm run dev
```

### View Celery tasks

```bash
docker compose logs -f market-data
docker compose exec market-data celery -A celery_app inspect active
```

### Database migrations

```bash
# Auth
docker compose exec auth alembic revision --autogenerate -m "add_column"
docker compose exec auth alembic upgrade head
```

---

## ☁️ Production Deploy (AWS)

### 1. Provision infrastructure

```bash
# RDS PostgreSQL
aws rds create-db-instance --db-instance-identifier robo-postgres ...

# ElastiCache Redis
aws elasticache create-cache-cluster --cache-cluster-id robo-redis ...
```

### 2. Store secrets in AWS Secrets Manager

```bash
aws secretsmanager create-secret --name robo/jwt-secret --secret-string "YOUR_SECRET"
aws secretsmanager create-secret --name robo/auth-db-url --secret-string "postgresql+asyncpg://..."
```

### 3. Register ECS tasks and push images

```bash
# Build and push
docker build -t ghcr.io/YOUR_ORG/robo-advisor-auth:latest services/auth/
docker push ghcr.io/YOUR_ORG/robo-advisor-auth:latest

# Register task
aws ecs register-task-definition --cli-input-json file://infrastructure/aws/ecs-tasks.json
```

### 4. GitHub Actions auto-deploys on push to `main`

---

## 🗺️ Roadmap

- **Phase 1** ✅ Auth, Portfolio, Market Data, Dashboard
- **Phase 2** — AI Advisor (LLM + RAG), Sentiment Analysis
- **Phase 3** — HuggingFace deploy, advanced rebalancing, notifications
