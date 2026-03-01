from pydantic import BaseModel


class StatsResponse(BaseModel):
    sent_today: int
    replies_today: int
    bounce_today: int
    reply_rate: float

