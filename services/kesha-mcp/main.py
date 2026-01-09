"""
Kesha MCP Server
Credit Intelligence & Lender Matching Agent
Receives anonymized CAM, calculates eligibility, ranks lenders, generates recommendations
"""

import load_env  # Load .env variables

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kesha MCP - Credit Intelligence",
    description="Credit assessment and lender matching agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lender criteria (in production, this would come from database)
LENDER_CRITERIA = {
    "bajaj_finserv": {
        "name": "Bajaj Finserv",
        "type": "nbfc",
        "min_turnover_lakhs": 10,
        "min_vintage_years": 1,
        "min_credit_score": 650,
        "max_dpd_days": 30,
        "interest_rate_range": "14-18%",
        "commission_pct": 2.5,
        "max_amount_lakhs": 80
    },
    "hdfc_bank": {
        "name": "HDFC Bank",
        "type": "private_bank",
        "min_turnover_lakhs": 50,
        "min_vintage_years": 2,
        "min_credit_score": 700,
        "max_dpd_days": 15,
        "interest_rate_range": "11-14%",
        "commission_pct": 2.0,
        "max_amount_lakhs": 100
    },
    "icici_bank": {
        "name": "ICICI Bank",
        "type": "private_bank",
        "min_turnover_lakhs": 50,
        "min_vintage_years": 2,
        "min_credit_score": 680,
        "max_dpd_days": 20,
        "interest_rate_range": "11.5-15%",
        "commission_pct": 2.0,
        "max_amount_lakhs": 150
    },
    "ugro_capital": {
        "name": "UGRO Capital",
        "type": "nbfc",
        "min_turnover_lakhs": 20,
        "min_vintage_years": 1,
        "min_credit_score": 600,
        "max_dpd_days": 45,
        "interest_rate_range": "15-19%",
        "commission_pct": 3.0,
        "max_amount_lakhs": 50
    },
    "indifi": {
        "name": "Indifi",
        "type": "fintech",
        "min_turnover_lakhs": 5,
        "min_vintage_years": 1,
        "min_credit_score": 550,
        "max_dpd_days": 60,
        "interest_rate_range": "18-24%",
        "commission_pct": 4.0,
        "max_amount_lakhs": 30
    }
}

# Request/Response Models
class AnonymizedCAM(BaseModel):
    cam_id: str
    business_profile: Dict[str, Any]
    financial_metrics: Dict[str, Any]
    credit_profile: Dict[str, Any]
    compliance: Dict[str, Any]
    loan_request: Dict[str, Any]
    customer_preferences: Dict[str, Any]

class LenderMatch(BaseModel):
    lender_id: str
    lender_name: str
    product: str
    eligible_amount_lakhs: float
    interest_rate_range: str
    tenure_months: int
    approval_probability: float
    commission_pct: float
    expected_value: float
    meets_customer_preference: bool
    preference_score: float
    rejection_risks: List[str]
    requirements: List[str]

class AssessmentResponse(BaseModel):
    assessment_id: str
    overall_eligibility: str
    max_eligible_amount_lakhs: float
    lender_matches: List[LenderMatch]
    recommendation: Dict[str, Any]
    customer_report: Dict[str, Any]
    internal_notes: str

def calculate_credit_score_numeric(score_str: str) -> int:
    """Convert CMR score to numeric for comparison"""
    score_map = {
        "CMR-1": 800,
        "CMR-2": 750,
        "CMR-3": 700,
        "CMR-4": 650,
        "CMR-5": 600,
        "CMR-6": 550,
        "CMR-7": 500,
        "CMR-8": 450
    }
    return score_map.get(score_str, 600)

def get_max_dpd(credit_profile: Dict[str, Any]) -> int:
    """Get maximum DPD from existing facilities"""
    facilities = credit_profile.get("existing_facilities", [])
    if not facilities:
        return 0
    return max((f.get("dpd_days", 0) for f in facilities), default=0)

def calculate_approval_probability(
    lender_criteria: Dict[str, Any],
    financial_metrics: Dict[str, Any],
    credit_profile: Dict[str, Any],
    business_profile: Dict[str, Any]
) -> float:
    """Calculate approval probability based on lender criteria match"""
    score = 1.0

    # Turnover check
    turnover = financial_metrics.get("annual_turnover_lakhs", 0)
    if turnover < lender_criteria["min_turnover_lakhs"]:
        score *= 0.3
    elif turnover < lender_criteria["min_turnover_lakhs"] * 1.5:
        score *= 0.7

    # Credit score check
    credit_score_str = credit_profile.get("commercial_score", "CMR-8")
    credit_score = calculate_credit_score_numeric(credit_score_str)
    if credit_score < lender_criteria["min_credit_score"]:
        score *= 0.4
    elif credit_score < lender_criteria["min_credit_score"] + 50:
        score *= 0.8

    # DPD check
    max_dpd = get_max_dpd(credit_profile)
    if max_dpd > lender_criteria["max_dpd_days"]:
        score *= 0.5
    elif max_dpd > lender_criteria["max_dpd_days"] * 0.7:
        score *= 0.9

    # Vintage check
    vintage = business_profile.get("vintage_years", 0)
    if vintage < lender_criteria["min_vintage_years"]:
        score *= 0.6

    return min(score, 0.95)

def identify_rejection_risks(
    lender_criteria: Dict[str, Any],
    financial_metrics: Dict[str, Any],
    credit_profile: Dict[str, Any],
    business_profile: Dict[str, Any]
) -> List[str]:
    """Identify potential rejection reasons"""
    risks = []

    turnover = financial_metrics.get("annual_turnover_lakhs", 0)
    if turnover < lender_criteria["min_turnover_lakhs"]:
        risks.append(f"Turnover below minimum requirement of ₹{lender_criteria['min_turnover_lakhs']}L")

    credit_score_str = credit_profile.get("commercial_score", "CMR-8")
    credit_score = calculate_credit_score_numeric(credit_score_str)
    if credit_score < lender_criteria["min_credit_score"]:
        risks.append(f"Credit score below minimum {lender_criteria['min_credit_score']}")

    max_dpd = get_max_dpd(credit_profile)
    if max_dpd > lender_criteria["max_dpd_days"]:
        risks.append(f"DPD of {max_dpd} days exceeds limit of {lender_criteria['max_dpd_days']} days")

    active_loans = credit_profile.get("active_loans_count", 0)
    if active_loans > 15:
        risks.append("High active loan count may raise concerns")

    utilization = credit_profile.get("utilization_pct", 0)
    if utilization > 0.9:
        risks.append("High credit utilization (>90%)")

    return risks

def calculate_eligible_amount(
    lender_criteria: Dict[str, Any],
    loan_request: Dict[str, Any],
    financial_metrics: Dict[str, Any]
) -> float:
    """Calculate eligible loan amount for lender"""
    requested = loan_request.get("amount_lakhs", 0)
    max_lender = lender_criteria["max_amount_lakhs"]

    # Simple eligibility: 20% of annual turnover or lender max, whichever is lower
    turnover_based = financial_metrics.get("annual_turnover_lakhs", 0) * 0.20

    return min(requested, max_lender, turnover_based)

def match_lenders(anonymized_cam: AnonymizedCAM) -> List[LenderMatch]:
    """Match customer to suitable lenders"""
    matches = []

    for lender_id, criteria in LENDER_CRITERIA.items():
        # Calculate approval probability
        approval_prob = calculate_approval_probability(
            criteria,
            anonymized_cam.financial_metrics,
            anonymized_cam.credit_profile,
            anonymized_cam.business_profile
        )

        # Skip if approval probability too low
        if approval_prob < 0.3:
            continue

        # Calculate eligible amount
        eligible_amount = calculate_eligible_amount(
            criteria,
            anonymized_cam.loan_request,
            anonymized_cam.financial_metrics
        )

        # Identify risks
        risks = identify_rejection_risks(
            criteria,
            anonymized_cam.financial_metrics,
            anonymized_cam.credit_profile,
            anonymized_cam.business_profile
        )

        # Check customer preference match
        pref = anonymized_cam.customer_preferences.get("priority", "low_interest")
        lender_pref = anonymized_cam.customer_preferences.get("lender_preference", "any")

        meets_preference = True
        preference_score = 0.5

        if lender_pref != "any" and lender_pref != criteria["type"]:
            meets_preference = False
            preference_score = 0.3
        else:
            if pref == "low_interest" and criteria["type"] in ["private_bank", "psu_bank"]:
                preference_score = 0.9
            elif pref == "quick_disbursement" and criteria["type"] in ["fintech", "nbfc"]:
                preference_score = 0.9
            else:
                preference_score = 0.7

        # Calculate expected value (commission * approval probability)
        expected_value = (criteria["commission_pct"] / 100) * eligible_amount * approval_prob

        match = LenderMatch(
            lender_id=lender_id,
            lender_name=criteria["name"],
            product="Business Loan",
            eligible_amount_lakhs=round(eligible_amount, 2),
            interest_rate_range=criteria["interest_rate_range"],
            tenure_months=anonymized_cam.loan_request.get("tenure_months", 36),
            approval_probability=round(approval_prob, 2),
            commission_pct=criteria["commission_pct"],
            expected_value=round(expected_value, 2),
            meets_customer_preference=meets_preference,
            preference_score=preference_score,
            rejection_risks=risks,
            requirements=["6-month bank statement", "Latest ITR", "GST certificate"]
        )

        matches.append(match)

    # Sort by preference score * approval probability
    matches.sort(key=lambda x: x.preference_score * x.approval_probability, reverse=True)

    return matches

def generate_customer_report(
    anonymized_cam: AnonymizedCAM,
    lender_matches: List[LenderMatch],
    overall_eligibility: str,
    max_eligible: float
) -> Dict[str, Any]:
    """Generate customer-facing report with recommendations"""

    # Identify strengths
    strengths = []
    if anonymized_cam.credit_profile.get("commercial_score") in ["CMR-1", "CMR-2", "CMR-3"]:
        strengths.append("Strong credit score")
    if anonymized_cam.compliance.get("filing_consistency", 0) > 0.8:
        strengths.append("Consistent GST filing")
    if anonymized_cam.financial_metrics.get("turnover_growth_yoy", 0) > 0.1:
        strengths.append("Good turnover growth")
    if anonymized_cam.financial_metrics.get("profit_margin", 0) > 0.15:
        strengths.append("Healthy profit margins")

    # Identify improvements
    improvements = []
    utilization = anonymized_cam.credit_profile.get("utilization_pct", 0)
    if utilization > 0.9:
        improvements.append("Reduce existing loan utilization below 80%")

    overdue = anonymized_cam.credit_profile.get("overdue_amount_lakhs", 0)
    if overdue > 0:
        improvements.append(f"Clear ₹{overdue}L overdue amount")

    max_dpd = get_max_dpd(anonymized_cam.credit_profile)
    if max_dpd > 30:
        improvements.append("Improve payment discipline to avoid delays")

    # Summary
    if overall_eligibility == "high":
        summary = f"Based on your business profile, you're eligible for up to ₹{max_eligible}L across multiple lenders. Your strong credit profile and business performance make you an attractive candidate for most lenders."
    elif overall_eligibility == "medium":
        summary = f"Based on your business profile, you're eligible for up to ₹{max_eligible}L. Some improvements to your credit profile could unlock better rates and higher amounts."
    else:
        summary = f"Based on your business profile, you have limited options currently. Working on the improvement areas listed below will significantly enhance your eligibility."

    # Next steps
    next_steps = [
        "Review lender options and select your preferred lender(s)",
        "Prepare required documents (bank statements, ITR, GST certificate)",
        "Submit application through our platform"
    ]

    return {
        "summary": summary,
        "strengths": strengths,
        "improvements": improvements,
        "next_steps": next_steps,
        "eligible_lenders_count": len(lender_matches),
        "best_rate_range": lender_matches[0].interest_rate_range if lender_matches else "N/A"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "kesha-mcp",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/assess", response_model=AssessmentResponse)
async def assess_cam(request: AnonymizedCAM):
    """
    Assess anonymized CAM and generate lender matches
    """
    try:
        logger.info(f"Assessment requested for CAM: {request.cam_id}")

        # Match lenders
        lender_matches = match_lenders(request)

        # Determine overall eligibility
        if not lender_matches:
            overall_eligibility = "ineligible"
            max_eligible = 0
        elif lender_matches[0].approval_probability > 0.7:
            overall_eligibility = "high"
            max_eligible = max(m.eligible_amount_lakhs for m in lender_matches)
        elif lender_matches[0].approval_probability > 0.5:
            overall_eligibility = "medium"
            max_eligible = max(m.eligible_amount_lakhs for m in lender_matches)
        else:
            overall_eligibility = "low"
            max_eligible = max(m.eligible_amount_lakhs for m in lender_matches)

        # Generate customer report
        customer_report = generate_customer_report(
            request,
            lender_matches,
            overall_eligibility,
            max_eligible
        )

        # Recommendation
        recommendation = {
            "primary": lender_matches[0].lender_id if lender_matches else None,
            "reason": f"Best match for {request.customer_preferences.get('priority', 'balanced')} priority with {int(lender_matches[0].approval_probability * 100)}% approval probability" if lender_matches else "No suitable lenders found",
            "alternatives": [m.lender_id for m in lender_matches[1:3]] if len(lender_matches) > 1 else []
        }

        # Internal notes
        internal_notes = ""
        max_dpd = get_max_dpd(request.credit_profile)
        if max_dpd > 30:
            internal_notes = f"High DPD of {max_dpd} days may cause issues with conservative lenders"

        assessment_id = str(uuid.uuid4())

        return AssessmentResponse(
            assessment_id=assessment_id,
            overall_eligibility=overall_eligibility,
            max_eligible_amount_lakhs=max_eligible,
            lender_matches=lender_matches,
            recommendation=recommendation,
            customer_report=customer_report,
            internal_notes=internal_notes
        )

    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
