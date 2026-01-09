# Loan Origination System - Production Architecture

## Document Version
- **Version**: 1.0
- **Last Updated**: January 2025
- **Status**: Draft for Review

---

## 1. System Overview

### 1.1 Architecture Philosophy
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER (n8n)                       │
│  Event-driven, parallel processing, state management                    │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  francis-mcp    │  │ data-services   │  │   nikita-mcp    │  │   kesha-mcp     │
│  (Customer UX)  │  │ (External APIs) │  │ (Doc Assembly)  │  │ (Credit Intel)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE LAYER                               │
│  PostgreSQL + Supabase (conversations, CAM, assessments, submissions)   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Principles
1. **Parallel by default** - GST triggers multiple lookups simultaneously
2. **Stateless agents** - All context passed explicitly, no hidden state
3. **PII isolation** - Kesha never sees raw identifiers
4. **Audit everything** - Consent, decisions, communications logged
5. **Deterministic where possible** - AI only for decisions requiring judgment

---

## 2. Agent Responsibilities

### 2.1 Francis (Customer Interface)
**Server**: `francis-mcp.onrender.com`

**Responsibilities**:
- Extract customer intent from natural language
- Capture and validate GST/PAN numbers
- Obtain and record all consents (credit bureau, data sharing, communication)
- Ask qualifying questions while Nikita processes
- Deliver reports and recommendations from Kesha
- Collect missing documents
- Handle invalid input errors gracefully

**Input Context**:
```json
{
  "conversation_id": "uuid",
  "customer_id": "uuid", 
  "channel": "whatsapp|web|app",
  "message": "string",
  "conversation_summary": "Last 3 messages + current phase",
  "pending_questions": ["collateral", "tenure_preference"],
  "pending_consents": ["credit_bureau", "lender_sharing"],
  "available_actions": ["ask_question", "request_consent", "deliver_report"]
}
```

**Output**:
```json
{
  "response_to_customer": "string",
  "extracted_data": {
    "gst_number": "string|null",
    "pan_number": "string|null",
    "loan_amount": "number|null",
    "loan_purpose": "string|null"
  },
  "consents_obtained": [{
    "type": "credit_bureau|lender_sharing|communication",
    "granted": true,
    "method": "otp|explicit_yes",
    "timestamp": "ISO8601"
  }],
  "questions_answered": {
    "collateral_available": "yes|no|value",
    "tenure_preference": "number",
    "priority": "low_emi|short_tenure|low_interest"
  },
  "action_requested": "trigger_cam_build|request_document|none"
}
```

**Regulatory Guardrails** (embedded in system prompt):
- DPDP Act compliance: Explain data usage before collecting
- RBI DSA guidelines: No misleading claims about approval certainty
- Fair lending disclosure: Present all options, not just high-commission
- Communication consent: Explicit opt-in for each channel

---

### 2.2 Data Services (External API Gateway)
**Server**: `data-services-mcp.onrender.com`

**Responsibilities**:
- GST verification via government/FameScore API
- PAN verification
- Credit bureau pulls (CIBIL, Experian - commercial + consumer)
- Bank statement parsing (when provided)
- Udyam registration lookup
- ITR data retrieval (with consent)

**Key Characteristic**: Stateless, cacheable, rate-limited

**Endpoints**:
```
POST /verify-gst
POST /verify-pan  
POST /pull-credit-bureau
POST /parse-bank-statement
POST /lookup-udyam
POST /fetch-itr
```

**Error Handling**:
- Invalid GST → Return error code, Francis asks for correction
- API timeout → Retry 3x with exponential backoff, then mark as "pending_verification"
- Bureau unavailable → Queue for retry, proceed with available data

---

### 2.3 Nikita (Document & Data Assembly)
**Server**: `nikita-mcp.onrender.com`

**Responsibilities**:
- Orchestrate parallel data collection from data-services
- Assemble comprehensive CAM (internal JSON format)
- Validate all required fields are populated
- Prepare bank-specific document packages (CAM/PD/FI Excel formats)
- Track document requirements per lender
- Flag data inconsistencies or missing information

**Input** (from n8n after data-services completes):
```json
{
  "conversation_id": "uuid",
  "gst_data": { /* FameScore-like structure */ },
  "pan_data": { /* verification result */ },
  "credit_bureau": { /* commercial + consumer */ },
  "bank_statements": { /* parsed if available */ },
  "udyam_data": { /* registration details */ },
  "itr_data": { /* if available */ },
  "customer_inputs": {
    "loan_amount_requested": 5000000,
    "loan_purpose": "working_capital",
    "collateral_available": true,
    "collateral_type": "property",
    "collateral_value": 8000000,
    "tenure_preference_months": 36
  }
}
```

**Output**:
```json
{
  "cam_id": "uuid",
  "cam_status": "complete|incomplete",
  "cam_data": { /* Full CAM structure - see Section 3 */ },
  "missing_fields": ["bank_statement_6_months"],
  "data_flags": [
    {"field": "gst_turnover_vs_itr", "issue": "15% variance", "severity": "warning"}
  ],
  "kesha_ready": true,
  "documents_for_francis": ["Request 6-month bank statement"]
}
```

**Regulatory Guardrails**:
- Data accuracy: Cross-validate GST turnover vs ITR vs bank credits
- Audit trail: Log all API calls with timestamps
- No PII in logs: Mask sensitive fields in debugging output

---

### 2.4 Kesha (Credit Intelligence)
**Server**: `kesha-mcp.onrender.com`

**Responsibilities**:
- Receive anonymized CAM (no raw GST/PAN, only derived metrics)
- Calculate eligibility scores per lender
- Match to lender criteria (min turnover, max DPD, sector restrictions)
- Rank lenders by customer preference AND expected value
- Generate customer-facing report with actionable advice
- Identify improvement opportunities (reduce existing debt, improve filing compliance)

**Input** (anonymized CAM slice):
```json
{
  "cam_id": "uuid",
  "business_profile": {
    "constitution": "private_limited",
    "vintage_years": 4,
    "industry_sector": "IT_services",
    "employee_count": 50,
    "state_registrations": ["UP", "KA", "TG"]
  },
  "financial_metrics": {
    "annual_turnover_lakhs": 2411,
    "turnover_growth_yoy": 0.17,
    "profit_margin": 0.30,
    "current_ratio": 7.0,
    "total_outside_liabilities_lakhs": 393
  },
  "credit_profile": {
    "commercial_score": "CMR-2",
    "promoter_scores": [800, 750],
    "total_outstanding_lakhs": 27.10,
    "overdue_amount_lakhs": 1.38,
    "active_loans_count": 19,
    "max_dpd_days": 40,
    "utilization_pct": 0.96
  },
  "compliance": {
    "gst_filing_consistency": 0.84,
    "itr_filed_on_time": true,
    "gst_return_pct": 0.0
  },
  "loan_request": {
    "amount_lakhs": 50,
    "purpose": "working_capital",
    "tenure_months": 36,
    "collateral_available": true,
    "collateral_value_lakhs": 80
  },
  "customer_preferences": {
    "priority": "low_interest",
    "urgency": "2_weeks",
    "lender_preference": "any"
  }
}
```

**Output**:
```json
{
  "assessment_id": "uuid",
  "overall_eligibility": "high|medium|low|ineligible",
  "max_eligible_amount_lakhs": 48.2,
  "lender_matches": [
    {
      "lender_id": "bajaj_finserv",
      "lender_name": "Bajaj Finserv",
      "product": "Business Loan",
      "eligible_amount_lakhs": 45,
      "interest_rate_range": "14-18%",
      "tenure_months": 36,
      "approval_probability": 0.85,
      "commission_pct": 2.5,
      "expected_value": 1.125,
      "meets_customer_preference": true,
      "preference_score": 0.9,
      "rejection_risks": ["High active loan count"],
      "requirements": ["6-month bank statement", "Latest ITR"]
    },
    // ... more lenders
  ],
  "recommendation": {
    "primary": "bajaj_finserv",
    "reason": "Best match for low interest priority with 85% approval probability",
    "alternatives": ["hdfc_bank", "icici_bank"]
  },
  "customer_report": {
    "summary": "Based on your business profile, you're eligible for up to ₹48L...",
    "strengths": ["Strong credit score", "Consistent GST filing", "Good turnover growth"],
    "improvements": ["Reduce existing loan utilization", "Clear ₹1.38L overdue"],
    "next_steps": ["Provide 6-month bank statement", "Choose preferred lender"]
  },
  "internal_notes": "High DPD on Union Bank facility may cause issues with PSU lenders"
}
```

**Regulatory Guardrails**:
- Fair lending: Cannot discriminate based on protected characteristics
- Disclosure: Must explain rejection reasons
- Commission transparency: Internal metric only, never shown to customer
- No guarantees: Language must indicate "eligibility" not "approval"

---

## 3. CAM (Credit Assessment Memorandum) Schema

### 3.1 Internal CAM Structure (JSON)

```json
{
  "cam_id": "uuid",
  "version": "1.0",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "status": "draft|complete|verified|submitted",
  
  "entity_identity": {
    "legal_name": "string",
    "trade_name": "string",
    "constitution": "proprietorship|partnership|llp|private_limited|public_limited",
    "date_of_incorporation": "date",
    "gst_numbers": [{
      "gstin": "string",
      "state": "string",
      "status": "active|cancelled|suspended"
    }],
    "pan": "string",
    "udyam_number": "string",
    "cin": "string|null",
    "registered_address": {
      "line1": "string",
      "line2": "string",
      "city": "string",
      "state": "string",
      "pincode": "string"
    },
    "business_address": { /* same structure */ }
  },
  
  "promoters": [{
    "name": "string",
    "designation": "string",
    "shareholding_pct": "number",
    "pan": "string",
    "aadhar_masked": "xxxx1234",
    "credit_score": "number",
    "credit_bureau": "CIBIL|Experian",
    "outstanding_amount_lakhs": "number",
    "overdue_amount_lakhs": "number",
    "active_loans": "number"
  }],
  
  "business_profile": {
    "industry_sector": "string",
    "nic_code": "string",
    "hsn_sac_codes": ["string"],
    "business_description": "string",
    "years_in_business": "number",
    "employee_count": "number",
    "enterprise_type": "micro|small|medium"
  },
  
  "banking_details": [{
    "bank_name": "string",
    "account_number_masked": "xxxx1234",
    "ifsc": "string",
    "account_type": "current|savings|od|cc",
    "branch_address": "string",
    "is_primary": "boolean"
  }],
  
  "financial_summary": {
    "source": "gst|itr|bank_statement|audited_financials",
    "period": "TTM|FY2023-24|FY2022-23",
    
    "turnover": {
      "annual_lakhs": "number",
      "monthly_average_lakhs": "number",
      "growth_yoy_pct": "number",
      "quarterly_breakdown": [{
        "quarter": "Q1",
        "year": "2024-25",
        "amount_lakhs": "number"
      }]
    },
    
    "profitability": {
      "net_profit_lakhs": "number",
      "net_profit_margin_pct": "number",
      "current_ratio": "number",
      "total_outside_liabilities_lakhs": "number",
      "net_worth_lakhs": "number"
    },
    
    "banking_behavior": {
      "total_credits_lakhs": "number",
      "bank_to_turnover_ratio": "number",
      "inward_bounce_count": "number",
      "outward_bounce_count": "number",
      "average_monthly_balance_lakhs": "number"
    },
    
    "sales_analysis": {
      "b2b_share_pct": "number",
      "export_share_pct": "number",
      "top_5_customer_concentration_pct": "number",
      "top_5_geographic_concentration_pct": "number",
      "total_customers_b2b": "number"
    },
    
    "purchase_analysis": {
      "total_purchases_lakhs": "number",
      "top_5_supplier_concentration_pct": "number",
      "total_suppliers": "number"
    }
  },
  
  "credit_profile": {
    "commercial_bureau": {
      "bureau": "Experian|CIBIL",
      "score": "string",
      "score_numeric": "number|null",
      "member_since": "date",
      "total_outstanding_lakhs": "number",
      "overdue_amount_lakhs": "number",
      "active_loans": "number",
      "write_offs": "number"
    },
    
    "existing_facilities": [{
      "facility_type": "term_loan|od|cc|ubl|wcdl",
      "lender": "string",
      "sanctioned_amount_lakhs": "number",
      "outstanding_lakhs": "number",
      "emi_lakhs": "number|null",
      "tenure_months": "number",
      "start_date": "date",
      "dpd_days": "number",
      "sma_status": "SMA0|SMA1|SMA2|NA",
      "status": "active|closed"
    }],
    
    "derived_metrics": {
      "total_serviceable_debt_lakhs": "number",
      "debt_to_turnover_ratio": "number",
      "monthly_obligations_lakhs": "number",
      "foir": "number"
    }
  },
  
  "compliance_status": {
    "gst": {
      "gstr1_filing_consistency": "number",
      "gstr3b_filing_consistency": "number",
      "delayed_filings_count": "number",
      "return_percentage": "number"
    },
    "itr": {
      "last_filed_year": "string",
      "filed_on_time": "boolean",
      "itr_type": "ITR-3|ITR-4|ITR-6"
    }
  },
  
  "eligibility_calculations": {
    "total_12_month_sales_lakhs": "number",
    "wc_requirement_pct": "number",
    "current_wc_limits_lakhs": "number",
    "additional_wc_eligible_lakhs": "number",
    "serviceable_debt_capacity_lakhs": "number",
    "term_loan_eligible_3yr_lakhs": "number"
  },
  
  "loan_request": {
    "amount_lakhs": "number",
    "purpose": "working_capital|equipment|expansion|debt_consolidation|other",
    "purpose_description": "string",
    "tenure_months": "number",
    "collateral": {
      "available": "boolean",
      "type": "property|fd|machinery|inventory|none",
      "estimated_value_lakhs": "number",
      "details": "string"
    },
    "urgency": "immediate|1_week|2_weeks|1_month|flexible"
  },
  
  "customer_preferences": {
    "priority": "low_emi|short_tenure|low_interest|quick_disbursement",
    "lender_preference": "psu_bank|private_bank|nbfc|fintech|any",
    "existing_relationships": ["string"]
  },
  
  "verification_flags": [{
    "check": "string",
    "status": "pass|warning|fail",
    "details": "string"
  }],
  
  "documents_collected": [{
    "type": "gst_certificate|pan|aadhar|bank_statement|itr|financials",
    "file_reference": "string",
    "collected_at": "ISO8601"
  }],
  
  "documents_pending": ["string"]
}
```

### 3.2 CAM to Bank Format Mapping

Nikita transforms internal CAM → Lender-specific formats:

| Internal CAM Field | UGRO CAM | Bajaj Format | HDFC Format |
|-------------------|----------|--------------|-------------|
| entity_identity.legal_name | NAME OF BORROWER | Applicant Name | Customer Name |
| promoters[0].credit_score | CIBIL/CRIF | Bureau Score | CIBIL Score |
| loan_request.amount_lakhs | LOAN AMOUNT | Requested Amount | Loan Amount |
| banking_details[0].account_number | ACCOUNT NUMBER | Bank A/c | Account No |

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- Conversations (Francis's domain - source of truth for customer interaction)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    channel VARCHAR(20) NOT NULL, -- whatsapp, web, app
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, abandoned
    current_phase VARCHAR(30) DEFAULT 'intake',
    
    -- Message history (for context)
    message_history JSONB DEFAULT '[]',
    
    -- Extracted data from conversation
    extracted_data JSONB DEFAULT '{}',
    
    -- Customer preferences captured
    preferences JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_active_conversation UNIQUE (customer_id, status) 
        WHERE status = 'active'
);

-- Consents (Critical for compliance)
CREATE TABLE consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id),
    customer_id UUID NOT NULL,
    
    consent_type VARCHAR(50) NOT NULL, -- credit_bureau, lender_sharing, communication_whatsapp, etc.
    granted BOOLEAN NOT NULL,
    method VARCHAR(20) NOT NULL, -- otp, explicit_yes, signed_document
    
    -- Audit fields
    ip_address INET,
    device_info JSONB,
    otp_verified_at TIMESTAMPTZ,
    
    -- Artifact reference if signed
    document_reference VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- Some consents may expire
    revoked_at TIMESTAMPTZ,
    
    INDEX idx_consents_customer (customer_id),
    INDEX idx_consents_type (consent_type)
);

-- CAM Records (Nikita's output)
CREATE TABLE cam_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id),
    
    status VARCHAR(20) DEFAULT 'building', -- building, complete, verified, submitted
    version INTEGER DEFAULT 1,
    
    -- The full CAM JSON
    cam_data JSONB NOT NULL,
    
    -- Quick-access fields for querying
    gstin VARCHAR(15),
    pan VARCHAR(10),
    annual_turnover_lakhs DECIMAL(12,2),
    credit_score_commercial VARCHAR(10),
    
    -- Validation
    missing_fields JSONB DEFAULT '[]',
    data_flags JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    
    INDEX idx_cam_gstin (gstin),
    INDEX idx_cam_pan (pan),
    INDEX idx_cam_conversation (conversation_id)
);

-- Credit Assessments (Kesha's output)
CREATE TABLE credit_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID REFERENCES cam_records(id),
    conversation_id UUID REFERENCES conversations(id),
    
    overall_eligibility VARCHAR(20), -- high, medium, low, ineligible
    max_eligible_amount_lakhs DECIMAL(12,2),
    
    -- Full assessment result
    assessment_data JSONB NOT NULL,
    
    -- Lender recommendations
    lender_matches JSONB NOT NULL,
    primary_recommendation VARCHAR(50),
    
    -- Customer-facing report
    customer_report JSONB NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_assessment_cam (cam_id),
    INDEX idx_assessment_conversation (conversation_id)
);

-- Lender Submissions (Tracking applications to lenders)
CREATE TABLE lender_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID REFERENCES cam_records(id),
    conversation_id UUID REFERENCES conversations(id),
    
    lender_id VARCHAR(50) NOT NULL,
    lender_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(50),
    
    -- Application tracking
    status VARCHAR(30) DEFAULT 'draft', 
    -- draft, submitted, under_review, approved, rejected, disbursed, cancelled
    
    application_reference VARCHAR(100), -- Lender's reference number
    
    -- Amounts
    amount_applied_lakhs DECIMAL(12,2),
    amount_sanctioned_lakhs DECIMAL(12,2),
    amount_disbursed_lakhs DECIMAL(12,2),
    
    -- Terms (if sanctioned)
    interest_rate DECIMAL(5,2),
    tenure_months INTEGER,
    emi_lakhs DECIMAL(10,2),
    
    -- Commission tracking
    commission_pct DECIMAL(5,2),
    commission_amount DECIMAL(12,2),
    commission_status VARCHAR(20), -- pending, invoiced, paid
    
    -- Documents sent
    documents_submitted JSONB DEFAULT '[]',
    
    -- Rejection details
    rejection_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    decision_at TIMESTAMPTZ,
    disbursed_at TIMESTAMPTZ,
    
    INDEX idx_submission_lender (lender_id),
    INDEX idx_submission_status (status),
    INDEX idx_submission_conversation (conversation_id)
);

-- Lenders Reference Table
CREATE TABLE lenders (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20), -- psu_bank, private_bank, nbfc, fintech
    active BOOLEAN DEFAULT true,
    
    -- Products offered
    products JSONB DEFAULT '[]',
    
    -- Eligibility criteria
    min_turnover_lakhs DECIMAL(12,2),
    min_vintage_years INTEGER,
    min_credit_score INTEGER,
    max_dpd_days INTEGER,
    restricted_sectors JSONB DEFAULT '[]',
    
    -- Commission structure
    commission_structure JSONB,
    
    -- Integration details
    submission_method VARCHAR(20), -- api, email, portal
    api_endpoint VARCHAR(255),
    
    -- Document requirements
    required_documents JSONB DEFAULT '[]',
    document_formats JSONB, -- Specific format templates
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log (Everything important)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    entity_type VARCHAR(50), -- conversation, cam, submission, consent
    entity_id UUID,
    
    action VARCHAR(50), -- created, updated, submitted, etc.
    actor VARCHAR(50), -- francis, nikita, kesha, system, user
    
    changes JSONB, -- What changed
    context JSONB, -- Additional context
    
    INDEX idx_audit_entity (entity_type, entity_id),
    INDEX idx_audit_timestamp (timestamp)
);
```

### 4.2 Database Views for PII Isolation

```sql
-- View for Kesha (no raw PII)
CREATE VIEW kesha_cam_view AS
SELECT 
    cr.id as cam_id,
    cr.conversation_id,
    cr.status,
    
    -- Business profile (no identifiers)
    cr.cam_data->'business_profile' as business_profile,
    cr.cam_data->'financial_summary' as financial_summary,
    cr.cam_data->'credit_profile' as credit_profile,
    cr.cam_data->'compliance_status' as compliance_status,
    cr.cam_data->'eligibility_calculations' as eligibility_calculations,
    cr.cam_data->'loan_request' as loan_request,
    cr.cam_data->'customer_preferences' as customer_preferences,
    cr.cam_data->'verification_flags' as verification_flags,
    
    -- Anonymized promoter data (scores only, no PAN/names)
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'designation', p->>'designation',
                'credit_score', p->>'credit_score',
                'outstanding_amount_lakhs', p->>'outstanding_amount_lakhs',
                'overdue_amount_lakhs', p->>'overdue_amount_lakhs'
            )
        )
        FROM jsonb_array_elements(cr.cam_data->'promoters') p
    ) as promoters_anonymized,
    
    cr.created_at,
    cr.updated_at
FROM cam_records cr
WHERE cr.status IN ('complete', 'verified');
```

---

## 5. n8n Workflow Structure

### 5.1 Main Flow (Event-Driven)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TRIGGER LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Webhook (Chat)  │  Webhook (Doc Upload)  │  Cron (Retry Failed)        │
└────────┬─────────┴──────────┬─────────────┴──────────┬──────────────────┘
         │                    │                        │
         ▼                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ROUTING & CONTEXT                                 │
│  Load conversation state → Determine action type → Build agent context  │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ├──► [New Message] ──► Francis Intent Extraction
         │                              │
         │                              ├──► GST Captured? ──► Trigger CAM Build
         │                              │
         │                              └──► Continue Conversation
         │
         ├──► [CAM Build Trigger] ──► Parallel Data Collection
         │                                    │
         │    ┌───────────────────────────────┼───────────────────────────┐
         │    │                               │                           │
         │    ▼                               ▼                           ▼
         │  GST Verify                   Credit Bureau               Udyam Lookup
         │    │                               │                           │
         │    └───────────────────────────────┼───────────────────────────┘
         │                                    │
         │                                    ▼
         │                           Nikita: Assemble CAM
         │                                    │
         │                                    ▼
         │                           CAM Complete? ──► Kesha: Assess
         │                                    │              │
         │                                    │              ▼
         │                                    │       Francis: Deliver Report
         │                                    │
         │                                    └──► Missing Data ──► Francis: Request
         │
         └──► [Document Upload] ──► Nikita: Process & Update CAM
```

### 5.2 Parallel Data Collection Sub-Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INPUT: GST Number + Consents Verified                                  │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐       ┌─────────┐
    │  GST    │       │  PAN    │       │ Credit  │       │  Udyam  │
    │ Verify  │       │ Verify  │       │ Bureau  │       │ Lookup  │
    └────┬────┘       └────┬────┘       └────┬────┘       └────┬────┘
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ Success │       │ Success │       │ Success │       │ Success │
    │   or    │       │   or    │       │   or    │       │   or    │
    │  Error  │       │  Error  │       │  Error  │       │  Error  │
    └────┬────┘       └────┬────┘       └────┬────┘       └────┬────┘
         │                  │                  │                  │
         └──────────────────┴──────────────────┴──────────────────┘
                                    │
                                    ▼
                           ┌───────────────┐
                           │  Merge Node   │
                           │  Wait for all │
                           └───────┬───────┘
                                   │
                                   ▼
                           ┌───────────────┐
                           │ Nikita: Build │
                           │     CAM       │
                           └───────────────┘
```

### 5.3 Error Handling Patterns

```javascript
// Retry configuration for external APIs
{
  "maxRetries": 3,
  "retryInterval": [2000, 5000, 10000], // Exponential backoff
  "retryOn": ["timeout", "5xx"],
  "fallback": {
    "action": "mark_pending",
    "notifyFrancis": true,
    "message": "We're experiencing delays verifying your GST. We'll update you shortly."
  }
}

// Error categorization
const errorHandling = {
  "invalid_gst": {
    "recoverable": true,
    "action": "ask_correction",
    "francisMessage": "The GST number you provided seems incorrect. Could you please check and share it again?"
  },
  "bureau_unavailable": {
    "recoverable": true,
    "action": "retry_later",
    "francisMessage": "We're fetching your credit information. This may take a few minutes."
  },
  "consent_missing": {
    "recoverable": true,
    "action": "request_consent",
    "francisMessage": "Before we proceed, I need your consent to check your credit history."
  }
};
```

---

## 6. State Machine Definition

### 6.1 Conversation States

```
                    ┌──────────────┐
                    │    INTAKE    │
                    │  (Francis)   │
                    └──────┬───────┘
                           │ GST captured + consent obtained
                           ▼
                    ┌──────────────┐
                    │   BUILDING   │
                    │   (Nikita)   │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  COMPLETE   │ │  INCOMPLETE │ │   ERROR     │
    │             │ │  (missing   │ │ (validation │
    │             │ │   docs)     │ │   failed)   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │               │ docs provided │ corrected
           │               └───────────────┤
           │                               │
           ▼                               │
    ┌──────────────┐                       │
    │  ASSESSING   │◄──────────────────────┘
    │   (Kesha)    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   ASSESSED   │
    │  (report     │
    │   ready)     │
    └──────┬───────┘
           │ customer chooses lender(s)
           ▼
    ┌──────────────┐
    │  SUBMITTING  │
    │   (Nikita    │
    │   prepares)  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  SUBMITTED   │
    │  (tracking)  │
    └──────┬───────┘
           │
    ┌──────┴──────────┬─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐   ┌──────────┐
│APPROVED │    │  REJECTED   │   │ DISBURSED│
│         │    │             │   │          │
└────┬────┘    └─────────────┘   └──────────┘
     │
     ▼
┌──────────┐
│DISBURSED │
└──────────┘
```

### 6.2 State Transition Rules

```javascript
const stateTransitions = {
  "intake": {
    "next": ["building"],
    "prerequisites": ["gst_number", "credit_bureau_consent"],
    "trigger": "manual" // Francis triggers when ready
  },
  "building": {
    "next": ["complete", "incomplete", "error"],
    "prerequisites": [],
    "trigger": "automatic", // n8n triggers
    "timeout": 300000 // 5 minutes max
  },
  "incomplete": {
    "next": ["building"],
    "prerequisites": ["missing_docs_provided"],
    "trigger": "event" // Document upload event
  },
  "complete": {
    "next": ["assessing"],
    "prerequisites": [],
    "trigger": "automatic"
  },
  "assessing": {
    "next": ["assessed"],
    "prerequisites": [],
    "trigger": "automatic",
    "timeout": 60000 // 1 minute
  },
  "assessed": {
    "next": ["submitting"],
    "prerequisites": ["lender_selected", "lender_consent"],
    "trigger": "manual" // Customer chooses
  },
  "submitting": {
    "next": ["submitted"],
    "prerequisites": ["documents_prepared"],
    "trigger": "automatic"
  },
  "submitted": {
    "next": ["approved", "rejected"],
    "prerequisites": [],
    "trigger": "external" // Lender response
  }
};
```

---

## 7. API Contracts

### 7.1 Francis MCP Endpoints

```yaml
# POST /francis/process-message
request:
  conversation_id: uuid
  customer_id: uuid
  channel: string
  message: string
  context:
    current_phase: string
    pending_questions: array
    pending_consents: array

response:
  response_to_customer: string
  extracted_data: object
  consents_obtained: array
  questions_answered: object
  action_requested: string
  next_questions: array

# POST /francis/format-report
request:
  assessment: object
  customer_preferences: object
  language: string

response:
  formatted_report: string
  key_highlights: array
  next_steps: array
```

### 7.2 Nikita MCP Endpoints

```yaml
# POST /nikita/build-cam
request:
  conversation_id: uuid
  data_sources:
    gst: object
    pan: object
    credit_bureau: object
    udyam: object
    bank_statements: array
  customer_inputs: object

response:
  cam_id: uuid
  status: string
  cam_data: object
  missing_fields: array
  data_flags: array
  kesha_ready: boolean

# POST /nikita/prepare-submission
request:
  cam_id: uuid
  lender_id: string
  format: string

response:
  documents: array
  submission_package: object
  validation_status: string
```

### 7.3 Kesha MCP Endpoints

```yaml
# POST /kesha/assess
request:
  cam_id: uuid
  anonymized_cam: object # From kesha_cam_view

response:
  assessment_id: uuid
  overall_eligibility: string
  max_eligible_amount_lakhs: number
  lender_matches: array
  recommendation: object
  customer_report: object

# POST /kesha/match-lenders
request:
  financial_metrics: object
  credit_profile: object
  loan_request: object
  preferences: object

response:
  matches: array
  ranking_explanation: string
```

---

## 8. Deployment Configuration

### 8.1 Render.com Services

```yaml
services:
  - name: francis-mcp
    type: web
    runtime: python
    repo: github.com/your-org/loan-origination
    rootDir: services/francis
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: loan-db
          property: connectionString
    scaling:
      minInstances: 1
      maxInstances: 3
    healthCheckPath: /health

  - name: data-services-mcp
    type: web
    runtime: python
    rootDir: services/data-services
    envVars:
      - key: FAMESCORE_API_KEY
        sync: false
      - key: CIBIL_API_KEY
        sync: false
    scaling:
      minInstances: 1
      maxInstances: 2

  - name: nikita-mcp
    type: web
    runtime: python
    rootDir: services/nikita
    scaling:
      minInstances: 1
      maxInstances: 2

  - name: kesha-mcp
    type: web
    runtime: python
    rootDir: services/kesha
    scaling:
      minInstances: 1
      maxInstances: 2

databases:
  - name: loan-db
    plan: starter
    postgresMajorVersion: 15
```

### 8.2 n8n Configuration

```javascript
// Workflow settings
{
  "executionOrder": "v1",
  "saveDataErrorExecution": "all",
  "saveDataSuccessExecution": "all",
  "saveManualExecutions": true,
  "saveExecutionProgress": true,
  "errorWorkflow": "error-handler-workflow-id",
  "timezone": "Asia/Kolkata"
}
```

---

## 9. Monitoring & Observability

### 9.1 Key Metrics to Track

```yaml
business_metrics:
  - conversations_started_per_day
  - cam_completion_rate
  - average_time_to_assessment
  - lender_submission_rate
  - approval_rate_by_lender
  - disbursement_rate
  - commission_earned

technical_metrics:
  - api_response_time_p95
  - api_error_rate
  - mcp_server_availability
  - database_query_latency
  - workflow_execution_time
  - retry_rate_by_service

compliance_metrics:
  - consent_capture_rate
  - data_access_audit_log_completeness
  - pii_exposure_incidents
```

### 9.2 Alerting Rules

```yaml
alerts:
  - name: high_error_rate
    condition: error_rate > 5%
    window: 5m
    severity: critical
    
  - name: slow_cam_build
    condition: cam_build_time_p95 > 60s
    severity: warning
    
  - name: consent_missing
    condition: cam_without_consent_count > 0
    severity: critical
    
  - name: bureau_api_down
    condition: bureau_api_success_rate < 90%
    window: 10m
    severity: high
```

---

## 10. Migration Plan from Current State

### Phase 1: Database & Schema (Week 1)
1. Create new tables with proper schema
2. Migrate existing `conversations` and `leads` data
3. Set up `kesha_cam_view` for PII isolation

### Phase 2: Data Services Extraction (Week 2)
1. Extract GST/PAN/Bureau calls to `data-services-mcp`
2. Implement retry logic and caching
3. Test with current workflow

### Phase 3: Nikita Refactor (Week 3)
1. Build CAM assembly logic based on FameScore schema
2. Implement parallel data collection in n8n
3. Create bank format templates

### Phase 4: Kesha Implementation (Week 4)
1. Build lender matching algorithm
2. Implement customer report generation
3. Connect to anonymized CAM view

### Phase 5: Francis Enhancement (Week 5)
1. Add consent capture flow
2. Implement qualifying questions
3. Connect report delivery

### Phase 6: Integration & Testing (Week 6)
1. End-to-end testing
2. Load testing (5 concurrent)
3. Regulatory compliance review

---

## Appendix A: FameScore to CAM Field Mapping

| FameScore Section | FameScore Field | CAM Path |
|------------------|-----------------|----------|
| Entity Information | Legal Name of the Business | entity_identity.legal_name |
| Entity Information | Constitution | entity_identity.constitution |
| Entity Information | GST Number(s) | entity_identity.gst_numbers |
| Entity Information | PAN of the ENTITY | entity_identity.pan |
| Entity Information | Udyam Number | entity_identity.udyam_number |
| Entity Information | GST Aggregated Turnover | financial_summary.turnover.annual_lakhs |
| Credit Bureau (Commercial) | Score | credit_profile.commercial_bureau.score |
| Credit Bureau (Commercial) | Total Outstanding Loan Amount | credit_profile.commercial_bureau.total_outstanding_lakhs |
| Credit Bureau (Consumer) | Score | promoters[].credit_score |
| Bank - Bureau Information | All facilities | credit_profile.existing_facilities[] |
| Compliance | GSTR1/3B filing status | compliance_status.gst |
| Income Tax Return | Net Profit, Current Ratio | financial_summary.profitability |
| Sales Data | Quarterly breakdown | financial_summary.turnover.quarterly_breakdown |
| Bank Statement Summary | Total Credit, BTO | financial_summary.banking_behavior |
| Bank Limit Eligibility | All calculations | eligibility_calculations |

---

## Appendix B: Regulatory Checklist

### RBI DSA Guidelines
- [ ] No misleading approval guarantees
- [ ] Clear fee disclosure
- [ ] Grievance redressal mechanism
- [ ] Agent registration displayed

### DPDP Act 2023
- [ ] Purpose limitation (only loan processing)
- [ ] Data minimization
- [ ] Explicit consent before collection
- [ ] Right to erasure capability
- [ ] Data retention policy

### Fair Lending Practices
- [ ] Non-discriminatory criteria
- [ ] Rejection reason disclosure
- [ ] All-in-cost transparency
- [ ] Cooling-off period information

---

*Document maintained by: Architecture Team*
*Next review: [Date]*
