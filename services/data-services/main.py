"""
Data Services MCP - External API Gateway
Port: 8001

Provides mock/simulated external API integrations for:
- GST verification
- PAN verification  
- Credit Bureau pulls
- Udyam registration lookup
- FameScore comprehensive reports
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uvicorn
import re
import random

app = FastAPI(
    title="Data Services MCP",
    description="External API Gateway for GST, PAN, Credit Bureau, and Udyam verification",
    version="1.0.0"
)

# CORS middleware - Restrict to internal services only
import os
INTERNAL_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://francis:8000,http://n8n:5678,http://localhost:8000").split(",")
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

class GSTVerifyRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15)
    
    @validator('gstin')
    def validate_gstin(cls, v):
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid GSTIN format')
        return v

class GSTEntityInfo(BaseModel):
    legal_name: str
    trade_name: str
    registration_date: str
    status: str
    constitution_type: str
    state: str
    address: str

class GSTSalesData(BaseModel):
    q1_lakhs: float
    q2_lakhs: float
    q3_lakhs: float
    q4_lakhs: float
    annual_lakhs: float

class GSTVerifyResponse(BaseModel):
    valid: bool
    gstin: str
    entity_info: Optional[GSTEntityInfo]
    sales_data: Optional[GSTSalesData]
    filing_status: Optional[Dict[str, str]]
    error: Optional[str] = None

class PANVerifyRequest(BaseModel):
    pan: str = Field(..., min_length=10, max_length=10)
    
    @validator('pan')
    def validate_pan(cls, v):
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pattern, v.upper()):
            raise ValueError('Invalid PAN format')
        return v.upper()

class PANVerifyResponse(BaseModel):
    valid: bool
    pan: str
    name: str
    entity_type: str
    status: str
    linked_aadhaar: bool
    error: Optional[str] = None

class CreditBureauRequest(BaseModel):
    entity_pan: str
    promoter_pans: List[str] = []
    consent_obtained: bool = True

class CommercialCredit(BaseModel):
    score: str  # CMR-1 to CMR-8
    score_numeric: int
    total_outstanding_lakhs: float
    active_loans: int
    max_dpd_days: int
    overdue_amount_lakhs: float
    credit_utilization_pct: float

class ConsumerCredit(BaseModel):
    name: str
    pan: str
    score: int
    total_outstanding_lakhs: float
    active_loans: int
    max_dpd_days: int

class CreditBureauResponse(BaseModel):
    success: bool
    commercial: Optional[CommercialCredit]
    consumer: List[ConsumerCredit] = []
    error: Optional[str] = None

class UdyamLookupRequest(BaseModel):
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    pan: Optional[str] = None

class UdyamLookupResponse(BaseModel):
    found: bool
    udyam_number: Optional[str]
    enterprise_name: Optional[str]
    category: Optional[str]  # Micro, Small, Medium
    type: Optional[str]  # Manufacturing, Service
    nic_code: Optional[str]
    date_of_registration: Optional[str]
    investment_lakhs: Optional[float]
    turnover_lakhs: Optional[float]
    error: Optional[str] = None

class FameScoreRequest(BaseModel):
    gstin: str
    pan: str
    consent_obtained: bool = True

class FameScoreResponse(BaseModel):
    success: bool
    gst_data: Optional[Dict[str, Any]]
    pan_data: Optional[Dict[str, Any]]
    credit_bureau: Optional[Dict[str, Any]]
    udyam_data: Optional[Dict[str, Any]]
    aggregated_score: Optional[Dict[str, Any]]
    error: Optional[str] = None

# ===========================================
# MOCK DATA GENERATORS
# ===========================================

def generate_mock_gst_data(gstin: str) -> GSTVerifyResponse:
    """Generate realistic mock GST data based on GSTIN"""
    
    # Extract state code from GSTIN
    state_code = gstin[:2]
    state_names = {
        "09": "Uttar Pradesh", "27": "Maharashtra", "29": "Karnataka",
        "33": "Tamil Nadu", "07": "Delhi", "06": "Haryana"
    }
    state = state_names.get(state_code, "Maharashtra")
    
    # Generate entity name from PAN portion
    pan_portion = gstin[2:12]
    
    entity_names = [
        "ABC IT Services LLP", "Dynamic Solutions Pvt Ltd",
        "Bharat Enterprises", "Tech Innovators India LLP",
        "Global Trade Corporation", "Sunrise Manufacturing Co"
    ]
    
    entity_info = GSTEntityInfo(
        legal_name=random.choice(entity_names),
        trade_name=random.choice(entity_names).replace(" LLP", "").replace(" Pvt Ltd", ""),
        registration_date="2018-06-15",
        status="Active",
        constitution_type="LLP" if "LLP" in random.choice(entity_names) else "Private Limited",
        state=state,
        address=f"123 Business Park, {state}"
    )
    
    # Generate sales data (realistic quarterly pattern)
    base_quarterly = random.uniform(400, 800)
    growth_factor = random.uniform(1.02, 1.08)
    
    q1 = round(base_quarterly, 2)
    q2 = round(q1 * growth_factor, 2)
    q3 = round(q2 * growth_factor, 2)
    q4 = round(q3 * growth_factor, 2)
    
    sales_data = GSTSalesData(
        q1_lakhs=q1,
        q2_lakhs=q2,
        q3_lakhs=q3,
        q4_lakhs=q4,
        annual_lakhs=round(q1 + q2 + q3 + q4, 2)
    )
    
    return GSTVerifyResponse(
        valid=True,
        gstin=gstin,
        entity_info=entity_info,
        sales_data=sales_data,
        filing_status={
            "gstr1": "Filed",
            "gstr3b": "Filed",
            "annual_return": "Filed"
        }
    )

def generate_mock_pan_data(pan: str) -> PANVerifyResponse:
    """Generate realistic mock PAN data"""
    
    # Fourth character determines entity type
    entity_char = pan[3]
    entity_types = {
        'C': 'Company',
        'P': 'Individual',
        'H': 'HUF',
        'F': 'Firm',
        'A': 'AOP',
        'T': 'Trust',
        'L': 'LLP'
    }
    
    entity_type = entity_types.get(entity_char, 'Company')
    
    names = {
        'C': ['ABC IT Services LLP', 'Dynamic Solutions Pvt Ltd'],
        'P': ['Rajesh Kumar', 'Priya Sharma', 'Amit Patel'],
        'L': ['ABC Tech LLP', 'Bharat Enterprises LLP']
    }
    
    name = random.choice(names.get(entity_char, ['Business Entity']))
    
    return PANVerifyResponse(
        valid=True,
        pan=pan,
        name=name,
        entity_type=entity_type,
        status="Active",
        linked_aadhaar=entity_char == 'P'
    )

def generate_mock_credit_bureau(entity_pan: str, promoter_pans: List[str]) -> CreditBureauResponse:
    """Generate realistic mock credit bureau data"""
    
    # Commercial credit
    cmr_score = random.choice([3, 4, 4, 5])  # Bias towards CMR-4
    
    commercial = CommercialCredit(
        score=f"CMR-{cmr_score}",
        score_numeric=800 - (cmr_score * 50),
        total_outstanding_lakhs=round(random.uniform(10, 100), 2),
        active_loans=random.randint(1, 25),
        max_dpd_days=random.choice([0, 0, 0, 30]),  # Mostly clean
        overdue_amount_lakhs=0 if random.random() > 0.2 else round(random.uniform(1, 10), 2),
        credit_utilization_pct=round(random.uniform(40, 80), 1)
    )
    
    # Consumer credit for promoters
    consumer_scores = []
    for i, pan in enumerate(promoter_pans[:3]):  # Max 3 promoters
        consumer_scores.append(ConsumerCredit(
            name=f"Promoter {i+1}",
            pan=pan,
            score=random.randint(700, 820),
            total_outstanding_lakhs=round(random.uniform(2, 20), 2),
            active_loans=random.randint(1, 5),
            max_dpd_days=0
        ))
    
    return CreditBureauResponse(
        success=True,
        commercial=commercial,
        consumer=consumer_scores
    )

def generate_mock_udyam(gstin: str) -> UdyamLookupResponse:
    """Generate realistic mock Udyam data"""
    
    # 70% chance of having Udyam registration
    if random.random() > 0.3:
        state_code = gstin[:2]
        udyam_number = f"UDYAM-{state_code}-01-{random.randint(1000000, 9999999)}"
        
        categories = ['Micro', 'Small', 'Medium']
        category = random.choice(categories)
        
        return UdyamLookupResponse(
            found=True,
            udyam_number=udyam_number,
            enterprise_name="ABC IT Services LLP",
            category=category,
            type="Service",
            nic_code="62" + str(random.randint(10, 99)),
            date_of_registration="2020-07-01",
            investment_lakhs=random.uniform(10, 500),
            turnover_lakhs=random.uniform(100, 5000)
        )
    else:
        return UdyamLookupResponse(
            found=False,
            error="No Udyam registration found for this GSTIN"
        )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-services",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/verify-gst", response_model=GSTVerifyResponse)
async def verify_gst(request: GSTVerifyRequest):
    """
    Verify GST number and fetch entity details + sales data.
    
    For MVP, returns realistic mock data.
    """
    try:
        return generate_mock_gst_data(request.gstin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-pan", response_model=PANVerifyResponse)
async def verify_pan(request: PANVerifyRequest):
    """
    Verify PAN and fetch entity details.
    
    For MVP, returns realistic mock data.
    """
    try:
        return generate_mock_pan_data(request.pan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pull-credit-bureau", response_model=CreditBureauResponse)
async def pull_credit_bureau(request: CreditBureauRequest):
    """
    Pull credit bureau report for entity and promoters.
    
    Requires consent_obtained=true.
    For MVP, returns realistic mock data.
    """
    if not request.consent_obtained:
        raise HTTPException(
            status_code=403, 
            detail="Credit bureau pull requires explicit consent"
        )
    
    try:
        return generate_mock_credit_bureau(
            request.entity_pan, 
            request.promoter_pans
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/lookup-udyam", response_model=UdyamLookupResponse)
async def lookup_udyam(request: UdyamLookupRequest):
    """
    Lookup Udyam registration by GSTIN, PAN, or Udyam number.
    
    For MVP, returns realistic mock data.
    """
    if not any([request.gstin, request.udyam_number, request.pan]):
        raise HTTPException(
            status_code=400,
            detail="At least one of gstin, udyam_number, or pan is required"
        )
    
    try:
        gstin = request.gstin or "09AADCF8429L1Z4"  # Use default for lookup
        return generate_mock_udyam(gstin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/famescore-report", response_model=FameScoreResponse)
async def get_famescore_report(request: FameScoreRequest):
    """
    Get comprehensive FameScore report combining all data sources.
    
    This is the primary endpoint called by n8n for parallel data aggregation.
    """
    if not request.consent_obtained:
        raise HTTPException(
            status_code=403,
            detail="FameScore report requires explicit consent"
        )
    
    try:
        # Fetch all data sources
        gst_response = generate_mock_gst_data(request.gstin)
        pan_response = generate_mock_pan_data(request.pan)
        bureau_response = generate_mock_credit_bureau(request.pan, [])
        udyam_response = generate_mock_udyam(request.gstin)
        
        # Calculate aggregated score
        base_score = 100
        
        # Deductions based on risk factors
        if bureau_response.commercial:
            if bureau_response.commercial.max_dpd_days > 0:
                base_score -= 15
            if bureau_response.commercial.overdue_amount_lakhs > 0:
                base_score -= 10
        
        if not udyam_response.found:
            base_score -= 5
        
        aggregated = {
            "overall_score": base_score,
            "risk_level": "low" if base_score >= 80 else "medium" if base_score >= 60 else "high",
            "data_completeness": 100 if udyam_response.found else 85,
            "recommendation": "proceed" if base_score >= 70 else "review"
        }
        
        return FameScoreResponse(
            success=True,
            gst_data=gst_response.dict() if gst_response.valid else None,
            pan_data=pan_response.dict() if pan_response.valid else None,
            credit_bureau=bureau_response.dict() if bureau_response.success else None,
            udyam_data=udyam_response.dict() if udyam_response.found else None,
            aggregated_score=aggregated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
