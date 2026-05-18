import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from asgi_lifespan import LifespanManager
from unittest.mock import patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

with patch.dict(os.environ, {
    "DATABASE_URL": TEST_DB_URL,
    "TIMESCALE_URL": TEST_DB_URL,
    "JWT_SECRET_KEY": "test-secret",
}):
    from main import app
    from database import Base, get_db
    import security


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL, echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[security.get_current_user_id] = lambda: TEST_USER_ID

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def portfolio(client):
    resp = await client.post("/portfolios/", json={
        "name": "Test Portfolio",
        "description": "My test portfolio",
        "currency": "USD",
    })
    assert resp.status_code == 201
    return resp.json()