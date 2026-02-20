-- Migration: Enable Row-Level Security
-- Date: 2026-02-20
-- Description: Enables RLS on sensitive tables and creates access policies

-- ============================================
-- ENABLE ROW LEVEL SECURITY
-- ============================================

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE cam_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE lender_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- ============================================
-- DROP EXISTING POLICIES (if any)
-- ============================================

DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Service role full access to conversations" ON conversations;

DROP POLICY IF EXISTS "Users can view own consents" ON consents;
DROP POLICY IF EXISTS "Users can insert own consents" ON consents;
DROP POLICY IF EXISTS "Service role full access to consents" ON consents;

DROP POLICY IF EXISTS "Service role full access to cam_records" ON cam_records;

DROP POLICY IF EXISTS "Users can view own assessments" ON credit_assessments;
DROP POLICY IF EXISTS "Service role full access to credit_assessments" ON credit_assessments;

DROP POLICY IF EXISTS "Users can view own submissions" ON lender_submissions;
DROP POLICY IF EXISTS "Service role full access to lender_submissions" ON lender_submissions;

DROP POLICY IF EXISTS "Service role full access to audit_log" ON audit_log;

-- ============================================
-- CREATE RLS POLICIES
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
CREATE POLICY "Service role full access to audit_log" ON audit_log
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
