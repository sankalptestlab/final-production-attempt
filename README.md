# MSME Loan Origination System - Production Build

## Overview

Complete production-ready loan origination platform for MSME businesses in India. Features AI-powered agents orchestrated through n8n for parallel data processing and intelligent lender matching.

## Architecture

### 4 MCP Servers + n8n Orchestration

```
┌─────────────────────────────────────────────────┐
│              n8n Orchestration Layer             │
│        (Event-driven workflow engine)            │
└─────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
    │Francis │  │  Data  │  │ Nikita │  │ Kesha  │
    │  MCP   │  │Services│  │  MCP   │  │  MCP   │
    │:8000   │  │MCP:8001│  │ :8002  │  │ :8003  │
    └────────┘  └────────┘  └────────┘  └────────┘
         │           │           │           │
         └───────────┴───────────┴───────────┘
                         │
                    ┌────▼────┐
                    │Supabase │
                    │PostgreSQL│
                    └─────────┘
```

### Agent Responsibilities

1. **Francis (Port 8000)**: Customer-facing conversation agent
   - Intent extraction
   - Consent capture (DPDP & RBI compliant)
   - Qualifying questions
   - Report delivery

2. **Data Services (Port 8001)**: Stateless API gateway
   - GST verification
   - PAN verification
   - Credit bureau pulls (CIBIL/Experian)
   - Udyam lookup
   - FameScore integration (mocked)

3. **Nikita (Port 8002)**: Document & CAM assembly
   - Parallel data orchestration
   - CAM building (Credit Assessment Memorandum)
   - Bank-specific format preparation
   - Data validation & flagging

4. **Kesha (Port 8003)**: Credit intelligence
   - Eligibility calculation
   - Lender matching algorithm
   - Risk assessment
   - Customer report generation

## Project Structure

```
Final Production Attempt/
├── database/
│   └── schema.sql              # Complete PostgreSQL schema
├── services/
│   ├── francis-mcp/
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── data-services-mcp/
│   │   ├── main.py
│   │   ├── mock_data_templates.py
│   │   └── requirements.txt
│   ├── nikita-mcp/
│   │   ├── main.py
│   │   └── requirements.txt
│   └── kesha-mcp/
│       ├── main.py
│       └── requirements.txt
├── web-interface/
│   └── index.html              # Test chat interface
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (Supabase recommended)
- Node.js 18+ (for n8n)
- Anthropic API key (for Francis)

### 1. Database Setup

```bash
# Connect to your Supabase PostgreSQL instance
psql "your-supabase-connection-string"

# Run the schema
\i database/schema.sql
```

This creates:
- 7 core tables (conversations, consents, cam_records, credit_assessments, lender_submissions, lenders, audit_log)
- Views for PII isolation (kesha_cam_view)
- Triggers, functions, and RLS policies
- Seed data for 5 lenders

### 2. Install & Run MCP Servers

Each service runs independently:

```bash
# Terminal 1: Francis
cd services/francis-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python main.py

# Terminal 2: Data Services
cd services/data-services-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Terminal 3: Nikita
cd services/nikita-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Terminal 4: Kesha
cd services/kesha-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 3. Test with Web Interface

```bash
# Open web-interface/index.html in browser
# Or serve with:
cd web-interface
python -m http.server 8080
# Then open http://localhost:8080
```

### 4. Test Flow

Start a conversation:
```
User: Hi, I need a business loan
Francis: Hello! I'm Francis... Could you share your GST number?

User: My GST is 09AADCF8429L1Z4
Francis: Great! I'll also need your PAN...

User: PAN is AADCF8429L
Francis: Perfect! May I proceed with credit bureau check?

User: Yes
Francis: Thank you! How much loan amount?

User: 50 lakhs
Francis: Excellent! Assessing your eligibility...
[System triggers CAM build → Nikita → Kesha → Francis delivers report]
```

## API Documentation

### Francis MCP (:8000)

**POST /process-message**
```json
Request:
{
  "conversation_id": "uuid",
  "customer_id": "uuid",
  "channel": "web",
  "message": "I need 50 lakh loan",
  "current_phase": "intake"
}

Response:
{
  "response_to_customer": "Great! I've noted...",
  "extracted_data": {
    "gst_number": "09AADCF8429L1Z4",
    "loan_amount": 50
  },
  "consents_obtained": [...],
  "action_requested": "trigger_cam_build"
}
```

### Data Services MCP (:8001)

**POST /famescore-report**
```json
Request:
{
  "gstin": "09AADCF8429L1Z4",
  "pan": "AADCF8429L",
  "include_bureau": true
}

Response:
{
  "success": true,
  "data": {
    "entity_information": {...},
    "credit_bureau_commercial": {...},
    "gst_sales_data": {...},
    "bank_limit_eligibility": {...}
  }
}
```

### Nikita MCP (:8002)

**POST /build-cam**
```json
Request:
{
  "conversation_id": "uuid",
  "gst_data": {...},
  "credit_bureau": {...},
  "customer_inputs": {
    "loan_amount_requested": 50,
    "tenure_preference_months": 36
  }
}

Response:
{
  "cam_id": "uuid",
  "cam_status": "complete",
  "cam_data": {...},
  "kesha_ready": true
}
```

### Kesha MCP (:8003)

**POST /assess**
```json
Request: {
  "cam_id": "uuid",
  "business_profile": {...},
  "financial_metrics": {...},
  "credit_profile": {...}
}

Response:
{
  "assessment_id": "uuid",
  "overall_eligibility": "high",
  "max_eligible_amount_lakhs": 48.2,
  "lender_matches": [
    {
      "lender_id": "bajaj_finserv",
      "eligible_amount_lakhs": 45,
      "approval_probability": 0.85,
      "interest_rate_range": "14-18%"
    }
  ]
}
```

## Data Flow

### Complete Loan Application Journey

1. **Customer Message** → Francis extracts GST/PAN + obtains consent
2. **Trigger CAM Build** → n8n orchestrates parallel calls:
   - Data Services: GST verify
   - Data Services: Credit bureau pull
   - Data Services: Udyam lookup
   - (All in parallel)
3. **Merge Data** → n8n sends to Nikita
4. **CAM Assembly** → Nikita builds comprehensive CAM
5. **Credit Assessment** → Kesha receives anonymized CAM (via DB view)
6. **Lender Matching** → Kesha ranks lenders
7. **Report Delivery** → Francis formats and delivers to customer

## Database Schema Highlights

### Key Tables

- **conversations**: Tracks all customer interactions
- **consents**: Audit trail for DPDP compliance
- **cam_records**: Full Credit Assessment Memorandum (JSONB)
- **credit_assessments**: Kesha's eligibility output
- **lender_submissions**: Application tracking to disbursement
- **lenders**: Reference data with criteria & commission
- **audit_log**: Complete system audit trail

### PII Isolation

`kesha_cam_view` - Database view that strips PII before Kesha access:
- No raw GST/PAN
- No entity names
- Only anonymized metrics and scores

## Regulatory Compliance

### DPDP Act 2023
- ✅ Explicit consent before data collection
- ✅ Purpose limitation (loan processing only)
- ✅ Data minimization
- ✅ Audit trail for all consents

### RBI DSA Guidelines
- ✅ No misleading approval guarantees
- ✅ Fair lender presentation
- ✅ Clear fee disclosure
- ✅ Audit logging

### Fair Lending
- ✅ Non-discriminatory criteria
- ✅ Rejection reason transparency
- ✅ All options presented objectively

## Mock Data

All external APIs are mocked based on FameScore PDF:
- `mock_data_templates.py` contains complete mock structures
- Switch to real APIs by replacing endpoints in `data-services-mcp/main.py`

## Lender Configuration

Seeded lenders in database:
1. **Bajaj Finserv** (NBFC): ₹1-80L, 14-18%, 2.5% commission
2. **HDFC Bank**: ₹5-100L, 11-14%, 2.0% commission
3. **ICICI Bank**: ₹5-150L, 11.5-15%, 2.0% commission
4. **UGRO Capital** (NBFC): ₹10-50L, 15-19%, 3.0% commission
5. **Indifi** (Fintech): ₹1-30L, 18-24%, 4.0% commission

## Deployment (Render.com Ready)

Each MCP server can be deployed independently:

```yaml
# render.yaml
services:
  - name: francis-mcp
    type: web
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false

  - name: data-services-mcp
    type: web
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py

  # ... repeat for nikita-mcp and kesha-mcp
```

## n8n Integration

Import workflow (to be created) that:
1. Listens for webhook triggers
2. Orchestrates parallel API calls
3. Manages state transitions
4. Handles error recovery

## Testing

### Manual Testing
Use the web interface at `web-interface/index.html`

### API Testing
```bash
# Test Francis
curl -X POST http://localhost:8000/process-message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test","customer_id":"test","channel":"web","message":"Hi"}'

# Test Data Services
curl -X POST http://localhost:8001/verify-gst \
  -H "Content-Type: application/json" \
  -d '{"gstin":"09AADCF8429L1Z4"}'

# Test complete flow
# See test_flow.md for complete examples
```

## Monitoring

Key metrics to track:
- **Business**: Conversations started, CAM completion rate, approval rate
- **Technical**: API response times, error rates, workflow execution time
- **Compliance**: Consent capture rate, audit log completeness

## Security

- 🔒 Row Level Security (RLS) enabled on sensitive tables
- 🔒 PII isolation via database views
- 🔒 All API calls logged in audit_log
- 🔒 Consent verification before bureau pulls
- 🔒 No PII in error logs (masked)

## Support & Issues

For questions or issues, contact the development team.

## License

Proprietary - All rights reserved
