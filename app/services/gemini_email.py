from textwrap import dedent
from typing import Tuple

import google.generativeai as genai

from app.core.config import get_settings
from app.models.lead import Lead


settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)


def generate_outreach_email(lead: Lead) -> Tuple[str, str]:
    """
    Uses Gemini to generate a subject and body for an outreach email.
    Returns (subject, body).
    """
    prompt = dedent(
        f"""
        You are writing a cold outreach email as Akshat Sharma, a freelance AI automation specialist offering services to startup founders.

        YOUR IDENTITY:
        - Name: Akshat Sharma
        - Role: Freelance AI automation specialist / consultant
        - Offering: AI-powered hiring outreach automation services
        - Approach: Personal, direct, and results-focused

        LEAD INFORMATION:
        - Founder Name: {lead.founder_name}
        - Startup Name: {lead.startup_name}
        - Hiring Role: {lead.hiring_role or "Not specified"}
        - Website: {lead.website or "Not provided"}
        - Context/Observation: {lead.observation or "No additional context"}

        YOUR TASK:
        Write a personal cold outreach email from Akshat Sharma that:
        
        1. SUBJECT LINE (max 50 characters):
           - Create curiosity or show clear value
           - Reference their startup name or role if relevant
           - Avoid spammy words (free, guarantee, etc.)
           - Examples: "Quick question about {lead.startup_name}", "{lead.founder_name} - hiring at {lead.startup_name}?", "Idea for {lead.startup_name}'s hiring"
        
        2. EMAIL BODY (120-150 words, 3-4 short paragraphs):
           - Opening: Personal hook referencing their startup, role, or a specific observation
           - Introduce yourself: Briefly mention you're Akshat, a freelance AI automation specialist
           - Value proposition: Explain how you can help them automate their hiring outreach with AI (faster hiring, better candidates, save time)
           - Social proof: Mention you've helped similar startups (be subtle, authentic)
           - Clear CTA: One simple ask - a quick call, chat, or reply to discuss how you can help
           - Sign-off: "Best regards" or "Cheers" followed by "Akshat Sharma"
        
        WRITING GUIDELINES:
        - Write in first person ("I", "my", "me") as Akshat Sharma
        - Use {lead.founder_name}'s name naturally in the first sentence
        - Reference {lead.startup_name} specifically (not generic "your startup")
        - If hiring_role is provided, acknowledge their hiring challenge and how you can help
        - If observation/context is provided, weave it into the personalization
        - Write like a real person - use contractions, natural language, be conversational
        - Be concise: busy founders skip long emails
        - Focus on THEIR benefit (faster hiring, better candidates, time saved)
        - Position yourself as a helpful freelancer, not a big company
        - End with a question to encourage replies
        - Sign off as "Akshat Sharma" or "Akshat"
        
        TONE:
        - Personal and authentic (you're a freelancer, not a corporation)
        - Professional but approachable
        - Confident but humble
        - Helpful and consultative
        - Respectful of their time
        - Direct and honest

        OUTPUT FORMAT:
        Respond ONLY with valid JSON, no markdown, no code blocks, no explanations.
        Format:
        {{"subject": "Your subject here", "body": "Your email body here"}}
        
        The body should use \\n for line breaks between paragraphs.
        Make sure to sign off as "Akshat Sharma" or "Akshat" at the end.
        """
    )

    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)
    text = response.text or "{}"

    import json
    import re

    # Clean the response - remove markdown code blocks if present
    text = text.strip()
    
    # Remove markdown code fences (```json ... ``` or ``` ... ```)
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
            subject = f"Quick idea for {lead.founder_name}'s hiring"
        if not body:
            raise ValueError("Empty body from Gemini")
            
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback: try to extract subject and body manually
        subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', text)
        body_match = re.search(r'"body"\s*:\s*"([^"]+)"', text, re.DOTALL)
        
        if subject_match and body_match:
            subject = subject_match.group(1).strip()
            body = body_match.group(1).strip()
            # Unescape newlines
            body = body.replace('\\n', '\n')
        else:
            # Last resort fallback
            subject = f"Quick idea for {lead.founder_name}'s hiring"
            body = f"""Hi {lead.founder_name},

I noticed {lead.startup_name} is hiring for {lead.hiring_role}. 

I help startups automate their hiring outreach with AI. Would you be open to a quick chat about how we could help accelerate your hiring process?

Best regards"""
            # Log the error for debugging
            print(f"Warning: Failed to parse Gemini response: {e}")
            print(f"Raw response: {text[:200]}...")

    return subject, body

