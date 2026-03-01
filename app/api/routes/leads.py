from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadRead
from app.services.resend_email import resend_email_to_lead
from pydantic import BaseModel
from uuid import UUID


router = APIRouter(tags=["leads"])


class LeadsResponse(BaseModel):
    leads: list[LeadRead]
    total: int
    page: int
    page_size: int


class LeadsSummaryResponse(BaseModel):
    total: int
    new: int
    sent: int
    replied: int
    bounce: int


@router.get("/leads", response_model=LeadsResponse)
async def get_leads(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: LeadStatus | None = Query(None),
) -> LeadsResponse:
    """
    Get paginated list of leads, optionally filtered by status.
    """
    # Build query
    query = select(Lead)
    count_query = select(func.count()).select_from(Lead)
    
    if status:
        query = query.where(Lead.status == status)
        count_query = count_query.where(Lead.status == status)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(Lead.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return LeadsResponse(
        leads=[LeadRead.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/leads/summary", response_model=LeadsSummaryResponse)
async def get_leads_summary(
    db: AsyncSession = Depends(get_db),
) -> LeadsSummaryResponse:
    """
    Get summary counts of leads by status.
    """
    total_result = await db.execute(select(func.count()).select_from(Lead))
    total = total_result.scalar() or 0
    
    new_result = await db.execute(
        select(func.count()).where(Lead.status == LeadStatus.NEW)
    )
    new = new_result.scalar() or 0
    
    sent_result = await db.execute(
        select(func.count()).where(Lead.status == LeadStatus.SENT)
    )
    sent = sent_result.scalar() or 0
    
    replied_result = await db.execute(
        select(func.count()).where(Lead.status == LeadStatus.REPLIED)
    )
    replied = replied_result.scalar() or 0
    
    bounce_result = await db.execute(
        select(func.count()).where(Lead.status == LeadStatus.BOUNCE)
    )
    bounce = bounce_result.scalar() or 0
    
    return LeadsSummaryResponse(
        total=total,
        new=new,
        sent=sent,
        replied=replied,
        bounce=bounce,
    )


@router.post("/leads/{lead_id}/resend-email")
async def resend_email(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resend an email to a specific lead, regardless of their current status.
    This generates a new personalized email and sends it.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    result = await resend_email_to_lead(lead, db)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "message": result["message"],
        "subject": result.get("subject"),
    }
