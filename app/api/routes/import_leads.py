from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import ImportLeadsResult
from app.services.google_sheets import fetch_leads_from_sheet


router = APIRouter(tags=["leads"])


@router.post("/import-leads", response_model=ImportLeadsResult)
async def import_leads(db: AsyncSession = Depends(get_db)) -> ImportLeadsResult:
    """
    Import leads from the configured Google Sheet, avoiding duplicates by email.
    """
    import os
    import traceback
    import json
    from app.core.config import get_settings
    
    settings = get_settings()
    
    # Check service account configuration
    if not settings.google_service_account_json and not settings.google_service_account_file:
        raise HTTPException(
            status_code=500,
            detail=(
                "Service account not configured.\n"
                "Please set either:\n"
                "1. GOOGLE_SERVICE_ACCOUNT_JSON (recommended) - Full JSON as string\n"
                "2. GOOGLE_SERVICE_ACCOUNT_FILE - Path to JSON file"
            )
        )
    
    # If using file, check if it exists
    if settings.google_service_account_file and not os.path.exists(settings.google_service_account_file):
        raise HTTPException(
            status_code=500,
            detail=(
                f"Service account file not found at: {settings.google_service_account_file}\n"
                f"Please check:\n"
                f"1. GOOGLE_SERVICE_ACCOUNT_FILE path is correct\n"
                f"2. File exists at the specified path\n"
                f"3. Or use GOOGLE_SERVICE_ACCOUNT_JSON instead (recommended)"
            )
        )
    
    # If using JSON, validate it
    if settings.google_service_account_json:
        try:
            json.loads(settings.google_service_account_json)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {str(e)}\n"
                    f"Please ensure the JSON is valid and properly escaped."
                )
            )
    
    try:
        rows = list(fetch_leads_from_sheet())
    except ValueError as e:
        # User-friendly validation errors
        error_msg = str(e)
        print(f"=== IMPORT LEADS 400 ERROR ===")
        print(f"ValueError: {error_msg}")
        print(f"Using JSON from env: {settings.google_service_account_json is not None}")
        print(f"Service Account File: {settings.google_service_account_file}")
        print(f"Google Sheets ID: {settings.google_sheets_id}")
        print(f"Google Sheets Worksheet: {settings.google_sheets_worksheet}")
        print(f"=============================")
        raise HTTPException(status_code=400, detail=error_msg)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Service account file not found: {str(e)}\n"
                f"Current path: {settings.google_service_account_file}\n"
                f"Please check GOOGLE_SERVICE_ACCOUNT_FILE environment variable."
            )
        )
    except Exception as e:
        # Log the full error for debugging
        error_trace = traceback.format_exc()
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Print full error for server logs
        print(f"=== IMPORT LEADS ERROR ===")
        print(f"Error Type: {error_type}")
        print(f"Error Message: {error_msg}")
        print(f"Using JSON from env: {settings.google_service_account_json is not None}")
        print(f"Service Account File: {settings.google_service_account_file}")
        print(f"Google Sheets ID: {settings.google_sheets_id}")
        print(f"Traceback:\n{error_trace}")
        print(f"=========================")
        
        # Return detailed error message
        if "service_account" in error_msg.lower() or "credentials" in error_msg.lower() or "json" in error_msg.lower():
            if settings.google_service_account_json:
                detail_msg = (
                    f"Google service account configuration error.\n"
                    f"Error: {error_msg}\n"
                    f"Check:\n"
                    f"1. GOOGLE_SERVICE_ACCOUNT_JSON contains valid JSON\n"
                    f"2. JSON is properly escaped (no line breaks, use \\n for newlines)\n"
                    f"3. Service account credentials are correct"
                )
            else:
                detail_msg = (
                    f"Google service account configuration error.\n"
                    f"Error: {error_msg}\n"
                    f"Check:\n"
                    f"1. GOOGLE_SERVICE_ACCOUNT_FILE path: {settings.google_service_account_file}\n"
                    f"2. File is valid JSON\n"
                    f"3. Service account credentials are correct\n"
                    f"4. Consider using GOOGLE_SERVICE_ACCOUNT_JSON instead (recommended)"
                )
        elif "permission" in error_msg.lower() or "403" in error_msg or "forbidden" in error_msg.lower():
            detail_msg = (
                f"Permission denied accessing Google Sheet.\n"
                f"Error: {error_msg}\n"
                f"Check:\n"
                f"1. Sheet is shared with service account\n"
                f"2. Service account has 'Viewer' access\n"
                f"3. Google Sheets API is enabled"
            )
        elif "not found" in error_msg.lower() or "404" in error_msg:
            detail_msg = (
                f"Google Sheet not found.\n"
                f"Error: {error_msg}\n"
                f"Check:\n"
                f"1. GOOGLE_SHEETS_ID: {settings.google_sheets_id}\n"
                f"2. Sheet ID is correct\n"
                f"3. Sheet exists and is accessible"
            )
        else:
            detail_msg = (
                f"Failed to fetch leads from Google Sheet.\n"
                f"Error Type: {error_type}\n"
                f"Error: {error_msg}\n"
                f"Check server logs for full traceback."
            )
        
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )
    if not rows:
        return ImportLeadsResult(inserted=0, skipped_duplicates=0)

    inserted = 0
    skipped = 0
    skipped_reasons = {
        "duplicate": 0,
        "missing_email": 0,
        "missing_founder": 0,
        "missing_startup": 0,
    }

    # Pre-fetch existing emails for faster duplicate checks
    result = await db.execute(select(Lead.email))
    existing_emails = {email.lower() for email in result.scalars().all()}

    for row in rows:
        email = (row.get("email") or "").strip().lower()
        founder_name = (row.get("founder_name") or "").strip()
        startup_name = (row.get("startup_name") or "").strip()
        
        # Skip if missing required fields
        if not email:
            skipped += 1
            skipped_reasons["missing_email"] += 1
            continue
        
        if not founder_name:
            skipped += 1
            skipped_reasons["missing_founder"] += 1
            continue
        
        if not startup_name:
            skipped += 1
            skipped_reasons["missing_startup"] += 1
            continue
        
        # Skip if duplicate email
        if email in existing_emails:
            skipped += 1
            skipped_reasons["duplicate"] += 1
            continue

        lead = Lead(
            founder_name=row.get("founder_name") or "",
            startup_name=row.get("startup_name") or "",
            email=email,
            hiring_role=row.get("hiring_role") or None,
            website=row.get("website") or None,
            observation=row.get("observation") or None,
            status=LeadStatus.NEW,
        )
        db.add(lead)
        existing_emails.add(email)
        inserted += 1

    await db.commit()

    return ImportLeadsResult(
        inserted=inserted,
        skipped_duplicates=skipped,
        skipped_reasons=skipped_reasons if skipped > 0 else None,
    )

