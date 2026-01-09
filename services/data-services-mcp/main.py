"""
Data Services MCP Server
Stateless API gateway for external data sources (GST, PAN, Credit Bureau, Udyam, ITR)
"""

import load_env  # Load .env variables

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime
import logging

from mock_data_templates import (
    generate_mock_famescore_report,
    generate_mock_pan_verification,
    generate_mock_gst_verification
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Services MCP",
    description="External API Gateway for GST, PAN, Credit Bureau, Udyam, ITR data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class GSTVerificationRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15, description="15-character GSTIN")

class PANVerificationRequest(BaseModel):
    pan: str = Field(..., min_length=10, max_length=10, description="10-character PAN")

class CreditBureauRequest(BaseModel):
    entity_pan: str = Field(..., description="Entity PAN for commercial bureau")
    promoter_pans: Optional[list[str]] = Field(default=[], description="Promoter PANs for consumer bureau")
    consent_obtained: bool = Field(..., description="Consent flag - must be true")

class UdyamLookupRequest(BaseModel):
    udyam_number: Optional[str] = Field(None, description="Udyam registration number")
    pan: Optional[str] = Field(None, description="PAN to search by")

class FameScoreRequest(BaseModel):
    gstin: str = Field(..., description="Primary GSTIN")
    pan: str = Field(..., description="Entity PAN")
    include_bureau: bool = Field(default=True, description="Include credit bureau data")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "data-services-mcp",
        "timestamp": datetime.now().isoformat()
    }

# GST Verification
@app.post("/verify-gst")
async def verify_gst(request: GSTVerificationRequest):
    """
    Verify GST number and return basic details
    Mock implementation - replace with actual GST API
    """
    try:
        logger.info(f"GST verification requested for: {request.gstin}")

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.5)

        # Return mock data
        result = generate_mock_gst_verification(request.gstin)

        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"GST verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# PAN Verification
@app.post("/verify-pan")
async def verify_pan(request: PANVerificationRequest):
    """
    Verify PAN and return entity details
    Mock implementation - replace with actual PAN verification API
    """
    try:
        logger.info(f"PAN verification requested for: {request.pan}")

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.3)

        # Return mock data
        result = generate_mock_pan_verification(request.pan)

        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"PAN verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Credit Bureau Pull
@app.post("/pull-credit-bureau")
async def pull_credit_bureau(request: CreditBureauRequest):
    """
    Pull credit bureau data for entity and promoters
    Mock implementation - replace with CIBIL/Experian API
    """
    try:
        if not request.consent_obtained:
            raise HTTPException(
                status_code=403,
                detail="Credit bureau consent not obtained"
            )

        logger.info(f"Credit bureau pull requested for PAN: {request.entity_pan}")

        # Simulate API delay
        import asyncio
        await asyncio.sleep(1.5)

        # Generate mock FameScore report which includes bureau data
        mock_report = generate_mock_famescore_report("09AADCF8429L1Z4", request.entity_pan)

        return {
            "success": True,
            "data": {
                "commercial": mock_report["credit_bureau_commercial"],
                "consumer": mock_report["credit_bureau_consumer"],
                "existing_facilities": mock_report["existing_facilities"],
                "closed_loans": mock_report["closed_loans"]
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credit bureau pull failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Udyam Lookup
@app.post("/lookup-udyam")
async def lookup_udyam(request: UdyamLookupRequest):
    """
    Lookup Udyam registration details
    Mock implementation - replace with actual Udyam API
    """
    try:
        logger.info(f"Udyam lookup requested")

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.8)

        # Generate mock data
        mock_report = generate_mock_famescore_report("09AADCF8429L1Z4", request.pan or "AADCF8429L")

        return {
            "success": True,
            "data": mock_report["udyam_registration"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Udyam lookup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# FameScore Full Report (Primary Integration Point)
@app.post("/famescore-report")
async def famescore_report(request: FameScoreRequest):
    """
    Get comprehensive FameScore report with GST, ITR, Bureau data
    This is the primary integration point that returns all data at once
    Mock implementation - replace with actual FameScore API
    """
    try:
        logger.info(f"FameScore report requested for GSTIN: {request.gstin}")

        # Simulate API delay (FameScore takes time to compile all data)
        import asyncio
        await asyncio.sleep(2.0)

        # Generate complete mock report
        report = generate_mock_famescore_report(request.gstin, request.pan)

        return {
            "success": True,
            "data": report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"FameScore report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Bank Statement Parsing
@app.post("/parse-bank-statement")
async def parse_bank_statement(file_reference: str):
    """
    Parse uploaded bank statement
    Mock implementation - replace with actual parser
    """
    try:
        logger.info(f"Bank statement parsing requested for: {file_reference}")

        # Simulate processing delay
        import asyncio
        await asyncio.sleep(1.0)

        # Return mock parsed data
        return {
            "success": True,
            "data": {
                "total_credits_lakhs": 111.913025,
                "total_debits_lakhs": 110.0,
                "average_monthly_balance_lakhs": 5.5,
                "inward_bounces": 0,
                "outward_bounces": 0,
                "bank_to_turnover_ratio": 3.87,
                "analysis_period_months": 12
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Bank statement parsing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ITR Fetch
@app.post("/fetch-itr")
async def fetch_itr(pan: str, consent_obtained: bool):
    """
    Fetch ITR data (with consent)
    Mock implementation - replace with actual ITR API
    """
    try:
        if not consent_obtained:
            raise HTTPException(
                status_code=403,
                detail="ITR access consent not obtained"
            )

        logger.info(f"ITR fetch requested for PAN: {pan}")

        # Simulate API delay
        import asyncio
        await asyncio.sleep(1.2)

        # Generate mock data
        mock_report = generate_mock_famescore_report("09AADCF8429L1Z4", pan)

        return {
            "success": True,
            "data": mock_report["itr_data"],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ITR fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
