-- Loan Origination System - Database Schema
-- PostgreSQL 15+
-- For use with Supabase

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Conversations (Francis's domain - source of truth for customer interaction)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('whatsapp', 'web', 'app')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    current_phase VARCHAR(30) DEFAULT 'intake' CHECK (current_phase IN (
        'intake', 'building', 'complete', 'incomplete', 'error',
        'assessing', 'assessed', 'submitting', 'submitted',
        'approved', 'rejected', 'disbursed'
    )),

    -- Message history (for context)
    message_history JSONB DEFAULT '[]'::jsonb,

    -- Extracted data from conversation
    extracted_data JSONB DEFAULT '{}'::jsonb,

    -- Customer preferences captured
    preferences JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique constraint for active conversations
CREATE UNIQUE INDEX unique_active_conversation
    ON conversations (customer_id, status)
    WHERE status = 'active';

-- Indexes for conversations
CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_phase ON conversations(current_phase);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

-- ============================================================================
-- CONSENTS (Critical for compliance)
-- ============================================================================

CREATE TABLE consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL,

    consent_type VARCHAR(50) NOT NULL CHECK (consent_type IN (
        'credit_bureau', 'lender_sharing', 'communication_whatsapp',
        'communication_sms', 'communication_email', 'data_processing'
    )),
    granted BOOLEAN NOT NULL,
    method VARCHAR(20) NOT NULL CHECK (method IN ('otp', 'explicit_yes', 'signed_document')),

    -- Audit fields
    ip_address INET,
    device_info JSONB,
    otp_verified_at TIMESTAMPTZ,

    -- Artifact reference if signed
    document_reference VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_consents_customer ON consents(customer_id);
CREATE INDEX idx_consents_conversation ON consents(conversation_id);
CREATE INDEX idx_consents_type ON consents(consent_type);
CREATE INDEX idx_consents_granted ON consents(granted) WHERE granted = true AND revoked_at IS NULL;

-- ============================================================================
-- CAM RECORDS (Nikita's output)
-- ============================================================================

CREATE TABLE cam_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,

    status VARCHAR(20) DEFAULT 'building' CHECK (status IN ('building', 'complete', 'verified', 'submitted')),
    version INTEGER DEFAULT 1,

    -- The full CAM JSON
    cam_data JSONB NOT NULL,

    -- Quick-access fields for querying (extracted from cam_data)
    gstin VARCHAR(15),
    pan VARCHAR(10),
    annual_turnover_lakhs DECIMAL(12,2),
    credit_score_commercial VARCHAR(10),

    -- Validation
    missing_fields JSONB DEFAULT '[]'::jsonb,
    data_flags JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE INDEX idx_cam_gstin ON cam_records(gstin);
CREATE INDEX idx_cam_pan ON cam_records(pan);
CREATE INDEX idx_cam_conversation ON cam_records(conversation_id);
CREATE INDEX idx_cam_status ON cam_records(status);

-- ============================================================================
-- CREDIT ASSESSMENTS (Kesha's output)
-- ============================================================================

CREATE TABLE credit_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID REFERENCES cam_records(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,

    overall_eligibility VARCHAR(20) CHECK (overall_eligibility IN ('high', 'medium', 'low', 'ineligible')),
    max_eligible_amount_lakhs DECIMAL(12,2),

    -- Full assessment result
    assessment_data JSONB NOT NULL,

    -- Lender recommendations
    lender_matches JSONB NOT NULL,
    primary_recommendation VARCHAR(50),

    -- Customer-facing report
    customer_report JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assessment_cam ON credit_assessments(cam_id);
CREATE INDEX idx_assessment_conversation ON credit_assessments(conversation_id);
CREATE INDEX idx_assessment_eligibility ON credit_assessments(overall_eligibility);

-- ============================================================================
-- LENDER SUBMISSIONS (Tracking applications to lenders)
-- ============================================================================

CREATE TABLE lender_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID REFERENCES cam_records(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,

    lender_id VARCHAR(50) NOT NULL,
    lender_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(50),

    -- Application tracking
    status VARCHAR(30) DEFAULT 'draft' CHECK (status IN (
        'draft', 'submitted', 'under_review', 'approved',
        'rejected', 'disbursed', 'cancelled'
    )),

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
    commission_status VARCHAR(20) CHECK (commission_status IN ('pending', 'invoiced', 'paid')),

    -- Documents sent
    documents_submitted JSONB DEFAULT '[]'::jsonb,

    -- Rejection details
    rejection_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    decision_at TIMESTAMPTZ,
    disbursed_at TIMESTAMPTZ
);

CREATE INDEX idx_submission_lender ON lender_submissions(lender_id);
CREATE INDEX idx_submission_status ON lender_submissions(status);
CREATE INDEX idx_submission_conversation ON lender_submissions(conversation_id);
CREATE INDEX idx_submission_cam ON lender_submissions(cam_id);

-- ============================================================================
-- LENDERS REFERENCE TABLE
-- ============================================================================

CREATE TABLE lenders (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('psu_bank', 'private_bank', 'nbfc', 'fintech')),
    active BOOLEAN DEFAULT true,

    -- Products offered
    products JSONB DEFAULT '[]'::jsonb,

    -- Eligibility criteria
    min_turnover_lakhs DECIMAL(12,2),
    min_vintage_years INTEGER,
    min_credit_score INTEGER,
    max_dpd_days INTEGER,
    restricted_sectors JSONB DEFAULT '[]'::jsonb,

    -- Commission structure
    commission_structure JSONB,

    -- Integration details
    submission_method VARCHAR(20) CHECK (submission_method IN ('api', 'email', 'portal')),
    api_endpoint VARCHAR(255),

    -- Document requirements
    required_documents JSONB DEFAULT '[]'::jsonb,
    document_formats JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lenders_active ON lenders(active) WHERE active = true;
CREATE INDEX idx_lenders_type ON lenders(type);

-- ============================================================================
-- AUDIT LOG (Everything important)
-- ============================================================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    entity_type VARCHAR(50),
    entity_id UUID,

    action VARCHAR(50),
    actor VARCHAR(50),

    changes JSONB,
    context JSONB,

    -- Add metadata for search
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_actor ON audit_log(actor);
CREATE INDEX idx_audit_action ON audit_log(action);

-- ============================================================================
-- VIEWS FOR PII ISOLATION
-- ============================================================================

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
                'shareholding_pct', (p->>'shareholding_pct')::numeric,
                'credit_score', (p->>'credit_score')::integer,
                'outstanding_amount_lakhs', (p->>'outstanding_amount_lakhs')::numeric,
                'overdue_amount_lakhs', (p->>'overdue_amount_lakhs')::numeric,
                'active_loans', (p->>'active_loans')::integer
            )
        )
        FROM jsonb_array_elements(cr.cam_data->'promoters') p
    ) as promoters_anonymized,

    cr.created_at,
    cr.updated_at
FROM cam_records cr
WHERE cr.status IN ('complete', 'verified');

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cam_records_updated_at
    BEFORE UPDATE ON cam_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lenders_updated_at
    BEFORE UPDATE ON lenders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA FOR LENDERS
-- ============================================================================

INSERT INTO lenders (id, name, type, active, products, min_turnover_lakhs, min_vintage_years, min_credit_score, max_dpd_days, commission_structure, submission_method, required_documents) VALUES
('bajaj_finserv', 'Bajaj Finserv', 'nbfc', true,
    '[{"name": "Business Loan", "min_amount": 1, "max_amount": 80}]'::jsonb,
    10, 1, 650, 30,
    '{"base_pct": 2.5, "incentive_tiers": [{"min_amount": 50, "pct": 3.0}]}'::jsonb,
    'api',
    '["gst_certificate", "pan", "bank_statement_6m", "itr_latest"]'::jsonb
),
('hdfc_bank', 'HDFC Bank', 'private_bank', true,
    '[{"name": "SME Business Loan", "min_amount": 5, "max_amount": 100}]'::jsonb,
    50, 2, 700, 15,
    '{"base_pct": 2.0, "incentive_tiers": [{"min_amount": 100, "pct": 2.5}]}'::jsonb,
    'portal',
    '["gst_certificate", "pan", "bank_statement_12m", "itr_2years", "financials"]'::jsonb
),
('icici_bank', 'ICICI Bank', 'private_bank', true,
    '[{"name": "Business Loan", "min_amount": 5, "max_amount": 150}]'::jsonb,
    50, 2, 680, 20,
    '{"base_pct": 2.0}'::jsonb,
    'portal',
    '["gst_certificate", "pan", "bank_statement_12m", "itr_latest"]'::jsonb
),
('ugro_capital', 'UGRO Capital', 'nbfc', true,
    '[{"name": "MSME Loan", "min_amount": 10, "max_amount": 50}]'::jsonb,
    20, 1, 600, 45,
    '{"base_pct": 3.0, "incentive_tiers": [{"min_amount": 30, "pct": 3.5}]}'::jsonb,
    'email',
    '["gst_certificate", "pan", "bank_statement_6m"]'::jsonb
),
('indifi', 'Indifi', 'fintech', true,
    '[{"name": "Working Capital Loan", "min_amount": 1, "max_amount": 30}]'::jsonb,
    5, 1, 550, 60,
    '{"base_pct": 4.0}'::jsonb,
    'api',
    '["gst_certificate", "pan", "bank_statement_3m"]'::jsonb
);

-- ============================================================================
-- FUNCTIONS FOR AUDIT LOGGING
-- ============================================================================

CREATE OR REPLACE FUNCTION log_conversation_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (entity_type, entity_id, action, actor, changes, context)
    VALUES (
        'conversation',
        NEW.id,
        CASE
            WHEN TG_OP = 'INSERT' THEN 'created'
            WHEN TG_OP = 'UPDATE' THEN 'updated'
        END,
        'system',
        CASE
            WHEN TG_OP = 'UPDATE' THEN
                jsonb_build_object(
                    'old', to_jsonb(OLD),
                    'new', to_jsonb(NEW)
                )
            ELSE to_jsonb(NEW)
        END,
        jsonb_build_object('operation', TG_OP)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_conversation_changes
    AFTER INSERT OR UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION log_conversation_changes();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get active consent for a customer
CREATE OR REPLACE FUNCTION has_active_consent(
    p_customer_id UUID,
    p_consent_type VARCHAR(50)
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM consents
        WHERE customer_id = p_customer_id
        AND consent_type = p_consent_type
        AND granted = true
        AND revoked_at IS NULL
        AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get latest CAM for a conversation
CREATE OR REPLACE FUNCTION get_latest_cam(p_conversation_id UUID)
RETURNS UUID AS $$
BEGIN
    RETURN (
        SELECT id FROM cam_records
        WHERE conversation_id = p_conversation_id
        ORDER BY version DESC, created_at DESC
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ROW LEVEL SECURITY (Optional - for Supabase)
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE cam_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_assessments ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth setup)
-- Example: Allow service role full access
CREATE POLICY "Service role has full access to conversations"
    ON conversations
    FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role has full access to consents"
    ON consents
    FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role has full access to cam_records"
    ON cam_records
    FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role has full access to credit_assessments"
    ON credit_assessments
    FOR ALL
    TO service_role
    USING (true);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE conversations IS 'Customer conversation tracking and state management';
COMMENT ON TABLE consents IS 'Regulatory compliance - all customer consents with audit trail';
COMMENT ON TABLE cam_records IS 'Credit Assessment Memorandum - full business profile';
COMMENT ON TABLE credit_assessments IS 'Kesha output - eligibility and lender matches';
COMMENT ON TABLE lender_submissions IS 'Application tracking through lender lifecycle';
COMMENT ON TABLE lenders IS 'Reference data for all partner lenders';
COMMENT ON TABLE audit_log IS 'Complete audit trail for compliance';
COMMENT ON VIEW kesha_cam_view IS 'PII-isolated view for credit assessment - no raw identifiers';

COMMENT ON COLUMN consents.method IS 'How consent was obtained: otp, explicit_yes, or signed_document';
COMMENT ON COLUMN cam_records.cam_data IS 'Full CAM JSON following schema in architecture doc';
COMMENT ON COLUMN lender_submissions.commission_status IS 'Commission payment tracking';
