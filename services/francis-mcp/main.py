"""
Francis MCP Server
Customer Interface Agent
Handles conversation, intent extraction, consent capture, and report delivery
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import logging
import anthropic
import os
import re
import uuid
import json

# Import database module
import database as db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Francis MCP - Customer Interface",
    description="Customer-facing conversation and intent extraction agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# Request/Response Models
class ConversationContext(BaseModel):
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    channel: str
    message: str
    conversation_summary: Optional[str] = None
    pending_questions: List[str] = []
    pending_consents: List[str] = []
    available_actions: List[str] = []
    current_phase: str = "intake"

class ExtractedData(BaseModel):
    gstin: Optional[str] = None
    pan: Optional[str] = None
    loan_amount_lakhs: Optional[float] = None
    loan_purpose: Optional[str] = None
    tenure_months: Optional[int] = None
    collateral_available: Optional[bool] = None
    customer_priority: Optional[str] = None
    consent_obtained: Optional[bool] = None

class ConsentRecord(BaseModel):
    type: str
    granted: bool
    method: str
    timestamp: str

class FrancisResponse(BaseModel):
    conversation_id: str
    customer_id: str
    response_to_customer: str
    extracted_data: ExtractedData
    consents_obtained: List[ConsentRecord]
    questions_answered: Dict[str, Any]
    action_requested: str  # trigger_cam_build, request_document, none
    next_questions: List[str]
    current_phase: str = "intake"

def extract_gstin(text: str) -> Optional[str]:
    """Extract GSTIN from text using regex"""
    pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_pan(text: str) -> Optional[str]:
    """Extract PAN from text using regex"""
    pattern = r'\b[A-Z]{5}\d{4}[A-Z]{1}\b'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_amount(text: str) -> Optional[float]:
    """Extract loan amount from text"""
    # Look for patterns like "50 lakh", "5 crore", "50L", "5cr"
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)\b', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b', 100),
        (r'(\d+(?:\.\d+)?)\s*million', 10)
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1)) * multiplier

    return None

FRANCIS_SYSTEM_PROMPT = """You are Francis, a helpful loan advisor for MSME businesses in India. Your role is to:

1. **Extract Information**: Identify GST number, PAN, loan amount, and purpose from customer messages
2. **Obtain Consents**: Ensure proper consent for credit bureau checks, data sharing, and communication
3. **Ask Qualifying Questions**: Gather information about collateral, tenure preference, and priorities
4. **Provide Guidance**: Explain the loan process clearly and handle questions professionally

**Regulatory Compliance**:
- DPDP Act: Always explain how data will be used BEFORE collecting it
- RBI DSA Guidelines: Never guarantee approval, only discuss eligibility
- Fair Lending: Present all options objectively, never push specific lenders
- Communication Consent: Get explicit opt-in for WhatsApp/SMS/Email

**Conversation Flow**:
1. Greet warmly and understand their loan need
2. Extract GST and PAN numbers (required for processing)
3. Obtain credit bureau consent (required by law)
4. Ask about loan amount, purpose, tenure
5. Ask about collateral availability
6. Understand their priority (low interest vs quick disbursal vs low EMI)
7. Once all data collected, inform them we'll assess their eligibility

**Guidelines**:
- Be conversational and warm, not robotic
- Use simple language, avoid jargon
- If customer shares GST/PAN, confirm you've noted it
- Always explain WHY you need information
- If customer hesitates on consent, explain the legal requirements
- Never make promises about approval or interest rates
- Be patient if they need time to gather documents

**Error Handling**:
- If invalid GST/PAN format, politely ask them to check and resend
- If they're confused, break down the process step-by-step
- If they have concerns, address them before proceeding
"""

async def process_with_claude(context: ConversationContext) -> Dict[str, Any]:
    """Process customer message using Claude AI"""

    # Build context for Claude
    user_message = f"""
Customer Message: {context.message}

Current Phase: {context.current_phase}
Pending Consents: {', '.join(context.pending_consents) if context.pending_consents else 'None'}
Pending Questions: {', '.join(context.pending_questions) if context.pending_questions else 'None'}

Previous Context: {context.conversation_summary or 'This is the first message'}

Analyze this message and provide:
1. A warm, helpful response to the customer
2. Any data extracted (GST, PAN, loan amount, purpose, tenure, collateral, priority)
3. Any consents obtained (credit_bureau, lender_sharing, communication)
4. Any questions answered (collateral, tenure, priority)
5. What action to take next (trigger_cam_build if all data collected, request_document if missing info, none otherwise)
6. What questions to ask next

Respond in JSON format:
{{
    "response": "Your message to customer",
    "extracted": {{
        "gstin": "15-char GSTIN if found",
        "pan": "10-char PAN if found",
        "loan_amount_lakhs": number or null,
        "loan_purpose": "Working Capital/Term Loan/Equipment Finance if mentioned",
        "tenure_months": number or null,
        "collateral_available": true/false or null,
        "customer_priority": "low_interest/quick_disbursement/low_emi or null",
        "consent_obtained": true if credit bureau consent given
    }},
    "consents": [
        {{"type": "credit_bureau", "granted": true/false, "method": "explicit_yes"}}
    ],
    "answers": {{
        "collateral_available": "yes/no/value",
        "tenure_preference": number,
        "priority": "low_emi/short_tenure/low_interest/quick_disbursement"
    }},
    "next_action": "trigger_cam_build/request_document/none",
    "next_questions": ["What to ask next"]
}}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=FRANCIS_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": user_message
            }]
        )

        # Parse Claude's response
        response_text = message.content[0].text

        # Try to extract JSON from response
        import json
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            # Fallback if Claude doesn't return JSON
            result = {
                "response": response_text,
                "extracted": {},
                "consents": [],
                "answers": {},
                "next_action": "none",
                "next_questions": []
            }

        return result

    except Exception as e:
        logger.error(f"Claude processing error: {str(e)}")
        # Fallback to rule-based extraction
        return fallback_processing(context)

def fallback_processing(context: ConversationContext) -> Dict[str, Any]:
    """Fallback rule-based processing if Claude API unavailable"""

    message = context.message.lower()

    # Extract data
    extracted = {}
    gstin = extract_gstin(context.message)
    if gstin:
        extracted["gstin"] = gstin

    pan = extract_pan(context.message)
    if pan:
        extracted["pan"] = pan

    amount = extract_amount(message)
    if amount:
        extracted["loan_amount_lakhs"] = amount

    # Check for consent keywords
    consents = []
    if any(word in message for word in ["yes", "agree", "consent", "okay", "ok", "sure"]):
        if "credit" in message or "bureau" in message or "cibil" in message:
            consents.append({
                "type": "credit_bureau",
                "granted": True,
                "method": "explicit_yes"
            })

    # Check for answers
    answers = {}
    if "collateral" in message:
        if any(word in message for word in ["yes", "have", "property", "available"]):
            answers["collateral_available"] = "yes"
        elif any(word in message for word in ["no", "don't", "dont"]):
            answers["collateral_available"] = "no"

    # Determine response
    if not extracted.get("gstin"):
        response = "Thank you for reaching out! To help you with a business loan, I'll need your GST number. Could you please share your 15-digit GSTIN?"
        next_action = "none"
        next_questions = ["GST number"]
    elif not extracted.get("pan"):
        response = f"Great, I've noted your GST number ({extracted['gstin']}). I'll also need your company's PAN number. Could you share that?"
        next_action = "none"
        next_questions = ["PAN number"]
    elif not consents:
        response = "Perfect! To assess your eligibility, I need your permission to check your credit bureau report. This is a standard requirement by RBI. The report will help us find the best loan options for you. May I proceed with the credit check?"
        next_action = "none"
        next_questions = ["Credit bureau consent"]
    elif not extracted.get("loan_amount_lakhs"):
        response = "Thank you for the consent! How much loan amount are you looking for? Please mention in lakhs (e.g., 50 lakhs)."
        next_action = "none"
        next_questions = ["Loan amount"]
    else:
        response = "Excellent! I have all the information I need. Let me assess your eligibility across our partner lenders. This will take about 2-3 minutes. I'll get back to you with personalized loan options shortly."
        next_action = "trigger_cam_build"
        next_questions = []

    return {
        "response": response,
        "extracted": extracted,
        "consents": consents,
        "answers": answers,
        "next_action": next_action,
        "next_questions": next_questions
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "francis-mcp",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process-message", response_model=FrancisResponse)
async def process_message(context: ConversationContext):
    """
    Process customer message and return response with extracted data
    """
    try:
        # Generate UUIDs for new conversations
        if context.conversation_id is None:
            context.conversation_id = str(uuid.uuid4())
        if context.customer_id is None:
            context.customer_id = str(uuid.uuid4())

        logger.info(f"Processing message for conversation: {context.conversation_id}")

        # Load existing conversation state from database
        existing_state = db.get_conversation_state(context.conversation_id)
        if existing_state:
            # Merge existing extracted data with context
            existing_data = existing_state.get("extracted_data", {})
            context.conversation_summary = f"Previous data: GSTIN={existing_data.get('gstin')}, PAN={existing_data.get('pan')}, Amount={existing_data.get('loan_amount_lakhs')}L, Consent={existing_data.get('consent_obtained')}"
            context.current_phase = existing_state.get("current_phase", "intake")
            logger.info(f"Loaded existing conversation state: {context.conversation_summary}")
        else:
            # Create new conversation in database
            db.get_or_create_conversation(
                context.conversation_id,
                context.customer_id,
                context.channel
            )

        # Save user message to history
        db.append_message(context.conversation_id, "user", context.message)

        # Process with Claude (or fallback)
        if os.environ.get("ANTHROPIC_API_KEY"):
            result = await process_with_claude(context)
        else:
            logger.warning("No Anthropic API key, using fallback processing")
            result = fallback_processing(context)

        # Merge extracted data with existing data
        new_extracted = result.get("extracted", {})
        if existing_state:
            existing_data = existing_state.get("extracted_data", {}) or {}
            # Only update fields that have new values
            for key, value in new_extracted.items():
                if value is not None:
                    existing_data[key] = value
            merged_data = existing_data
        else:
            merged_data = new_extracted

        # Save assistant response to history
        db.append_message(context.conversation_id, "assistant", result["response"])

        # Update conversation state in database
        db.update_conversation(
            context.conversation_id,
            extracted_data=merged_data,
            current_phase=context.current_phase
        )

        # Save any new consents
        for consent in result.get("consents", []):
            db.save_consent(
                context.conversation_id,
                context.customer_id,
                consent["type"],
                consent["granted"],
                consent.get("method", "explicit_yes")
            )

        # Build response with merged data
        extracted_data = ExtractedData(**merged_data)

        consents_obtained = [
            ConsentRecord(
                type=c["type"],
                granted=c["granted"],
                method=c.get("method", "explicit_yes"),
                timestamp=datetime.now().isoformat()
            )
            for c in result.get("consents", [])
        ]

        return FrancisResponse(
            conversation_id=context.conversation_id,
            customer_id=context.customer_id,
            response_to_customer=result["response"],
            extracted_data=extracted_data,
            consents_obtained=consents_obtained,
            questions_answered=result.get("answers", {}),
            action_requested=result["next_action"],
            next_questions=result.get("next_questions", []),
            current_phase=context.current_phase
        )

    except Exception as e:
        logger.error(f"Message processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Assessment result models
class AssessmentResult(BaseModel):
    conversation_id: str
    assessment_id: str
    overall_eligibility: str
    max_eligible_amount: float
    top_lenders: List[str]
    customer_report: Dict[str, Any]

class AssessmentResponse(BaseModel):
    success: bool
    message_to_customer: str

@app.post("/receive-assessment", response_model=AssessmentResponse)
async def receive_assessment(result: AssessmentResult):
    """Receive assessment results from Kesha MCP"""
    try:
        logger.info(f"Received assessment for conversation: {result.conversation_id}")

        if result.overall_eligibility == "high":
            message = f"Great news! Based on your business profile, you're eligible for up to Rs {result.max_eligible_amount}L.\n\nTop Lender Options:\n" + \
                      "\n".join(f"{i+1}. {lender}" for i, lender in enumerate(result.top_lenders[:3]))
        elif result.overall_eligibility == "medium":
            message = f"Good news! You're eligible for up to Rs {result.max_eligible_amount}L.\n\nAvailable Lenders:\n" + \
                      "\n".join(f"{i+1}. {lender}" for i, lender in enumerate(result.top_lenders))
        elif result.overall_eligibility == "low":
            message = f"Thank you for your application. You have limited options with eligibility up to Rs {result.max_eligible_amount}L."
        else:
            message = "Thank you for your interest. Unfortunately, you don't meet the minimum requirements at this time."

        return AssessmentResponse(success=True, message_to_customer=message)

    except Exception as e:
        logger.error(f"Error processing assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/format-report")
async def format_report(
    assessment: Dict[str, Any],
    customer_preferences: Dict[str, Any],
    language: str = "english"
):
    """
    Format Kesha's assessment into customer-friendly report
    """
    try:
        logger.info("Formatting assessment report for customer")

        customer_report = assessment.get("customer_report", {})
        lender_matches = assessment.get("lender_matches", [])

        # Build formatted message
        report = f"""
🎉 Great news! Based on your business profile, here's what we found:

📊 **Your Eligibility**: {assessment.get("overall_eligibility", "").upper()}
💰 **Maximum Amount**: Up to ₹{assessment.get("max_eligible_amount_lakhs", 0)}L

✅ **Your Strengths**:
{chr(10).join(f'  • {s}' for s in customer_report.get("strengths", []))}

"""

        if customer_report.get("improvements"):
            report += f"""
💡 **Areas to Improve**:
{chr(10).join(f'  • {i}' for i in customer_report.get("improvements", []))}

"""

        report += f"""
🏦 **Top Lender Recommendations**:

"""

        for i, match in enumerate(lender_matches[:3], 1):
            report += f"""{i}. **{match.get("lender_name")}**
   • Amount: Up to ₹{match.get("eligible_amount_lakhs")}L
   • Interest Rate: {match.get("interest_rate_range")}
   • Approval Probability: {int(match.get("approval_probability", 0) * 100)}%
   • Tenure: {match.get("tenure_months")} months

"""

        report += f"""
📋 **Next Steps**:
{chr(10).join(f'  {i+1}. {step}' for i, step in enumerate(customer_report.get("next_steps", [])))}

Would you like to proceed with any of these lenders? I can help you with the application process!
"""

        return {
            "formatted_report": report,
            "key_highlights": customer_report.get("strengths", []),
            "recommended_lender": lender_matches[0].get("lender_name") if lender_matches else None
        }

    except Exception as e:
        logger.error(f"Report formatting failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
