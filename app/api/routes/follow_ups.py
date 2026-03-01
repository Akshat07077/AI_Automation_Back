from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.models.outreach_log import OutreachLog
from app.schemas.lead import LeadRead
from app.services.follow_up import send_follow_up, process_scheduled_follow_ups
from pydantic import BaseModel


router = APIRouter(tags=["follow-ups"])


class FollowUpLeadRead(LeadRead):
    follow_up_count: int
    next_follow_up_date: datetime | None
    days_since_last_contact: int | None

    class Config:
        from_attributes = True


class FollowUpsResponse(BaseModel):
    leads: list[FollowUpLeadRead]
    total: int
    page: int
    page_size: int


class SendFollowUpResponse(BaseModel):
    success: bool
    message: str
    follow_up_number: int | None = None


@router.get("/follow-ups", response_model=FollowUpsResponse)
async def get_follow_ups(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str = Query("pending", description="Filter: 'pending' (scheduled), 'ready' (due now), 'all'"),
) -> FollowUpsResponse:
    """
    Get leads that need follow-ups or have scheduled follow-ups.
    
    Status filters:
    - 'pending': Leads with scheduled follow-ups (not due yet)
    - 'ready': Leads with follow-ups due now
    - 'all': All leads that have been sent but not replied
    """
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    
    # Build base query - only SENT leads (not replied, not bounced)
    base_condition = Lead.status == LeadStatus.SENT
    
    # Apply status filter
    if status == "ready":
        # Follow-ups due now or in the past
        condition = and_(base_condition, Lead.next_follow_up_date <= now)
    elif status == "pending":
        # Follow-ups scheduled but not due yet
        condition = and_(
            base_condition,
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date > now,
        )
    else:
        # 'all' - all sent leads
        condition = base_condition
    
    # Build queries
    query = select(Lead).where(condition)
    count_query = select(Lead).where(condition)
    
    # Get total count
    from sqlalchemy import func
    total_result = await db.execute(select(func.count()).select_from(Lead).where(condition))
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(Lead.next_follow_up_date.asc().nulls_last())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    leads = result.scalars().all()
    
    # Calculate days since last contact
    follow_up_leads = []
    for lead in leads:
        days_since = None
        if lead.last_contacted:
            days_since = (now - lead.last_contacted).days
        
        follow_up_leads.append(FollowUpLeadRead(
            id=lead.id,
            founder_name=lead.founder_name,
            startup_name=lead.startup_name,
            email=lead.email,
            hiring_role=lead.hiring_role,
            website=lead.website,
            status=lead.status.value,
            created_at=lead.created_at,
            last_contacted=lead.last_contacted,
            follow_up_count=lead.follow_up_count,
            next_follow_up_date=lead.next_follow_up_date,
            days_since_last_contact=days_since,
        ))
    
    return FollowUpsResponse(
        leads=follow_up_leads,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/send-follow-up/{lead_id}", response_model=SendFollowUpResponse)
async def send_follow_up_manual(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SendFollowUpResponse:
    """
    Manually send a follow-up email to a specific lead.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.status != LeadStatus.SENT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send follow-up to lead with status '{lead.status.value}'. Only 'sent' leads can receive follow-ups."
        )
    
    result = await send_follow_up(lead, db)
    
    return SendFollowUpResponse(
        success=result["success"],
        message=result["message"],
        follow_up_number=result.get("follow_up_number"),
    )


@router.post("/process-follow-ups")
async def process_follow_ups(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually trigger processing of scheduled follow-ups.
    This checks for leads with follow-ups due and sends them.
    """
    result = await process_scheduled_follow_ups(db)
    return {
        "message": f"Processed {result['processed']} follow-ups",
        "sent": result["sent"],
        "errors": result["errors"],
    }
