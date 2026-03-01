from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.schemas.stats import StatsResponse


router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    """
    Returns outreach stats for today.
    """
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    def _count(event_type: OutreachEventType):
        return select(func.count()).where(
            OutreachLog.event_type == event_type,
            OutreachLog.timestamp >= start_of_day,
        )

    sent_today_result = await db.execute(_count(OutreachEventType.SENT))
    sent_today = int(sent_today_result.scalar() or 0)

    replies_today_result = await db.execute(_count(OutreachEventType.REPLIED))
    replies_today = int(replies_today_result.scalar() or 0)

    bounce_today_result = await db.execute(_count(OutreachEventType.BOUNCE))
    bounce_today = int(bounce_today_result.scalar() or 0)

    reply_rate = (replies_today / sent_today) if sent_today > 0 else 0.0

    return StatsResponse(
        sent_today=sent_today,
        replies_today=replies_today,
        bounce_today=bounce_today,
        reply_rate=reply_rate,
    )

