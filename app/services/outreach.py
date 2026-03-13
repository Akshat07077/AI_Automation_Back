import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.follow_up import schedule_initial_follow_up
from app.services.gemini_email import generate_outreach_email
from app.services.gmail_email import send_gmail_email


MAX_BATCH_SIZE = 25
DELAY_SECONDS = 45


async def run_outreach_batch(db: AsyncSession) -> dict:
    """
    Fetch leads, send emails via Gmail API with user-defined delay,
    update statuses and logs.
    """
    # Fetch user for Gmail credentials and limits
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_first()
    
    if not user or not user.gmail_access_token:
        return {"error": "Gmail not connected. Please connect Gmail in Settings."}

    # Use user-defined limits or defaults
    batch_size = getattr(user, "daily_send_limit", 25)
    delay_seconds = getattr(user, "delay_between_emails_seconds", 60)

    result = await db.execute(
        select(Lead)
        .where(Lead.status == LeadStatus.NEW)
        .order_by(Lead.created_at)
        .limit(batch_size)
    )
    leads: list[Lead] = list(result.scalars().all())

    sent_count = 0
    for idx, lead in enumerate(leads):
        subject, body = generate_outreach_email(lead)
        
        # Send via Gmail API
        message_id = send_gmail_email(user, lead.email, subject, body)

        lead.status = LeadStatus.SENT
        lead.last_contacted = datetime.now(timezone.utc)
        db.add(
            OutreachLog(
                lead_id=lead.id,
                event_type=OutreachEventType.SENT,
                email_subject=subject,
                email_body=body,
                message_id=message_id,
            )
        )
        await db.commit()
        
        # Schedule first follow-up
        await schedule_initial_follow_up(lead, db)
        
        sent_count += 1

        # Delay between sends
        if idx < len(leads) - 1:
            await asyncio.sleep(delay_seconds)

    return {"sent": sent_count}

