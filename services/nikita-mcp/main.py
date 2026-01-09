"""
Nikita MCP Server
Document & CAM Assembly Agent
Orchestrates data collection and builds comprehensive Credit Assessment Memorandum
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
    title="Nikita MCP - CAM Assembly",
    description="Document assembly and CAM building agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class CAMBuildRequest(BaseModel):
    conversation_id: str
    gst_data: Dict[str, Any]
    pan_data: Dict[str, Any]
    credit_bureau: Dict[str, Any]
    bank_statements: Optional[Dict[str, Any]] = None
    udyam_data: Optional[Dict[str, Any]] = None
    itr_data: Optional[Dict[str, Any]] = None
    customer_inputs: Dict[str, Any]

class CAMBuildResponse(BaseModel):
    cam_id: str
    cam_status: str  # complete, incomplete
    cam_data: Dict[str, Any]
    missing_fields: List[str]
    data_flags: List[Dict[str, Any]]
    kesha_ready: bool
    documents_for_francis: List[str]

def build_cam_from_data(request: CAMBuildRequest) -> Dict[str, Any]:
    """
    Build comprehensive CAM structure from multiple data sources
    """
    cam_id = str(uuid.uuid4())

    # Extract entity identity from GST/PAN data
    entity_identity = {
        "legal_name": request.gst_data.get("entity_information", {}).get("legal_name"),
        "trade_name": request.gst_data.get("entity_information", {}).get("trade_name"),
        "constitution": request.gst_data.get("entity_information", {}).get("constitution"),
        "date_of_incorporation": request.gst_data.get("entity_information", {}).get("date_of_incorporation"),
        "gst_numbers": request.gst_data.get("entity_information", {}).get("gst_numbers", []),
        "pan": request.pan_data.get("pan"),
        "udyam_number": request.gst_data.get("entity_information", {}).get("udyam_number"),
        "cin": None,
        "registered_address": request.gst_data.get("entity_information", {}).get("registered_address", {})
    }

    # Extract promoters from credit bureau consumer data
    promoters = []
    if request.credit_bureau and "consumer" in request.credit_bureau:
        for promoter in request.credit_bureau["consumer"].get("promoters", []):
            promoters.append({
                "name": promoter.get("name"),
                "designation": "Director",
                "shareholding_pct": 50.0 / len(request.credit_bureau["consumer"].get("promoters", [1])),
                "pan": "XXXXX0000X",  # Masked
                "aadhar_masked": "xxxx1234",
                "credit_score": promoter.get("score"),
                "credit_bureau": promoter.get("bureau_type"),
                "outstanding_amount_lakhs": promoter.get("total_outstanding"),
                "overdue_amount_lakhs": promoter.get("overdue_amount"),
                "active_loans": promoter.get("active_loans")
            })

    # Business profile
    business_profile = {
        "industry_sector": "IT_services",
        "nic_code": request.udyam_data.get("activity_code") if request.udyam_data else "NIC 224",
        "hsn_sac_codes": ["998313"],
        "business_description": "Information Technology services, consulting and support",
        "years_in_business": calculate_years_in_business(entity_identity.get("date_of_incorporation")),
        "employee_count": request.udyam_data.get("employment", {}).get("total_employees", 50) if request.udyam_data else 50,
        "enterprise_type": "micro"
    }

    # Banking details
    banking_details = request.gst_data.get("bank_details", [])

    # Financial summary from GST and ITR
    financial_summary = build_financial_summary(request)

    # Credit profile
    credit_profile = build_credit_profile(request)

    # Compliance status
    compliance_status = {
        "gst": request.gst_data.get("compliance", {}),
        "itr": {
            "last_filed_year": request.itr_data["last_2_years"][0]["financial_year"] if request.itr_data else "2022-2023",
            "filed_on_time": True,
            "itr_type": "ITR-6"
        }
    }

    # Eligibility calculations
    eligibility = request.gst_data.get("bank_limit_eligibility", {})

    # Loan request
    loan_request = {
        "amount_lakhs": request.customer_inputs.get("loan_amount_requested"),
        "purpose": request.customer_inputs.get("loan_purpose"),
        "purpose_description": request.customer_inputs.get("loan_purpose_description", ""),
        "tenure_months": request.customer_inputs.get("tenure_preference_months"),
        "collateral": {
            "available": request.customer_inputs.get("collateral_available", False),
            "type": request.customer_inputs.get("collateral_type", "none"),
            "estimated_value_lakhs": request.customer_inputs.get("collateral_value", 0),
            "details": request.customer_inputs.get("collateral_details", "")
        },
        "urgency": request.customer_inputs.get("urgency", "2_weeks")
    }

    # Customer preferences
    customer_preferences = {
        "priority": request.customer_inputs.get("priority", "low_interest"),
        "lender_preference": request.customer_inputs.get("lender_preference", "any"),
        "existing_relationships": request.customer_inputs.get("existing_relationships", [])
    }

    # Validation flags
    verification_flags = perform_data_validation(request)

    # Documents
    documents_collected = []
    documents_pending = check_missing_documents(request)

    # Build complete CAM
    cam_data = {
        "cam_id": cam_id,
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "complete" if len(documents_pending) == 0 else "incomplete",
        "entity_identity": entity_identity,
        "promoters": promoters,
        "business_profile": business_profile,
        "banking_details": banking_details,
        "financial_summary": financial_summary,
        "credit_profile": credit_profile,
        "compliance_status": compliance_status,
        "eligibility_calculations": eligibility,
        "loan_request": loan_request,
        "customer_preferences": customer_preferences,
        "verification_flags": verification_flags,
        "documents_collected": documents_collected,
        "documents_pending": documents_pending
    }

    return cam_data

def calculate_years_in_business(incorporation_date: str) -> int:
    """Calculate years since incorporation"""
    if not incorporation_date:
        return 3
    try:
        inc_date = datetime.strptime(incorporation_date, "%Y-%m-%d")
        return (datetime.now() - inc_date).days // 365
    except:
        return 3

def build_financial_summary(request: CAMBuildRequest) -> Dict[str, Any]:
    """Build financial summary from GST and ITR data"""
    gst_sales = request.gst_data.get("gst_sales_data", {}).get("ttm_summary", {})
    bank_limit = request.gst_data.get("bank_limit_eligibility", {})

    return {
        "source": "gst_and_itr",
        "period": "TTM",
        "turnover": {
            "annual_lakhs": gst_sales.get("total_sales", 0),
            "monthly_average_lakhs": gst_sales.get("total_sales", 0) / 12,
            "growth_yoy_pct": 17.0,
            "quarterly_breakdown": request.gst_data.get("gst_sales_data", {}).get("quarterly_breakdown", [])
        },
        "profitability": {
            "net_profit_lakhs": request.itr_data["last_2_years"][0]["net_profit"] if request.itr_data else 8.92,
            "net_profit_margin_pct": 30.0,
            "current_ratio": request.itr_data["last_2_years"][0]["current_ratio"] if request.itr_data else 7.0,
            "total_outside_liabilities_lakhs": request.itr_data["last_2_years"][0]["total_outside_liabilities"] if request.itr_data else 393.74,
            "net_worth_lakhs": 0.0
        },
        "banking_behavior": {
            "total_credits_lakhs": request.bank_statements.get("total_credits_lakhs") if request.bank_statements else 111.91,
            "bank_to_turnover_ratio": request.bank_statements.get("bank_to_turnover_ratio") if request.bank_statements else 3.87,
            "inward_bounce_count": request.bank_statements.get("inward_bounces") if request.bank_statements else 0,
            "outward_bounce_count": request.bank_statements.get("outward_bounces") if request.bank_statements else 0,
            "average_monthly_balance_lakhs": request.bank_statements.get("average_monthly_balance_lakhs") if request.bank_statements else 5.5
        },
        "sales_analysis": {
            "b2b_share_pct": gst_sales.get("b2b_share_pct", 95.64),
            "export_share_pct": gst_sales.get("export_sales_pct", 4.19),
            "top_5_customer_concentration_pct": gst_sales.get("top_5_customer_concentration_pct", 69.50),
            "top_5_geographic_concentration_pct": gst_sales.get("top_5_geographic_concentration_pct", 96.02),
            "total_customers_b2b": gst_sales.get("b2b_customers", 930)
        },
        "purchase_analysis": {
            "total_purchases_lakhs": request.gst_data.get("gst_purchase_data", {}).get("ttm_summary", {}).get("total_purchase", 0),
            "top_5_supplier_concentration_pct": request.gst_data.get("gst_purchase_data", {}).get("ttm_summary", {}).get("top_5_supplier_concentration_pct", 0),
            "total_suppliers": request.gst_data.get("gst_purchase_data", {}).get("ttm_summary", {}).get("suppliers", 0)
        }
    }

def build_credit_profile(request: CAMBuildRequest) -> Dict[str, Any]:
    """Build credit profile from bureau data"""
    commercial = request.credit_bureau.get("commercial", {})
    facilities = request.credit_bureau.get("existing_facilities", [])

    # Calculate derived metrics
    total_outstanding = commercial.get("total_outstanding_loan_amount", 0)
    total_emi = sum(f.get("emi_in_bureau", 0) or 0 for f in facilities if f.get("status") == "Active")

    return {
        "commercial_bureau": {
            "bureau": "Experian",
            "score": commercial.get("score", "CMR-2"),
            "score_numeric": None,
            "member_since": commercial.get("member_since"),
            "total_outstanding_lakhs": total_outstanding,
            "overdue_amount_lakhs": commercial.get("overdue_amount", 0),
            "active_loans": commercial.get("active_loans", 0),
            "write_offs": 0
        },
        "existing_facilities": facilities,
        "derived_metrics": {
            "total_serviceable_debt_lakhs": total_outstanding,
            "debt_to_turnover_ratio": total_outstanding / request.gst_data.get("bank_limit_eligibility", {}).get("total_12_month_sales", 1) if request.gst_data.get("bank_limit_eligibility", {}).get("total_12_month_sales", 0) > 0 else 0,
            "monthly_obligations_lakhs": total_emi,
            "foir": total_emi / (request.gst_data.get("bank_limit_eligibility", {}).get("total_12_month_sales", 1) / 12) if request.gst_data.get("bank_limit_eligibility", {}).get("total_12_month_sales", 0) > 0 else 0
        }
    }

def perform_data_validation(request: CAMBuildRequest) -> List[Dict[str, Any]]:
    """Perform cross-validation checks"""
    flags = []

    # Check GST turnover vs ITR variance
    if request.itr_data and request.gst_data:
        gst_turnover = request.gst_data.get("bank_limit_eligibility", {}).get("total_12_month_sales", 0)
        itr_profit = request.itr_data["last_2_years"][0]["net_profit"] if request.itr_data else 0

        if abs(gst_turnover - (itr_profit * 10)) / gst_turnover > 0.15:
            flags.append({
                "field": "gst_turnover_vs_itr",
                "issue": "15% variance detected",
                "severity": "warning"
            })

    # Check bank credits to turnover ratio
    if request.bank_statements:
        bto_ratio = request.bank_statements.get("bank_to_turnover_ratio", 0)
        if bto_ratio < 0.8 or bto_ratio > 1.2:
            flags.append({
                "field": "bank_to_turnover_ratio",
                "issue": f"Ratio {bto_ratio} outside acceptable range (0.8-1.2)",
                "severity": "warning"
            })

    return flags

def check_missing_documents(request: CAMBuildRequest) -> List[str]:
    """Check for missing required documents"""
    missing = []

    if not request.bank_statements:
        missing.append("bank_statement_6_months")

    if not request.itr_data:
        missing.append("itr_latest")

    if not request.udyam_data:
        missing.append("udyam_certificate")

    return missing

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "nikita-mcp",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/build-cam", response_model=CAMBuildResponse)
async def build_cam(request: CAMBuildRequest):
    """
    Build comprehensive CAM from collected data sources
    """
    try:
        logger.info(f"CAM build requested for conversation: {request.conversation_id}")

        # Build CAM
        cam_data = build_cam_from_data(request)

        # Determine completeness
        missing_fields = cam_data["documents_pending"]
        data_flags = cam_data["verification_flags"]

        cam_status = "complete" if len(missing_fields) == 0 else "incomplete"
        kesha_ready = cam_status == "complete"

        # Generate messages for Francis
        documents_for_francis = []
        if "bank_statement_6_months" in missing_fields:
            documents_for_francis.append("Please upload your last 6 months bank statement")
        if "itr_latest" in missing_fields:
            documents_for_francis.append("Please upload your latest ITR")

        return CAMBuildResponse(
            cam_id=cam_data["cam_id"],
            cam_status=cam_status,
            cam_data=cam_data,
            missing_fields=missing_fields,
            data_flags=data_flags,
            kesha_ready=kesha_ready,
            documents_for_francis=documents_for_francis
        )

    except Exception as e:
        logger.error(f"CAM build failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prepare-submission")
async def prepare_submission(cam_id: str, lender_id: str, format: str = "excel"):
    """
    Prepare lender-specific document package
    Transform CAM to lender format (e.g., UGRO CAM Excel, HDFC format)
    """
    try:
        logger.info(f"Document preparation for CAM {cam_id}, Lender {lender_id}")

        # Mock response - in production, this would transform CAM data to lender format
        return {
            "success": True,
            "documents": [
                {
                    "type": "cam_excel",
                    "lender_format": lender_id,
                    "file_reference": f"cam_{cam_id}_{lender_id}.xlsx",
                    "ready_for_submission": True
                }
            ],
            "submission_package": {
                "cam_id": cam_id,
                "lender_id": lender_id,
                "documents_count": 5,
                "validation_status": "passed"
            }
        }

    except Exception as e:
        logger.error(f"Document preparation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
