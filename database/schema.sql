-- MSME Loan Origination Platform - Database Schema
-- PostgreSQL/Supabase Migration
-- Version: 1.0
-- Date: February 2026

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CONVERSATIONS TABLE
-- Tracks all chat sessions with customers
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'web' CHECK (channel IN ('web', 'whatsapp', 'app')),
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned', 'error')),
    current_phase VARCHAR(30) NOT NULL DEFAULT 'intake' CHECK (current_phase IN ('intake', 'assessing', 'assessed', 'submitted', 'sanctioned', 'disbursed')),
    message_history JSONB DEFAULT '[]'::jsonb,
    extracted_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for conversations
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);

-- ============================================
-- CONSENTS TABLE
-- DPDP Act 2023 compliance - tracks all consents
-- ============================================
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL,
    consent_type VARCHAR(50) NOT NULL CHECK (consent_type IN ('credit_bureau', 'data_processing', 'marketing', 'terms_conditions')),
    granted BOOLEAN NOT NULL DEFAULT false,
    method VARCHAR(30) NOT NULL DEFAULT 'text' CHECK (method IN ('text', 'button', 'checkbox', 'otp')),
    ip_address INET,
    device_info JSONB DEFAULT '{}'::jsonb,
    otp_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

-- Indexes for consents
CREATE INDEX idx_consents_customer_id ON consents(customer_id);
CREATE INDEX idx_consents_conversation_id ON consents(conversation_id);
CREATE INDEX idx_consents_type ON consents(consent_type);

-- ============================================
-- CAM_RECORDS TABLE
-- Credit Assessment Memorandums
-- ============================================
CREATE TABLE IF NOT EXISTS cam_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'building' CHECK (status IN ('building', 'complete', 'incomplete', 'error')),
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Core identifiers (PII - protected)
    gstin VARCHAR(15),
    pan VARCHAR(10),
    
    -- Aggregated financial data
    annual_turnover_lakhs DECIMAL(15,2),
    credit_score VARCHAR(10),
    
    -- Full CAM data as JSONB
    cam_data JSONB DEFAULT '{}'::jsonb,
    
    -- Validation tracking
    missing_fields JSONB DEFAULT '[]'::jsonb,
    data_flags JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

-- Indexes for cam_records
CREATE INDEX idx_cam_records_gstin ON cam_records(gstin);
CREATE INDEX idx_cam_records_pan ON cam_records(pan);
CREATE INDEX idx_cam_records_conversation_id ON cam_records(conversation_id);

-- ============================================
-- CREDIT_ASSESSMENTS TABLE
-- Eligibility and lender matching results
-- ============================================
CREATE TABLE IF NOT EXISTS credit_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID NOT NULL REFERENCES cam_records(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Overall assessment
    overall_eligibility VARCHAR(20) NOT NULL CHECK (overall_eligibility IN ('high', 'medium', 'low', 'ineligible')),
    max_eligible_amount_lakhs DECIMAL(15,2),
    
    -- Detailed results
    assessment_data JSONB DEFAULT '{}'::jsonb,
    lender_matches JSONB DEFAULT '[]'::jsonb,
    customer_report JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for credit_assessments
CREATE INDEX idx_credit_assessments_cam_id ON credit_assessments(cam_id);
CREATE INDEX idx_credit_assessments_conversation_id ON credit_assessments(conversation_id);
CREATE INDEX idx_credit_assessments_eligibility ON credit_assessments(overall_eligibility);

-- ============================================
-- LENDERS TABLE
-- Lender master data and eligibility criteria
-- ============================================
CREATE TABLE IF NOT EXISTS lenders (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(30) NOT NULL CHECK (type IN ('private_bank', 'psu_bank', 'nbfc', 'fintech', 'sfb')),
    active BOOLEAN DEFAULT true,
    
    -- Eligibility criteria
    min_turnover_lakhs DECIMAL(15,2) NOT NULL DEFAULT 0,
    max_turnover_lakhs DECIMAL(15,2),
    min_credit_score INTEGER NOT NULL DEFAULT 0,
    max_dpd_days INTEGER DEFAULT 0,
    min_years_in_business INTEGER DEFAULT 0,
    
    -- Loan parameters
    min_loan_amount_lakhs DECIMAL(15,2) DEFAULT 5,
    max_loan_amount_lakhs DECIMAL(15,2) DEFAULT 500,
    interest_rate_min DECIMAL(5,2),
    interest_rate_max DECIMAL(5,2),
    
    -- Commission structure
    commission_structure JSONB DEFAULT '{}'::jsonb,
    
    -- Product offerings
    products JSONB DEFAULT '[]'::jsonb,
    required_documents JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- LENDER_SUBMISSIONS TABLE
-- Track applications submitted to lenders
-- ============================================
CREATE TABLE IF NOT EXISTS lender_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cam_id UUID NOT NULL REFERENCES cam_records(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    lender_id VARCHAR(50) NOT NULL REFERENCES lenders(id),
    lender_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(50),
    
    -- Application status
    status VARCHAR(30) NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'under_review', 'approved', 'sanctioned', 'disbursed', 'rejected', 'withdrawn')),
    
    -- Amounts
    amount_applied_lakhs DECIMAL(15,2),
    amount_sanctioned_lakhs DECIMAL(15,2),
    amount_disbursed_lakhs DECIMAL(15,2),
    
    -- Terms
    interest_rate DECIMAL(5,2),
    tenure_months INTEGER,
    
    -- Commission
    commission_pct DECIMAL(5,2),
    commission_amount DECIMAL(15,2),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    sanctioned_at TIMESTAMPTZ,
    disbursed_at TIMESTAMPTZ
);

-- Indexes for lender_submissions
CREATE INDEX idx_lender_submissions_lender_id ON lender_submissions(lender_id);
CREATE INDEX idx_lender_submissions_status ON lender_submissions(status);
CREATE INDEX idx_lender_submissions_conversation_id ON lender_submissions(conversation_id);

-- ============================================
-- AUDIT_LOG TABLE
-- Complete audit trail for compliance
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    action VARCHAR(30) NOT NULL CHECK (action IN ('create', 'read', 'update', 'delete', 'consent_granted', 'consent_revoked', 'data_accessed')),
    actor_type VARCHAR(30) DEFAULT 'system' CHECK (actor_type IN ('system', 'user', 'service', 'admin')),
    actor_id VARCHAR(100),
    changes JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT
);

-- Indexes for audit_log
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);

-- ============================================
-- KESHA_CAM_VIEW
-- Anonymized view for credit assessment (NO PII)
-- ============================================
CREATE OR REPLACE VIEW kesha_cam_view AS
SELECT 
    cr.id AS cam_id,
    cr.conversation_id,
    cr.status,
    cr.version,
    
    -- Financial data (non-PII)
    cr.annual_turnover_lakhs,
    cr.credit_score,
    
    -- Extract anonymized fields from cam_data
    cr.cam_data->>'industry_sector' AS industry_sector,
    (cr.cam_data->>'years_in_business')::INTEGER AS years_in_business,
    (cr.cam_data->'financial_summary'->>'monthly_average_lakhs')::DECIMAL AS monthly_average_lakhs,
    (cr.cam_data->'financial_summary'->>'yoy_growth_pct')::DECIMAL AS yoy_growth_pct,
    cr.cam_data->'credit_profile' AS credit_profile,
    cr.cam_data->'loan_request' AS loan_request,
    
    -- Flags and validation
    cr.missing_fields,
    cr.data_flags,
    
    cr.created_at,
    cr.updated_at
FROM cam_records cr
-- Explicitly EXCLUDE: gstin, pan, entity_name, address, promoter details
;

-- ============================================
-- SEED DATA: Initial Lenders
-- ============================================
INSERT INTO lenders (id, name, type, min_turnover_lakhs, min_credit_score, max_dpd_days, min_loan_amount_lakhs, max_loan_amount_lakhs, interest_rate_min, interest_rate_max, products, required_documents)
VALUES 
    ('hdfc_bank', 'HDFC Bank', 'private_bank', 50, 700, 0, 10, 100, 11.00, 14.00, 
     '["working_capital", "term_loan", "overdraft"]'::jsonb,
     '["pan", "aadhaar", "gst_certificate", "bank_statements_12m", "itr_2y", "financials_audited"]'::jsonb),
    
    ('icici_bank', 'ICICI Bank', 'private_bank', 50, 680, 0, 10, 150, 11.50, 15.00,
     '["working_capital", "term_loan", "equipment_finance"]'::jsonb,
     '["pan", "aadhaar", "gst_certificate", "bank_statements_12m", "itr_2y", "financials_audited"]'::jsonb),
    
    ('bajaj_finserv', 'Bajaj Finserv', 'nbfc', 10, 650, 30, 5, 80, 14.00, 18.00,
     '["working_capital", "term_loan", "equipment_finance"]'::jsonb,
     '["pan", "aadhaar", "gst_certificate", "bank_statements_12m", "udyam_certificate"]'::jsonb),
    
    ('ugro_capital', 'UGRO Capital', 'nbfc', 20, 600, 60, 5, 50, 15.00, 19.00,
     '["working_capital", "term_loan"]'::jsonb,
     '["pan", "aadhaar", "gst_certificate", "bank_statements_12m", "udyam_certificate"]'::jsonb),
    
    ('indifi', 'Indifi', 'fintech', 5, 550, 90, 2, 30, 18.00, 24.00,
     '["working_capital", "invoice_discounting"]'::jsonb,
     '["pan", "aadhaar", "gst_certificate", "bank_statements_6m", "udyam_certificate"]'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- TRIGGERS: Auto-update timestamps
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_cam_records_updated_at
    BEFORE UPDATE ON cam_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_lender_submissions_updated_at
    BEFORE UPDATE ON lender_submissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_lenders_updated_at
    BEFORE UPDATE ON lenders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- ROW LEVEL SECURITY (RLS) - ENABLED
-- ============================================

-- Enable RLS on all sensitive tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE cam_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE lender_submissions ENABLE ROW LEVEL SECURITY;

-- ============================================
-- RLS POLICIES
-- ============================================

-- Conversations: Users can only access their own conversations
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT USING (customer_id = auth.uid());

CREATE POLICY "Users can insert own conversations" ON conversations
    FOR INSERT WITH CHECK (customer_id = auth.uid());

CREATE POLICY "Users can update own conversations" ON conversations
    FOR UPDATE USING (customer_id = auth.uid());

-- Service role bypass for backend services
CREATE POLICY "Service role full access to conversations" ON conversations
    FOR ALL USING (auth.role() = 'service_role');

-- Consents: Users can only access their own consents
CREATE POLICY "Users can view own consents" ON consents
    FOR SELECT USING (customer_id = auth.uid());

CREATE POLICY "Users can insert own consents" ON consents
    FOR INSERT WITH CHECK (customer_id = auth.uid());

CREATE POLICY "Service role full access to consents" ON consents
    FOR ALL USING (auth.role() = 'service_role');

-- CAM Records: Only service role can access (contains PII)
CREATE POLICY "Service role full access to cam_records" ON cam_records
    FOR ALL USING (auth.role() = 'service_role');

-- Credit Assessments: Users can view their own assessments via conversation
CREATE POLICY "Users can view own assessments" ON credit_assessments
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE customer_id = auth.uid()
        )
    );

CREATE POLICY "Service role full access to credit_assessments" ON credit_assessments
    FOR ALL USING (auth.role() = 'service_role');

-- Lender Submissions: Users can view their own submissions
CREATE POLICY "Users can view own submissions" ON lender_submissions
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE customer_id = auth.uid()
        )
    );

CREATE POLICY "Service role full access to lender_submissions" ON lender_submissions
    FOR ALL USING (auth.role() = 'service_role');

-- Audit Log: Only service role can access
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to audit_log" ON audit_log
    FOR ALL USING (auth.role() = 'service_role');

-- Lenders: Public read access (non-sensitive data)
-- No RLS needed as lender info is public

-- ============================================
-- GRANT PERMISSIONS TO SERVICE ROLE
-- ============================================
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

COMMENT ON TABLE conversations IS 'Tracks all customer chat sessions';
COMMENT ON TABLE consents IS 'DPDP Act 2023 compliant consent tracking';
COMMENT ON TABLE cam_records IS 'Credit Assessment Memorandums';
COMMENT ON TABLE credit_assessments IS 'Eligibility and lender matching results';
COMMENT ON TABLE lenders IS 'Lender master data and criteria';
COMMENT ON TABLE lender_submissions IS 'Applications submitted to lenders';
COMMENT ON TABLE audit_log IS 'Complete audit trail for compliance';
COMMENT ON VIEW kesha_cam_view IS 'Anonymized CAM view for Kesha (no PII)';
