import email
import imaplib
from collections import defaultdict
from datetime import datetime, timezone
from email.header import decode_header
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.lead import Lead, LeadStatus
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.telegram import send_telegram_message


settings = get_settings()


def _decode_mime_words(s: str) -> str:
    decoded = decode_header(s)
    return "".join(
        [
            (part.decode(charset or "utf-8") if isinstance(part, bytes) else part)
            for part, charset in decoded
        ]
    )


def fetch_recent_replies() -> Iterable[tuple[str, str]]:
    """
    Returns an iterable of (email_address, subject) for new replies/bounces.
    This is a naive implementation that looks at the INBOX for unseen messages.
    """
    results: list[tuple[str, str]] = []
    mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        mail.login(settings.imap_username, settings.imap_password)
        mail.select("INBOX")

        typ, data = mail.search(None, "UNSEEN")
        if typ != "OK":
            return results

        for num in data[0].split():
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            from_header = msg.get("From", "")
            subject = msg.get("Subject", "")
            subject = _decode_mime_words(subject)

            # Extract email address from "Name <email>"
            addr = email.utils.parseaddr(from_header)[1]
            if not addr:
                continue

            results.append((addr.lower(), subject))

    finally:
        try:
            mail.logout()
        except Exception:
            pass

    return results


async def process_imap_replies(db: AsyncSession) -> None:
    """
    Check IMAP for new replies/bounces and update leads/logs.
    """
    events = list(fetch_recent_replies())
    if not events:
        return

    # Group by email for efficiency
    by_email: dict[str, list[str]] = defaultdict(list)
    for addr, subject in events:
        by_email[addr].append(subject)

    for email_addr, subjects in by_email.items():
        result = await db.execute(select(Lead).where(Lead.email == email_addr))
        lead: Lead | None = result.scalar_one_or_none()
        if not lead:
            continue

        # Naive classification: subject containing 'bounce' -> bounce, else reply
        aggregated_subjects = " ".join(subjects).lower()
        if "undeliverable" in aggregated_subjects or "delivery status notification" in aggregated_subjects or "bounce" in aggregated_subjects:
            new_status = LeadStatus.BOUNCE
            event_type = OutreachEventType.BOUNCE
        else:
            new_status = LeadStatus.REPLIED
            event_type = OutreachEventType.REPLIED

        lead.status = new_status
        lead.last_contacted = datetime.now(timezone.utc)
        db.add(
            OutreachLog(
                lead_id=lead.id,
                event_type=event_type,
            )
        )

        if event_type == OutreachEventType.REPLIED:
            send_telegram_message(
                f"✅ New reply from *{lead.founder_name}* ({lead.email}) for *{lead.startup_name}*"
            )

    await db.commit()

