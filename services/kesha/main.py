"""
Kesha MCP - Credit Assessor & Lender Matcher
Port: 8003

Assesses eligibility and matches borrowers with lenders:
- Evaluates against lender criteria
- Calculates eligible loan amounts
- Scores approval probability
- Ranks lenders by customer preference
- Generates customer-friendly reports

IMPORTANT: This service receives ONLY anonymized data (no PII)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uvicorn
import uuid

app = FastAPI(
    title="Kesha MCP - Credit Assessor",
    description="Credit assessment and lender matching service (PII-isolated)",
    version="1.0.0"
)

# CORS middleware - Restrict to internal services only
import os
INTERNAL_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://n8n:5678,http://francis:8000,http://localhost:5678").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=INTERNAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ===========================================
# LENDER DATA (Would be from DB in production)
# ===========================================

LENDERS = {
    "hdfc_bank": {
        "id": "hdfc_bank",
        "name": "HDFC Bank",
        "type": "private_bank",
        "min_turnover_lakhs": 50,
        "min_credit_score": 700,
        "max_dpd_days": 0,
        "min_years_in_business": 3,
        "max_loan_amount_lakhs": 100,
        "interest_rate_min": 11.0,
        "interest_rate_max": 14.0,
        "products": ["working_capital", "term_loan", "overdraft"],
        "processing_time_days": 7,
        "collateral_required_above_lakhs": 50
    },
    "icici_bank": {
        "id": "icici_bank",
        "name": "ICICI Bank",
        "type": "private_bank",
        "min_turnover_lakhs": 50,
        "min_credit_score": 680,
        "max_dpd_days": 0,
        "min_years_in_business": 2,
        "max_loan_amount_lakhs": 150,
        "interest_rate_min": 11.5,
        "interest_rate_max": 15.0,
        "products": ["working_capital", "term_loan", "equipment_finance"],
        "processing_time_days": 5,
        "collateral_required_above_lakhs": 75
    },
    "bajaj_finserv": {
        "id": "bajaj_finserv",
        "name": "Bajaj Finserv",
        "type": "nbfc",
        "min_turnover_lakhs": 10,
        "min_credit_score": 650,
        "max_dpd_days": 30,
        "min_years_in_business": 1,
        "max_loan_amount_lakhs": 80,
        "interest_rate_min": 14.0,
        "interest_rate_max": 18.0,
        "products": ["working_capital", "term_loan", "equipment_finance"],
        "processing_time_days": 3,
        "collateral_required_above_lakhs": 40
    },
    "ugro_capital": {
        "id": "ugro_capital",
        "name": "UGRO Capital",
        "type": "nbfc",
        "min_turnover_lakhs": 20,
        "min_credit_score": 600,
        "max_dpd_days": 60,
        "min_years_in_business": 1,
        "max_loan_amount_lakhs": 50,
        "interest_rate_min": 15.0,
        "interest_rate_max": 19.0,
        "products": ["working_capital", "term_loan"],
        "processing_time_days": 2,
        "collateral_required_above_lakhs": 30
    },
    "indifi": {
        "id": "indifi",
        "name": "Indifi",
        "type": "fintech",
        "min_turnover_lakhs": 5,
        "min_credit_score": 550,
        "max_dpd_days": 90,
        "min_years_in_business": 0,
        "max_loan_amount_lakhs": 30,
        "interest_rate_min": 18.0,
        "interest_rate_max": 24.0,
        "products": ["working_capital", "invoice_discounting"],
        "processing_time_days": 1,
        "collateral_required_above_lakhs": 20
    }
}

# ===========================================
# MODELS
# ===========================================

class EligibilityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INELIGIBLE = "ineligible"

class CustomerPriority(str, Enum):
    LOW_INTEREST = "low_interest"
    QUICK_DISBURSAL = "quick_disbursal"
    MAX_AMOUNT = "max_amount"

class BusinessProfile(BaseModel):
    industry_sector: str
    years_in_business: int
    annual_turnover_lakhs: float
    quarterly_trend: str
    msme_category: Optional[str] = None
    udyam_registered: bool = False

class FinancialMetrics(BaseModel):
    loan_to_turnover_pct: float
    debt_burden_ratio: float
    credit_utilization_pct: float
    monthly_average_lakhs: float

class CreditProfileInput(BaseModel):
    commercial_score: str
    commercial_score_numeric: int
    max_dpd_days: int
    active_loans: int
    total_outstanding_lakhs: float
    overdue_amount_lakhs: float

class LoanRequestInput(BaseModel):
    amount_requested_lakhs: float
    purpose: str
    tenure_months: int
    collateral_available: bool

class CustomerPreferences(BaseModel):
    priority: CustomerPriority = CustomerPriority.LOW_INTEREST

class AssessRequest(BaseModel):
    cam_id: str
    business_profile: BusinessProfile
    financial_metrics: FinancialMetrics
    credit_profile: CreditProfileInput
    loan_request: LoanRequestInput
    customer_preferences: Optional[CustomerPreferences] = None
    data_flags: Optional[List[Dict[str, Any]]] = []

class RejectionRisk(BaseModel):
    criteria: str
    current_value: Any
    required_value: Any
    severity: str

class LenderMatch(BaseModel):
    rank: int
    lender_id: str
    lender_name: str
    lender_type: str
    product: str
    eligible_amount_lakhs: float
    interest_rate_range: str
    tenure_months: int
    approval_probability: float
    processing_time_days: int
    collateral_required: bool
    rejection_risks: List[RejectionRisk] = []
    preference_score: float

class CustomerReportStrength(BaseModel):
    factor: str
    description: str
    impact: str

class CustomerReportImprovement(BaseModel):
    factor: str
    current_state: str
    recommendation: str
    impact_if_addressed: str

class CustomerReportNextStep(BaseModel):
    step: int
    action: str
    details: str

class CustomerReport(BaseModel):
    summary: str
    strengths: List[CustomerReportStrength]
    improvements: List[CustomerReportImprovement]
    next_steps: List[CustomerReportNextStep]

class AssessResponse(BaseModel):
    assessment_id: str
    cam_id: str
    overall_eligibility: EligibilityLevel
    max_eligible_amount_lakhs: float
    lender_matches: List[LenderMatch]
    customer_report: CustomerReport
    assessed_at: str

# ===========================================
# ASSESSMENT LOGIC
# ===========================================

def evaluate_lender_eligibility(
    lender: Dict,
    business: BusinessProfile,
    credit: CreditProfileInput,
    loan: LoanRequestInput
) -> tuple[bool, List[RejectionRisk], float]:
    """
    Evaluate if borrower meets lender's criteria.
    Returns (eligible, rejection_risks, probability)
    """
    
    risks = []
    probability = 100.0
    
    # Turnover check
    if business.annual_turnover_lakhs < lender["min_turnover_lakhs"]:
        risks.append(RejectionRisk(
            criteria="minimum_turnover",
            current_value=business.annual_turnover_lakhs,
            required_value=lender["min_turnover_lakhs"],
            severity="critical"
        ))
        probability -= 40
    
    # Credit score check
    if credit.commercial_score_numeric < lender["min_credit_score"]:
        severity = "critical" if credit.commercial_score_numeric < lender["min_credit_score"] - 50 else "high"
        risks.append(RejectionRisk(
            criteria="minimum_credit_score",
            current_value=credit.commercial_score_numeric,
            required_value=lender["min_credit_score"],
            severity=severity
        ))
        probability -= 30 if severity == "critical" else 15
    
    # DPD check
    if credit.max_dpd_days > lender["max_dpd_days"]:
        severity = "critical" if credit.max_dpd_days > 90 else "high" if credit.max_dpd_days > 60 else "medium"
        risks.append(RejectionRisk(
            criteria="max_dpd_days",
            current_value=credit.max_dpd_days,
            required_value=lender["max_dpd_days"],
            severity=severity
        ))
        probability -= 50 if severity == "critical" else 25 if severity == "high" else 10
    
    # Years in business check
    if business.years_in_business < lender["min_years_in_business"]:
        risks.append(RejectionRisk(
            criteria="years_in_business",
            current_value=business.years_in_business,
            required_value=lender["min_years_in_business"],
            severity="medium"
        ))
        probability -= 15
    
    # Overdue amount check
    if credit.overdue_amount_lakhs > 0:
        risks.append(RejectionRisk(
            criteria="active_overdue",
            current_value=credit.overdue_amount_lakhs,
            required_value=0,
            severity="high"
        ))
        probability -= 20
    
    # Eligible if no critical risks
    has_critical = any(r.severity == "critical" for r in risks)
    eligible = not has_critical
    
    return eligible, risks, max(probability, 0)

def calculate_eligible_amount(
    lender: Dict,
    business: BusinessProfile,
    loan: LoanRequestInput
) -> float:
    """Calculate maximum eligible loan amount"""
    
    # 20% of annual turnover rule
    max_by_turnover = business.annual_turnover_lakhs * 0.20
    
    # Lender's maximum
    max_by_lender = lender["max_loan_amount_lakhs"]
    
    # Customer's request
    requested = loan.amount_requested_lakhs
    
    # Return minimum of all three
    return min(max_by_turnover, max_by_lender, requested)

def calculate_preference_score(
    lender: Dict,
    priority: CustomerPriority,
    eligible_amount: float,
    probability: float
) -> float:
    """Calculate preference score based on customer priority"""
    
    score = 50  # Base score
    
    if priority == CustomerPriority.LOW_INTEREST:
        # Lower interest = higher score
        avg_rate = (lender["interest_rate_min"] + lender["interest_rate_max"]) / 2
        score += max(0, (20 - avg_rate) * 3)  # Max ~15 points for lowest rates
        
    elif priority == CustomerPriority.QUICK_DISBURSAL:
        # Faster processing = higher score
        score += max(0, (10 - lender["processing_time_days"]) * 5)  # Max ~45 points
        
    elif priority == CustomerPriority.MAX_AMOUNT:
        # Higher eligible amount = higher score
        score += min(eligible_amount / 10, 20)  # Max 20 points
    
    # Add probability factor
    score += probability * 0.3
    
    return round(score, 2)

def generate_customer_report(
    business: BusinessProfile,
    credit: CreditProfileInput,
    loan: LoanRequestInput,
    matches: List[LenderMatch],
    data_flags: List[Dict]
) -> CustomerReport:
    """Generate user-friendly customer report"""
    
    # Determine summary
    if len(matches) >= 3:
        summary = f"Great news! You're eligible for loans from {len(matches)} lenders. Your strong business profile and clean credit history make you an attractive borrower."
    elif len(matches) >= 1:
        summary = f"Good news! You qualify for loans from {len(matches)} lender(s). With a few improvements, you could access even more options."
    else:
        summary = "Based on your current profile, we recommend improving certain factors before applying. Here's what you can do."
    
    # Identify strengths
    strengths = []
    
    if business.annual_turnover_lakhs >= 100:
        strengths.append(CustomerReportStrength(
            factor="Strong Revenue",
            description=f"Your annual turnover of ₹{business.annual_turnover_lakhs}L demonstrates solid business operations",
            impact="Qualifies you for larger loan amounts"
        ))
    
    if credit.max_dpd_days == 0:
        strengths.append(CustomerReportStrength(
            factor="Clean Payment History",
            description="No payment delays on existing credit",
            impact="Significantly improves approval chances"
        ))
    
    if business.years_in_business >= 3:
        strengths.append(CustomerReportStrength(
            factor="Established Business",
            description=f"{business.years_in_business} years in operation",
            impact="Demonstrates stability and reliability"
        ))
    
    if credit.commercial_score_numeric >= 700:
        strengths.append(CustomerReportStrength(
            factor="Good Credit Score",
            description=f"Commercial score of {credit.commercial_score}",
            impact="Opens doors to premium lenders with better rates"
        ))
    
    if business.udyam_registered:
        strengths.append(CustomerReportStrength(
            factor="MSME Registered",
            description=f"Udyam registered as {business.msme_category or 'MSME'}",
            impact="Eligible for government schemes and priority lending"
        ))
    
    # Identify improvements
    improvements = []
    
    if credit.max_dpd_days > 0:
        improvements.append(CustomerReportImprovement(
            factor="Payment Delays",
            current_state=f"{credit.max_dpd_days} days past due history",
            recommendation="Clear any outstanding dues and maintain timely payments for 6 months",
            impact_if_addressed="Could improve approval probability by 20-30%"
        ))
    
    if not business.udyam_registered:
        improvements.append(CustomerReportImprovement(
            factor="MSME Registration",
            current_state="Not registered under Udyam",
            recommendation="Register at udyamregistration.gov.in (free, takes 10 minutes)",
            impact_if_addressed="Access to additional lenders and government schemes"
        ))
    
    if credit.credit_utilization_pct > 75:
        improvements.append(CustomerReportImprovement(
            factor="Credit Utilization",
            current_state=f"{credit.credit_utilization_pct}% of credit limit used",
            recommendation="Reduce utilization below 70% by paying down existing facilities",
            impact_if_addressed="Improves credit score and lender confidence"
        ))
    
    # Generate next steps
    next_steps = []
    
    if len(matches) > 0:
        next_steps.append(CustomerReportNextStep(
            step=1,
            action="Select Your Preferred Lender",
            details=f"We recommend {matches[0].lender_name} based on your preferences"
        ))
        next_steps.append(CustomerReportNextStep(
            step=2,
            action="Keep Documents Ready",
            details="PAN, Aadhaar, GST Certificate, Bank Statements (12 months), ITR (2 years)"
        ))
        next_steps.append(CustomerReportNextStep(
            step=3,
            action="Submit Application",
            details="We'll handle the submission and keep you updated on status"
        ))
    else:
        next_steps.append(CustomerReportNextStep(
            step=1,
            action="Address Credit Issues",
            details="Focus on clearing any overdue amounts and improving payment history"
        ))
        next_steps.append(CustomerReportNextStep(
            step=2,
            action="Complete MSME Registration",
            details="Register on Udyam portal to access more lending options"
        ))
        next_steps.append(CustomerReportNextStep(
            step=3,
            action="Try Again in 3-6 Months",
            details="With improvements, you'll have access to better loan options"
        ))
    
    return CustomerReport(
        summary=summary,
        strengths=strengths[:4],  # Max 4 strengths
        improvements=improvements[:3],  # Max 3 improvements
        next_steps=next_steps[:4]  # Max 4 steps
    )

def assess_and_match(request: AssessRequest) -> AssessResponse:
    """Main assessment and matching function"""
    
    assessment_id = str(uuid.uuid4())
    priority = request.customer_preferences.priority if request.customer_preferences else CustomerPriority.LOW_INTEREST
    
    matches = []
    max_eligible = 0.0
    
    # Evaluate each lender
    for lender_id, lender in LENDERS.items():
        eligible, risks, probability = evaluate_lender_eligibility(
            lender,
            request.business_profile,
            request.credit_profile,
            request.loan_request
        )
        
        if eligible:
            eligible_amount = calculate_eligible_amount(
                lender,
                request.business_profile,
                request.loan_request
            )
            
            preference_score = calculate_preference_score(
                lender,
                priority,
                eligible_amount,
                probability
            )
            
            # Determine if collateral is required
            collateral_required = eligible_amount > lender.get("collateral_required_above_lakhs", 50)
            
            matches.append(LenderMatch(
                rank=0,  # Will be set after sorting
                lender_id=lender_id,
                lender_name=lender["name"],
                lender_type=lender["type"],
                product=request.loan_request.purpose.replace("_", " ").title(),
                eligible_amount_lakhs=eligible_amount,
                interest_rate_range=f"{lender['interest_rate_min']}-{lender['interest_rate_max']}%",
                tenure_months=request.loan_request.tenure_months,
                approval_probability=round(probability / 100, 2),
                processing_time_days=lender["processing_time_days"],
                collateral_required=collateral_required and not request.loan_request.collateral_available,
                rejection_risks=risks,
                preference_score=preference_score
            ))
            
            max_eligible = max(max_eligible, eligible_amount)
    
    # Sort by preference score
    matches.sort(key=lambda x: x.preference_score, reverse=True)
    
    # Assign ranks
    for i, match in enumerate(matches):
        match.rank = i + 1
    
    # Determine overall eligibility
    if len(matches) >= 3:
        overall = EligibilityLevel.HIGH
    elif len(matches) >= 1:
        avg_prob = sum(m.approval_probability for m in matches) / len(matches)
        overall = EligibilityLevel.MEDIUM if avg_prob >= 0.6 else EligibilityLevel.LOW
    else:
        overall = EligibilityLevel.INELIGIBLE
    
    # Generate customer report
    customer_report = generate_customer_report(
        request.business_profile,
        request.credit_profile,
        request.loan_request,
        matches,
        request.data_flags or []
    )
    
    return AssessResponse(
        assessment_id=assessment_id,
        cam_id=request.cam_id,
        overall_eligibility=overall,
        max_eligible_amount_lakhs=max_eligible,
        lender_matches=matches[:5],  # Top 5 matches
        customer_report=customer_report,
        assessed_at=datetime.utcnow().isoformat()
    )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "kesha",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/assess", response_model=AssessResponse)
async def assess_eligibility(request: AssessRequest):
    """
    Assess eligibility and match with lenders.
    
    IMPORTANT: This endpoint receives ONLY anonymized data.
    No PII (names, PAN, GSTIN, addresses) should be in the request.
    """
    try:
        return assess_and_match(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lenders")
async def list_lenders():
    """
    List all available lenders and their criteria.
    """
    return {
        "lenders": [
            {
                "id": l["id"],
                "name": l["name"],
                "type": l["type"],
                "min_turnover_lakhs": l["min_turnover_lakhs"],
                "min_credit_score": l["min_credit_score"],
                "max_loan_amount_lakhs": l["max_loan_amount_lakhs"],
                "interest_rate_range": f"{l['interest_rate_min']}-{l['interest_rate_max']}%",
                "products": l["products"]
            }
            for l in LENDERS.values()
        ],
        "count": len(LENDERS)
    }

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
