# Product Requirements Document (PRD)
# MSME Loan Origination Platform

---

## Document Information
| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Last Updated** | January 2026 |
| **Status** | MVP Complete - Demo Ready |
| **Product Owner** | [TBD] |

---

## 1. Executive Summary

### 1.1 Product Vision
An AI-powered loan origination platform that streamlines the MSME (Micro, Small, and Medium Enterprise) lending process in India through conversational interfaces, automated credit assessment, and intelligent lender matching.

### 1.2 Problem Statement
Indian MSMEs face significant challenges in accessing formal credit:
- Complex, time-consuming application processes
- Lack of transparency in eligibility criteria
- Multiple document submissions to different lenders
- Long waiting periods for credit decisions
- Limited understanding of best-fit lending options

### 1.3 Solution Overview
A multi-agent AI system that:
1. **Converses naturally** with business owners to collect loan requirements
2. **Automates data collection** from GST, PAN, credit bureaus, and other sources
3. **Builds comprehensive credit profiles** (CAM - Credit Assessment Memorandum)
4. **Matches borrowers** with optimal lenders based on eligibility and preferences
5. **Provides actionable insights** on loan eligibility and improvement opportunities

---

## 2. Target Users

### 2.1 Primary Users
| User Type | Description | Needs |
|-----------|-------------|-------|
| **MSME Owners** | Business owners seeking working capital, term loans, invoice discounting | Quick eligibility check, transparent process, best rates |
| **DSA Agents** | Direct Selling Agents processing loan applications | Efficient data collection, multi-lender submission |
| **Loan Officers** | Bank/NBFC staff reviewing applications | Structured CAM data, risk assessment |

### 2.2 User Personas

**Persona 1: Rajesh (MSME Owner)**
- Runs a manufacturing unit with Rs 2.5 Cr annual turnover
- Needs Rs 50L working capital loan
- Limited time, prefers quick digital process
- Values transparency in rates and terms

**Persona 2: Priya (DSA Agent)**
- Processes 20+ loan applications monthly
- Works with multiple lenders
- Needs efficient document collection
- Commission-driven, values approval rates

---

## 3. Product Requirements

### 3.1 Functional Requirements

#### FR-1: Conversational Loan Intake (Francis MCP)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-1.1 | Extract loan amount from natural language | P0 | Implemented |
| FR-1.2 | Validate and extract GST number (15-digit format) | P0 | Implemented |
| FR-1.3 | Validate and extract PAN (10-character format) | P0 | Implemented |
| FR-1.4 | Capture loan purpose (working capital, equipment, etc.) | P0 | Implemented |
| FR-1.5 | Obtain explicit credit bureau consent | P0 | Implemented |
| FR-1.6 | Ask qualifying questions (collateral, tenure, priority) | P1 | Implemented |
| FR-1.7 | Support multi-channel (web, WhatsApp, app) | P1 | Partial (web only) |
| FR-1.8 | Multilingual support (Hindi, regional languages) | P2 | Designed, not implemented |
| FR-1.9 | Voice input support | P2 | Not started |

#### FR-2: External Data Collection (Data Services MCP)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-2.1 | GST verification and data retrieval | P0 | Implemented (mock) |
| FR-2.2 | PAN verification | P0 | Implemented (mock) |
| FR-2.3 | Credit bureau pull (commercial - Experian/CIBIL) | P0 | Implemented (mock) |
| FR-2.4 | Credit bureau pull (consumer - promoter scores) | P0 | Implemented (mock) |
| FR-2.5 | FameScore-style comprehensive report | P0 | Implemented (mock) |
| FR-2.6 | Udyam registration lookup | P1 | Implemented (mock) |
| FR-2.7 | Bank statement parsing | P1 | Not implemented |
| FR-2.8 | ITR data retrieval | P2 | Not implemented |
| FR-2.9 | Real API integrations | P0 | Not started |

#### FR-3: CAM Assembly (Nikita MCP)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-3.1 | Assemble comprehensive CAM from data sources | P0 | Implemented |
| FR-3.2 | Validate required fields populated | P0 | Implemented |
| FR-3.3 | Flag data inconsistencies | P1 | Implemented |
| FR-3.4 | Calculate eligibility metrics | P0 | Implemented |
| FR-3.5 | Generate bank-specific document formats | P1 | Not implemented |
| FR-3.6 | Track missing documents | P1 | Implemented |

#### FR-4: Credit Assessment & Lender Matching (Kesha MCP)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-4.1 | Calculate overall eligibility score | P0 | Implemented |
| FR-4.2 | Match to lender criteria | P0 | Implemented |
| FR-4.3 | Rank lenders by customer preference | P0 | Implemented |
| FR-4.4 | Generate customer-facing report | P0 | Implemented |
| FR-4.5 | Identify improvement opportunities | P1 | Implemented |
| FR-4.6 | PII isolation (anonymized CAM view) | P0 | Implemented |
| FR-4.7 | Commission tracking (internal) | P2 | Designed, not implemented |

#### FR-5: Workflow Orchestration (n8n)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-5.1 | Parallel data collection on GST capture | P0 | Designed |
| FR-5.2 | CAM build trigger on consent capture | P0 | Designed |
| FR-5.3 | Error handling and retry logic | P1 | Designed |
| FR-5.4 | State management for conversation phases | P1 | Partial |
| FR-5.5 | Webhook integration with Francis | P0 | Configured |

#### FR-6: Data Persistence (Supabase)
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-6.1 | Store conversations with message history | P0 | Implemented |
| FR-6.2 | Store consent records with audit trail | P0 | Implemented |
| FR-6.3 | Store CAM records | P0 | Implemented |
| FR-6.4 | Store lender information | P0 | Implemented (5 lenders) |
| FR-6.5 | Anonymized view for Kesha | P0 | Implemented |
| FR-6.6 | Assessment results storage | P1 | Schema ready |

### 3.2 Non-Functional Requirements

#### NFR-1: Performance
| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-1.1 | API response time (p95) | < 2 seconds | Met (local) |
| NFR-1.2 | Conversation response time | < 5 seconds | Met |
| NFR-1.3 | CAM build time | < 60 seconds | Met |
| NFR-1.4 | Concurrent users supported | 10+ | Not tested |

#### NFR-2: Availability
| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-2.1 | Service uptime | 99% | Render free tier (limited) |
| NFR-2.2 | Database availability | 99.9% | Supabase managed |
| NFR-2.3 | Graceful degradation on API failures | Yes | Implemented (fallback) |

#### NFR-3: Security
| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-3.1 | PII isolation | Required | Implemented |
| NFR-3.2 | HTTPS for all endpoints | Required | Implemented (Render) |
| NFR-3.3 | API key protection | Required | Environment variables |
| NFR-3.4 | Consent audit trail | Required | Implemented |
| NFR-3.5 | Data encryption at rest | Required | Supabase default |

#### NFR-4: Compliance
| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-4.1 | DPDP Act 2023 compliance | Required | Partial |
| NFR-4.2 | RBI DSA guidelines | Required | Designed |
| NFR-4.3 | Fair lending practices | Required | Implemented |
| NFR-4.4 | Consent before data collection | Required | Implemented |

---

## 4. System Architecture

### 4.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│   Web Interface  │  WhatsApp (planned)  │  Mobile App (planned) │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION (n8n)                           │
│         Webhooks  │  Parallel Processing  │  State Machine       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Francis MCP  │    │  Nikita MCP   │    │  Kesha MCP    │
│  (Conversation)│    │  (CAM Build)  │    │  (Assessment) │
│  Port 8000    │    │  Port 8002    │    │  Port 8003    │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        │            ┌───────┴───────┐            │
        │            ▼               │            │
        │    ┌───────────────┐       │            │
        │    │ Data Services │       │            │
        │    │  (APIs/Mock)  │       │            │
        │    │  Port 8001    │       │            │
        │    └───────────────┘       │            │
        │                            │            │
        └────────────────────────────┴────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE (Supabase)                        │
│   conversations  │  consents  │  cam_records  │  lenders         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Service Details

| Service | URL | Purpose | Tech Stack |
|---------|-----|---------|------------|
| Francis MCP | https://francis-mcp.onrender.com | Customer conversation, data extraction | FastAPI, Claude AI |
| Data Services MCP | https://data-services-mcp.onrender.com | External API gateway | FastAPI, Mock data |
| Nikita MCP | https://nikita-mcp.onrender.com | CAM assembly, validation | FastAPI |
| Kesha MCP | https://kesha-mcp.onrender.com | Credit assessment, lender matching | FastAPI, Supabase |
| Database | Supabase PostgreSQL | Data persistence | PostgreSQL 15 |
| Orchestration | n8n Cloud/Self-hosted | Workflow automation | n8n |

---

## 5. Data Models

### 5.1 Key Entities

**Conversation**
- conversation_id, customer_id, channel
- message_history, extracted_data, preferences
- current_phase, status, timestamps

**Consent**
- consent_type (credit_bureau, lender_sharing, communication)
- granted, method, timestamp
- audit fields (IP, device, OTP verification)

**CAM Record**
- entity_identity, promoters, business_profile
- financial_summary, credit_profile, compliance_status
- loan_request, customer_preferences, verification_flags

**Lender**
- id, name, type (PSU, private, NBFC, fintech)
- eligibility criteria (min turnover, credit score, etc.)
- products, commission structure, required documents

### 5.2 Sample Lenders Configured

| Lender | Type | Min Turnover | Min Credit Score | Products |
|--------|------|--------------|------------------|----------|
| Bajaj Finserv | NBFC | Rs 50L | 650 | Business Loan, LAP |
| HDFC Bank | Private | Rs 1 Cr | 700 | Working Capital, Term Loan |
| ICICI Bank | Private | Rs 75L | 680 | Business Loan, OD |
| Tata Capital | NBFC | Rs 40L | 625 | MSME Loan, Equipment Finance |
| Lendingkart | Fintech | Rs 25L | 600 | Working Capital, Invoice Discounting |

---

## 6. User Flows

### 6.1 Primary Flow: Loan Application

```
Customer                     Francis                    System
   │                           │                          │
   │──"I need 50L loan"───────▶│                          │
   │                           │──Extract amount──────────▶│
   │◀──"What's your GST?"──────│                          │
   │                           │                          │
   │──"29ABCDE1234F1Z5"───────▶│                          │
   │                           │──Validate & extract──────▶│
   │◀──"What's your PAN?"──────│                          │
   │                           │                          │
   │──"ABCDE1234F"────────────▶│                          │
   │                           │──Validate & extract──────▶│
   │◀──"Consent for credit     │                          │
   │    bureau check?"─────────│                          │
   │                           │                          │
   │──"Yes, I consent"────────▶│                          │
   │                           │──Capture consent─────────▶│
   │                           │──Trigger CAM build───────▶│
   │                           │                          │
   │◀──"Processing your        │◀─────────────────────────│
   │    application..."────────│     [Parallel data       │
   │                           │      collection]         │
   │                           │                          │
   │◀──"You're eligible for    │◀──Assessment complete────│
   │    Rs 48L from 3 lenders" │                          │
   │                           │                          │
```

### 6.2 State Transitions

```
INTAKE → BUILDING → COMPLETE → ASSESSING → ASSESSED → SUBMITTING → SUBMITTED
           ↓                                              ↓
      INCOMPLETE ←─────────────────────────────────→ APPROVED/REJECTED/DISBURSED
```

---

## 7. Success Metrics

### 7.1 Business Metrics
| Metric | Description | Target (MVP) |
|--------|-------------|--------------|
| Conversation completion rate | % of conversations reaching assessment | > 60% |
| CAM completion rate | % of CAMs with all required data | > 80% |
| Time to assessment | Minutes from start to lender matches | < 5 min |
| Lender match rate | % of customers matched to ≥1 lender | > 70% |

### 7.2 Technical Metrics
| Metric | Description | Target |
|--------|-------------|--------|
| API availability | Uptime percentage | > 99% |
| Response time (p95) | 95th percentile latency | < 2s |
| Error rate | % of failed API calls | < 1% |

---

## 8. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Claude API rate limits | Service degradation | Medium | Fallback rule-based extraction |
| External API unavailability | Incomplete CAM | Medium | Mock data, retry logic |
| Render cold starts | Slow response | High (free tier) | Warm-up script, paid tier for prod |
| Data accuracy issues | Wrong assessments | Medium | Cross-validation, flags |
| Regulatory non-compliance | Legal issues | Low | Consent capture, audit trails |

---

## 9. Roadmap

### Phase 1: MVP (Current) - Demo Ready
- [x] Conversational intake with Claude AI
- [x] GST/PAN extraction and validation
- [x] Credit bureau consent capture
- [x] Mock FameScore data integration
- [x] CAM assembly and validation
- [x] Lender matching (5 lenders)
- [x] Customer eligibility report
- [x] Supabase persistence
- [x] Render deployment
- [x] Basic web interface

### Phase 2: Production Ready
- [ ] Real GST API integration
- [ ] Real credit bureau integration (CIBIL/Experian)
- [ ] n8n workflow full implementation
- [ ] WhatsApp channel integration
- [ ] Bank statement parsing
- [ ] Enhanced error handling
- [ ] Load testing and optimization
- [ ] Security audit

### Phase 3: Scale
- [ ] Mobile app (React Native)
- [ ] Multilingual support (Hindi, Tamil, etc.)
- [ ] Voice input processing
- [ ] Additional lenders (20+)
- [ ] Lender API integrations
- [ ] Commission management
- [ ] Analytics dashboard
- [ ] White-label capability

---

## 10. Appendices

### Appendix A: API Endpoints

**Francis MCP (Port 8000)**
- `GET /health` - Health check
- `POST /process-message` - Process customer message

**Data Services MCP (Port 8001)**
- `GET /health` - Health check
- `POST /famescore-report` - Get comprehensive business report
- `POST /verify-gst` - Verify GST number
- `POST /verify-pan` - Verify PAN
- `POST /pull-credit-bureau` - Pull credit report
- `POST /lookup-udyam` - Lookup Udyam registration

**Nikita MCP (Port 8002)**
- `GET /health` - Health check
- `POST /build-cam` - Build CAM from data sources
- `POST /validate-cam` - Validate CAM completeness

**Kesha MCP (Port 8003)**
- `GET /health` - Health check
- `POST /assess` - Assess eligibility and match lenders
- `GET /lenders` - List available lenders

### Appendix B: Environment Variables

```bash
# Francis MCP
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# All Services
PYTHON_VERSION=3.11.0
```

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| CAM | Credit Assessment Memorandum - structured loan application document |
| CIBIL | Credit Information Bureau India Limited |
| DSA | Direct Selling Agent |
| FameScore | Third-party business credit scoring service |
| GSTIN | Goods and Services Tax Identification Number |
| MCP | Model Context Protocol - AI agent server |
| MSME | Micro, Small, and Medium Enterprises |
| NBFC | Non-Banking Financial Company |
| PAN | Permanent Account Number |
| PII | Personally Identifiable Information |

---

*Document maintained by: Product Team*
*Last reviewed: January 2026*
