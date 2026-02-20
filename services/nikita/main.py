"""
Nikita MCP - CAM (Credit Assessment Memo) Builder
Port: 8002

Builds standardized Credit Assessment Memorandums from aggregated data:
- Merges GST, PAN, Bureau, Udyam data
- Validates data completeness
- Calculates financial ratios
- Generates risk flags
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uvicorn
import uuid
import os

app = FastAPI(
    title="Nikita MCP - CAM Builder",
    description="Credit Assessment Memorandum builder service",
    version="1.0.0"
)

# CORS middleware - Restrict to internal services only
INTERNAL_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://n8n:5678,http://francis:8000,http://localhost:5678").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=INTERNAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ===========================================
# MODELS
# ===========================================

class CustomerInputs(BaseModel):
    loan_amount_requested_lakhs: float
    loan_purpose: str
    tenure_preference_months: Optional[int] = 36
    collateral_available: Optional[bool] = False
    customer_priority: Optional[str] = "low_interest"  # low_interest | quick_disbursal

class GSTData(BaseModel):
    gstin: str
    entity_info: Dict[str, Any]
    sales_data: Dict[str, Any]
    filing_status: Optional[Dict[str, str]] = None

class PANData(BaseModel):
    pan: str
    name: str
    entity_type: str
    status: str

class CreditBureauData(BaseModel):
    commercial: Optional[Dict[str, Any]] = None
    consumer: Optional[List[Dict[str, Any]]] = []

class UdyamData(BaseModel):
    found: bool
    udyam_number: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    nic_code: Optional[str] = None

class CAMBuildRequest(BaseModel):
    conversation_id: str
    gst_data: GSTData
    pan_data: PANData
    credit_bureau: CreditBureauData
    udyam_data: Optional[UdyamData] = None
    customer_inputs: CustomerInputs

class EntityIdentity(BaseModel):
    gstin: str
    pan: str
    legal_name: str
    trade_name: str
    entity_type: str
    constitution_type: str
    registration_date: str
    state: str
    address: str
    years_in_business: int

class FinancialSummary(BaseModel):
    annual_turnover_lakhs: float
    q1_lakhs: float
    q2_lakhs: float
    q3_lakhs: float
    q4_lakhs: float
    monthly_average_lakhs: float
    yoy_growth_pct: Optional[float] = None
    quarterly_trend: str  # increasing | decreasing | stable

class CreditProfile(BaseModel):
    commercial_score: str
    commercial_score_numeric: int
    total_outstanding_lakhs: float
    active_loans: int
    max_dpd_days: int
    overdue_amount_lakhs: float
    credit_utilization_pct: float
    promoter_scores: List[Dict[str, Any]] = []

class LoanRequest(BaseModel):
    amount_requested_lakhs: float
    purpose: str
    tenure_months: int
    collateral_available: bool
    customer_priority: str

class MSMEProfile(BaseModel):
    udyam_registered: bool
    udyam_number: Optional[str] = None
    category: Optional[str] = None  # Micro, Small, Medium
    industry_type: Optional[str] = None
    nic_code: Optional[str] = None

class FinancialRatios(BaseModel):
    loan_to_turnover_pct: float
    debt_burden_ratio: float
    credit_utilization_pct: float
    recommended_loan_amount_lakhs: float

class CAMData(BaseModel):
    entity_identity: EntityIdentity
    financial_summary: FinancialSummary
    credit_profile: CreditProfile
    loan_request: LoanRequest
    msme_profile: MSMEProfile
    financial_ratios: FinancialRatios
    industry_sector: str
    years_in_business: int

class RiskFlag(BaseModel):
    code: str
    severity: str  # low | medium | high | critical
    description: str
    recommendation: str

class CAMBuildResponse(BaseModel):
    cam_id: str
    conversation_id: str
    status: str  # building | complete | incomplete | error
    cam_data: CAMData
    missing_fields: List[str] = []
    data_flags: List[RiskFlag] = []
    completeness_score: float
    created_at: str

class CAMValidateRequest(BaseModel):
    cam_id: str
    cam_data: Dict[str, Any]

class CAMValidateResponse(BaseModel):
    valid: bool
    completeness_score: float
    missing_fields: List[str]
    data_flags: List[RiskFlag]

# ===========================================
# CAM BUILDING LOGIC
# ===========================================

def calculate_years_in_business(registration_date: str) -> int:
    """Calculate years since registration"""
    try:
        reg_date = datetime.strptime(registration_date, "%Y-%m-%d")
        today = datetime.now()
        years = (today - reg_date).days // 365
        return max(years, 0)
    except:
        return 3  # Default assumption

def calculate_quarterly_trend(q1: float, q2: float, q3: float, q4: float) -> str:
    """Determine quarterly sales trend"""
    quarters = [q1, q2, q3, q4]
    increases = sum(1 for i in range(1, len(quarters)) if quarters[i] > quarters[i-1])
    
    if increases >= 3:
        return "increasing"
    elif increases <= 1:
        return "decreasing"
    else:
        return "stable"

def determine_industry_sector(nic_code: Optional[str], trade_name: str) -> str:
    """Determine industry sector from NIC code or trade name"""
    if nic_code:
        nic_prefix = nic_code[:2] if len(nic_code) >= 2 else nic_code
        nic_sectors = {
            "62": "IT_services",
            "46": "wholesale_trade",
            "47": "retail_trade",
            "25": "manufacturing_metal",
            "10": "food_processing",
            "13": "textiles"
        }
        if nic_prefix in nic_sectors:
            return nic_sectors[nic_prefix]
    
    # Fallback to trade name analysis
    trade_lower = trade_name.lower()
    if any(kw in trade_lower for kw in ["it", "tech", "software", "digital"]):
        return "IT_services"
    elif any(kw in trade_lower for kw in ["trade", "export", "import"]):
        return "trading"
    elif any(kw in trade_lower for kw in ["manufacturing", "industrial"]):
        return "manufacturing"
    else:
        return "services"

def calculate_financial_ratios(
    loan_amount: float,
    annual_turnover: float,
    total_outstanding: float,
    credit_utilization: float
) -> FinancialRatios:
    """Calculate key financial ratios"""
    
    # Loan to turnover percentage
    loan_to_turnover = (loan_amount / annual_turnover * 100) if annual_turnover > 0 else 0
    
    # Debt burden ratio (existing + new debt to turnover)
    total_debt = total_outstanding + loan_amount
    debt_burden = (total_debt / annual_turnover * 100) if annual_turnover > 0 else 0
    
    # Recommended loan amount (20% of turnover rule)
    max_by_turnover = annual_turnover * 0.20
    
    return FinancialRatios(
        loan_to_turnover_pct=round(loan_to_turnover, 2),
        debt_burden_ratio=round(debt_burden, 2),
        credit_utilization_pct=round(credit_utilization, 2),
        recommended_loan_amount_lakhs=round(max_by_turnover, 2)
    )

def generate_risk_flags(
    cam_data: CAMData,
    gst_data: GSTData,
    credit_bureau: CreditBureauData
) -> List[RiskFlag]:
    """Generate risk flags based on data analysis"""
    
    flags = []
    
    # DPD flag
    if cam_data.credit_profile.max_dpd_days > 0:
        severity = "critical" if cam_data.credit_profile.max_dpd_days > 90 else \
                   "high" if cam_data.credit_profile.max_dpd_days > 60 else \
                   "medium" if cam_data.credit_profile.max_dpd_days > 30 else "low"
        
        flags.append(RiskFlag(
            code="DPD_HISTORY",
            severity=severity,
            description=f"Days past due history: {cam_data.credit_profile.max_dpd_days} days",
            recommendation="Review payment history in detail before approval"
        ))
    
    # Overdue amount flag
    if cam_data.credit_profile.overdue_amount_lakhs > 0:
        flags.append(RiskFlag(
            code="ACTIVE_OVERDUE",
            severity="high",
            description=f"Active overdue amount: ₹{cam_data.credit_profile.overdue_amount_lakhs}L",
            recommendation="Require overdue clearance before new disbursement"
        ))
    
    # High loan to turnover flag
    if cam_data.financial_ratios.loan_to_turnover_pct > 25:
        flags.append(RiskFlag(
            code="HIGH_LOAN_TO_TURNOVER",
            severity="medium",
            description=f"Loan amount is {cam_data.financial_ratios.loan_to_turnover_pct}% of turnover",
            recommendation="Consider reducing loan amount or require additional collateral"
        ))
    
    # No Udyam registration flag
    if not cam_data.msme_profile.udyam_registered:
        flags.append(RiskFlag(
            code="NO_UDYAM",
            severity="low",
            description="No Udyam registration found",
            recommendation="Recommend Udyam registration for better terms"
        ))
    
    # Declining sales trend
    if cam_data.financial_summary.quarterly_trend == "decreasing":
        flags.append(RiskFlag(
            code="DECLINING_SALES",
            severity="medium",
            description="Quarterly sales show declining trend",
            recommendation="Investigate reasons for sales decline"
        ))
    
    # High credit utilization
    if cam_data.financial_ratios.credit_utilization_pct > 75:
        flags.append(RiskFlag(
            code="HIGH_CREDIT_UTILIZATION",
            severity="medium",
            description=f"Credit utilization at {cam_data.financial_ratios.credit_utilization_pct}%",
            recommendation="Monitor cash flow closely"
        ))
    
    # New business (less than 2 years)
    if cam_data.years_in_business < 2:
        flags.append(RiskFlag(
            code="NEW_BUSINESS",
            severity="medium",
            description=f"Business operational for only {cam_data.years_in_business} year(s)",
            recommendation="Consider shorter tenure or lower amount"
        ))
    
    return flags

def identify_missing_fields(
    gst_data: GSTData,
    pan_data: PANData,
    credit_bureau: CreditBureauData,
    udyam_data: Optional[UdyamData]
) -> List[str]:
    """Identify missing required fields"""
    
    missing = []
    
    # GST data checks
    if not gst_data.sales_data:
        missing.append("gst_sales_data")
    if not gst_data.entity_info or not gst_data.entity_info.get("legal_name"):
        missing.append("entity_name")
    
    # Credit bureau checks
    if not credit_bureau.commercial:
        missing.append("commercial_credit_score")
    
    # Udyam is optional but valuable
    if not udyam_data or not udyam_data.found:
        missing.append("udyam_registration")  # This is informational
    
    return missing

def build_cam(request: CAMBuildRequest) -> CAMBuildResponse:
    """Build complete CAM from aggregated data"""
    
    cam_id = str(uuid.uuid4())
    
    # Extract data
    gst = request.gst_data
    pan = request.pan_data
    bureau = request.credit_bureau
    udyam = request.udyam_data
    inputs = request.customer_inputs
    
    # Build Entity Identity
    years_in_business = calculate_years_in_business(
        gst.entity_info.get("registration_date", "2020-01-01")
    )
    
    entity_identity = EntityIdentity(
        gstin=gst.gstin,
        pan=pan.pan,
        legal_name=gst.entity_info.get("legal_name", "Unknown"),
        trade_name=gst.entity_info.get("trade_name", "Unknown"),
        entity_type=pan.entity_type,
        constitution_type=gst.entity_info.get("constitution_type", "Unknown"),
        registration_date=gst.entity_info.get("registration_date", "Unknown"),
        state=gst.entity_info.get("state", "Unknown"),
        address=gst.entity_info.get("address", "Unknown"),
        years_in_business=years_in_business
    )
    
    # Build Financial Summary
    sales = gst.sales_data
    q1 = sales.get("q1_lakhs", 0)
    q2 = sales.get("q2_lakhs", 0)
    q3 = sales.get("q3_lakhs", 0)
    q4 = sales.get("q4_lakhs", 0)
    annual = sales.get("annual_lakhs", q1 + q2 + q3 + q4)
    
    financial_summary = FinancialSummary(
        annual_turnover_lakhs=annual,
        q1_lakhs=q1,
        q2_lakhs=q2,
        q3_lakhs=q3,
        q4_lakhs=q4,
        monthly_average_lakhs=round(annual / 12, 2),
        yoy_growth_pct=None,  # Would need previous year data
        quarterly_trend=calculate_quarterly_trend(q1, q2, q3, q4)
    )
    
    # Build Credit Profile
    commercial = bureau.commercial or {}
    credit_profile = CreditProfile(
        commercial_score=commercial.get("score", "CMR-5"),
        commercial_score_numeric=commercial.get("score_numeric", 600),
        total_outstanding_lakhs=commercial.get("total_outstanding_lakhs", 0),
        active_loans=commercial.get("active_loans", 0),
        max_dpd_days=commercial.get("max_dpd_days", 0),
        overdue_amount_lakhs=commercial.get("overdue_amount_lakhs", 0),
        credit_utilization_pct=commercial.get("credit_utilization_pct", 0),
        promoter_scores=bureau.consumer or []
    )
    
    # Build Loan Request
    loan_request = LoanRequest(
        amount_requested_lakhs=inputs.loan_amount_requested_lakhs,
        purpose=inputs.loan_purpose,
        tenure_months=inputs.tenure_preference_months or 36,
        collateral_available=inputs.collateral_available or False,
        customer_priority=inputs.customer_priority or "low_interest"
    )
    
    # Build MSME Profile
    msme_profile = MSMEProfile(
        udyam_registered=udyam.found if udyam else False,
        udyam_number=udyam.udyam_number if udyam else None,
        category=udyam.category if udyam else None,
        industry_type=udyam.type if udyam else None,
        nic_code=udyam.nic_code if udyam else None
    )
    
    # Calculate Financial Ratios
    financial_ratios = calculate_financial_ratios(
        inputs.loan_amount_requested_lakhs,
        annual,
        credit_profile.total_outstanding_lakhs,
        credit_profile.credit_utilization_pct
    )
    
    # Determine Industry Sector
    industry_sector = determine_industry_sector(
        msme_profile.nic_code,
        entity_identity.trade_name
    )
    
    # Assemble CAM Data
    cam_data = CAMData(
        entity_identity=entity_identity,
        financial_summary=financial_summary,
        credit_profile=credit_profile,
        loan_request=loan_request,
        msme_profile=msme_profile,
        financial_ratios=financial_ratios,
        industry_sector=industry_sector,
        years_in_business=years_in_business
    )
    
    # Identify missing fields
    missing_fields = identify_missing_fields(gst, pan, bureau, udyam)
    
    # Remove optional fields from missing
    missing_fields = [f for f in missing_fields if f != "udyam_registration"]
    
    # Generate risk flags
    data_flags = generate_risk_flags(cam_data, gst, bureau)
    
    # Calculate completeness score
    required_fields = 10
    present_fields = required_fields - len(missing_fields)
    completeness_score = round((present_fields / required_fields) * 100, 1)
    
    # Determine status
    status = "complete" if completeness_score >= 80 else "incomplete"
    
    return CAMBuildResponse(
        cam_id=cam_id,
        conversation_id=request.conversation_id,
        status=status,
        cam_data=cam_data,
        missing_fields=missing_fields,
        data_flags=data_flags,
        completeness_score=completeness_score,
        created_at=datetime.utcnow().isoformat()
    )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "nikita",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/build-cam", response_model=CAMBuildResponse)
async def api_build_cam(request: CAMBuildRequest):
    """
    Build a Credit Assessment Memorandum from aggregated data.
    
    This is the primary endpoint called by n8n after data aggregation.
    """
    try:
        result = build_cam(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate-cam", response_model=CAMValidateResponse)
async def validate_cam(request: CAMValidateRequest):
    """
    Validate an existing CAM for completeness.
    """
    try:
        cam_data = request.cam_data
        
        # Simple validation - check required sections exist
        required_sections = [
            "entity_identity", "financial_summary", "credit_profile",
            "loan_request", "msme_profile", "financial_ratios"
        ]
        
        missing = [s for s in required_sections if s not in cam_data]
        completeness = ((len(required_sections) - len(missing)) / len(required_sections)) * 100
        
        return CAMValidateResponse(
            valid=len(missing) == 0,
            completeness_score=round(completeness, 1),
            missing_fields=missing,
            data_flags=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
