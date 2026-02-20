"""
Compliance Agent - DPDP Act, RBI Guidelines, Fraud Detection
Port: 8005

Ensures regulatory compliance and detects fraud:
- DPDP Act 2023 consent verification
- RBI DSA guidelines compliance
- Fraud pattern detection
- AML/KYC basic checks
- Consent audit trail
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
import uuid
import re

app = FastAPI(
    title="Compliance Agent",
    description="DPDP Act compliance, RBI guidelines, fraud detection, consent verification",
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
# COMPLIANCE RULES DEFINITIONS
# ===========================================

# DPDP Act 2023 Requirements
DPDP_REQUIRED_CONSENTS = [
    "credit_bureau_pull",
    "data_processing",
    "data_sharing_with_lenders",
]

DPDP_OPTIONAL_CONSENTS = [
    "marketing_communications",
    "third_party_offers",
]

# RBI DSA Guidelines
RBI_DSA_REQUIREMENTS = {
    "max_interest_rate_pct": 36.0,  # Annual
    "min_loan_tenure_days": 7,
    "mandatory_disclosures": [
        "total_cost_of_credit",
        "annual_percentage_rate",
        "processing_fees",
        "prepayment_charges",
    ],
    "cooling_off_period_days": 3,
}

# High-risk industries for fraud detection
HIGH_RISK_INDUSTRIES = [
    "cryptocurrency",
    "gambling",
    "adult_entertainment",
    "weapons",
    "tobacco",
]

# Fraud patterns
FRAUD_INDICATORS = {
    "rapid_applications": {"threshold": 3, "period_days": 7},
    "mismatched_data": {"severity": "high"},
    "blacklisted_entity": {"severity": "critical"},
    "suspicious_turnover_pattern": {"variance_threshold": 0.5},
}

# ===========================================
# MODELS
# ===========================================

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"

class CheckSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ConsentType(str, Enum):
    CREDIT_BUREAU_PULL = "credit_bureau_pull"
    DATA_PROCESSING = "data_processing"
    DATA_SHARING_WITH_LENDERS = "data_sharing_with_lenders"
    MARKETING_COMMUNICATIONS = "marketing_communications"
    THIRD_PARTY_OFFERS = "third_party_offers"

class ConsentRecord(BaseModel):
    consent_type: ConsentType
    granted: bool
    granted_at: Optional[str] = None
    ip_address: Optional[str] = None
    method: str = "text"  # text, button, checkbox, otp

class ApplicantData(BaseModel):
    gstin: Optional[str] = None
    pan: Optional[str] = None
    entity_name: Optional[str] = None
    promoter_pans: List[str] = []
    industry_sector: Optional[str] = None
    annual_turnover_lakhs: Optional[float] = None
    years_in_business: Optional[int] = None

class LoanTerms(BaseModel):
    amount_lakhs: float
    interest_rate_pct: float
    tenure_months: int
    processing_fee_pct: Optional[float] = None

class ComplianceCheckRequest(BaseModel):
    conversation_id: str
    check_type: str = "full"  # "pre_assessment", "pre_submission", "full"
    applicant_data: ApplicantData
    consents: List[ConsentRecord] = []
    loan_terms: Optional[LoanTerms] = None
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None

class ComplianceCheck(BaseModel):
    check_id: str
    category: str
    rule: str
    status: str  # "passed", "failed", "warning"
    severity: CheckSeverity
    message: str
    details: Optional[Dict[str, Any]] = None

class FraudFlag(BaseModel):
    flag_id: str
    type: str
    severity: CheckSeverity
    description: str
    confidence: float
    affected_fields: List[str]
    recommended_action: str

class ConsentStatus(BaseModel):
    all_required_granted: bool
    missing_required: List[str]
    granted_consents: List[str]
    consent_expiry_warning: bool = False

class ComplianceCheckResponse(BaseModel):
    request_id: str
    conversation_id: str
    overall_status: ComplianceStatus
    checks_passed: List[ComplianceCheck]
    checks_failed: List[ComplianceCheck]
    fraud_flags: List[FraudFlag]
    consent_status: ConsentStatus
    can_proceed: bool
    blocking_reasons: List[str]
    recommendations: List[str]
    checked_at: str

# ===========================================
# COMPLIANCE LOGIC
# ===========================================

def check_dpdp_compliance(consents: List[ConsentRecord]) -> tuple[List[ComplianceCheck], ConsentStatus]:
    """Check DPDP Act 2023 compliance"""
    checks = []
    granted_consents = []
    missing_required = []

    # Build consent map
    consent_map = {c.consent_type.value: c for c in consents}

    # Check required consents
    for required in DPDP_REQUIRED_CONSENTS:
        consent = consent_map.get(required)
        check_id = str(uuid.uuid4())[:8]

        if consent and consent.granted:
            granted_consents.append(required)
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="dpdp",
                rule=f"consent_{required}",
                status="passed",
                severity=CheckSeverity.INFO,
                message=f"Required consent '{required}' obtained",
                details={"granted_at": consent.granted_at, "method": consent.method}
            ))
        else:
            missing_required.append(required)
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="dpdp",
                rule=f"consent_{required}",
                status="failed",
                severity=CheckSeverity.CRITICAL,
                message=f"Required consent '{required}' not obtained",
                details={"required_by": "DPDP Act 2023"}
            ))

    # Check optional consents (just record status)
    for optional in DPDP_OPTIONAL_CONSENTS:
        consent = consent_map.get(optional)
        if consent and consent.granted:
            granted_consents.append(optional)

    # Check consent validity (should be recent)
    consent_expiry_warning = False
    for consent in consents:
        if consent.granted and consent.granted_at:
            try:
                granted_time = datetime.fromisoformat(consent.granted_at.replace('Z', '+00:00'))
                if datetime.utcnow() - granted_time.replace(tzinfo=None) > timedelta(days=30):
                    consent_expiry_warning = True
            except:
                pass

    consent_status = ConsentStatus(
        all_required_granted=len(missing_required) == 0,
        missing_required=missing_required,
        granted_consents=granted_consents,
        consent_expiry_warning=consent_expiry_warning
    )

    return checks, consent_status

def check_rbi_dsa_compliance(loan_terms: Optional[LoanTerms]) -> List[ComplianceCheck]:
    """Check RBI DSA guidelines compliance"""
    checks = []

    if not loan_terms:
        return checks

    # Interest rate check
    check_id = str(uuid.uuid4())[:8]
    if loan_terms.interest_rate_pct > RBI_DSA_REQUIREMENTS["max_interest_rate_pct"]:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="rbi_dsa",
            rule="max_interest_rate",
            status="failed",
            severity=CheckSeverity.CRITICAL,
            message=f"Interest rate {loan_terms.interest_rate_pct}% exceeds RBI maximum of {RBI_DSA_REQUIREMENTS['max_interest_rate_pct']}%",
            details={"current": loan_terms.interest_rate_pct, "max_allowed": RBI_DSA_REQUIREMENTS["max_interest_rate_pct"]}
        ))
    else:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="rbi_dsa",
            rule="max_interest_rate",
            status="passed",
            severity=CheckSeverity.INFO,
            message="Interest rate within RBI guidelines"
        ))

    # Minimum tenure check
    check_id = str(uuid.uuid4())[:8]
    tenure_days = loan_terms.tenure_months * 30
    if tenure_days < RBI_DSA_REQUIREMENTS["min_loan_tenure_days"]:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="rbi_dsa",
            rule="min_tenure",
            status="failed",
            severity=CheckSeverity.ERROR,
            message=f"Loan tenure {tenure_days} days below RBI minimum of {RBI_DSA_REQUIREMENTS['min_loan_tenure_days']} days",
            details={"current_days": tenure_days, "min_required": RBI_DSA_REQUIREMENTS["min_loan_tenure_days"]}
        ))
    else:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="rbi_dsa",
            rule="min_tenure",
            status="passed",
            severity=CheckSeverity.INFO,
            message="Loan tenure meets RBI minimum"
        ))

    return checks

def check_kyc_compliance(applicant: ApplicantData) -> List[ComplianceCheck]:
    """Check KYC requirements"""
    checks = []

    # GSTIN validation
    check_id = str(uuid.uuid4())[:8]
    if applicant.gstin:
        gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if re.match(gstin_pattern, applicant.gstin):
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="kyc",
                rule="gstin_format",
                status="passed",
                severity=CheckSeverity.INFO,
                message="GSTIN format valid"
            ))
        else:
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="kyc",
                rule="gstin_format",
                status="failed",
                severity=CheckSeverity.ERROR,
                message="Invalid GSTIN format",
                details={"provided": applicant.gstin}
            ))
    else:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="kyc",
            rule="gstin_format",
            status="warning",
            severity=CheckSeverity.WARNING,
            message="GSTIN not provided"
        ))

    # PAN validation
    check_id = str(uuid.uuid4())[:8]
    if applicant.pan:
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if re.match(pan_pattern, applicant.pan):
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="kyc",
                rule="pan_format",
                status="passed",
                severity=CheckSeverity.INFO,
                message="PAN format valid"
            ))
        else:
            checks.append(ComplianceCheck(
                check_id=check_id,
                category="kyc",
                rule="pan_format",
                status="failed",
                severity=CheckSeverity.ERROR,
                message="Invalid PAN format",
                details={"provided": applicant.pan}
            ))
    else:
        checks.append(ComplianceCheck(
            check_id=check_id,
            category="kyc",
            rule="pan_format",
            status="failed",
            severity=CheckSeverity.CRITICAL,
            message="PAN is required for KYC compliance"
        ))

    return checks

def detect_fraud_patterns(applicant: ApplicantData, ip_address: Optional[str]) -> List[FraudFlag]:
    """Detect potential fraud patterns"""
    flags = []

    # Check high-risk industry
    if applicant.industry_sector:
        industry_lower = applicant.industry_sector.lower()
        for high_risk in HIGH_RISK_INDUSTRIES:
            if high_risk in industry_lower:
                flags.append(FraudFlag(
                    flag_id=str(uuid.uuid4())[:8],
                    type="high_risk_industry",
                    severity=CheckSeverity.WARNING,
                    description=f"Industry '{applicant.industry_sector}' is classified as high-risk",
                    confidence=0.9,
                    affected_fields=["industry_sector"],
                    recommended_action="Enhanced due diligence required"
                ))
                break

    # Check for new business applying for large loan
    if applicant.years_in_business is not None and applicant.annual_turnover_lakhs is not None:
        if applicant.years_in_business < 1 and applicant.annual_turnover_lakhs > 100:
            flags.append(FraudFlag(
                flag_id=str(uuid.uuid4())[:8],
                type="suspicious_profile",
                severity=CheckSeverity.WARNING,
                description=f"New business (<1 year) with unusually high turnover (₹{applicant.annual_turnover_lakhs}L)",
                confidence=0.7,
                affected_fields=["years_in_business", "annual_turnover_lakhs"],
                recommended_action="Verify turnover with bank statements and GST returns"
            ))

    # Check for missing critical identifiers
    if not applicant.gstin and not applicant.pan:
        flags.append(FraudFlag(
            flag_id=str(uuid.uuid4())[:8],
            type="missing_identifiers",
            severity=CheckSeverity.CRITICAL,
            description="Both GSTIN and PAN are missing - cannot verify identity",
            confidence=1.0,
            affected_fields=["gstin", "pan"],
            recommended_action="Block application until identity documents provided"
        ))

    # Placeholder for IP-based checks (would use external service in production)
    if ip_address:
        # In production, would check:
        # - IP geolocation vs stated business address
        # - Known VPN/proxy detection
        # - IP reputation score
        pass

    return flags

def generate_recommendations(
    checks_failed: List[ComplianceCheck],
    fraud_flags: List[FraudFlag],
    consent_status: ConsentStatus
) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []

    # Consent recommendations
    if not consent_status.all_required_granted:
        recommendations.append(
            f"Obtain missing consents before proceeding: {', '.join(consent_status.missing_required)}"
        )

    if consent_status.consent_expiry_warning:
        recommendations.append(
            "Some consents are older than 30 days - consider requesting fresh consent"
        )

    # KYC recommendations
    kyc_failures = [c for c in checks_failed if c.category == "kyc"]
    if kyc_failures:
        recommendations.append(
            "Complete KYC verification: ensure valid GSTIN and PAN are provided"
        )

    # Fraud recommendations
    critical_flags = [f for f in fraud_flags if f.severity == CheckSeverity.CRITICAL]
    if critical_flags:
        recommendations.append(
            "CRITICAL: Manual review required before proceeding with this application"
        )

    warning_flags = [f for f in fraud_flags if f.severity == CheckSeverity.WARNING]
    if warning_flags:
        recommendations.append(
            "Enhanced due diligence recommended due to risk indicators"
        )

    return recommendations

# ===========================================
# MAIN PROCESSING
# ===========================================

def run_compliance_check(request: ComplianceCheckRequest) -> ComplianceCheckResponse:
    """Run full compliance check"""
    request_id = str(uuid.uuid4())

    all_checks = []
    checks_passed = []
    checks_failed = []

    # DPDP Compliance
    dpdp_checks, consent_status = check_dpdp_compliance(request.consents)
    all_checks.extend(dpdp_checks)

    # RBI DSA Compliance
    if request.loan_terms:
        rbi_checks = check_rbi_dsa_compliance(request.loan_terms)
        all_checks.extend(rbi_checks)

    # KYC Compliance
    kyc_checks = check_kyc_compliance(request.applicant_data)
    all_checks.extend(kyc_checks)

    # Separate passed and failed
    for check in all_checks:
        if check.status == "passed":
            checks_passed.append(check)
        else:
            checks_failed.append(check)

    # Fraud Detection
    fraud_flags = detect_fraud_patterns(request.applicant_data, request.ip_address)

    # Determine overall status
    critical_failures = [c for c in checks_failed if c.severity == CheckSeverity.CRITICAL]
    critical_fraud = [f for f in fraud_flags if f.severity == CheckSeverity.CRITICAL]

    blocking_reasons = []

    if critical_failures:
        for failure in critical_failures:
            blocking_reasons.append(failure.message)

    if critical_fraud:
        for flag in critical_fraud:
            blocking_reasons.append(flag.description)

    if blocking_reasons:
        overall_status = ComplianceStatus.BLOCKED
        can_proceed = False
    elif checks_failed or fraud_flags:
        # Check if only warnings
        error_level_issues = [c for c in checks_failed if c.severity in [CheckSeverity.ERROR, CheckSeverity.CRITICAL]]
        if error_level_issues:
            overall_status = ComplianceStatus.NON_COMPLIANT
            can_proceed = False
        else:
            overall_status = ComplianceStatus.NEEDS_REVIEW
            can_proceed = True
    else:
        overall_status = ComplianceStatus.COMPLIANT
        can_proceed = True

    # Generate recommendations
    recommendations = generate_recommendations(checks_failed, fraud_flags, consent_status)

    return ComplianceCheckResponse(
        request_id=request_id,
        conversation_id=request.conversation_id,
        overall_status=overall_status,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        fraud_flags=fraud_flags,
        consent_status=consent_status,
        can_proceed=can_proceed,
        blocking_reasons=blocking_reasons,
        recommendations=recommendations,
        checked_at=datetime.utcnow().isoformat()
    )

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/check", response_model=ComplianceCheckResponse)
async def check_compliance(request: ComplianceCheckRequest):
    """
    Run comprehensive compliance check.

    Checks:
    - DPDP Act 2023 consent requirements
    - RBI DSA guidelines (interest rates, tenure)
    - KYC validation (GSTIN, PAN format)
    - Fraud pattern detection

    Returns compliance status and whether application can proceed.
    """
    try:
        return run_compliance_check(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-consents")
async def verify_consents(consents: List[ConsentRecord]):
    """
    Quick consent verification - checks if all required consents are present.
    Use as a workflow gate before credit bureau pulls.
    """
    try:
        checks, consent_status = check_dpdp_compliance(consents)
        return {
            "all_required_granted": consent_status.all_required_granted,
            "missing_required": consent_status.missing_required,
            "granted_consents": consent_status.granted_consents,
            "can_proceed": consent_status.all_required_granted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect-fraud")
async def detect_fraud(
    applicant_data: ApplicantData,
    ip_address: Optional[str] = None
):
    """
    Run fraud detection only.
    Returns fraud flags and risk assessment.
    """
    try:
        flags = detect_fraud_patterns(applicant_data, ip_address)

        risk_level = "low"
        if any(f.severity == CheckSeverity.CRITICAL for f in flags):
            risk_level = "critical"
        elif any(f.severity == CheckSeverity.ERROR for f in flags):
            risk_level = "high"
        elif any(f.severity == CheckSeverity.WARNING for f in flags):
            risk_level = "medium"

        return {
            "fraud_flags": [f.dict() for f in flags],
            "flag_count": len(flags),
            "risk_level": risk_level,
            "requires_manual_review": risk_level in ["critical", "high"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rules")
async def get_compliance_rules():
    """
    Get current compliance rules configuration.
    Useful for documentation and UI display.
    """
    return {
        "dpdp": {
            "required_consents": DPDP_REQUIRED_CONSENTS,
            "optional_consents": DPDP_OPTIONAL_CONSENTS,
        },
        "rbi_dsa": RBI_DSA_REQUIREMENTS,
        "high_risk_industries": HIGH_RISK_INDUSTRIES,
        "fraud_indicators": list(FRAUD_INDICATORS.keys())
    }

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
