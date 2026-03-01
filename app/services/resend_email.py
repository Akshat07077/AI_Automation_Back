from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.gemini_email import generate_outreach_email
from app.services.smtp_email import send_email


async def resend_email_to_lead(lead: Lead, db: AsyncSession) -> dict:
    """
    Resend an email to a lead, regardless of their current status.
    This generates a new email and sends it, logging it as a new outreach.
    """
    try:
        # Generate new email (will be personalized based on current lead data)
        subject, body = generate_outreach_email(lead)
        
        # Send email
        message_id = send_email(lead.email, subject, body)
        
        # Update last contacted time
        lead.last_contacted = datetime.now(timezone.utc)
        
        # Log the resend as a new "sent" event
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
        
        return {
            "success": True,
            "message": f"Email resent successfully to {lead.email}",
            "subject": subject,
        }
        
    except Exception as e:
        await db.rollback()
        return {
            "success": False,
            "message": f"Failed to resend email: {str(e)}"
        }
