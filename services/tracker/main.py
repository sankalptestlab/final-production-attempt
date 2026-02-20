"""
Application Tracker Agent - Lifecycle Tracking, State Machine, SLA Monitoring
Port: 8008

Tracks loan applications through their complete lifecycle:
- State machine for application phases
- Timeline event logging
- SLA monitoring and alerts
- Status queries and updates
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
import uuid

app = FastAPI(
    title="Application Tracker Agent",
    description="Application lifecycle tracking, state machine, SLA monitoring",
    version="1.0.0"
)

# CORS middleware - Restrict to internal services only
import os
INTERNAL_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://francis:8000,http://lender-hub:8006,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=INTERNAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ===========================================
# STATE MACHINE DEFINITIONS
# ===========================================

class ApplicationStage(str, Enum):
    INTAKE = "intake"
    DATA_COLLECTION = "data_collection"
    DATA_VALIDATION = "data_validation"
    CAM_BUILDING = "cam_building"
    ASSESSMENT = "assessment"
    LENDER_SELECTION = "lender_selection"
    DOCUMENT_COLLECTION = "document_collection"
    SUBMISSION = "submission"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SANCTIONED = "sanctioned"
    DISBURSEMENT = "disbursement"
    COMPLETED = "completed"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class SLAStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"

# Valid state transitions
VALID_TRANSITIONS = {
    ApplicationStage.INTAKE: [ApplicationStage.DATA_COLLECTION, ApplicationStage.WITHDRAWN],
    ApplicationStage.DATA_COLLECTION: [ApplicationStage.DATA_VALIDATION, ApplicationStage.WITHDRAWN],
    ApplicationStage.DATA_VALIDATION: [ApplicationStage.CAM_BUILDING, ApplicationStage.DATA_COLLECTION, ApplicationStage.WITHDRAWN],
    ApplicationStage.CAM_BUILDING: [ApplicationStage.ASSESSMENT, ApplicationStage.WITHDRAWN],
    ApplicationStage.ASSESSMENT: [ApplicationStage.LENDER_SELECTION, ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN],
    ApplicationStage.LENDER_SELECTION: [ApplicationStage.DOCUMENT_COLLECTION, ApplicationStage.WITHDRAWN],
    ApplicationStage.DOCUMENT_COLLECTION: [ApplicationStage.SUBMISSION, ApplicationStage.WITHDRAWN],
    ApplicationStage.SUBMISSION: [ApplicationStage.UNDER_REVIEW, ApplicationStage.WITHDRAWN],
    ApplicationStage.UNDER_REVIEW: [ApplicationStage.APPROVED, ApplicationStage.REJECTED],
    ApplicationStage.APPROVED: [ApplicationStage.SANCTIONED, ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN],
    ApplicationStage.SANCTIONED: [ApplicationStage.DISBURSEMENT, ApplicationStage.WITHDRAWN],
    ApplicationStage.DISBURSEMENT: [ApplicationStage.COMPLETED],
    ApplicationStage.COMPLETED: [],
    ApplicationStage.REJECTED: [],
    ApplicationStage.WITHDRAWN: [],
}

# SLA definitions (hours)
SLA_DEFINITIONS = {
    ApplicationStage.INTAKE: {"max_hours": 1, "warning_hours": 0.5},
    ApplicationStage.DATA_COLLECTION: {"max_hours": 24, "warning_hours": 12},
    ApplicationStage.DATA_VALIDATION: {"max_hours": 2, "warning_hours": 1},
    ApplicationStage.CAM_BUILDING: {"max_hours": 1, "warning_hours": 0.5},
    ApplicationStage.ASSESSMENT: {"max_hours": 1, "warning_hours": 0.5},
    ApplicationStage.LENDER_SELECTION: {"max_hours": 48, "warning_hours": 24},
    ApplicationStage.DOCUMENT_COLLECTION: {"max_hours": 72, "warning_hours": 48},
    ApplicationStage.SUBMISSION: {"max_hours": 4, "warning_hours": 2},
    ApplicationStage.UNDER_REVIEW: {"max_hours": 168, "warning_hours": 120},  # 7 days
    ApplicationStage.APPROVED: {"max_hours": 24, "warning_hours": 12},
    ApplicationStage.SANCTIONED: {"max_hours": 72, "warning_hours": 48},
    ApplicationStage.DISBURSEMENT: {"max_hours": 48, "warning_hours": 24},
}

# ===========================================
# IN-MEMORY STORAGE (Would be DB in production)
# ===========================================

applications: Dict[str, Dict[str, Any]] = {}
timelines: Dict[str, List[Dict[str, Any]]] = {}

# ===========================================
# MODELS
# ===========================================

class CreateApplicationRequest(BaseModel):
    conversation_id: str
    customer_id: Optional[str] = None
    initial_stage: ApplicationStage = ApplicationStage.INTAKE
    metadata: Optional[Dict[str, Any]] = None

class UpdateStatusRequest(BaseModel):
    application_id: str
    new_stage: ApplicationStage
    actor_type: str = "system"  # "system", "user", "lender", "admin"
    actor_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    actor_type: str
    actor_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PendingAction(BaseModel):
    action: str
    description: str
    required_by: Optional[str] = None
    priority: str = "medium"

class ApplicationStatus(BaseModel):
    application_id: str
    conversation_id: str
    current_stage: ApplicationStage
    stage_entered_at: str
    time_in_stage_hours: float
    sla_status: SLAStatus
    sla_deadline: Optional[str] = None
    pending_actions: List[PendingAction]
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class ApplicationStatusResponse(BaseModel):
    application: ApplicationStatus
    timeline: List[TimelineEvent]
    next_possible_stages: List[str]

class SLACheckResponse(BaseModel):
    application_id: str
    current_stage: str
    sla_status: SLAStatus
    time_in_stage_hours: float
    max_allowed_hours: float
    time_remaining_hours: Optional[float] = None
    breach_time: Optional[str] = None

# ===========================================
# BUSINESS LOGIC
# ===========================================

def create_application(request: CreateApplicationRequest) -> str:
    """Create a new application tracking record"""
    app_id = str(uuid.uuid4())
    now = datetime.utcnow()

    applications[app_id] = {
        "application_id": app_id,
        "conversation_id": request.conversation_id,
        "customer_id": request.customer_id,
        "current_stage": request.initial_stage,
        "stage_entered_at": now.isoformat(),
        "metadata": request.metadata or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # Initialize timeline
    timelines[app_id] = [{
        "event_id": str(uuid.uuid4()),
        "timestamp": now.isoformat(),
        "event_type": "application_created",
        "from_stage": None,
        "to_stage": request.initial_stage.value,
        "actor_type": "system",
        "actor_id": None,
        "notes": "Application tracking initiated",
        "metadata": request.metadata
    }]

    return app_id

def update_status(request: UpdateStatusRequest) -> bool:
    """Update application status with state machine validation"""
    if request.application_id not in applications:
        raise ValueError(f"Application not found: {request.application_id}")

    app = applications[request.application_id]
    current_stage = ApplicationStage(app["current_stage"])

    # Validate transition
    valid_next_stages = VALID_TRANSITIONS.get(current_stage, [])
    if request.new_stage not in valid_next_stages:
        raise ValueError(
            f"Invalid transition from {current_stage.value} to {request.new_stage.value}. "
            f"Valid transitions: {[s.value for s in valid_next_stages]}"
        )

    now = datetime.utcnow()

    # Update application
    app["current_stage"] = request.new_stage
    app["stage_entered_at"] = now.isoformat()
    app["updated_at"] = now.isoformat()
    if request.metadata:
        app["metadata"].update(request.metadata)

    # Add timeline event
    timelines[request.application_id].append({
        "event_id": str(uuid.uuid4()),
        "timestamp": now.isoformat(),
        "event_type": "stage_transition",
        "from_stage": current_stage.value,
        "to_stage": request.new_stage.value,
        "actor_type": request.actor_type,
        "actor_id": request.actor_id,
        "notes": request.notes,
        "metadata": request.metadata
    })

    return True

def calculate_sla_status(app: Dict[str, Any]) -> tuple[SLAStatus, Optional[datetime]]:
    """Calculate SLA status for an application"""
    stage = ApplicationStage(app["current_stage"])

    if stage not in SLA_DEFINITIONS:
        return SLAStatus.ON_TRACK, None

    sla = SLA_DEFINITIONS[stage]
    stage_entered = datetime.fromisoformat(app["stage_entered_at"])
    now = datetime.utcnow()
    time_in_stage = (now - stage_entered).total_seconds() / 3600  # hours

    deadline = stage_entered + timedelta(hours=sla["max_hours"])

    if time_in_stage > sla["max_hours"]:
        return SLAStatus.BREACHED, deadline
    elif time_in_stage > sla["warning_hours"]:
        return SLAStatus.AT_RISK, deadline
    else:
        return SLAStatus.ON_TRACK, deadline

def get_pending_actions(stage: ApplicationStage) -> List[PendingAction]:
    """Get pending actions for a stage"""
    actions_map = {
        ApplicationStage.INTAKE: [
            PendingAction(action="collect_basic_info", description="Collect GSTIN, PAN, and loan requirements", priority="high")
        ],
        ApplicationStage.DATA_COLLECTION: [
            PendingAction(action="verify_gstin", description="Verify GST registration", priority="high"),
            PendingAction(action="verify_pan", description="Verify PAN details", priority="high"),
            PendingAction(action="pull_bureau", description="Pull credit bureau report", priority="high"),
        ],
        ApplicationStage.DATA_VALIDATION: [
            PendingAction(action="validate_data", description="Run data quality checks", priority="high")
        ],
        ApplicationStage.LENDER_SELECTION: [
            PendingAction(action="select_lender", description="Customer to select preferred lender", priority="high")
        ],
        ApplicationStage.DOCUMENT_COLLECTION: [
            PendingAction(action="upload_pan", description="Upload PAN card copy", priority="high"),
            PendingAction(action="upload_aadhaar", description="Upload Aadhaar card copy", priority="high"),
            PendingAction(action="upload_bank_statements", description="Upload 12 months bank statements", priority="high"),
            PendingAction(action="upload_gst_certificate", description="Upload GST registration certificate", priority="medium"),
        ],
        ApplicationStage.UNDER_REVIEW: [
            PendingAction(action="await_lender_decision", description="Awaiting lender review", priority="medium")
        ],
        ApplicationStage.SANCTIONED: [
            PendingAction(action="sign_agreement", description="Customer to sign loan agreement", priority="high")
        ],
    }

    return actions_map.get(stage, [])

def get_application_status(app_id: str) -> ApplicationStatusResponse:
    """Get full application status with timeline"""
    if app_id not in applications:
        raise ValueError(f"Application not found: {app_id}")

    app = applications[app_id]
    stage = ApplicationStage(app["current_stage"])
    stage_entered = datetime.fromisoformat(app["stage_entered_at"])
    now = datetime.utcnow()

    time_in_stage = (now - stage_entered).total_seconds() / 3600
    sla_status, deadline = calculate_sla_status(app)
    pending_actions = get_pending_actions(stage)

    status = ApplicationStatus(
        application_id=app["application_id"],
        conversation_id=app["conversation_id"],
        current_stage=stage,
        stage_entered_at=app["stage_entered_at"],
        time_in_stage_hours=round(time_in_stage, 2),
        sla_status=sla_status,
        sla_deadline=deadline.isoformat() if deadline else None,
        pending_actions=pending_actions,
        metadata=app.get("metadata"),
        created_at=app["created_at"],
        updated_at=app["updated_at"]
    )

    timeline_events = [
        TimelineEvent(**event) for event in timelines.get(app_id, [])
    ]

    next_stages = [s.value for s in VALID_TRANSITIONS.get(stage, [])]

    return ApplicationStatusResponse(
        application=status,
        timeline=timeline_events,
        next_possible_stages=next_stages
    )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tracker",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "active_applications": len(applications)
    }

@app.post("/create")
async def create(request: CreateApplicationRequest):
    """
    Create a new application tracking record.
    Returns the application ID for future tracking.
    """
    try:
        app_id = create_application(request)
        return {
            "application_id": app_id,
            "conversation_id": request.conversation_id,
            "initial_stage": request.initial_stage.value,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-status")
async def update_application_status(request: UpdateStatusRequest):
    """
    Update application status with state machine validation.
    Only valid transitions are allowed.
    """
    try:
        update_status(request)
        return {
            "success": True,
            "application_id": request.application_id,
            "new_stage": request.new_stage.value,
            "updated_at": datetime.utcnow().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{application_id}", response_model=ApplicationStatusResponse)
async def get_status(application_id: str):
    """
    Get full application status including timeline and pending actions.
    """
    try:
        return get_application_status(application_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/by-conversation/{conversation_id}")
async def get_status_by_conversation(conversation_id: str):
    """
    Get application status by conversation ID.
    """
    for app_id, app in applications.items():
        if app["conversation_id"] == conversation_id:
            return get_application_status(app_id)

    raise HTTPException(status_code=404, detail=f"No application found for conversation: {conversation_id}")

@app.get("/timeline/{application_id}")
async def get_timeline(application_id: str):
    """
    Get timeline events for an application.
    """
    if application_id not in timelines:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")

    return {
        "application_id": application_id,
        "events": timelines[application_id],
        "event_count": len(timelines[application_id])
    }

@app.get("/sla-check/{application_id}", response_model=SLACheckResponse)
async def check_sla(application_id: str):
    """
    Check SLA status for an application.
    """
    if application_id not in applications:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")

    app = applications[application_id]
    stage = ApplicationStage(app["current_stage"])
    stage_entered = datetime.fromisoformat(app["stage_entered_at"])
    now = datetime.utcnow()

    time_in_stage = (now - stage_entered).total_seconds() / 3600
    sla_status, deadline = calculate_sla_status(app)

    sla_def = SLA_DEFINITIONS.get(stage, {"max_hours": 0})
    time_remaining = sla_def.get("max_hours", 0) - time_in_stage

    return SLACheckResponse(
        application_id=application_id,
        current_stage=stage.value,
        sla_status=sla_status,
        time_in_stage_hours=round(time_in_stage, 2),
        max_allowed_hours=sla_def.get("max_hours", 0),
        time_remaining_hours=max(0, round(time_remaining, 2)) if time_remaining > 0 else None,
        breach_time=deadline.isoformat() if deadline and sla_status == SLAStatus.BREACHED else None
    )

@app.get("/sla-breaches")
async def get_sla_breaches():
    """
    Get all applications with breached or at-risk SLAs.
    """
    breaches = []
    at_risk = []

    for app_id, app in applications.items():
        stage = ApplicationStage(app["current_stage"])
        if stage in [ApplicationStage.COMPLETED, ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN]:
            continue

        sla_status, _ = calculate_sla_status(app)

        if sla_status == SLAStatus.BREACHED:
            breaches.append({
                "application_id": app_id,
                "conversation_id": app["conversation_id"],
                "current_stage": stage.value,
                "stage_entered_at": app["stage_entered_at"]
            })
        elif sla_status == SLAStatus.AT_RISK:
            at_risk.append({
                "application_id": app_id,
                "conversation_id": app["conversation_id"],
                "current_stage": stage.value,
                "stage_entered_at": app["stage_entered_at"]
            })

    return {
        "breached": breaches,
        "breached_count": len(breaches),
        "at_risk": at_risk,
        "at_risk_count": len(at_risk),
        "checked_at": datetime.utcnow().isoformat()
    }

@app.post("/add-event/{application_id}")
async def add_timeline_event(
    application_id: str,
    event_type: str,
    notes: Optional[str] = None,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Add a custom timeline event (without changing stage).
    Useful for logging milestones, comments, or external events.
    """
    if application_id not in applications:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")

    now = datetime.utcnow()
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": now.isoformat(),
        "event_type": event_type,
        "from_stage": None,
        "to_stage": None,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "notes": notes,
        "metadata": metadata
    }

    timelines[application_id].append(event)
    applications[application_id]["updated_at"] = now.isoformat()

    return {"success": True, "event_id": event["event_id"]}

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
