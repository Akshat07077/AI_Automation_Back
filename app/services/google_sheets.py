from typing import Iterable
import json
import os

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import get_settings


settings = get_settings()


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_gspread_client() -> gspread.Client:
    """
    Get gspread client using service account credentials.
    Supports both JSON from environment variable and file path.
    """
    # Priority: 1. JSON from env var, 2. File path
    if settings.google_service_account_json:
        # Parse JSON from environment variable
        try:
            service_account_info = json.loads(settings.google_service_account_json)
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES,
            )
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {str(e)}"
            )
    elif settings.google_service_account_file:
        # Use file path
        if not os.path.exists(settings.google_service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {settings.google_service_account_file}"
            )
        creds = Credentials.from_service_account_file(
            settings.google_service_account_file,
            scopes=SCOPES,
        )
    else:
        raise ValueError(
            "Either GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE must be set"
        )
    
    return gspread.authorize(creds)


def fetch_leads_from_sheet() -> Iterable[dict]:
    """
    Reads all rows from the configured Google Sheet worksheet and yields dicts.

    Supports multiple column name formats (case-insensitive):
      - founder_name, Founder_Name, "Founder Name"
      - startup_name, Startup_Name, "Startup Name"
      - email, Email
      - hiring_role, Hiring_Role, "Hiring Role"
      - website, Website
      - observation, Observation
    """
    client = get_gspread_client()
    
    try:
        sheet = client.open_by_key(settings.google_sheets_id)
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(
            f"Google Sheet not found. Please check:\n"
            f"1. Sheet ID is correct: {settings.google_sheets_id}\n"
            f"2. Sheet is shared with service account: ai-auto@robust-chess-427018-j2.iam.gserviceaccount.com\n"
            f"3. Service account has 'Viewer' access to the sheet"
        )
    except gspread.exceptions.APIError as e:
        if e.response.status_code == 403:
            raise ValueError(
                f"Permission denied. Please:\n"
                f"1. Share the sheet with: ai-auto@robust-chess-427018-j2.iam.gserviceaccount.com\n"
                f"2. Give it 'Viewer' access\n"
                f"3. Make sure Google Sheets API is enabled in your project"
            )
        raise
    
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

