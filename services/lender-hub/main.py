"""
LenderHub Service
Unified Gateway for integration with multiple lender systems.
Handles protocol translation (REST/SOAP), data mapping, and submission.
"""

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import uuid
import asyncio
from datetime import datetime
import json
import httpx
import os

from models import (
    LenderSubmissionRequest, 
    LenderSubmissionResponse, 
    ApplicationStatusRequest, 
    ApplicationStatusResponse,
    LenderID
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lender-hub")

# Configuration
PORT = int(os.getenv("PORT", 8006))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections
    logger.info(f"Starting LenderHub Service on port {PORT}")
    yield
    # Shutdown: Cleanup
    logger.info("Shutting down LenderHub Service")

app = FastAPI(
    title="LenderHub Service",
    description="Unified Gateway for Lender Integration",
    version="1.0.0",
    lifespan=lifespan
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

# Mock databases for dev (simulating external lender systems)
MOCK_LENDER_DB = {
    "hdfc": {},
    "icici": {},
    "bajaj": {},
    "ugro": {},
    "indifi": {}
}

async def notify_tracker(application_id: str, status: str, details: dict):
    """Notify the Tracker service about submission updates"""
    try:
        tracker_url = os.getenv("TRACKER_URL", "http://tracker:8008")
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{tracker_url}/update-status",
                json={
                    "application_id": application_id,
                    "stage": status, 
                    "notes": f"Lender submission update: {json.dumps(details)}"
                }
            )
            logger.info(f"Notified tracker for {application_id}: {status}")
    except Exception as e:
        logger.error(f"Failed to notify tracker: {e}")

# =========================================================================
# LENDER ADAPTERS (Simulated)
# =========================================================================

async def submit_to_hdfc(request: LenderSubmissionRequest) -> dict:
    """Adapter for HDFC Bank (Simulating Enterprise REST API)"""
    # Simulate network latency
    await asyncio.sleep(1.5)
    
    # HDFC might require specific data transformation
    external_id = f"HDFC-{uuid.uuid4().hex[:8].upper()}"
    
    # Store in mock DB
    MOCK_LENDER_DB["hdfc"][external_id] = {
        "status": "UNDER_REVIEW",
        "submitted_at": datetime.now().isoformat(),
        "details": request.dict()
    }
    
    return {
        "external_id": external_id,
        "status": "submitted",
        "eta_days": 3,
        "message": "Application received. Relationship manager will contact within 24 hours."
    }

async def submit_to_icici(request: LenderSubmissionRequest) -> dict:
    """Adapter for ICICI Bank (Simulating SOAP/XML over HTTP)"""
    await asyncio.sleep(2.0)
    
    external_id = f"ICICI/SME/{uuid.uuid4().hex[:6].upper()}"
    
    MOCK_LENDER_DB["icici"][external_id] = {
        "status": "RECEIVED",
        "submitted_at": datetime.now().isoformat(),
        "details": request.dict()
    }
    
    return {
        "external_id": external_id,
        "status": "processing",
        "eta_days": 2,
        "message": "Digital application initiated."
    }

async def submit_to_bajaj(request: LenderSubmissionRequest) -> dict:
    """Adapter for Bajaj Finserv (Simulating Fast Fintech JSON API)"""
    await asyncio.sleep(0.5)
    
    external_id = f"BFL-{uuid.uuid4().int}"[:12]
    
    MOCK_LENDER_DB["bajaj"][external_id] = {
        "status": "AI_ASSESSMENT",
        "submitted_at": datetime.now().isoformat(),
        "details": request.dict()
    }
    
    return {
        "external_id": external_id,
        "status": "submitted",
        "eta_days": 1,
        "message": "Instant approval process started."
    }

# =========================================================================
# ENDPOINTS
# =========================================================================

@app.post("/submit", response_model=LenderSubmissionResponse)
async def submit_application(request: LenderSubmissionRequest, background_tasks: BackgroundTasks):
    """
    Submit an application to the selected lender.
    Routes to the appropriate adapter based on lender_id.
    """
    logger.info(f"Received submission for {request.lender_id}: {request.application_id}")
    
    try:
        if request.lender_id == LenderID.HDFC:
            result = await submit_to_hdfc(request)
        elif request.lender_id == LenderID.ICICI:
            result = await submit_to_icici(request)
        elif request.lender_id == LenderID.BAJAJ:
            result = await submit_to_bajaj(request)
        else:
            # Generic fallback for others
            await asyncio.sleep(1)
            external_id = f"GEN-{uuid.uuid4().hex[:8]}"
            MOCK_LENDER_DB[request.lender_id.value][external_id] = {
                "status": "recieved", "timestamp": datetime.now().isoformat()
            }
            result = {
                "external_id": external_id,
                "status": "submitted",
                "eta_days": 5,
                "message": "Standard processing."
            }
            
        # Notify tracker in background (fire and forget)
        # In a real system, this might update the main 'applications' table too
        background_tasks.add_task(
            notify_tracker, 
            request.application_id, 
            "submitted_to_lender",
            {"lender": request.lender_id, "external_id": result["external_id"]}
        )
            
        return LenderSubmissionResponse(
            platform_application_id=request.application_id,
            lender_id=request.lender_id,
            external_application_id=result["external_id"],
            status=result["status"],
            submission_timestamp=datetime.now().isoformat(),
            estimated_processing_days=result["eta_days"],
            next_steps=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Error submitting to {request.lender_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")

@app.post("/status", response_model=ApplicationStatusResponse)
async def check_status(request: ApplicationStatusRequest):
    """Check status of an application in the external lender system"""
    
    lender_db = MOCK_LENDER_DB.get(request.lender_id.value, {})
    record = lender_db.get(request.external_application_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Application not found in lender system")
        
    return ApplicationStatusResponse(
        platform_application_id=request.platform_application_id,
        external_application_id=request.external_application_id,
        current_stage=record.get("status", "UNKNOWN"),
        status_message="Processing normally",
        last_updated=datetime.now().isoformat()
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "lender-hub", "lenders_configured": len(MOCK_LENDER_DB)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)