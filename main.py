from contextlib import asynccontextmanager, suppress
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api.routes.import_leads import router as import_leads_router
from app.api.routes.leads import router as leads_router
from app.api.routes.outreach import router as outreach_router
from app.api.routes.outreach_logs import router as outreach_logs_router
from app.api.routes.follow_ups import router as follow_ups_router
from app.api.routes.activity_log import router as activity_log_router
from app.api.routes.stats import router as stats_router
from app.api.routes.test_email import router as test_email_router
from app.api.routes.users import router as users_router
from app.api.routes.google_auth import router as google_auth_router
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, init_db
from app.services.imap_watcher import process_imap_replies
from app.services.follow_up import process_scheduled_follow_ups


settings = get_settings()

# Initialize Sentry error tracking if DSN is provided
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        environment=os.getenv("ENVIRONMENT", "production"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema
    await init_db()

    stop_event = asyncio.Event()

    async def imap_loop() -> None:
        while not stop_event.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    await process_imap_replies(db)
            except Exception:
                # TODO: add proper logging
                pass
            await asyncio.sleep(settings.imap_poll_interval_seconds)

    async def follow_up_loop() -> None:
        """Check for scheduled follow-ups every hour."""
        while not stop_event.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    await process_scheduled_follow_ups(db)
            except Exception:
                # TODO: add proper logging
                pass
            await asyncio.sleep(3600)  # Check every hour

    imap_task = asyncio.create_task(imap_loop())
    follow_up_task = asyncio.create_task(follow_up_loop())
    try:
        yield
    finally:
        stop_event.set()
        imap_task.cancel()
        follow_up_task.cancel()
        with suppress(asyncio.CancelledError):
            await imap_task
            await follow_up_task


app = FastAPI(title="AI Outreach Automation", lifespan=lifespan)

# Add CORS middleware to allow frontend to connect
# Get allowed origins from environment or use defaults
import os
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ai-automation-front.vercel.app",
    "https://ai-automation-front.onrender.com",
]

# Add any additional origins from environment variable
if os.getenv("ALLOWED_ORIGINS"):
    allowed_origins.extend(os.getenv("ALLOWED_ORIGINS").split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"status": "ok"}


app.include_router(import_leads_router)
app.include_router(leads_router)
app.include_router(outreach_router)
app.include_router(outreach_logs_router)
app.include_router(follow_ups_router)
app.include_router(activity_log_router)
app.include_router(stats_router)
app.include_router(test_email_router)
app.include_router(users_router)
app.include_router(google_auth_router)
