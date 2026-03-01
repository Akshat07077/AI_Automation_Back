from textwrap import dedent
from typing import Tuple

import google.generativeai as genai

from app.core.config import get_settings
from app.models.lead import Lead


settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)


def generate_follow_up_email(lead: Lead, follow_up_number: int) -> Tuple[str, str]:
    """
    Generate a follow-up email with different angles based on follow-up number.
    
    Follow-up 1 (after 3-4 days): Value reminder, different angle
    Follow-up 2 (after 5-7 days): Social proof, case study
    Follow-up 3 (after 8-10 days): Final touch, soft close
    """
    
    # Different angles for each follow-up
    angles = {
        1: {
            "name": "Value Reminder",
            "approach": "Remind them of the value proposition with a different angle. Maybe focus on time saved, or better candidate quality, or cost efficiency.",
            "tone": "Friendly reminder, not pushy"
        },
        2: {
            "name": "Social Proof",
            "approach": "Share a brief case study or example of how you helped a similar startup. Be specific but brief.",
            "tone": "Helpful and consultative"
        },
        3: {
            "name": "Final Touch",
            "approach": "Soft close - acknowledge they're busy, offer a quick 15-min call, or ask if they'd like to be removed from the list.",
            "tone": "Respectful and understanding"
        }
    }
    
    angle = angles.get(follow_up_number, angles[3])
    
    # Calculate days since last contact
    from datetime import datetime, timezone
    days_since = 0
    if lead.last_contacted:
        days_since = (datetime.now(timezone.utc) - lead.last_contacted).days
    
    prompt = dedent(
        f"""
        You are Akshat Sharma, a freelance AI automation specialist. You're writing a follow-up email 
        to {lead.founder_name} at {lead.startup_name} who hasn't replied to your initial outreach.
        
        CONTEXT:
        - This is follow-up #{follow_up_number}
        - Days since last contact: {days_since} days
        - Original hiring role: {lead.hiring_role or "Not specified"}
        - Original observation: {lead.observation or "None"}
        
        FOLLOW-UP STRATEGY:
        - Angle: {angle['name']}
        - Approach: {angle['approach']}
        - Tone: {angle['tone']}
        
        YOUR TASK:
        Write a follow-up email that:
        
        1. SUBJECT LINE (max 50 characters):
           - Reference the previous email subtly (e.g., "Re: [original topic]", "Following up on...")
           - Or use a new angle entirely
           - Examples: "Re: {lead.startup_name} hiring", "Quick follow-up", "One more thing about {lead.startup_name}"
        
        2. EMAIL BODY (80-120 words, 2-3 short paragraphs):
           - Opening: Brief acknowledgment that you reached out before (don't be apologetic, just matter-of-fact)
           - Middle: {angle['approach']}
           - Closing: Soft CTA - offer value, ask a question, or offer to remove from list if not interested
           - Sign-off: "Best regards, Akshat Sharma"
        
        WRITING GUIDELINES:
        - Write in first person as Akshat Sharma
        - Don't be pushy or salesy
        - Be respectful of their time
        - Keep it shorter than the original email
        - Use {angle['tone']} tone
        - If this is follow-up #3, offer to remove them from the list if not interested
        - Focus on being helpful, not just selling
        
        IMPORTANT RULES:
        - Never apologize for following up (it's normal business practice)
        - Don't mention how many times you've emailed
        - Keep it brief and valuable
        - End with a question or soft CTA
        
        OUTPUT FORMAT:
        Respond ONLY with valid JSON, no markdown, no code blocks, no explanations.
        Format:
        {{"subject": "Your subject here", "body": "Your email body here"}}
        
        The body should use \\n for line breaks between paragraphs.
        """
    )

    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)
    text = response.text or "{}"

    import json
    import re

    # Clean the response - remove markdown code blocks if present
    text = text.strip()
    
    # Remove markdown code fences
    text = re.sub(r'^```(?:json)?\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    
    # Try to extract JSON from the text
    json_match = re.search(r'\{[^{}]*"subject"[^{}]*"body"[^{}]*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    try:
        data = json.loads(text)
        subject = data.get("subject", "").strip()
        body = data.get("body", "").strip()
        
        # Validate we got actual content
        if not subject:
            subject = f"Re: {lead.startup_name} hiring"
        if not body:
            # Fallback follow-up
            body = f"""Hi {lead.founder_name},

Just following up on my previous email about helping {lead.startup_name} automate your hiring outreach.

I know you're busy, but I wanted to share that I've helped similar startups cut their hiring time in half using AI automation.

Would you be open to a quick 15-minute call to see if this could work for you?

Best regards,
Akshat Sharma"""
            
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback: try to extract subject and body manually
        subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', text)
        body_match = re.search(r'"body"\s*:\s*"([^"]+)"', text, re.DOTALL)
        
        if subject_match and body_match:
            subject = subject_match.group(1).strip()
            body = body_match.group(1).strip()
            body = body.replace('\\n', '\n')
        else:
            # Last resort fallback
            subject = f"Re: {lead.startup_name} hiring"
            body = f"""Hi {lead.founder_name},

Just following up on my previous email about helping {lead.startup_name} automate your hiring outreach.

Would you be open to a quick chat?

Best regards,
Akshat Sharma"""
            print(f"Warning: Failed to parse Gemini follow-up response: {e}")

    return subject, body
