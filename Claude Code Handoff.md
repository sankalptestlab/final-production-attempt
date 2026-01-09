Loan Origination System - Claude Code Handoff
What We're Building
MSME loan origination platform for India. Three AI agents (Francis/Nikita/Kesha) orchestrated by n8n, each with dedicated MCP server. Parallel processing architecture where GST capture triggers simultaneous data collection.
Architecture (4 MCP Servers)

francis-mcp: Customer-facing. Intent extraction, consent capture, qualifying questions, report delivery. Writes to DB.
data-services-mcp: Stateless API gateway. GST/PAN verification, credit bureau pulls, Udyam lookup. Cacheable, rate-limited.
nikita-mcp: Document assembly. Consumes data-services output, builds CAM (Credit Assessment Memorandum), prepares bank-specific formats.
kesha-mcp: Credit intelligence. Receives anonymized CAM (no raw PII), calculates eligibility, ranks lenders, generates customer reports.

Data Flow
Customer message → Francis extracts GST + obtains consent
                         ↓
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
    GST Verify     Credit Bureau    Udyam Lookup  [parallel]
         └───────────────┼───────────────┘
                         ↓
              Nikita assembles CAM
                         ↓
              Kesha assesses (via DB view, no PII)
                         ↓
              Francis delivers report
Key Technical Decisions

PII Isolation: Kesha reads from kesha_cam_view (Postgres view stripping identifiers)
Consent tracking: Dedicated table with OTP verification, timestamps, audit trail
CAM schema: Based on FameScore report structure (39 pages of fields) + bank submission formats (CAM/PD/FI Excel)
Mock adapters: All external APIs mocked initially, swap for real when partnerships signed
State machine: intake → building → complete → assessing → assessed → submitting → submitted → approved/disbursed

Database Tables Needed

conversations (Francis domain)
consents (audit trail)
cam_records (Nikita output, full CAM JSON)
credit_assessments (Kesha output)
lender_submissions (tracking to disbursement)
lenders (reference data with criteria)
audit_log

Reference Files

FameScore PDF: Sample report showing all data fields from GST/bureau APIs (this is what data-services returns)
CAM Excel: Bank submission format (CAM/PD/FI/Document Checklist sheets) - Nikita transforms CAM JSON into these formats

Build Order

Database schema (SQL)
data-services-mcp with mock FameScore adapter
nikita-mcp CAM assembly
kesha-mcp assessment + lender matching
francis-mcp conversation handling
n8n workflow connecting everything

Current State
No existing customers. Old n8n workflow abandoned. FameScore API is mocked. Lender partnerships being established in parallel with build.

Architecture doc with full schemas, API contracts, and state machine definitions available in project files.