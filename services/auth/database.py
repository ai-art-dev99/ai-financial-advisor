from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from config import settings
import asyncpg
import asyncio
import logging

logger = logging.getLogger(__name__)

_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_is_sqlite = _url.startswith("sqlite")

engine = create_async_engine(
    _url,
    echo=settings.environment == "development",
    **({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    } if _is_sqlite else {
        "pool_size": 10,
        "max_overflow": 20,
    })
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def create_databases_if_not_exist():
    """Create required databases if they don't exist (runs on startup)"""
    if _is_sqlite:
        return

    try:
        # Parse connection info from URL
        # postgresql+asyncpg://user:pass@host:port/dbname
        url = settings.database_url
        url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
        userpass, hostdb = url.split("@")
        user, password = userpass.split(":")
        hostport, _ = hostdb.split("/")
        if ":" in hostport:
            host, port = hostport.split(":")
            port = int(port)
        else:
            host, port = hostport, 5432

        # Connect to postgres default db and create missing databases
        conn = await asyncpg.connect(
            host=host, port=port,
            user=user, password=password,
            database="robo_auth"
        )

        databases = ["robo_portfolio"]
        for db in databases:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname=$1", db
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db}"')
                logger.info(f"Created database: {db}")
            else:
                logger.info(f"Database already exists: {db}")

        await conn.close()
    except Exception as e:
        logger.warning(f"Could not create databases: {e}")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()