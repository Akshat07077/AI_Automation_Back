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
# SSL is conditionally enabled - only for cloud databases (detected by hostname)
import os
database_url_lower = settings.database_url.lower()

# Detect cloud databases by hostname
is_neon = "neon.tech" in database_url_lower or "neon" in database_url_lower
is_cloud_db = any(host in database_url_lower for host in [
    "neon.tech", "render.com", "supabase.co", "aws.amazon.com", 
    "azure.com", "cloud.google.com", "digitalocean.com", "railway.app",
    "fly.io", "heroku.com", "planetscale.com"
])

# Detect local databases
is_local = any(host in database_url_lower for host in [
    "localhost", "127.0.0.1", "0.0.0.0", "::1"
])

# Debug: Print connection info
print(f"Database Connection Info:")
print(f"   URL (masked): {settings.database_url[:50]}...")
print(f"   Is Local: {is_local}")
print(f"   Is Cloud: {is_cloud_db}")
print(f"   Is Neon: {is_neon}")

# For local databases, explicitly disable SSL; for cloud, use SSL
# asyncpg expects: False (no SSL), True (require SSL), or SSLContext
# Neon specifically requires SSL but may need 'require' mode
if is_local:
    connect_args = {"ssl": False}  # Explicitly disable SSL for local databases
    print(f"   SSL: Disabled (local database)")
elif is_neon:
    # Neon requires SSL - try with SSL context for better compatibility
    import ssl
    ssl_context = ssl.create_default_context()
    connect_args = {"ssl": ssl_context}
    print(f"   SSL: Enabled with SSL context (Neon database)")
elif is_cloud_db:
    connect_args = {"ssl": True}  # Require SSL for cloud databases
    print(f"   SSL: Enabled (cloud database)")
else:
    # Default: try without SSL first
    connect_args = {"ssl": False}
    print(f"   SSL: Disabled (default)")

# Add connection timeout to connect_args for asyncpg
if "timeout" not in connect_args:
    connect_args["command_timeout"] = 10  # 10 second timeout for queries

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    poolclass=NullPool,  # Use NullPool to avoid parameter passing issues
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using
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
    from app.models.user import User  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Run migrations to add any missing columns
        from app.db.migrations import run_migrations
        await run_migrations()
        print("Database initialized successfully")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"Database initialization failed:")
        print(f"   Error Type: {error_type}")
        print(f"   Error: {error_msg}")
        print()
        print("Troubleshooting:")
        print("1. Check DATABASE_URL is correct")
        print("2. Verify database credentials")
        print("3. Ensure database is accessible (not paused)")
        print("4. Check network/firewall settings")
        print("5. For Neon: Verify connection string from dashboard")
        raise

