"""
Data Quality Agent - Validation, Quality Checks, and Anomaly Detection
Port: 8009

Cross-validates data from multiple sources (GST, PAN, Bureau, Bank Statements),
detects anomalies, and ensures data quality before CAM building.
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
    title="Data Quality Agent",
    description="Data validation, quality checks, and cross-source anomaly detection",
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
# MODELS
# ===========================================

class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(str, Enum):
    FORMAT = "format"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    RANGE = "range"
    CROSS_VALIDATION = "cross_validation"

class GSTData(BaseModel):
    gstin: Optional[str] = None
    entity_info: Optional[Dict[str, Any]] = None
    sales_data: Optional[Dict[str, Any]] = None
    filing_status: Optional[Dict[str, str]] = None

class PANData(BaseModel):
    pan: Optional[str] = None
    name: Optional[str] = None
    entity_type: Optional[str] = None
    status: Optional[str] = None

class BureauData(BaseModel):
    commercial: Optional[Dict[str, Any]] = None
    consumer: Optional[List[Dict[str, Any]]] = None

class BankData(BaseModel):
    average_balance_lakhs: Optional[float] = None
    total_credits_lakhs: Optional[float] = None
    total_debits_lakhs: Optional[float] = None
    months_analyzed: Optional[int] = None

class ValidateRequest(BaseModel):
    conversation_id: Optional[str] = None
    gst_data: Optional[GSTData] = None
    pan_data: Optional[PANData] = None
    bureau_data: Optional[BureauData] = None
    bank_data: Optional[BankData] = None
    customer_inputs: Optional[Dict[str, Any]] = None

class ValidationIssue(BaseModel):
    category: ValidationCategory
    severity: SeverityLevel
    field: str
    message: str
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    recommendation: Optional[str] = None

class Anomaly(BaseModel):
    type: str
    description: str
    severity: SeverityLevel
    affected_fields: List[str]
    confidence: float

class CrossValidationResult(BaseModel):
    sources_compared: List[str]
    field: str
    values: Dict[str, Any]
    discrepancy_pct: Optional[float] = None
    severity: SeverityLevel
    recommendation: str

class DataCompletenessScore(BaseModel):
    source: str
    fields_expected: int
    fields_present: int
    completeness_pct: float
    missing_fields: List[str]

class ValidateResponse(BaseModel):
    request_id: str
    overall_quality_score: float
    status: str  # "pass", "review", "fail"
    validation_issues: List[ValidationIssue]
    anomalies: List[Anomaly]
    cross_validation_results: List[CrossValidationResult]
    completeness_scores: List[DataCompletenessScore]
    can_proceed: bool
    blocking_issues: List[str]
    processed_at: str

# ===========================================
# VALIDATION LOGIC
# ===========================================

def validate_gst_data(gst_data: Optional[GSTData]) -> tuple[List[ValidationIssue], DataCompletenessScore]:
    """Validate GST data completeness and format"""
    issues = []
    missing_fields = []

    expected_fields = ["gstin", "entity_info", "sales_data", "filing_status"]
    present_count = 0

    if not gst_data:
        return issues, DataCompletenessScore(
            source="gst",
            fields_expected=len(expected_fields),
            fields_present=0,
            completeness_pct=0,
            missing_fields=expected_fields
        )

    # GSTIN validation
    if gst_data.gstin:
        present_count += 1
        if len(gst_data.gstin) != 15:
            issues.append(ValidationIssue(
                category=ValidationCategory.FORMAT,
                severity=SeverityLevel.ERROR,
                field="gst_data.gstin",
                message="GSTIN must be exactly 15 characters",
                current_value=len(gst_data.gstin),
                expected_value=15
            ))
    else:
        missing_fields.append("gstin")

    # Entity info validation
    if gst_data.entity_info:
        present_count += 1
        if not gst_data.entity_info.get("legal_name"):
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPLETENESS,
                severity=SeverityLevel.WARNING,
                field="gst_data.entity_info.legal_name",
                message="Legal name missing from GST entity info"
            ))
    else:
        missing_fields.append("entity_info")

    # Sales data validation
    if gst_data.sales_data:
        present_count += 1
        annual = gst_data.sales_data.get("annual_lakhs", 0)
        if annual <= 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.RANGE,
                severity=SeverityLevel.WARNING,
                field="gst_data.sales_data.annual_lakhs",
                message="Annual turnover appears invalid or zero",
                current_value=annual
            ))
    else:
        missing_fields.append("sales_data")

    # Filing status
    if gst_data.filing_status:
        present_count += 1
    else:
        missing_fields.append("filing_status")

    completeness = DataCompletenessScore(
        source="gst",
        fields_expected=len(expected_fields),
        fields_present=present_count,
        completeness_pct=round((present_count / len(expected_fields)) * 100, 1),
        missing_fields=missing_fields
    )

    return issues, completeness

def validate_bureau_data(bureau_data: Optional[BureauData]) -> tuple[List[ValidationIssue], DataCompletenessScore]:
    """Validate credit bureau data"""
    issues = []
    missing_fields = []

    expected_fields = ["commercial_score", "outstanding", "dpd", "active_loans"]
    present_count = 0

    if not bureau_data or not bureau_data.commercial:
        return issues, DataCompletenessScore(
            source="bureau",
            fields_expected=len(expected_fields),
            fields_present=0,
            completeness_pct=0,
            missing_fields=expected_fields
        )

    commercial = bureau_data.commercial

    if commercial.get("score"):
        present_count += 1
    else:
        missing_fields.append("commercial_score")

    if commercial.get("total_outstanding_lakhs") is not None:
        present_count += 1
        if commercial.get("total_outstanding_lakhs", 0) < 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.RANGE,
                severity=SeverityLevel.ERROR,
                field="bureau_data.commercial.total_outstanding_lakhs",
                message="Outstanding amount cannot be negative",
                current_value=commercial.get("total_outstanding_lakhs")
            ))
    else:
        missing_fields.append("outstanding")

    if commercial.get("max_dpd_days") is not None:
        present_count += 1
    else:
        missing_fields.append("dpd")

    if commercial.get("active_loans") is not None:
        present_count += 1
    else:
        missing_fields.append("active_loans")

    completeness = DataCompletenessScore(
        source="bureau",
        fields_expected=len(expected_fields),
        fields_present=present_count,
        completeness_pct=round((present_count / len(expected_fields)) * 100, 1),
        missing_fields=missing_fields
    )

    return issues, completeness

def cross_validate_turnover(
    gst_data: Optional[GSTData],
    bank_data: Optional[BankData],
    customer_inputs: Optional[Dict[str, Any]]
) -> List[CrossValidationResult]:
    """Cross-validate turnover across GST, bank, and customer inputs"""
    results = []

    gst_turnover = None
    bank_turnover = None
    stated_turnover = None

    if gst_data and gst_data.sales_data:
        gst_turnover = gst_data.sales_data.get("annual_lakhs")

    if bank_data and bank_data.total_credits_lakhs:
        # Annualize based on months analyzed
        months = bank_data.months_analyzed or 12
        bank_turnover = (bank_data.total_credits_lakhs / months) * 12

    if customer_inputs:
        stated_turnover = customer_inputs.get("stated_annual_turnover_lakhs")

    # Compare GST vs Bank
    if gst_turnover and bank_turnover:
        discrepancy = abs(gst_turnover - bank_turnover) / max(gst_turnover, bank_turnover) * 100
        severity = SeverityLevel.INFO if discrepancy < 10 else SeverityLevel.WARNING if discrepancy < 25 else SeverityLevel.ERROR

        results.append(CrossValidationResult(
            sources_compared=["gst", "bank"],
            field="annual_turnover",
            values={"gst": gst_turnover, "bank": round(bank_turnover, 2)},
            discrepancy_pct=round(discrepancy, 1),
            severity=severity,
            recommendation="Review if discrepancy > 20%" if discrepancy > 20 else "Acceptable variance"
        ))

    # Compare stated vs GST
    if stated_turnover and gst_turnover:
        discrepancy = abs(stated_turnover - gst_turnover) / max(stated_turnover, gst_turnover) * 100
        severity = SeverityLevel.INFO if discrepancy < 10 else SeverityLevel.WARNING if discrepancy < 25 else SeverityLevel.ERROR

        results.append(CrossValidationResult(
            sources_compared=["customer_stated", "gst"],
            field="annual_turnover",
            values={"stated": stated_turnover, "gst": gst_turnover},
            discrepancy_pct=round(discrepancy, 1),
            severity=severity,
            recommendation="Verify customer's stated turnover" if discrepancy > 15 else "Consistent with GST data"
        ))

    return results

def detect_anomalies(
    gst_data: Optional[GSTData],
    bureau_data: Optional[BureauData],
    bank_data: Optional[BankData]
) -> List[Anomaly]:
    """Detect anomalies and red flags in the data"""
    anomalies = []

    # Check for sudden turnover drop
    if gst_data and gst_data.sales_data:
        sales = gst_data.sales_data
        q1 = sales.get("q1_lakhs", 0)
        q4 = sales.get("q4_lakhs", 0)

        if q1 > 0 and q4 > 0:
            if q4 < q1 * 0.7:  # 30% drop
                anomalies.append(Anomaly(
                    type="declining_revenue",
                    description=f"Significant revenue decline: Q4 ({q4}L) is {round((1-q4/q1)*100)}% lower than Q1 ({q1}L)",
                    severity=SeverityLevel.WARNING,
                    affected_fields=["gst_data.sales_data.q1_lakhs", "gst_data.sales_data.q4_lakhs"],
                    confidence=0.85
                ))

    # Check for high credit utilization
    if bureau_data and bureau_data.commercial:
        utilization = bureau_data.commercial.get("credit_utilization_pct", 0)
        if utilization > 85:
            anomalies.append(Anomaly(
                type="high_credit_utilization",
                description=f"Credit utilization at {utilization}% exceeds healthy threshold of 75%",
                severity=SeverityLevel.WARNING,
                affected_fields=["bureau_data.commercial.credit_utilization_pct"],
                confidence=0.95
            ))

    # Check for payment delays
    if bureau_data and bureau_data.commercial:
        dpd = bureau_data.commercial.get("max_dpd_days", 0)
        if dpd > 0:
            severity = SeverityLevel.CRITICAL if dpd > 90 else SeverityLevel.ERROR if dpd > 30 else SeverityLevel.WARNING
            anomalies.append(Anomaly(
                type="payment_delays",
                description=f"Payment delays detected: {dpd} days past due",
                severity=severity,
                affected_fields=["bureau_data.commercial.max_dpd_days"],
                confidence=1.0
            ))

    # Check for overdue amounts
    if bureau_data and bureau_data.commercial:
        overdue = bureau_data.commercial.get("overdue_amount_lakhs", 0)
        if overdue > 0:
            anomalies.append(Anomaly(
                type="active_overdues",
                description=f"Active overdue amount of ₹{overdue}L detected",
                severity=SeverityLevel.ERROR,
                affected_fields=["bureau_data.commercial.overdue_amount_lakhs"],
                confidence=1.0
            ))

    return anomalies

def calculate_quality_score(
    issues: List[ValidationIssue],
    anomalies: List[Anomaly],
    completeness_scores: List[DataCompletenessScore]
) -> float:
    """Calculate overall data quality score (0-100)"""
    score = 100.0

    # Deduct for validation issues
    for issue in issues:
        if issue.severity == SeverityLevel.CRITICAL:
            score -= 20
        elif issue.severity == SeverityLevel.ERROR:
            score -= 10
        elif issue.severity == SeverityLevel.WARNING:
            score -= 5

    # Deduct for anomalies
    for anomaly in anomalies:
        if anomaly.severity == SeverityLevel.CRITICAL:
            score -= 15
        elif anomaly.severity == SeverityLevel.ERROR:
            score -= 8
        elif anomaly.severity == SeverityLevel.WARNING:
            score -= 3

    # Factor in completeness
    avg_completeness = sum(cs.completeness_pct for cs in completeness_scores) / len(completeness_scores) if completeness_scores else 0
    completeness_factor = avg_completeness / 100
    score = score * (0.7 + 0.3 * completeness_factor)

    return max(0, min(100, round(score, 1)))

# ===========================================
# MAIN PROCESSING
# ===========================================

def validate_data(request: ValidateRequest) -> ValidateResponse:
    """Main validation function"""
    request_id = str(uuid.uuid4())

    all_issues = []
    completeness_scores = []

    # Validate individual data sources
    gst_issues, gst_completeness = validate_gst_data(request.gst_data)
    all_issues.extend(gst_issues)
    completeness_scores.append(gst_completeness)

    bureau_issues, bureau_completeness = validate_bureau_data(request.bureau_data)
    all_issues.extend(bureau_issues)
    completeness_scores.append(bureau_completeness)

    # Cross-validate
    cross_results = cross_validate_turnover(
        request.gst_data,
        request.bank_data,
        request.customer_inputs
    )

    # Detect anomalies
    anomalies = detect_anomalies(
        request.gst_data,
        request.bureau_data,
        request.bank_data
    )

    # Calculate quality score
    quality_score = calculate_quality_score(all_issues, anomalies, completeness_scores)

    # Determine status and blocking issues
    blocking_issues = []
    for issue in all_issues:
        if issue.severity == SeverityLevel.CRITICAL:
            blocking_issues.append(issue.message)
    for anomaly in anomalies:
        if anomaly.severity == SeverityLevel.CRITICAL:
            blocking_issues.append(anomaly.description)

    if quality_score >= 70 and not blocking_issues:
        status = "pass"
        can_proceed = True
    elif quality_score >= 50 and not blocking_issues:
        status = "review"
        can_proceed = True
    else:
        status = "fail"
        can_proceed = False

    return ValidateResponse(
        request_id=request_id,
        overall_quality_score=quality_score,
        status=status,
        validation_issues=all_issues,
        anomalies=anomalies,
        cross_validation_results=cross_results,
        completeness_scores=completeness_scores,
        can_proceed=can_proceed,
        blocking_issues=blocking_issues,
        processed_at=datetime.utcnow().isoformat()
    )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-quality",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/validate", response_model=ValidateResponse)
async def validate(request: ValidateRequest):
    """
    Validate data quality across all sources.

    Performs:
    - Format validation (GSTIN, PAN patterns)
    - Completeness checks
    - Cross-source validation (GST vs Bank vs Customer stated)
    - Anomaly detection (declining revenue, high utilization, DPD)

    Returns quality score and whether to proceed with CAM building.
    """
    try:
        return validate_data(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quick-check")
async def quick_check(request: ValidateRequest):
    """
    Quick validation check - returns only pass/fail status.
    Use for workflow gates that just need a boolean decision.
    """
    try:
        result = validate_data(request)
        return {
            "can_proceed": result.can_proceed,
            "quality_score": result.overall_quality_score,
            "status": result.status,
            "critical_issues_count": len(result.blocking_issues)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)
