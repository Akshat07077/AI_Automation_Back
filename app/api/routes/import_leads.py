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
    try:
        rows = list(fetch_leads_from_sheet())
    except ValueError as e:
        # User-friendly validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Service account file not found: {str(e)}. Please check GOOGLE_SERVICE_ACCOUNT_FILE environment variable."
        )
    except Exception as e:
        # Log the full error for debugging, but return user-friendly message
        import traceback
        error_trace = traceback.format_exc()
        print(f"Import leads error: {error_trace}")  # TODO: Use proper logging
        
        error_msg = str(e)
        if "service_account" in error_msg.lower() or "credentials" in error_msg.lower():
            error_msg = "Google service account configuration error. Check GOOGLE_SERVICE_ACCOUNT_FILE path and credentials."
        elif "permission" in error_msg.lower() or "403" in error_msg:
            error_msg = "Permission denied. Ensure the Google Sheet is shared with the service account."
        elif "not found" in error_msg.lower() or "404" in error_msg:
            error_msg = "Google Sheet not found. Check GOOGLE_SHEETS_ID environment variable."
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch leads from Google Sheet: {error_msg}"
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

