"""
Loan Application Orchestration Endpoint
Handles complete loan assessment flow from frontend
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid
import httpx
import os

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Loan Application"])

# Service URLs
DATA_SERVICES_URL = os.environ.get("DATA_SERVICES_URL", "http://localhost:8001")
NIKITA_MCP_URL = os.environ.get("NIKITA_MCP_URL", "http://localhost:8002")
KESHA_MCP_URL = os.environ.get("KESHA_MCP_URL", "http://localhost:8003")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")

# Request Models
class LoanApplicationRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15, description="15-character GSTIN")
    pan: str = Field(..., min_length=10, max_length=10, description="10-character PAN")
    loan_amount_lakhs: float = Field(..., gt=0, description="Loan amount requested in lakhs")
    loan_purpose: str = Field(..., description="Purpose of loan")
    tenure_months: int = Field(default=36, description="Preferred tenure in months")
    priority: str = Field(default="low_interest", description="Customer priority: low_interest, quick_disbursement, high_amount")
    has_collateral: bool = Field(default=False, description="Whether collateral is available")
    consent_credit_bureau: bool = Field(default=True, description="Consent for credit bureau check")
    consent_data_sharing: bool = Field(default=True, description="Consent for data sharing with lenders")

# Response Models
class LenderMatch(BaseModel):
    lender_id: str
    lender_name: str
    product: str
    eligible_amount_lakhs: float
    interest_rate_range: str
    tenure_months: int
    approval_probability: float
    requirements: List[str]

class LoanApplicationResponse(BaseModel):
    application_id: str
    conversation_id: str
    status: str
    overall_eligibility: str
    max_eligible_amount_lakhs: float
    business_name: str
    credit_score: str
    strengths: List[str]
    improvements: List[str]
    lender_matches: List[LenderMatch]
    recommendation: Dict[str, Any]
    next_steps: List[str]
    created_at: str

@router.post("/submit", response_model=LoanApplicationResponse)
async def submit_loan_application(request: LoanApplicationRequest):
    """
    Submit a loan application and get instant eligibility assessment

    This endpoint orchestrates the complete flow:
    1. Fetches business data from Data Services (GST, PAN, Credit Bureau)
    2. Builds CAM using Nikita
    3. Gets credit assessment and lender matches from Kesha
    4. Returns comprehensive results to frontend
    """
    application_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())

    logger.info(f"New loan application: {application_id}, GSTIN: {request.gstin}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Fetch FameScore report from Data Services
            logger.info("Step 1: Fetching FameScore report...")
            famescore_response = await client.post(
                f"{DATA_SERVICES_URL}/famescore-report",
                json={
                    "gstin": request.gstin,
                    "pan": request.pan,
                    "include_bureau": request.consent_credit_bureau
                }
            )

            if famescore_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Data Services error: {famescore_response.text}"
                )

            famescore_data = famescore_response.json().get("data", {})
            logger.info("FameScore report fetched successfully")

            # Step 2: Build CAM using Nikita
            logger.info("Step 2: Building CAM...")
            cam_request = {
                "conversation_id": conversation_id,
                "gst_data": {
                    "entity_information": famescore_data.get("entity_information", {}),
                    "bank_limit_eligibility": famescore_data.get("bank_limit_eligibility", {}),
                    "gst_sales_data": famescore_data.get("gst_sales_data", {}),
                    "gst_purchase_data": famescore_data.get("gst_purchase_data", {}),
                    "compliance": famescore_data.get("compliance", {})
                },
                "pan_data": {"pan": request.pan},
                "credit_bureau": {
                    "commercial": famescore_data.get("credit_bureau_commercial", {}),
                    "consumer": famescore_data.get("credit_bureau_consumer", {}),
                    "existing_facilities": famescore_data.get("existing_facilities", [])
                },
                "bank_statements": famescore_data.get("bank_statement_analysis", {}),
                "udyam_data": famescore_data.get("udyam_registration", {}),
                "itr_data": famescore_data.get("itr_data", {}),
                "customer_inputs": {
                    "loan_amount_requested": request.loan_amount_lakhs,
                    "loan_purpose": request.loan_purpose,
                    "tenure_preference_months": request.tenure_months,
                    "priority": request.priority,
                    "collateral_available": request.has_collateral
                }
            }

            cam_response = await client.post(
                f"{NIKITA_MCP_URL}/build-cam",
                json=cam_request
            )

            if cam_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Nikita CAM build error: {cam_response.text}"
                )

            cam_result = cam_response.json()
            cam_data = cam_result.get("cam_data", {})
            logger.info(f"CAM built successfully: {cam_result.get('cam_id')}")

            # Step 3: Get credit assessment from Kesha
            logger.info("Step 3: Getting credit assessment...")

            # Extract financial metrics from CAM
            financial_summary = cam_data.get("financial_summary", {})
            turnover = financial_summary.get("turnover", {})

            assessment_request = {
                "cam_id": cam_result.get("cam_id"),
                "business_profile": {
                    "vintage_years": cam_data.get("business_profile", {}).get("years_in_business", 3),
                    "industry_sector": cam_data.get("business_profile", {}).get("industry_sector", "general"),
                    "enterprise_type": cam_data.get("business_profile", {}).get("enterprise_type", "micro")
                },
                "financial_metrics": {
                    "annual_turnover_lakhs": turnover.get("annual_lakhs", 100),
                    "profit_margin": financial_summary.get("profitability", {}).get("net_profit_margin_pct", 10) / 100,
                    "turnover_growth_yoy": turnover.get("growth_yoy_pct", 10) / 100
                },
                "credit_profile": {
                    "commercial_score": cam_data.get("credit_profile", {}).get("commercial_bureau", {}).get("score", "CMR-4"),
                    "active_loans_count": cam_data.get("credit_profile", {}).get("commercial_bureau", {}).get("active_loans", 0),
                    "utilization_pct": 0.5,
                    "existing_facilities": cam_data.get("credit_profile", {}).get("existing_facilities", [])
                },
                "compliance": {
                    "filing_consistency": cam_data.get("compliance_status", {}).get("gst", {}).get("filing_consistency", 0.9)
                },
                "loan_request": {
                    "amount_lakhs": request.loan_amount_lakhs,
                    "purpose": request.loan_purpose,
                    "tenure_months": request.tenure_months
                },
                "customer_preferences": {
                    "priority": request.priority,
                    "lender_preference": "any"
                }
            }

            assessment_response = await client.post(
                f"{KESHA_MCP_URL}/assess",
                json=assessment_request
            )

            if assessment_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Kesha assessment error: {assessment_response.text}"
                )

            assessment_result = assessment_response.json()
            logger.info(f"Assessment complete: {assessment_result.get('overall_eligibility')}")

            # Step 4: Trigger n8n webhook (if configured) for async processing
            if N8N_WEBHOOK_URL:
                try:
                    await client.post(
                        N8N_WEBHOOK_URL,
                        json={
                            "application_id": application_id,
                            "conversation_id": conversation_id,
                            "cam_id": cam_result.get("cam_id"),
                            "assessment_id": assessment_result.get("assessment_id"),
                            "gstin": request.gstin,
                            "status": "assessment_complete"
                        }
                    )
                    logger.info("n8n webhook triggered successfully")
                except Exception as e:
                    logger.warning(f"n8n webhook failed (non-critical): {str(e)}")

            # Build response
            entity_info = famescore_data.get("entity_information", {})
            business_name = entity_info.get("legal_name") or entity_info.get("trade_name") or "Your Business"

            customer_report = assessment_result.get("customer_report", {})

            # Transform lender matches
            lender_matches = []
            for match in assessment_result.get("lender_matches", []):
                lender_matches.append(LenderMatch(
                    lender_id=match.get("lender_id"),
                    lender_name=match.get("lender_name"),
                    product=match.get("product"),
                    eligible_amount_lakhs=match.get("eligible_amount_lakhs"),
                    interest_rate_range=match.get("interest_rate_range"),
                    tenure_months=match.get("tenure_months"),
                    approval_probability=match.get("approval_probability"),
                    requirements=match.get("requirements", [])
                ))

            return LoanApplicationResponse(
                application_id=application_id,
                conversation_id=conversation_id,
                status="assessment_complete",
                overall_eligibility=assessment_result.get("overall_eligibility", "medium"),
                max_eligible_amount_lakhs=assessment_result.get("max_eligible_amount_lakhs", 0),
                business_name=business_name,
                credit_score=cam_data.get("credit_profile", {}).get("commercial_bureau", {}).get("score", "N/A"),
                strengths=customer_report.get("strengths", []),
                improvements=customer_report.get("improvements", []),
                lender_matches=lender_matches,
                recommendation=assessment_result.get("recommendation", {}),
                next_steps=customer_report.get("next_steps", [
                    "Review lender options and select your preferred lender(s)",
                    "Prepare required documents (bank statements, ITR, GST certificate)",
                    "Submit application through our platform"
                ]),
                created_at=datetime.now().isoformat()
            )

    except httpx.TimeoutException:
        logger.error("Service timeout during loan application processing")
        raise HTTPException(
            status_code=504,
            detail="Service timeout. Please try again."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Loan application failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Application processing failed: {str(e)}"
        )


@router.get("/status/{application_id}")
async def get_application_status(application_id: str):
    """Get the status of a loan application"""
    # In production, this would fetch from database
    return {
        "application_id": application_id,
        "status": "assessment_complete",
        "message": "Your application has been assessed. View results in your dashboard."
    }
