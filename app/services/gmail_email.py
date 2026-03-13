import base64
from email.mime.text import MIMEText
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from app.models.user import User
from app.core.config import get_settings

settings = get_settings()

def get_gmail_credentials(user: User) -> Credentials:
    """
    Returns Google Credentials object for the user, refreshing it if necessary.
    """
    if not user.gmail_access_token or not user.gmail_refresh_token:
        raise ValueError("User has not connected their Gmail account.")

    creds = Credentials(
        token=user.gmail_access_token,
        refresh_token=user.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        expiry=user.gmail_token_expiry
    )

    # Check if we need to refresh the token
    if creds.expired:
        try:
            creds.refresh(Request())
            # Update user tokens in the background would be better, 
            # but for now we'll assume the caller handles the DB commit 
            # or we just use the refreshed crds for this request.
            # In a real app, we should save these back to the DB.
            user.gmail_access_token = creds.token
            if creds.expiry:
                user.gmail_token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
        except Exception as e:
            raise ValueError(f"Failed to refresh Gmail token: {str(e)}")

    return creds

def send_gmail_email(user: User, to_email: str, subject: str, body: str) -> str:
    """
    Sends an email using the Gmail API on behalf of the user.
    """
    try:
        creds = get_gmail_credentials(user)
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message in base64
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        return sent_message['id']

    except Exception as e:
        raise Exception(f"Failed to send email via Gmail API: {str(e)}")
