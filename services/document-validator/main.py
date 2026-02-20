"""
Document Validator Agent - Document Validation, OCR, Authenticity Checks
Port: 8004

Validates and extracts data from uploaded documents:
- Document type classification
- OCR text extraction (mock for MVP)
- Data extraction (PAN, GSTIN, amounts)
- Authenticity indicators
- Cross-validation with provided data
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uvicorn
import uuid
import re
import random

app = FastAPI(
    title="Document Validator Agent",
    description="Document validation, OCR extraction, authenticity checks",
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
# DOCUMENT DEFINITIONS
# ===========================================

class DocumentType(str, Enum):
    PAN_CARD = "pan_card"
    AADHAAR_CARD = "aadhaar_card"
    GST_CERTIFICATE = "gst_certificate"
    BANK_STATEMENT = "bank_statement"
    ITR = "itr"
    UDYAM_CERTIFICATE = "udyam_certificate"
    BUSINESS_REGISTRATION = "business_registration"
    UNKNOWN = "unknown"

class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"
    UNREADABLE = "unreadable"

# Document requirements per type
DOCUMENT_REQUIREMENTS = {
    DocumentType.PAN_CARD: {
        "required_fields": ["pan_number", "name"],
        "optional_fields": ["date_of_birth", "father_name"],
        "file_types": ["pdf", "jpg", "jpeg", "png"],
        "max_size_mb": 5,
    },
    DocumentType.AADHAAR_CARD: {
        "required_fields": ["aadhaar_number", "name"],
        "optional_fields": ["address", "date_of_birth"],
        "file_types": ["pdf", "jpg", "jpeg", "png"],
        "max_size_mb": 5,
    },
    DocumentType.GST_CERTIFICATE: {
        "required_fields": ["gstin", "legal_name", "registration_date"],
        "optional_fields": ["trade_name", "address", "state"],
        "file_types": ["pdf"],
        "max_size_mb": 10,
    },
    DocumentType.BANK_STATEMENT: {
        "required_fields": ["account_number", "bank_name", "period"],
        "optional_fields": ["opening_balance", "closing_balance", "transactions"],
        "file_types": ["pdf"],
        "max_size_mb": 20,
    },
    DocumentType.ITR: {
        "required_fields": ["pan", "assessment_year", "total_income"],
        "optional_fields": ["tax_paid", "refund", "form_type"],
        "file_types": ["pdf"],
        "max_size_mb": 10,
    },
    DocumentType.UDYAM_CERTIFICATE: {
        "required_fields": ["udyam_number", "enterprise_name", "category"],
        "optional_fields": ["nic_code", "date_of_registration"],
        "file_types": ["pdf"],
        "max_size_mb": 5,
    },
}

# ===========================================
# MODELS
# ===========================================

class ValidateDocumentRequest(BaseModel):
    conversation_id: str
    document_type: DocumentType
    file_name: str
    file_content_base64: Optional[str] = None  # For base64 encoded files
    file_url: Optional[str] = None  # For URL-based files
    expected_data: Optional[Dict[str, Any]] = None  # Data to cross-validate

class ExtractedField(BaseModel):
    field_name: str
    value: Any
    confidence: float
    bounding_box: Optional[Dict[str, int]] = None  # For OCR location

class ValidationIssue(BaseModel):
    issue_type: str
    severity: str  # "error", "warning", "info"
    message: str
    field: Optional[str] = None

class AuthenticityIndicator(BaseModel):
    check: str
    passed: bool
    confidence: float
    details: Optional[str] = None

class CrossValidationResult(BaseModel):
    field: str
    document_value: Any
    expected_value: Any
    matches: bool
    similarity_score: Optional[float] = None

class ValidateDocumentResponse(BaseModel):
    request_id: str
    conversation_id: str
    document_type: DocumentType
    detected_type: DocumentType
    validation_status: ValidationStatus
    extracted_data: Dict[str, Any]
    extracted_fields: List[ExtractedField]
    validation_issues: List[ValidationIssue]
    authenticity_indicators: List[AuthenticityIndicator]
    cross_validation_results: List[CrossValidationResult]
    overall_confidence: float
    is_acceptable: bool
    recommendations: List[str]
    processed_at: str

class DocumentRequirementsResponse(BaseModel):
    document_type: DocumentType
    required_fields: List[str]
    optional_fields: List[str]
    accepted_file_types: List[str]
    max_size_mb: int

# ===========================================
# EXTRACTION LOGIC (Mock for MVP)
# ===========================================

def extract_pan_from_text(text: str) -> Optional[str]:
    """Extract PAN number from text using regex"""
    pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
    match = re.search(pan_pattern, text)
    return match.group() if match else None

def extract_gstin_from_text(text: str) -> Optional[str]:
    """Extract GSTIN from text using regex"""
    gstin_pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
    match = re.search(gstin_pattern, text)
    return match.group() if match else None

def extract_aadhaar_from_text(text: str) -> Optional[str]:
    """Extract Aadhaar number from text (masked format)"""
    aadhaar_pattern = r'[X]{4}\s?[X]{4}\s?[0-9]{4}'
    match = re.search(aadhaar_pattern, text)
    return match.group() if match else None

def simulate_ocr_extraction(document_type: DocumentType, file_name: str) -> Dict[str, Any]:
    """
    Simulate OCR extraction for MVP.
    In production, would integrate with:
    - Google Vision API
    - AWS Textract
    - Azure Form Recognizer
    """

    # Generate realistic mock data based on document type
    mock_extractions = {
        DocumentType.PAN_CARD: {
            "pan_number": f"ABCDE{random.randint(1000, 9999)}F",
            "name": "RAJESH KUMAR SHARMA",
            "father_name": "MOHAN LAL SHARMA",
            "date_of_birth": "15/08/1985",
            "raw_text_confidence": 0.92
        },
        DocumentType.AADHAAR_CARD: {
            "aadhaar_number": f"XXXX XXXX {random.randint(1000, 9999)}",
            "name": "Rajesh Kumar Sharma",
            "address": "123 Main Street, New Delhi - 110001",
            "date_of_birth": "15/08/1985",
            "raw_text_confidence": 0.89
        },
        DocumentType.GST_CERTIFICATE: {
            "gstin": f"07ABCDE{random.randint(1000, 9999)}F1Z{random.randint(0, 9)}",
            "legal_name": "ABC ENTERPRISES LLP",
            "trade_name": "ABC Solutions",
            "registration_date": "01/07/2017",
            "state": "Delhi",
            "address": "456 Business Park, Delhi",
            "raw_text_confidence": 0.95
        },
        DocumentType.BANK_STATEMENT: {
            "account_number": f"XXXX{random.randint(1000, 9999)}",
            "bank_name": "HDFC Bank",
            "branch": "Connaught Place, New Delhi",
            "period": "01/01/2025 - 31/12/2025",
            "opening_balance": round(random.uniform(100000, 500000), 2),
            "closing_balance": round(random.uniform(150000, 600000), 2),
            "total_credits": round(random.uniform(5000000, 20000000), 2),
            "total_debits": round(random.uniform(4500000, 19000000), 2),
            "raw_text_confidence": 0.88
        },
        DocumentType.ITR: {
            "pan": f"ABCDE{random.randint(1000, 9999)}F",
            "assessment_year": "2024-25",
            "form_type": "ITR-4",
            "total_income": round(random.uniform(1000000, 5000000), 2),
            "tax_paid": round(random.uniform(100000, 500000), 2),
            "filing_date": "31/07/2024",
            "raw_text_confidence": 0.94
        },
        DocumentType.UDYAM_CERTIFICATE: {
            "udyam_number": f"UDYAM-DL-07-{random.randint(1000000, 9999999)}",
            "enterprise_name": "ABC Enterprises",
            "category": random.choice(["Micro", "Small", "Medium"]),
            "type": random.choice(["Manufacturing", "Service"]),
            "nic_code": f"62{random.randint(10, 99)}",
            "date_of_registration": "01/07/2020",
            "raw_text_confidence": 0.93
        },
    }

    return mock_extractions.get(document_type, {"raw_text_confidence": 0.5})

def run_authenticity_checks(document_type: DocumentType, extracted_data: Dict[str, Any]) -> List[AuthenticityIndicator]:
    """Run authenticity checks on the document"""
    indicators = []

    # Format validation check
    if document_type == DocumentType.PAN_CARD and extracted_data.get("pan_number"):
        pan = extracted_data["pan_number"]
        is_valid_format = bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan))
        indicators.append(AuthenticityIndicator(
            check="pan_format_validation",
            passed=is_valid_format,
            confidence=1.0 if is_valid_format else 0.0,
            details="PAN format matches expected pattern" if is_valid_format else "Invalid PAN format"
        ))

    if document_type == DocumentType.GST_CERTIFICATE and extracted_data.get("gstin"):
        gstin = extracted_data["gstin"]
        is_valid_format = bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin))
        indicators.append(AuthenticityIndicator(
            check="gstin_format_validation",
            passed=is_valid_format,
            confidence=1.0 if is_valid_format else 0.0,
            details="GSTIN format matches expected pattern" if is_valid_format else "Invalid GSTIN format"
        ))

    # Document quality check (simulated)
    quality_score = extracted_data.get("raw_text_confidence", 0.8)
    indicators.append(AuthenticityIndicator(
        check="document_quality",
        passed=quality_score >= 0.7,
        confidence=quality_score,
        details=f"Document readability score: {quality_score:.0%}"
    ))

    # Tampering detection (simulated - would use ML model in production)
    tampering_detected = random.random() < 0.05  # 5% chance of flagging
    indicators.append(AuthenticityIndicator(
        check="tampering_detection",
        passed=not tampering_detected,
        confidence=0.85 if not tampering_detected else 0.3,
        details="No signs of digital manipulation detected" if not tampering_detected else "Possible tampering detected - manual review recommended"
    ))

    return indicators

def cross_validate_data(
    extracted_data: Dict[str, Any],
    expected_data: Optional[Dict[str, Any]],
    document_type: DocumentType
) -> List[CrossValidationResult]:
    """Cross-validate extracted data against expected values"""
    results = []

    if not expected_data:
        return results

    # Define field mappings for cross-validation
    field_mappings = {
        DocumentType.PAN_CARD: [("pan_number", "pan")],
        DocumentType.GST_CERTIFICATE: [("gstin", "gstin"), ("legal_name", "entity_name")],
        DocumentType.BANK_STATEMENT: [("account_number", "account_number")],
        DocumentType.ITR: [("pan", "pan"), ("assessment_year", "assessment_year")],
    }

    mappings = field_mappings.get(document_type, [])

    for doc_field, expected_field in mappings:
        doc_value = extracted_data.get(doc_field)
        exp_value = expected_data.get(expected_field)

        if doc_value and exp_value:
            # Simple string comparison (case-insensitive)
            doc_str = str(doc_value).upper().replace(" ", "")
            exp_str = str(exp_value).upper().replace(" ", "")
            matches = doc_str == exp_str

            # Calculate similarity for partial matches
            similarity = 1.0 if matches else 0.0
            if not matches and len(doc_str) > 0 and len(exp_str) > 0:
                # Simple character overlap similarity
                common = set(doc_str) & set(exp_str)
                similarity = len(common) / max(len(set(doc_str)), len(set(exp_str)))

            results.append(CrossValidationResult(
                field=doc_field,
                document_value=doc_value,
                expected_value=exp_value,
                matches=matches,
                similarity_score=round(similarity, 2)
            ))

    return results

def generate_recommendations(
    validation_issues: List[ValidationIssue],
    authenticity_indicators: List[AuthenticityIndicator],
    cross_validation_results: List[CrossValidationResult]
) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []

    # Check for failed authenticity
    failed_authenticity = [a for a in authenticity_indicators if not a.passed]
    if failed_authenticity:
        for indicator in failed_authenticity:
            if indicator.check == "tampering_detection":
                recommendations.append("Document flagged for potential tampering - manual review required")
            elif indicator.check == "document_quality":
                recommendations.append("Document quality is poor - request a clearer scan or photo")

    # Check for cross-validation mismatches
    mismatches = [cv for cv in cross_validation_results if not cv.matches]
    if mismatches:
        for mismatch in mismatches:
            recommendations.append(
                f"Data mismatch in '{mismatch.field}': document shows '{mismatch.document_value}' "
                f"but expected '{mismatch.expected_value}' - verify correct document uploaded"
            )

    # Check for validation issues
    errors = [vi for vi in validation_issues if vi.severity == "error"]
    if errors:
        for error in errors:
            recommendations.append(f"Fix required: {error.message}")

    if not recommendations:
        recommendations.append("Document validated successfully - no issues found")

    return recommendations

# ===========================================
# MAIN PROCESSING
# ===========================================

def validate_document(request: ValidateDocumentRequest) -> ValidateDocumentResponse:
    """Main document validation function"""
    request_id = str(uuid.uuid4())

    # Simulate OCR extraction
    extracted_data = simulate_ocr_extraction(request.document_type, request.file_name)

    # Build extracted fields list with confidence
    extracted_fields = []
    for field_name, value in extracted_data.items():
        if field_name != "raw_text_confidence":
            extracted_fields.append(ExtractedField(
                field_name=field_name,
                value=value,
                confidence=extracted_data.get("raw_text_confidence", 0.8) * random.uniform(0.9, 1.0)
            ))

    # Check document requirements
    validation_issues = []
    requirements = DOCUMENT_REQUIREMENTS.get(request.document_type, {})

    for required_field in requirements.get("required_fields", []):
        if required_field not in extracted_data or not extracted_data[required_field]:
            validation_issues.append(ValidationIssue(
                issue_type="missing_field",
                severity="error",
                message=f"Required field '{required_field}' not found in document",
                field=required_field
            ))

    # Run authenticity checks
    authenticity_indicators = run_authenticity_checks(request.document_type, extracted_data)

    # Cross-validate with expected data
    cross_validation_results = cross_validate_data(
        extracted_data,
        request.expected_data,
        request.document_type
    )

    # Calculate overall confidence
    field_confidences = [f.confidence for f in extracted_fields]
    authenticity_scores = [a.confidence for a in authenticity_indicators if a.passed]
    all_scores = field_confidences + authenticity_scores

    overall_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.5

    # Determine validation status
    has_errors = any(vi.severity == "error" for vi in validation_issues)
    has_failed_authenticity = any(not a.passed for a in authenticity_indicators)
    has_cross_validation_failures = any(not cv.matches for cv in cross_validation_results)

    if has_errors or (has_failed_authenticity and overall_confidence < 0.5):
        validation_status = ValidationStatus.INVALID
        is_acceptable = False
    elif has_failed_authenticity or has_cross_validation_failures:
        validation_status = ValidationStatus.NEEDS_REVIEW
        is_acceptable = overall_confidence >= 0.6
    elif overall_confidence < 0.7:
        validation_status = ValidationStatus.UNREADABLE
        is_acceptable = False
    else:
        validation_status = ValidationStatus.VALID
        is_acceptable = True

    # Generate recommendations
    recommendations = generate_recommendations(
        validation_issues,
        authenticity_indicators,
        cross_validation_results
    )

    return ValidateDocumentResponse(
        request_id=request_id,
        conversation_id=request.conversation_id,
        document_type=request.document_type,
        detected_type=request.document_type,  # Would use classifier in production
        validation_status=validation_status,
        extracted_data=extracted_data,
        extracted_fields=extracted_fields,
        validation_issues=validation_issues,
        authenticity_indicators=authenticity_indicators,
        cross_validation_results=cross_validation_results,
        overall_confidence=round(overall_confidence, 2),
        is_acceptable=is_acceptable,
        recommendations=recommendations,
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
        "service": "document-validator",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/validate", response_model=ValidateDocumentResponse)
async def validate(request: ValidateDocumentRequest):
    """
    Validate a document and extract data.

    Performs:
    - OCR text extraction
    - Required field validation
    - Authenticity checks (format, quality, tampering)
    - Cross-validation with expected data

    Returns validation status and extracted data.
    """
    try:
        return validate_document(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/requirements/{document_type}", response_model=DocumentRequirementsResponse)
async def get_requirements(document_type: DocumentType):
    """
    Get requirements for a specific document type.
    Useful for displaying upload instructions to users.
    """
    requirements = DOCUMENT_REQUIREMENTS.get(document_type)

    if not requirements:
        raise HTTPException(status_code=404, detail=f"Unknown document type: {document_type}")

    return DocumentRequirementsResponse(
        document_type=document_type,
        required_fields=requirements.get("required_fields", []),
        optional_fields=requirements.get("optional_fields", []),
        accepted_file_types=requirements.get("file_types", []),
        max_size_mb=requirements.get("max_size_mb", 10)
    )

@app.get("/supported-types")
async def get_supported_types():
    """Get list of supported document types with their requirements."""
    return {
        "document_types": [
            {
                "type": doc_type.value,
                "display_name": doc_type.value.replace("_", " ").title(),
                "required_fields": req.get("required_fields", []),
                "accepted_formats": req.get("file_types", []),
                "max_size_mb": req.get("max_size_mb", 10)
            }
            for doc_type, req in DOCUMENT_REQUIREMENTS.items()
        ]
    }

@app.post("/extract-only")
async def extract_only(
    document_type: DocumentType,
    file_name: str
):
    """
    Extract data from document without validation.
    Use when you just need the extracted data.
    """
    try:
        extracted_data = simulate_ocr_extraction(document_type, file_name)
        return {
            "document_type": document_type.value,
            "extracted_data": extracted_data,
            "confidence": extracted_data.get("raw_text_confidence", 0.8)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-validate")
async def batch_validate(documents: List[ValidateDocumentRequest]):
    """
    Validate multiple documents in a single request.
    Returns validation results for each document.
    """
    try:
        results = []
        for doc in documents:
            result = validate_document(doc)
            results.append(result)

        all_acceptable = all(r.is_acceptable for r in results)

        return {
            "total_documents": len(documents),
            "all_acceptable": all_acceptable,
            "valid_count": sum(1 for r in results if r.validation_status == ValidationStatus.VALID),
            "invalid_count": sum(1 for r in results if r.validation_status == ValidationStatus.INVALID),
            "needs_review_count": sum(1 for r in results if r.validation_status == ValidationStatus.NEEDS_REVIEW),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
