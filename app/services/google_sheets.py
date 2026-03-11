from typing import Iterable
import json
import os

import gspread
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_gspread_client(user: User) -> gspread.Client:
    """
    Get gspread client using the authenticated user's OAuth tokens.
    """
    if not user.google_access_token or not user.google_refresh_token:
        raise ValueError("User has not connected their Google account.")

    # These must be set in your .env or Config for the token refresh to work automatically
    client_id = getattr(settings, "google_client_id", "")
    client_secret = getattr(settings, "google_client_secret", "")

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    
    return gspread.authorize(creds)


def fetch_leads_from_sheet(user: User, sheet_id: str) -> Iterable[dict]:
    """
    Reads all rows from the selected Google Sheet worksheet and yields dicts.

    Supports multiple column name formats (case-insensitive):
      - founder_name, Founder_Name, "Founder Name"
      - startup_name, Startup_Name, "Startup Name"
      - email, Email
      - hiring_role, Hiring_Role, "Hiring Role"
      - website, Website
      - observation, Observation
    """
    if not sheet_id:
        raise ValueError("No Google Sheet selected. Please select one in Settings.")

    try:
        client = get_gspread_client(user)
    except Exception as e:
        raise ValueError(f"Failed to authorize with Google: {str(e)}")
    
    try:
        sheet = client.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(
            f"Google Sheet not found. Please check:\n"
            f"1. Sheet ID is correct.\n"
            f"2. Note: You must select a new sheet in the Dashboard Settings since auth changed."
        )
    except gspread.exceptions.APIError as e:
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        if status_code == 403:
            raise ValueError(
                f"Permission denied. Make sure your Google account has access to the sheet."
            )
        elif status_code == 404:
            raise ValueError(
                f"Google Sheet not found."
            )
        else:
            # Convert other API errors to ValueError for better error handling
            error_msg = str(e)
            raise ValueError(
                f"Google Sheets API error (status {status_code}): {error_msg}\n"
                f"Check:\n"
                f"1. Google Sheets API is enabled\n"
                f"2. Service account has proper permissions\n"
                f"3. Sheet ID is correct"
            )
    
    # Try to get the worksheet, with helpful error if not found
    try:
        worksheet = sheet.worksheet(settings.google_sheets_worksheet)
    except gspread.exceptions.WorksheetNotFound:
        # List available worksheets for better error message
        available_worksheets = [ws.title for ws in sheet.worksheets()]
        raise ValueError(
            f"Worksheet '{settings.google_sheets_worksheet}' not found.\n"
            f"Available worksheets: {', '.join(available_worksheets)}\n"
            f"Update GOOGLE_SHEETS_WORKSHEET in your .env file."
        )
    
    rows = worksheet.get_all_records()

    normalized = []
    for row in rows:
        # Try multiple column name variations (case-insensitive)
        # Handle: founder_name, Founder_Name, "Founder Name", etc.
        founder_name = (
            row.get("founder_name") or 
            row.get("Founder_Name") or 
            row.get("Founder Name") or 
            row.get("FOUNDER_NAME") or
            ""
        )
        
        startup_name = (
            row.get("startup_name") or 
            row.get("Startup_Name") or 
            row.get("Startup Name") or 
            row.get("STARTUP_NAME") or
            ""
        )
        
        email = (
            row.get("email") or 
            row.get("Email") or 
            row.get("EMAIL") or
            ""
        )
        
        hiring_role = (
            row.get("hiring_role") or 
            row.get("Hiring_Role") or 
            row.get("Hiring Role") or 
            row.get("HIRING_ROLE") or
            ""
        )
        
        website = (
            row.get("website") or 
            row.get("Website") or 
            row.get("WEBSITE") or
            ""
        )
        
        observation = (
            row.get("observation") or 
            row.get("Observation") or 
            row.get("OBSERVATION") or
            ""
        )
        
        # Only add if we have at least founder_name, startup_name, and email
        if founder_name and startup_name and email:
            normalized.append(
                {
                    "founder_name": founder_name.strip(),
                    "startup_name": startup_name.strip(),
                    "email": email.strip().lower(),
                    "hiring_role": hiring_role.strip() if hiring_role else None,
                    "website": website.strip() if website else None,
                    "observation": observation.strip() if observation else None,
                }
            )
    
    return normalized

