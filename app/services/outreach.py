import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadStatus
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.follow_up import schedule_initial_follow_up
from app.services.gemini_email import generate_outreach_email
from app.services.smtp_email import send_email


MAX_BATCH_SIZE = 25
DELAY_SECONDS = 45


async def run_outreach_batch(db: AsyncSession) -> dict:
    """
    Fetch up to 25 new leads, send emails with 45s delay between each,
    update statuses and logs.
    """
    result = await db.execute(
        select(Lead)
        .where(Lead.status == LeadStatus.NEW)
        .order_by(Lead.created_at)
        .limit(MAX_BATCH_SIZE)
    )
    leads: list[Lead] = list(result.scalars().all())

    sent_count = 0
    for idx, lead in enumerate(leads):
        subject, body = generate_outreach_email(lead)
        message_id = send_email(lead.email, subject, body)

        lead.status = LeadStatus.SENT
        lead.last_contacted = datetime.now(timezone.utc)
        db.add(
            OutreachLog(
                lead_id=lead.id,
                event_type=OutreachEventType.SENT,
                email_subject=subject,
                email_body=body,  # Store full email body for reference
                message_id=message_id,  # Store Message-ID for reply threading
            )
        )
        await db.commit()
        
        # Schedule first follow-up
        await schedule_initial_follow_up(lead, db)
        
        sent_count += 1

        # Delay between sends, except after the last one
        if idx < len(leads) - 1:
            await asyncio.sleep(DELAY_SECONDS)

    return {"sent": sent_count}

