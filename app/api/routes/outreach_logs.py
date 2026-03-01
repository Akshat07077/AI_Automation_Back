from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.models.lead import Lead
from pydantic import BaseModel
from uuid import UUID


router = APIRouter(tags=["outreach-logs"])


class OutreachLogRead(BaseModel):
    id: UUID
    lead_id: UUID
    event_type: str
    timestamp: datetime
    email_subject: str | None
    email_body: str | None
    # Lead details
    lead_founder_name: str
    lead_startup_name: str
    lead_email: str

    class Config:
        from_attributes = True


class OutreachLogsResponse(BaseModel):
    logs: list[OutreachLogRead]
    total: int
    page: int
    page_size: int


@router.get("/outreach-logs", response_model=OutreachLogsResponse)
async def get_outreach_logs(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: OutreachEventType | None = Query(None, alias="event_type"),
    lead_id: UUID | None = Query(None, alias="lead_id"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> OutreachLogsResponse:
    """
    Get paginated outreach logs with filters.
    
    Filters:
    - event_type: Filter by event type (sent, replied, bounce)
    - lead_id: Filter by specific lead
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """
    # Build query with join to get lead details
    query = select(OutreachLog).options(selectinload(OutreachLog.lead))
    count_query = select(func.count()).select_from(OutreachLog)
    
    # Apply filters
    conditions = []
    if event_type:
        conditions.append(OutreachLog.event_type == event_type)
    if lead_id:
        conditions.append(OutreachLog.lead_id == lead_id)
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
    
    # Apply pagination and ordering
    query = query.order_by(OutreachLog.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Format response with lead details
    log_reads = []
    for log in logs:
        log_reads.append(OutreachLogRead(
            id=log.id,
            lead_id=log.lead_id,
            event_type=log.event_type.value,
            timestamp=log.timestamp,
            email_subject=log.email_subject,
            email_body=log.email_body,
            lead_founder_name=log.lead.founder_name,
            lead_startup_name=log.lead.startup_name,
            lead_email=log.lead.email,
        ))
    
    return OutreachLogsResponse(
        logs=log_reads,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/outreach-logs/summary")
async def get_outreach_logs_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get summary of outreach logs by event type.
    """
    sent_result = await db.execute(
        select(func.count()).where(OutreachLog.event_type == OutreachEventType.SENT)
    )
    sent_count = sent_result.scalar() or 0
    
    replied_result = await db.execute(
        select(func.count()).where(OutreachLog.event_type == OutreachEventType.REPLIED)
    )
    replied_count = replied_result.scalar() or 0
    
    bounce_result = await db.execute(
        select(func.count()).where(OutreachLog.event_type == OutreachEventType.BOUNCE)
    )
    bounce_count = bounce_result.scalar() or 0
    
    return {
        "sent": sent_count,
        "replied": replied_count,
        "bounce": bounce_count,
        "total": sent_count + replied_count + bounce_count,
    }
