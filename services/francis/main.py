"""
Francis MCP - Conversational AI Service
Port: 8000

Handles customer conversations for loan applications:
- Natural language processing via Claude AI
- Intent extraction (GSTIN, PAN, loan amount, purpose)
- Consent capture (DPDP Act compliant)
- Triggers CAM build workflow via n8n
- Receives and presents assessment results
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uvicorn
import uuid
import os
import re
import httpx
import sys

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
try:
    from supabase_client import ConversationDB, ConsentDB, CreditAssessmentDB, CAMRecordDB, get_client
    SUPABASE_CLIENT_AVAILABLE = True
except ImportError:
    SUPABASE_CLIENT_AVAILABLE = False
    ConversationDB = None
    ConsentDB = None
    CreditAssessmentDB = None
    CAMRecordDB = None

# Anthropic imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

app = FastAPI(
    title="Francis MCP - Conversational AI",
    description="AI-powered loan application conversation handler",
    version="1.0.0"
)

# CORS middleware - Whitelist specific origins for security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Environment configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/cam-build-trigger")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Anthropic client if available
anthropic_client = None
if ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ===========================================
# MODELS
# ===========================================

class Channel(str, Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    APP = "app"

class Phase(str, Enum):
    INTAKE = "intake"
    ASSESSING = "assessing"
    ASSESSED = "assessed"
    SUBMITTED = "submitted"

class ActionRequested(str, Enum):
    NONE = "none"
    TRIGGER_CAM_BUILD = "trigger_cam_build"
    REQUEST_DOCUMENT = "request_document"
    AWAIT_CONSENT = "await_consent"
    SELECT_LENDER = "select_lender"

class ProcessMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    channel: Channel = Channel.WEB
    message: str
    current_phase: Phase = Phase.INTAKE
    pending_questions: List[str] = []
    pending_consents: List[str] = []
    extracted_data: Optional[Dict[str, Any]] = {}
    ip_address: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = {}

class ExtractedData(BaseModel):
    gstin: Optional[str] = None
    pan: Optional[str] = None
    loan_amount_lakhs: Optional[float] = None
    loan_purpose: Optional[str] = None
    tenure_months: Optional[int] = None
    collateral_available: Optional[bool] = None
    customer_priority: Optional[str] = None

class ConsentObtained(BaseModel):
    consent_type: str
    granted: bool
    timestamp: str
    method: str

class ProcessMessageResponse(BaseModel):
    conversation_id: str
    response_to_customer: str
    extracted_data: Dict[str, Any]
    consents_obtained: List[ConsentObtained]
    action_requested: ActionRequested
    next_questions: List[str]
    current_phase: Phase
    ready_for_assessment: bool

class AssessmentReceiveRequest(BaseModel):
    conversation_id: str
    assessment_id: str
    overall_eligibility: str
    lender_matches: List[Dict[str, Any]]
    customer_report: Dict[str, Any]

class LoanSubmitRequest(BaseModel):
    gstin: str
    pan: str
    loan_amount_lakhs: float
    loan_purpose: str
    tenure_months: Optional[int] = 36
    collateral_available: Optional[bool] = False
    customer_priority: Optional[str] = "low_interest"
    
    @validator('gstin')
    def validate_gstin(cls, v):
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid GSTIN format')
        return v
    
    @validator('pan')
    def validate_pan(cls, v):
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pattern, v.upper()):
            raise ValueError('Invalid PAN format')
        return v.upper()

class LoanSubmitResponse(BaseModel):
    application_id: str
    conversation_id: str
    status: str
    estimated_time_seconds: int
    message: str

# ===========================================
# CONVERSATION STORAGE (Supabase with in-memory fallback)
# ===========================================

# In-memory cache for performance and fallback
_conversation_cache: Dict[str, Dict] = {}

def get_conversation(conversation_id: str, customer_id: str = None) -> Dict:
    """Get or create conversation with Supabase persistence"""
    # Check cache first
    if conversation_id in _conversation_cache:
        return _conversation_cache[conversation_id]

    # Try to fetch from Supabase
    if SUPABASE_CLIENT_AVAILABLE and ConversationDB:
        db_conv = ConversationDB.get(conversation_id)
        if db_conv:
            # Convert DB format to internal format
            conv = {
                "id": db_conv["id"],
                "customer_id": db_conv.get("customer_id"),
                "messages": db_conv.get("message_history", []),
                "extracted_data": db_conv.get("extracted_data", {}),
                "consents": [],
                "phase": db_conv.get("current_phase", "intake"),
                "created_at": db_conv.get("created_at"),
                "business_data": db_conv.get("extracted_data", {}).get("business_data", {}),
                "assessment": db_conv.get("extracted_data", {}).get("assessment")
            }
            _conversation_cache[conversation_id] = conv
            return conv

    # Create new conversation
    new_conv = {
        "id": conversation_id,
        "customer_id": customer_id or str(uuid.uuid4()),
        "messages": [],
        "extracted_data": {},
        "consents": [],
        "phase": "intake",
        "created_at": datetime.utcnow().isoformat()
    }

    # Persist to Supabase
    if SUPABASE_CLIENT_AVAILABLE and ConversationDB:
        db_result = ConversationDB.create(
            customer_id=new_conv["customer_id"],
            channel="web",
            initial_data={}
        )
        if db_result:
            new_conv["id"] = db_result["id"]
            conversation_id = db_result["id"]

    _conversation_cache[conversation_id] = new_conv
    return new_conv

def update_conversation(conversation_id: str, data: Dict):
    """Update conversation data with Supabase persistence"""
    # Update cache
    if conversation_id in _conversation_cache:
        _conversation_cache[conversation_id].update(data)

    # Persist to Supabase
    if SUPABASE_CLIENT_AVAILABLE and ConversationDB:
        # Map internal format to DB format
        db_updates = {}
        if "phase" in data:
            db_updates["current_phase"] = data["phase"]
        if "extracted_data" in data:
            db_updates["extracted_data"] = data["extracted_data"]
        if "messages" in data:
            db_updates["message_history"] = data["messages"]
            db_updates["last_message_at"] = datetime.utcnow().isoformat()

        if db_updates:
            ConversationDB.update(conversation_id, db_updates)

def save_consent_to_db(conversation_id: str, consent_type: str, granted: bool,
                       ip_address: str = None, device_info: Dict = None):
    """Persist consent to Supabase for DPDP compliance"""
    if SUPABASE_CLIENT_AVAILABLE and ConsentDB:
        ConsentDB.create(
            conversation_id=conversation_id,
            consent_type=consent_type,
            granted=granted,
            capture_method="text",
            ip_address=ip_address,
            device_info=device_info
        )

# ===========================================
# EXTRACTION FUNCTIONS
# ===========================================

def extract_gstin(text: str) -> Optional[str]:
    """Extract GSTIN from text"""
    pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_pan(text: str) -> Optional[str]:
    """Extract PAN from text"""
    pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None

def extract_loan_amount(text: str) -> Optional[float]:
    """Extract loan amount from text"""
    # Handle various formats: "50 lakh", "50L", "50 lakhs", "₹50L"
    patterns = [
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b',
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b',
    ]
    
    text_lower = text.lower()
    
    for pattern in patterns[:1]:  # Lakhs pattern
        match = re.search(pattern, text_lower)
        if match:
            return float(match.group(1))
    
    for pattern in patterns[1:]:  # Crore pattern
        match = re.search(pattern, text_lower)
        if match:
            return float(match.group(1)) * 100  # Convert to lakhs
    
    return None

def extract_loan_purpose(text: str) -> Optional[str]:
    """Extract loan purpose from text"""
    purposes = {
        "working capital": ["working capital", "wc", "day to day", "operational"],
        "term loan": ["term loan", "expansion", "business expansion"],
        "equipment finance": ["equipment", "machinery", "machine"],
        "invoice discounting": ["invoice", "receivables", "bills"],
        "overdraft": ["overdraft", "od", "cc", "cash credit"]
    }
    
    text_lower = text.lower()
    
    for purpose, keywords in purposes.items():
        if any(kw in text_lower for kw in keywords):
            return purpose.replace(" ", "_")
    
    return None

def check_consent_given(text: str) -> bool:
    """Check if user has given consent"""
    affirmatives = ["yes", "agree", "i agree", "i consent", "proceed", "ok", "okay", "sure", "go ahead", "haan", "ha", "ji"]
    return any(word in text.lower() for word in affirmatives)

# ===========================================
# CLAUDE AI INTEGRATION
# ===========================================

SYSTEM_PROMPT = """You are Francis, a knowledgeable and friendly loan advisor helping Indian MSMEs get business financing. You have deep knowledge about business lending, GST compliance, credit scores, and the MSME ecosystem in India.

## Your Personality
- Warm and encouraging, but also professional and credible
- You demonstrate knowledge by referencing specific details about the customer's business
- You speak naturally, not like a checklist bot
- You can explain financial concepts simply when needed
- You mix English and Hindi naturally when appropriate (e.g., "Bahut accha!" or "Theek hai")

## Current Conversation Context
{conversation_context}

## Business Knowledge (if available)
{business_context}

## What You Know About This Customer
{customer_summary}

## Application Status
- Phase: {phase}
- Data collected: {data_status}
- Still needed: {missing_items}

## Guidelines
- Reference specific business details when you have them (e.g., "I see your business has been registered since 2019 - that's great for lender confidence!")
- If you have their turnover/revenue data, mention it naturally in context
- When asking for information, explain briefly why it matters for their loan
- Keep responses conversational - 2-3 sentences usually, but can be longer when explaining something important
- Never promise approval - use phrases like "looking positive", "strong eligibility", "good chances"
- If assessment results are available, discuss them knowledgeably

Respond naturally to the customer's message, using your knowledge of their business to make the conversation feel personalized."""


def build_business_context(conversation: Dict) -> str:
    """Build rich business context from available data for Claude."""

    business_data = conversation.get("business_data", {})
    assessment = conversation.get("assessment", {})
    extracted = conversation.get("extracted_data", {})

    if not business_data and not assessment:
        return "No business data retrieved yet - still in information gathering phase."

    context_parts = []

    # GST Information
    gst_data = business_data.get("gst", {})
    if gst_data:
        context_parts.append(f"""**GST Profile:**
- Legal Name: {gst_data.get('legal_name', 'N/A')}
- Trade Name: {gst_data.get('trade_name', 'N/A')}
- Business Type: {gst_data.get('constitution_of_business', 'N/A')}
- Registration Date: {gst_data.get('registration_date', 'N/A')}
- Status: {gst_data.get('status', 'N/A')}
- Principal Place: {gst_data.get('principal_place_of_business', 'N/A')}""")

        # GST Financials
        financials = gst_data.get("financials", {})
        if financials:
            context_parts.append(f"""**GST Filing & Revenue:**
- Annual Turnover: ₹{financials.get('annual_turnover_lakhs', 'N/A')} Lakhs
- Average Monthly Sales: ₹{financials.get('avg_monthly_sales_lakhs', 'N/A')} Lakhs
- Filing Compliance: {financials.get('filing_compliance_percent', 'N/A')}%
- Returns Filed (Last 12 months): {financials.get('returns_filed_count', 'N/A')}/12""")

    # Credit Bureau Data
    bureau_data = business_data.get("credit_bureau", {})
    if bureau_data:
        commercial = bureau_data.get("commercial_score", {})
        consumer = bureau_data.get("consumer_score", {})
        context_parts.append(f"""**Credit Profile:**
- Commercial Credit Score (CMR): {commercial.get('score', 'N/A')} ({commercial.get('rating', 'N/A')})
- Consumer Credit Score (CIBIL): {consumer.get('score', 'N/A')}
- Active Loans: {bureau_data.get('active_loans', 'N/A')}
- Payment History: {bureau_data.get('payment_history_summary', 'N/A')}
- Credit Utilization: {bureau_data.get('credit_utilization_percent', 'N/A')}%""")

    # Udyam Registration
    udyam_data = business_data.get("udyam", {})
    if udyam_data:
        context_parts.append(f"""**MSME Registration (Udyam):**
- Udyam Number: {udyam_data.get('udyam_number', 'N/A')}
- Enterprise Type: {udyam_data.get('enterprise_type', 'N/A')} ({udyam_data.get('classification', 'N/A')})
- Major Activity: {udyam_data.get('major_activity', 'N/A')}
- NIC Code: {udyam_data.get('nic_code', 'N/A')}
- Date of Registration: {udyam_data.get('date_of_registration', 'N/A')}""")

    # Assessment Results
    if assessment:
        lender_matches = assessment.get("lender_matches", [])
        context_parts.append(f"""**Eligibility Assessment:**
- Overall Eligibility: {assessment.get('eligibility', 'N/A').upper()}
- Matched Lenders: {len(lender_matches)}""")

        if lender_matches:
            top_3 = lender_matches[:3]
            lender_summary = []
            for lender in top_3:
                lender_summary.append(
                    f"  - {lender.get('lender_name')}: ₹{lender.get('eligible_amount_lakhs')}L "
                    f"@ {lender.get('interest_rate_range')} "
                    f"({int(lender.get('approval_probability', 0) * 100)}% approval chance)"
                )
            context_parts.append("**Top Lender Matches:**\n" + "\n".join(lender_summary))

        # Customer report insights
        customer_report = assessment.get("customer_report", {})
        if customer_report.get("strengths"):
            context_parts.append("**Business Strengths:** " + ", ".join(customer_report["strengths"][:3]))
        if customer_report.get("improvement_areas"):
            context_parts.append("**Areas to Improve:** " + ", ".join(customer_report["improvement_areas"][:2]))

    return "\n\n".join(context_parts) if context_parts else "Business data being processed..."


def build_customer_summary(extracted_data: Dict) -> str:
    """Build a natural language summary of what we know about the customer."""

    if not extracted_data:
        return "New customer - no information collected yet."

    parts = []

    if extracted_data.get("gstin"):
        parts.append(f"GSTIN: {extracted_data['gstin']}")

    if extracted_data.get("pan"):
        parts.append(f"PAN: {extracted_data['pan']}")

    if extracted_data.get("loan_amount_lakhs"):
        parts.append(f"Requested loan: ₹{extracted_data['loan_amount_lakhs']} Lakhs")

    if extracted_data.get("loan_purpose"):
        purpose_display = extracted_data["loan_purpose"].replace("_", " ").title()
        parts.append(f"Purpose: {purpose_display}")

    if extracted_data.get("tenure_months"):
        parts.append(f"Tenure: {extracted_data['tenure_months']} months")

    if extracted_data.get("collateral_available"):
        parts.append("Has collateral available")

    if extracted_data.get("credit_bureau_consent"):
        parts.append("✓ Credit check consent given")

    return " | ".join(parts) if parts else "No information collected yet."


def build_conversation_context(messages: List[Dict], max_messages: int = 10) -> str:
    """Build conversation history for context."""

    if not messages:
        return "This is the start of the conversation."

    recent = messages[-max_messages:]
    formatted = []

    for msg in recent:
        role = "Customer" if msg.get("role") == "user" else "Francis"
        content = msg.get("content", "")
        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "..."
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)

async def get_claude_response(
    user_message: str,
    conversation: Dict,
    missing_fields: List[str],
    pending_consent: bool
) -> str:
    """Get response from Claude AI with full conversation context."""

    extracted_data = conversation.get("extracted_data", {})

    if not anthropic_client:
        return generate_fallback_response(extracted_data, missing_fields, pending_consent)

    try:
        # Build rich context for Claude
        messages_history = conversation.get("messages", [])
        business_context = build_business_context(conversation)
        customer_summary = build_customer_summary(extracted_data)
        conversation_context = build_conversation_context(messages_history)

        # Determine phase description
        phase = conversation.get("phase", "intake")
        phase_descriptions = {
            "intake": "Gathering application information",
            "assessing": "Processing assessment - data being analyzed",
            "assessed": "Assessment complete - discussing results",
            "submitted": "Application submitted to lender"
        }
        phase_desc = phase_descriptions.get(phase, phase)

        # Determine data status
        collected = [k for k in ["gstin", "pan", "loan_amount_lakhs", "loan_purpose"] if k in extracted_data]
        data_status = f"{len(collected)}/4 required fields" + (", consent obtained" if extracted_data.get("credit_bureau_consent") else "")

        # Build missing items description
        missing_display = []
        if "gstin" in missing_fields:
            missing_display.append("GSTIN (15-char GST number)")
        if "pan" in missing_fields:
            missing_display.append("PAN (10-char)")
        if "loan_amount" in missing_fields:
            missing_display.append("Loan amount")
        if "loan_purpose" in missing_fields:
            missing_display.append("Loan purpose")
        if pending_consent:
            missing_display.append("Credit bureau consent")

        missing_items = ", ".join(missing_display) if missing_display else "None - ready for assessment!"

        # Format system prompt with all context
        system = SYSTEM_PROMPT.format(
            conversation_context=conversation_context,
            business_context=business_context,
            customer_summary=customer_summary,
            phase=phase_desc,
            data_status=data_status,
            missing_items=missing_items
        )

        # Build messages array with history
        claude_messages = []

        # Include recent conversation history (last 8 exchanges)
        for msg in messages_history[-16:]:  # 8 user + 8 assistant = 16
            role = msg.get("role")
            if role in ["user", "assistant"]:
                claude_messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        # Add current user message
        claude_messages.append({"role": "user", "content": user_message})

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,  # Increased for richer responses
            system=system,
            messages=claude_messages
        )

        return response.content[0].text
    except Exception as e:
        print(f"Claude API error: {e}")
        return generate_fallback_response(extracted_data, missing_fields, pending_consent)

def generate_fallback_response(
    extracted_data: Dict,
    missing_fields: List[str],
    pending_consent: bool
) -> str:
    """Generate response without Claude"""
    
    if pending_consent:
        return ("To proceed with your loan application, we need to check your credit history. "
                "Do you consent to a credit bureau inquiry? Please reply with 'Yes' to continue.")
    
    if "gstin" in missing_fields:
        return ("Thank you for your interest in a business loan! "
                "To get started, could you please share your GSTIN (15-character GST number)?")
    
    if "pan" in missing_fields:
        return ("Great, I have your GST details. "
                "Could you please share your business PAN (10-character alphanumeric)?")
    
    if "loan_amount" in missing_fields:
        return ("Perfect! How much loan amount are you looking for? "
                "Please specify in lakhs (e.g., '50 lakhs' or '1 crore').")
    
    if "loan_purpose" in missing_fields:
        return ("What is the primary purpose of this loan? "
                "Common uses include: Working Capital, Term Loan, Equipment Finance, etc.")
    
    # All data collected
    return ("Excellent! I have all the information needed. "
            "Processing your application now. This will take just a moment...")

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "francis",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "claude_available": anthropic_client is not None
    }

@app.post("/process-message", response_model=ProcessMessageResponse)
async def process_message(request: ProcessMessageRequest):
    """
    Process a customer message and return AI response.
    
    This is the main conversation endpoint that:
    1. Extracts any data from the message
    2. Updates conversation state
    3. Generates appropriate response
    4. Determines next action
    """
    
    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    conversation = get_conversation(conversation_id)
    
    # Merge existing extracted data
    extracted_data = {**conversation.get("extracted_data", {}), **(request.extracted_data or {})}
    
    # Extract new data from message
    message = request.message
    
    new_gstin = extract_gstin(message)
    if new_gstin:
        extracted_data["gstin"] = new_gstin
    
    new_pan = extract_pan(message)
    if new_pan:
        extracted_data["pan"] = new_pan
    
    new_amount = extract_loan_amount(message)
    if new_amount:
        extracted_data["loan_amount_lakhs"] = new_amount
    
    new_purpose = extract_loan_purpose(message)
    if new_purpose:
        extracted_data["loan_purpose"] = new_purpose
    
    # Check for consent
    consents_obtained = []
    consent_needed = ("credit_bureau" in request.pending_consents or 
                     ("gstin" in extracted_data and "pan" in extracted_data and 
                      "credit_bureau_consent" not in extracted_data))
    
    if consent_needed and check_consent_given(message):
        extracted_data["credit_bureau_consent"] = True
        consents_obtained.append(ConsentObtained(
            consent_type="credit_bureau",
            granted=True,
            timestamp=datetime.utcnow().isoformat(),
            method="text"
        ))
        # Persist consent to database for DPDP Act 2023 compliance
        save_consent_to_db(
            conversation_id=conversation_id,
            consent_type="credit_bureau",
            granted=True,
            ip_address=request.ip_address,
            device_info=request.device_info
        )
    
    # Determine missing fields
    missing_fields = []
    if "gstin" not in extracted_data:
        missing_fields.append("gstin")
    if "pan" not in extracted_data:
        missing_fields.append("pan")
    if "loan_amount_lakhs" not in extracted_data:
        missing_fields.append("loan_amount")
    if "loan_purpose" not in extracted_data:
        missing_fields.append("loan_purpose")
    
    # Determine if consent is pending
    pending_consent = (not missing_fields and 
                      "credit_bureau_consent" not in extracted_data)
    
    # Update conversation with extracted data before generating response
    conversation["extracted_data"] = extracted_data

    # Generate response with full conversation context
    response_text = await get_claude_response(
        message,
        conversation,
        missing_fields,
        pending_consent
    )
    
    # Determine action and phase
    ready_for_assessment = (not missing_fields and 
                           extracted_data.get("credit_bureau_consent", False))
    
    if ready_for_assessment:
        action = ActionRequested.TRIGGER_CAM_BUILD
        phase = Phase.ASSESSING
    elif pending_consent:
        action = ActionRequested.AWAIT_CONSENT
        phase = Phase.INTAKE
    else:
        action = ActionRequested.NONE
        phase = Phase.INTAKE
    
    # Update conversation
    conversation["extracted_data"] = extracted_data
    conversation["phase"] = phase.value
    conversation["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    conversation["messages"].append({
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Persist to database
    update_conversation(conversation_id, {
        "phase": phase.value,
        "extracted_data": extracted_data,
        "messages": conversation["messages"]
    })

    # Determine next questions
    next_questions = []
    if missing_fields:
        next_questions = missing_fields[:1]  # Ask one at a time
    elif pending_consent:
        next_questions = ["credit_bureau_consent"]
    
    return ProcessMessageResponse(
        conversation_id=conversation_id,
        response_to_customer=response_text,
        extracted_data=extracted_data,
        consents_obtained=consents_obtained,
        action_requested=action,
        next_questions=next_questions,
        current_phase=phase,
        ready_for_assessment=ready_for_assessment
    )

@app.post("/receive-assessment")
async def receive_assessment(request: AssessmentReceiveRequest):
    """
    Receive assessment results from n8n/Kesha.

    Updates conversation with results and prepares customer-facing message.
    Persists assessment to database for compliance and audit trail.
    """

    conversation = get_conversation(request.conversation_id)

    # Store assessment results in conversation
    assessment_data = {
        "id": request.assessment_id,
        "eligibility": request.overall_eligibility,
        "lender_matches": request.lender_matches,
        "customer_report": request.customer_report,
        "received_at": datetime.utcnow().isoformat()
    }
    conversation["assessment"] = assessment_data
    conversation["phase"] = "assessed"

    # Persist assessment to database for compliance audit trail
    if SUPABASE_CLIENT_AVAILABLE and CreditAssessmentDB:
        try:
            max_amount = 0
            if request.lender_matches:
                max_amount = max(lm.get("eligible_amount_lakhs", 0) for lm in request.lender_matches)

            CreditAssessmentDB.create(
                cam_id=request.assessment_id,
                conversation_id=request.conversation_id,
                overall_eligibility=request.overall_eligibility,
                max_eligible_amount_lakhs=max_amount,
                lender_matches=request.lender_matches,
                customer_report=request.customer_report
            )
        except Exception as e:
            print(f"Warning: Could not persist assessment to database: {e}")

    # Persist conversation state
    update_conversation(request.conversation_id, {
        "phase": "assessed",
        "extracted_data": {
            **conversation.get("extracted_data", {}),
            "assessment": assessment_data
        }
    })

    # Generate customer-facing result message
    if request.lender_matches:
        top_lender = request.lender_matches[0]
        message = f"""Great news! Based on your business profile, you're eligible for loans from {len(request.lender_matches)} lender(s)!

Top recommendation: **{top_lender['lender_name']}**
- Eligible amount: ₹{top_lender['eligible_amount_lakhs']} Lakhs
- Interest rate: {top_lender['interest_rate_range']}
- Approval probability: {int(top_lender['approval_probability'] * 100)}%

Would you like to proceed with this lender or see other options?"""
    else:
        message = """Based on your current profile, we're working on finding the best options for you.

Our team will review your application and get back to you with recommendations. In the meantime, you can improve your eligibility by:
1. Ensuring all GST returns are filed
2. Maintaining good payment records
3. Registering on Udyam portal if not done"""

    conversation["messages"].append({
        "role": "assistant",
        "content": message,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Persist messages
    update_conversation(request.conversation_id, {"messages": conversation["messages"]})

    return {
        "status": "success",
        "message_delivered": True,
        "next_phase": "assessed"
    }


class BusinessDataRequest(BaseModel):
    """Request model for receiving business data from n8n."""
    conversation_id: str
    gst_data: Optional[Dict[str, Any]] = None
    credit_bureau_data: Optional[Dict[str, Any]] = None
    udyam_data: Optional[Dict[str, Any]] = None
    pan_data: Optional[Dict[str, Any]] = None


@app.post("/receive-business-data")
async def receive_business_data(request: BusinessDataRequest):
    """
    Receive enriched business data from n8n after data services calls.

    This endpoint is called by n8n after it fetches GST, credit bureau,
    and Udyam data. This allows Francis to have rich business context
    for more intelligent conversations even before assessment completes.
    """

    conversation = get_conversation(request.conversation_id)

    # Initialize or update business_data
    if "business_data" not in conversation:
        conversation["business_data"] = {}

    # Store each data type if provided
    if request.gst_data:
        conversation["business_data"]["gst"] = request.gst_data

    if request.credit_bureau_data:
        conversation["business_data"]["credit_bureau"] = request.credit_bureau_data

    if request.udyam_data:
        conversation["business_data"]["udyam"] = request.udyam_data

    if request.pan_data:
        conversation["business_data"]["pan"] = request.pan_data

    conversation["business_data"]["last_updated"] = datetime.utcnow().isoformat()

    # Extract useful summary data into extracted_data for quick reference
    extracted = conversation.get("extracted_data", {})

    # Enrich extracted_data with business insights
    if request.gst_data:
        if request.gst_data.get("legal_name"):
            extracted["business_name"] = request.gst_data["legal_name"]
        financials = request.gst_data.get("financials", {})
        if financials.get("annual_turnover_lakhs"):
            extracted["annual_turnover_lakhs"] = financials["annual_turnover_lakhs"]

    if request.credit_bureau_data:
        commercial = request.credit_bureau_data.get("commercial_score", {})
        consumer = request.credit_bureau_data.get("consumer_score", {})
        if commercial.get("score"):
            extracted["commercial_credit_score"] = commercial["score"]
        if consumer.get("score"):
            extracted["consumer_credit_score"] = consumer["score"]

    if request.udyam_data:
        if request.udyam_data.get("enterprise_type"):
            extracted["enterprise_type"] = request.udyam_data["enterprise_type"]
        if request.udyam_data.get("udyam_number"):
            extracted["udyam_number"] = request.udyam_data["udyam_number"]

    conversation["extracted_data"] = extracted

    return {
        "status": "success",
        "conversation_id": request.conversation_id,
        "data_received": {
            "gst": request.gst_data is not None,
            "credit_bureau": request.credit_bureau_data is not None,
            "udyam": request.udyam_data is not None,
            "pan": request.pan_data is not None
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/loan/submit", response_model=LoanSubmitResponse)
async def submit_loan_application(request: LoanSubmitRequest):
    """
    Submit a new loan application directly (structured form).
    
    Creates conversation and triggers CAM build workflow.
    """
    
    conversation_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())
    
    # Create conversation with extracted data
    conversation = get_conversation(conversation_id)
    conversation["extracted_data"] = {
        "gstin": request.gstin,
        "pan": request.pan,
        "loan_amount_lakhs": request.loan_amount_lakhs,
        "loan_purpose": request.loan_purpose,
        "tenure_months": request.tenure_months,
        "collateral_available": request.collateral_available,
        "customer_priority": request.customer_priority,
        "credit_bureau_consent": True
    }
    conversation["phase"] = "assessing"
    conversation["application_id"] = application_id
    
    # Trigger n8n workflow (async)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "conversation_id": conversation_id,
                    "application_id": application_id,
                    "gstin": request.gstin,
                    "pan": request.pan,
                    "loan_amount_lakhs": request.loan_amount_lakhs,
                    "loan_purpose": request.loan_purpose,
                    "tenure_months": request.tenure_months,
                    "collateral_available": request.collateral_available,
                    "customer_priority": request.customer_priority
                },
                timeout=5.0
            )
    except Exception as e:
        # Log but don't fail - workflow can be triggered manually
        print(f"Warning: Could not trigger n8n workflow: {e}")
    
    return LoanSubmitResponse(
        application_id=application_id,
        conversation_id=conversation_id,
        status="processing",
        estimated_time_seconds=5,
        message="Your loan application is being processed. We'll have results in a few seconds."
    )

@app.get("/loan/status/{application_id}")
async def get_loan_status(application_id: str):
    """
    Get the status of a loan application.
    """
    
    # Find conversation by application_id
    for conv_id, conv in conversations.items():
        if conv.get("application_id") == application_id:
            assessment = conv.get("assessment")
            if assessment:
                return {
                    "application_id": application_id,
                    "conversation_id": conv_id,
                    "status": "assessed",
                    "phase": conv.get("phase"),
                    "eligibility": assessment.get("eligibility"),
                    "lender_matches_count": len(assessment.get("lender_matches", [])),
                    "customer_report": assessment.get("customer_report")
                }
            else:
                return {
                    "application_id": application_id,
                    "conversation_id": conv_id,
                    "status": "processing",
                    "phase": conv.get("phase"),
                    "message": "Assessment in progress..."
                }
    
    raise HTTPException(status_code=404, detail="Application not found")

@app.get("/conversation/{conversation_id}")
async def get_conversation_details(conversation_id: str):
    """
    Get full conversation details including message history.
    """
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = conversations[conversation_id]
    return {
        "conversation_id": conversation_id,
        "phase": conv.get("phase"),
        "extracted_data": conv.get("extracted_data", {}),
        "message_count": len(conv.get("messages", [])),
        "messages": conv.get("messages", [])[-10:],  # Last 10 messages
        "assessment": conv.get("assessment"),
        "created_at": conv.get("created_at")
    }

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
