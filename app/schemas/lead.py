from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.lead import LeadStatus


class LeadBase(BaseModel):
    founder_name: str
    startup_name: str
    email: EmailStr
    hiring_role: str | None = None
    website: str | None = None
    observation: str | None = None
    status: LeadStatus
    last_contacted: datetime | None = None


class LeadRead(LeadBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ImportLeadsResult(BaseModel):
    inserted: int
    skipped_duplicates: int
    skipped_reasons: dict[str, int] | None = None

