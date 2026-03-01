from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.gemini_email import generate_outreach_email
from app.services.smtp_email import send_email
from app.models.lead import Lead, LeadStatus
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
async def test_email(request: TestEmailRequest) -> dict:
    """
    Test endpoint to verify Gemini email generation and SMTP sending.
    
    This creates a mock lead and:
    1. Generates an email using Gemini
    2. Sends it via SMTP
    
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
        
        # Step 2: Send email via SMTP
        try:
            send_email(request.to_email, subject, body)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email via SMTP: {str(e)}. Check your SMTP credentials (SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)."
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


@router.get("/test-smtp")
async def test_smtp() -> dict:
    """
    Test endpoint to verify SMTP connection.
    Note: This will attempt to send a test email to the SMTP_USERNAME email.
    """
    try:
        from app.core.config import get_settings
        
        settings = get_settings()
        test_subject = "Test Email from AI Outreach Automation"
        test_body = "This is a test email to verify SMTP configuration is working correctly."
        
        # Send test email to yourself
        send_email(settings.smtp_username, test_subject, test_body)
        
        return {
            "success": True,
            "message": f"Test email sent to {settings.smtp_username}",
            "note": "Check your inbox (and spam folder) for the test email.",
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SMTP test failed: {str(e)}. Check your SMTP credentials (SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM) in .env"
        )
