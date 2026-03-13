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
from app.models.user import User
from app.models.outreach_log import OutreachEventType, OutreachLog
from app.services.telegram import send_telegram_message
from app.services.gmail_email import get_gmail_credentials
from googleapiclient.discovery import build


settings = get_settings()


def _decode_mime_words(s: str) -> str:
    decoded = decode_header(s)
    return "".join(
        [
            (part.decode(charset or "utf-8") if isinstance(part, bytes) else part)
            for part, charset in decoded
        ]
    )


def fetch_gmail_replies(user: User) -> Iterable[tuple[str, str]]:
    """
    Returns an iterable of (email_address, subject) for new replies/bounces using Gmail API.
    """
    results: list[tuple[str, str]] = []
    try:
        creds = get_gmail_credentials(user)
        service = build('gmail', 'v1', credentials=creds)

        # Search for unread messages in the inbox
        response = service.users().messages().list(userId='me', q='is:unread label:INBOX').execute()
        messages = response.get('messages', [])

        for msg_meta in messages:
            msg = service.users().messages().get(userId='me', id=msg_meta['id']).execute()
            headers = msg.get('payload', {}).get('headers', [])
            
            from_email = ""
            subject = ""
            
            for header in headers:
                if header['name'].lower() == 'from':
                    from_email = email.utils.parseaddr(header['value'])[1]
                if header['name'].lower() == 'subject':
                    subject = header['value']
            
            if from_email:
                results.append((from_email.lower(), subject))
                
                # Mark as read (optional, but good practice so we don't process again)
                service.users().messages().batchModify(
                    userId='me',
                    body={
                        'ids': [msg_meta['id']],
                        'removeLabelIds': ['UNREAD']
                    }
                ).execute()

    except Exception as e:
        print(f"Error fetching Gmail replies: {e}")

    return results


async def process_imap_replies(db: AsyncSession) -> None:
    """
    Check Gmail API for new replies/bounces (reusing name for compatibility with main loop).
    """
    # Fetch user for Gmail credentials
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none() # Changed from scalar_first() to scalar_one_or_none() for robustness
    
    if not user or not user.gmail_access_token:
        return

    events = list(fetch_gmail_replies(user))
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

