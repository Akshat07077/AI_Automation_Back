from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.gemini_email import generate_outreach_email
from app.services.gmail_email import send_gmail_email
from app.api.routes.google_auth import get_current_user
from app.models.user import User
from app.models.lead import Lead, LeadStatus
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from sqlalchemy import select
from datetime import datetime, timezone

router = APIRouter(tags=["test"])


class TestEmailRequest(BaseModel):
    to_email: EmailStr
    founder_name: str = "John Doe"
    startup_name: str = "Test Startup"
    hiring_role: str = "Software Engineer"
    website: str = "https://example.com"
    observation: str = "Testing email functionality"


@router.post("/test-email")
async def test_email(
    request: TestEmailRequest, 
    user: User = Depends(get_current_user)
) -> dict:
    """
    Test endpoint to verify Gemini email generation and Gmail API sending.
    
    This creates a mock lead and:
    1. Generates an email using Gemini
    2. Sends it via Gmail API
    
    Use this to test your email configuration.
    """
    try:
        # Create a mock lead for testing
        mock_lead = Lead(
            id="00000000-0000-0000-0000-000000000000",  # Dummy UUID
            founder_name=request.founder_name,
            startup_name=request.startup_name,
            email=request.to_email,
            hiring_role=request.hiring_role,
            website=request.website,
            observation=request.observation,
            status=LeadStatus.NEW,
            created_at=datetime.now(timezone.utc),
        )
        
        # Step 1: Generate email with Gemini
        try:
            subject, body = generate_outreach_email(mock_lead)
            if not subject or not body:
                raise ValueError("Gemini returned empty subject or body")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate email with Gemini: {str(e)}. Check your GEMINI_API_KEY."
            )
        
        # Step 2: Send email via Gmail API
        try:
            send_gmail_email(user, request.to_email, subject, body)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email via Gmail API: {str(e)}. Make sure your Gmail is connected in Settings."
            )
        
        return {
            "success": True,
            "message": f"Test email sent successfully to {request.to_email}",
            "subject": subject,
            "body_preview": body[:200] + "..." if len(body) > 200 else body,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/test-gemini")
async def test_gemini() -> dict:
    """
    Test endpoint to verify Gemini API connection.
    Returns a simple test to check if Gemini is working.
    """
    try:
        
        # Create a minimal test lead
        test_lead = Lead(
            id="00000000-0000-0000-0000-000000000000",
            founder_name="Test Founder",
            startup_name="Test Company",
            email="test@example.com",
            hiring_role="Developer",
            website="https://test.com",
            observation="Testing Gemini API",
            status=LeadStatus.NEW,
            created_at=datetime.now(timezone.utc),
        )
        
        subject, body = generate_outreach_email(test_lead)
        
        return {
            "success": True,
            "message": "Gemini API is working!",
            "generated_subject": subject,
            "generated_body_preview": body[:200] + "..." if len(body) > 200 else body,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API test failed: {str(e)}. Check your GEMINI_API_KEY in .env"
        )


@router.get("/test-gmail")
async def test_gmail(
    user: User = Depends(get_current_user)
) -> dict:
    """
    Test endpoint to verify Gmail API connection.
    Note: This will attempt to send a test email to your own Gmail address.
    """
    try:
        test_subject = "Test Email from AI Outreach Automation"
        test_body = "This is a test email to verify Gmail API configuration is working correctly."
        
        if not user.gmail_email:
            raise ValueError("Gmail account not connected.")
            
        send_gmail_email(user, user.gmail_email, test_subject, test_body)
        
        return {
            "success": True,
            "message": f"Test email sent to {user.gmail_email}",
            "note": "Check your inbox (and sent folder) for the test email.",
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gmail API test failed: {str(e)}. Make sure you have connected your Gmail in Settings."
        )
