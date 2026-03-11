import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.core.config import get_settings

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

settings = get_settings()

router = APIRouter(tags=["google_auth"])

# Using the explicit required scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

def get_google_flow() -> Flow:
    # We must require GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to be set now
    if not getattr(settings, "google_client_id", None) or not getattr(settings, "google_client_secret", None):
        raise HTTPException(
            status_code=500, 
            detail="Google OAuth Client ID and Secret are not configured in environment variables."
        )

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "project_id": getattr(settings, "google_project_id", "ai-automation"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.google_client_secret,
            # We redirect back to our backend
            "redirect_uris": [getattr(settings, "google_redirect_uri", "http://localhost:8000/auth/google/callback")],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=client_config["web"]["redirect_uris"][0]
    )
    return flow

# Dummy user auth dependency since there is no JWT setup yet in the codebase.
# We will lookup the single user or first user for demo purposes if not provided an auth token.
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    # In a real SaaS with JWT, you'd decode the token and query the user.
    # For this migration step, let's just grab the first user in the DB
    result = await db.execute(select(User).limit(1))
    user = result.scalar_first()
    if not user:
        # Create a dummy user for testing
        user = User(
            username="test_founder",
            password_hash="fake_hash"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("/auth/google")
async def login_google():
    """Generates the Google OAuth consent screen URL and redirects the user."""
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent" # Force consent to ensure we get a refresh token
    )
    return RedirectResponse(authorization_url)


@router.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Handles the OAuth callback, exchanges code for tokens, and saves them to the user log."""
    # We retrieve the "current user" who initiated this request
    
    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save tokens to database
        user.google_access_token = credentials.token
        user.google_refresh_token = credentials.refresh_token
        
        if credentials.expiry:
            # credentials.expiry is a datetime object in UTC context
            user.token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)
            
        # Optional: we can fetch the user's email using a different scope or just leave it empty 
        # unless userinfo scope is added. For now we will mark as connected.
        user.google_email = "connected@oauth.com" # Placeholder
        
        await db.commit()
        
        # Redirect back to the frontend settings page
        frontend_url = getattr(settings, "frontend_url", "http://localhost:3000/settings")
        return RedirectResponse(f"{frontend_url}?google_auth_success=true")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth flow: {str(e)}")


@router.get("/google/sheets")
async def list_google_sheets(user: User = Depends(get_current_user)):
    """Fetches a list of the user's Google Spreadsheets using their stored OAuth credentials."""
    if not user.google_access_token:
        raise HTTPException(status_code=400, detail="User has not connected their Google account.")
    
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=getattr(settings, "google_client_id", ""),
        client_secret=getattr(settings, "google_client_secret", "")
    )
    
    try:
        service = build('drive', 'v3', credentials=creds)
        # Search for only Google Sheets
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=50,
            fields="nextPageToken, files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        return {"sheets": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sheets: {str(e)}")


from pydantic import BaseModel
class SelectSheetRequest(BaseModel):
    sheet_id: str

@router.post("/google/select-sheet")
async def select_google_sheet(request: SelectSheetRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Saves the chosen sheet ID to the user's profile."""
    user.google_sheet_id = request.sheet_id
    await db.commit()
    return {"message": "Sheet selected successfully.", "sheet_id": user.google_sheet_id}

@router.get("/users/me/google-status")
async def get_google_integration_status(user: User = Depends(get_current_user)):
    """Returns the Google OAuth connection status for the frontend settings page."""
    return {
        "is_connected": bool(user.google_access_token),
        "email": user.google_email,
        "sheet_id": user.google_sheet_id
    }
