from fastapi import APIRouter, BackgroundTasks

from app.db.session import AsyncSessionLocal
from app.services.outreach import run_outreach_batch


router = APIRouter(tags=["outreach"])


async def _run_outreach_background() -> None:
    async with AsyncSessionLocal() as db:
        await run_outreach_batch(db)


@router.post("/run-outreach")
async def run_outreach(background_tasks: BackgroundTasks) -> dict:
    """
    Trigger an outreach batch in the background.

    - Picks up to 25 leads with status=new.
    - Generates emails via Gemini.
    - Sends via Gmail SMTP with 45s delay between sends.
    """
    background_tasks.add_task(_run_outreach_background)
    return {"detail": "Outreach batch started in background"}

