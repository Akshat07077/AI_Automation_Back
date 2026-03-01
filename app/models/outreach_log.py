import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.lead import Lead


class OutreachEventType(str, PyEnum):
    SENT = "sent"
    REPLIED = "replied"
    BOUNCE = "bounce"
    FOLLOW_UP = "follow_up"


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[OutreachEventType] = mapped_column(
        Enum(OutreachEventType, name="outreach_event_type", native_enum=False),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Store email details for sent emails
    email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Store Message-ID for reply threading
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    lead: Mapped[Lead] = relationship("Lead", back_populates="outreach_logs")

