from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


# Create async engine with SSL enabled for Neon/cloud Postgres
# All query parameters are removed from URL in config validator to avoid conflicts
# Use NullPool to avoid connection pooling issues with parameter passing
# SSL is enabled via connect_args with boolean True (asyncpg supports this)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    poolclass=NullPool,  # Use NullPool to avoid parameter passing issues
    connect_args={
        "ssl": True,  # Enable SSL for Neon (boolean works with asyncpg)
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from app.models.lead import Lead  # noqa: F401
    from app.models.outreach_log import OutreachLog  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Run migrations to add any missing columns
    from app.db.migrations import run_migrations
    await run_migrations()

