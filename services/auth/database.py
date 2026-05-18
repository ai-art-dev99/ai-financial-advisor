from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from config import settings

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