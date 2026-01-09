"""
Conversation processing endpoint
Main customer interaction logic
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid

from utils.extraction import extract_gstin, extract_pan, extract_amount
from utils.claude_client import process_with_claude
from config import FRANCIS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Conversation"])

# Request/Response Models
class MessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    channel: str
    message: str

class MessageResponse(BaseModel):
    conversation_id: str
    customer_id: str
    response_to_customer: str
    extracted_data: Dict[str, Any]
    current_phase: str
    action_requested: Optional[str] = None

# In-memory conversation storage (replace with database in production)
conversations = {}

@router.post("/process-message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """
    Process customer message and return response

    This endpoint handles:
    - New conversation creation
    - Data extraction (GST, PAN, amount, etc.)
    - Consent capture
    - Phase progression
    - CAM build triggering
    """
    try:
        # Create new conversation if needed
        if not request.conversation_id:
            request.conversation_id = str(uuid.uuid4())
            request.customer_id = str(uuid.uuid4())
            conversations[request.conversation_id] = {
                "messages": [],
                "extracted_data": {},
                "phase": "intake",
                "created_at": datetime.now().isoformat()
            }
            logger.info(f"New conversation created: {request.conversation_id}")

        conv = conversations.get(request.conversation_id, {
            "messages": [],
            "extracted_data": {},
            "phase": "intake"
        })

        # Add user message to history
        conv["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })

        # Extract data from message
        extracted_data = conv.get("extracted_data", {})

        gstin = extract_gstin(request.message)
        if gstin:
            extracted_data["gstin"] = gstin
            logger.info(f"Extracted GSTIN: {gstin}")

        pan = extract_pan(request.message)
        if pan:
            extracted_data["pan"] = pan
            logger.info(f"Extracted PAN: {pan}")

        amount = extract_amount(request.message)
        if amount:
            extracted_data["loan_amount_lakhs"] = amount
            logger.info(f"Extracted amount: {amount}L")

        # Detect consent
        consent_keywords = ["yes", "agree", "consent", "okay", "sure", "proceed", "हां", "ठीक है"]
        if any(keyword in request.message.lower() for keyword in consent_keywords):
            if "credit bureau" in conv["messages"][-2]["content"].lower() if len(conv["messages"]) > 1 else False:
                extracted_data["consent_obtained"] = True
                logger.info("Credit bureau consent obtained")

        # Extract loan details
        if "working capital" in request.message.lower():
            extracted_data["loan_purpose"] = "Working Capital"
        elif "term loan" in request.message.lower():
            extracted_data["loan_purpose"] = "Term Loan"
        elif "equipment" in request.message.lower():
            extracted_data["loan_purpose"] = "Equipment Finance"

        # Extract tenure
        if "36" in request.message or "three year" in request.message.lower():
            extracted_data["tenure_months"] = 36
        elif "24" in request.message or "two year" in request.message.lower():
            extracted_data["tenure_months"] = 24
        elif "60" in request.message or "five year" in request.message.lower():
            extracted_data["tenure_months"] = 60

        # Collateral
        if "collateral" in request.message.lower():
            if any(word in request.message.lower() for word in ["yes", "have", "available"]):
                extracted_data["collateral_available"] = True
            elif any(word in request.message.lower() for word in ["no", "don't", "not"]):
                extracted_data["collateral_available"] = False

        # Priority
        if "low interest" in request.message.lower() or "lowest rate" in request.message.lower():
            extracted_data["customer_priority"] = "low_interest"
        elif "quick" in request.message.lower() or "fast" in request.message.lower():
            extracted_data["customer_priority"] = "quick_disbursement"

        conv["extracted_data"] = extracted_data

        # Process with Claude AI (or fallback to rule-based)
        try:
            response_text = await process_with_claude(conv, request.message)
        except Exception as e:
            logger.warning(f"Claude API unavailable, using fallback: {str(e)}")
            response_text = generate_fallback_response(extracted_data, conv["phase"])

        # Add assistant response to history
        conv["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })

        # Determine if we should trigger CAM build
        action_requested = None
        required_fields = ["gstin", "pan", "consent_obtained", "loan_amount_lakhs"]
        if all(field in extracted_data for field in required_fields):
            action_requested = "trigger_cam_build"
            conv["phase"] = "building"
            logger.info(f"All required data collected, triggering CAM build")

        # Update conversation
        conversations[request.conversation_id] = conv

        return MessageResponse(
            conversation_id=request.conversation_id,
            customer_id=request.customer_id,
            response_to_customer=response_text,
            extracted_data=extracted_data,
            current_phase=conv["phase"],
            action_requested=action_requested
        )

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_fallback_response(extracted_data: Dict, phase: str) -> str:
    """
    Generate rule-based response when Claude API is unavailable
    Supports multiple languages through simple template matching
    """
    if not extracted_data.get("gstin"):
        return "Thank you for your interest! To get started, could you please share your business's GSTIN (GST number)? / आपकी रुचि के लिए धन्यवाद! शुरू करने के लिए, क्या आप अपने व्यवसाय का GSTIN साझा कर सकते हैं?"

    if not extracted_data.get("pan"):
        return "Great! Now, could you please provide your PAN number? / बढ़िया! अब, क्या आप अपना PAN नंबर प्रदान कर सकते हैं?"

    if not extracted_data.get("consent_obtained"):
        return "To assess your eligibility, I need to check your credit profile. This will be a soft inquiry that won't affect your credit score. Your data will only be used for loan assessment. Do you consent to this credit bureau check? / आपकी पात्रता का आकलन करने के लिए, मुझे आपकी क्रेडिट प्रोफ़ाइल जांचनी होगी। क्या आप सहमत हैं?"

    if not extracted_data.get("loan_amount_lakhs"):
        return "How much loan amount are you looking for? Please specify in lakhs. / आप कितनी ऋण राशि की तलाश में हैं?"

    if not extracted_data.get("loan_purpose"):
        return "What is the purpose of the loan? (e.g., Working Capital, Equipment, Business Expansion) / ऋण का उद्देश्य क्या है?"

    return "Thank you! I'm now processing your application. This will take a few moments... / धन्यवाद! मैं अब आपके आवेदन पर काम कर रहा हूं..."
