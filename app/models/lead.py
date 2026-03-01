import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class LeadStatus(str, PyEnum):
    NEW = "new"
    SENT = "sent"
    REPLIED = "replied"
    BOUNCE = "bounce"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    founder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    startup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hiring_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        default=LeadStatus.NEW,
        nullable=False,
        index=True,
    )
    last_contacted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_count: Mapped[int] = mapped_column(default=0, nullable=False)
    next_follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    outreach_logs: Mapped[list["OutreachLog"]] = relationship(
        "OutreachLog", back_populates="lead", cascade="all, delete-orphan"
    )

