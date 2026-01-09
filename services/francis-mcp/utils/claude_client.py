"""
Claude AI client wrapper
Handles multilingual conversation processing
"""

import anthropic
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

async def process_with_claude(conversation: Dict[str, Any], user_message: str) -> str:
    """
    Process message with Claude AI

    Claude is inherently multilingual and will:
    - Automatically detect the user's language
    - Respond in the same language
    - Handle code-switching (mixing languages)
    - Understand regional variations (Indian English, Hinglish)

    Supported languages include:
    - English
    - Hindi (हिंदी)
    - Tamil (தமிழ்)
    - Telugu (తెలుగు)
    - Bengali (বাংলা)
    - Marathi (मराठी)
    - Gujarati (ગુજરાતી)
    - Kannada (ಕನ್ನಡ)
    - Malayalam (മലയാളം)
    - Punjabi (ਪੰਜਾਬੀ)
    - And 90+ other languages
    """
    try:
        from ..config import FRANCIS_SYSTEM_PROMPT

        # Build message history for Claude
        messages = []
        for msg in conversation.get("messages", []):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Call Claude API
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=FRANCIS_SYSTEM_PROMPT,
            messages=messages
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        raise
