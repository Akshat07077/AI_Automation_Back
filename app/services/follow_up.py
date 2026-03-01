import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadStatus
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.follow_up_email import generate_follow_up_email
from app.services.smtp_email import send_email


# Follow-up schedule: days to wait before each follow-up
FOLLOW_UP_SCHEDULE = {
    1: 4,  # First follow-up after 4 days
    2: 7,  # Second follow-up after 7 days (11 days total)
    3: 10,  # Third follow-up after 10 days (21 days total)
}
MAX_FOLLOW_UPS = 3


async def send_follow_up(lead: Lead, db: AsyncSession) -> dict:
    """
    Send a follow-up email to a lead as a reply to the original email.
    Returns dict with success status and details.
    """
    follow_up_number = lead.follow_up_count + 1
    
    if follow_up_number > MAX_FOLLOW_UPS:
        return {
            "success": False,
            "message": f"Maximum follow-ups ({MAX_FOLLOW_UPS}) already sent"
        }
    
    try:
        # Find the original SENT email to get its Message-ID for threading
        original_log_result = await db.execute(
            select(OutreachLog)
            .where(
                and_(
                    OutreachLog.lead_id == lead.id,
                    OutreachLog.event_type == OutreachEventType.SENT,
                )
            )
            .order_by(OutreachLog.timestamp.asc())
            .limit(1)
        )
        original_log = original_log_result.scalar_one_or_none()
        
        if not original_log or not original_log.message_id:
            return {
                "success": False,
                "message": "Original email not found or missing Message-ID. Cannot send reply."
            }
        
        # Generate follow-up email
        subject, body = generate_follow_up_email(lead, follow_up_number)
        
        # Send email as a reply to the original
        # Use the original subject (will get "Re: " prefix automatically)
        original_subject = original_log.email_subject or subject
        send_email(
            lead.email,
            original_subject,  # Use original subject for threading
            body,
            in_reply_to=original_log.message_id,
            references=original_log.message_id,
        )
        
        # Update lead
        lead.follow_up_count = follow_up_number
        lead.last_contacted = datetime.now(timezone.utc)
        
        # Calculate next follow-up date
        if follow_up_number < MAX_FOLLOW_UPS:
            days_to_wait = FOLLOW_UP_SCHEDULE.get(follow_up_number + 1, 10)
            lead.next_follow_up_date = datetime.now(timezone.utc) + timedelta(days=days_to_wait)
        else:
            lead.next_follow_up_date = None  # No more follow-ups
        
        # Log the follow-up
        db.add(
            OutreachLog(
                lead_id=lead.id,
                event_type=OutreachEventType.FOLLOW_UP,
                email_subject=f"Re: {original_subject}",  # Store with Re: prefix
                email_body=body,
            )
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Follow-up #{follow_up_number} sent successfully as reply",
            "follow_up_number": follow_up_number,
        }
        
    except Exception as e:
        await db.rollback()
        return {
            "success": False,
            "message": f"Failed to send follow-up: {str(e)}"
        }


async def process_scheduled_follow_ups(db: AsyncSession) -> dict:
    """
    Check for leads that need follow-ups and send them.
    Returns dict with counts of processed follow-ups.
    """
    now = datetime.now(timezone.utc)
    
    # Find leads that:
    # 1. Have status SENT (not replied, not bounced)
    # 2. Have a next_follow_up_date that is today or in the past
    # 3. Haven't exceeded max follow-ups
    result = await db.execute(
        select(Lead)
        .where(
            and_(
                Lead.status == LeadStatus.SENT,
                Lead.next_follow_up_date <= now,
                Lead.follow_up_count < MAX_FOLLOW_UPS,
            )
        )
        .order_by(Lead.next_follow_up_date)
        .limit(25)  # Process max 25 at a time
    )
    
    leads = list(result.scalars().all())
    
    sent_count = 0
    error_count = 0
    
    for idx, lead in enumerate(leads):
        result = await send_follow_up(lead, db)
        
        if result["success"]:
            sent_count += 1
        else:
            error_count += 1
        
        # Delay between sends (45 seconds)
        if idx < len(leads) - 1:
            await asyncio.sleep(45)
    
    return {
        "processed": len(leads),
        "sent": sent_count,
        "errors": error_count,
    }


async def schedule_initial_follow_up(lead: Lead, db: AsyncSession) -> None:
    """
    Schedule the first follow-up after the initial email is sent.
    Called from the outreach service after sending initial email.
    """
    lead.next_follow_up_date = datetime.now(timezone.utc) + timedelta(days=FOLLOW_UP_SCHEDULE[1])
    await db.commit()
