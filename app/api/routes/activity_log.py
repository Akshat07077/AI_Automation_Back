from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.models.lead import Lead
from pydantic import BaseModel
from uuid import UUID


router = APIRouter(tags=["activity-log"])


class ActivityLogEntry(BaseModel):
    id: str
    timestamp: datetime
    type: str  # "email_sent", "email_replied", "email_bounced", "follow_up_sent", "lead_imported"
    title: str
    description: str
    lead_id: str | None
    lead_founder_name: str | None
    lead_startup_name: str | None
    lead_email: str | None
    email_subject: str | None
    metadata: dict | None = None

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    entries: list[ActivityLogEntry]
    total: int
    page: int
    page_size: int


@router.get("/activity-log", response_model=ActivityLogResponse)
async def get_activity_log(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: OutreachEventType | None = Query(None, alias="event_type"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> ActivityLogResponse:
    """
    Get comprehensive activity log showing all system events.
    
    Includes:
    - Emails sent (initial + follow-ups)
    - Replies received
    - Bounces
    - Lead imports (from outreach_logs with special handling)
    """
    # Build query for outreach logs
    query = select(OutreachLog).options(selectinload(OutreachLog.lead))
    count_query = select(func.count()).select_from(OutreachLog)
    
    # Apply filters
    conditions = []
    if event_type:
        conditions.append(OutreachLog.event_type == event_type)
    if start_date:
        conditions.append(OutreachLog.timestamp >= start_date)
    if end_date:
        conditions.append(OutreachLog.timestamp <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering (newest first)
    query = query.order_by(OutreachLog.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Convert to activity log entries
    entries = []
    for log in logs:
        # Determine activity type and title
        if log.event_type == OutreachEventType.SENT:
            activity_type = "email_sent"
            title = "Email Sent"
            description = f"Sent email to {log.lead.founder_name} at {log.lead.startup_name}"
        elif log.event_type == OutreachEventType.FOLLOW_UP:
            activity_type = "follow_up_sent"
            title = "Follow-Up Sent"
            description = f"Sent follow-up email to {log.lead.founder_name} at {log.lead.startup_name}"
        elif log.event_type == OutreachEventType.REPLIED:
            activity_type = "email_replied"
            title = "Reply Received"
            description = f"Received reply from {log.lead.founder_name} at {log.lead.startup_name}"
        elif log.event_type == OutreachEventType.BOUNCE:
            activity_type = "email_bounced"
            title = "Email Bounced"
            description = f"Email bounced from {log.lead.email} ({log.lead.startup_name})"
        else:
            activity_type = "unknown"
            title = "Unknown Event"
            description = f"Event: {log.event_type.value}"
        
        entries.append(ActivityLogEntry(
            id=str(log.id),
            timestamp=log.timestamp,
            type=activity_type,
            title=title,
            description=description,
            lead_id=str(log.lead_id),
            lead_founder_name=log.lead.founder_name,
            lead_startup_name=log.lead.startup_name,
            lead_email=log.lead.email,
            email_subject=log.email_subject,
            metadata={
                "event_type": log.event_type.value,
            }
        ))
    
    return ActivityLogResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/activity-log/summary")
async def get_activity_summary(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30),
) -> dict:
    """
    Get activity summary for the last N days.
    """
    from datetime import timedelta, timezone
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Count by event type - extract scalar values immediately
    sent_result = await db.execute(
        select(func.count()).where(
            and_(
                OutreachLog.event_type == OutreachEventType.SENT,
                OutreachLog.timestamp >= start_date,
            )
        )
    )
    sent = sent_result.scalar() or 0
    
    follow_up_result = await db.execute(
        select(func.count()).where(
            and_(
                OutreachLog.event_type == OutreachEventType.FOLLOW_UP,
                OutreachLog.timestamp >= start_date,
            )
        )
    )
    follow_ups = follow_up_result.scalar() or 0
    
    replied_result = await db.execute(
        select(func.count()).where(
            and_(
                OutreachLog.event_type == OutreachEventType.REPLIED,
                OutreachLog.timestamp >= start_date,
            )
        )
    )
    replied = replied_result.scalar() or 0
    
    bounce_result = await db.execute(
        select(func.count()).where(
            and_(
                OutreachLog.event_type == OutreachEventType.BOUNCE,
                OutreachLog.timestamp >= start_date,
            )
        )
    )
    bounced = bounce_result.scalar() or 0
    
    return {
        "period_days": days,
        "sent": sent,
        "follow_ups": follow_ups,
        "replied": replied,
        "bounced": bounced,
        "total": sent + follow_ups + replied + bounced,
    }
