import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings


settings = get_settings()


def send_email(to_email: str, subject: str, body: str, in_reply_to: str | None = None, references: str | None = None) -> str:
    """
    Send an email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body text (will be cleaned and formatted)
        in_reply_to: Message-ID of the email this is replying to (for threading)
        references: References header for email threading (usually same as in_reply_to)
    
    Returns:
        The Message-ID of the sent email
    """
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to_email
    
    # Generate Message-ID if not replying, otherwise use the one from the original email
    message_id = None
    if in_reply_to:
        # This is a reply - set threading headers
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = references or in_reply_to
        # Ensure subject has "Re: " prefix if not already present
        if not subject.lower().startswith("re:"):
            msg["Subject"] = f"Re: {subject}"
        else:
            msg["Subject"] = subject
        # Generate a new Message-ID for this reply
        message_id = make_msgid()
    else:
        # New email - generate a Message-ID
        message_id = make_msgid()
        msg["Subject"] = subject
    
    msg["Message-ID"] = message_id
    
    # Clean and format the body
    # Remove any JSON artifacts, ensure proper line breaks
    body = body.strip()
    # Replace escaped newlines with actual newlines
    body = body.replace('\\n', '\n')
    # Ensure consistent line breaks
    body = '\n'.join(line.strip() for line in body.split('\n'))
    
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
            
            # Return the Message-ID
            return message_id
    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e)
        if "BadCredentials" in error_msg or "535" in error_msg:
            raise ValueError(
                "Gmail authentication failed. Make sure you're using a Gmail App Password, not your regular password. "
                "Create one at: https://myaccount.google.com/apppasswords (requires 2-Step Verification to be enabled)."
            ) from e
        raise

