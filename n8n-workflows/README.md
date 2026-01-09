# n8n Workflow Documentation

## Overview

This directory contains n8n workflow JSON files that orchestrate the MCP servers for the MSME loan origination platform.

## Workflow: CAM Processing

**File**: `cam-processing-workflow.json`

### Purpose
Orchestrates the complete CAM (Credit Assessment Memorandum) building and lender matching process with parallel data collection.

### Flow Diagram

```
Francis Webhook Trigger
    ↓
Extract Parameters
    ↓
    ├─→ FameScore API ────┐
    ├─→ Credit Bureau ────┤
    ├─→ GST Lookup ───────┤
    └─→ Udyam Lookup ─────┤
                          ↓
                    Merge All Data
                          ↓
                  Format Nikita Request
                          ↓
                  Call Nikita (Build CAM)
                          ↓
                  Save CAM to Database
                          ↓
                  Call Kesha (Assess & Match)
                          ↓
                  Finalize Assessment
                          ↓
                  Notify Francis → Customer
```

### Webhook Trigger

**URL**: `/trigger-cam-build`
**Method**: POST
**Payload**:
```json
{
  "conversation_id": "uuid",
  "customer_id": "uuid",
  "extracted_data": {
    "gstin": "29ABCDE1234F1Z5",
    "pan": "ABCDE1234F",
    "consent_obtained": true,
    "loan_amount_lakhs": 50,
    "loan_purpose": "Working Capital",
    "tenure_months": 36,
    "collateral_available": true,
    "customer_priority": "low_interest"
  }
}
```

### Parallel Processing (Key Feature)

The workflow executes 4 data collection calls **simultaneously**:
1. FameScore comprehensive report (2-3s)
2. Commercial credit bureau (1-2s)
3. GST basic lookup (0.5s)
4. Udyam registration lookup (0.5s)

This reduces total wait time from ~4-6 seconds (sequential) to ~2-3 seconds (parallel).

### Error Handling

Each HTTP request node has:
- **Timeout**: 30 seconds
- **Retry**: Configured in n8n settings (recommend 2 retries with 5s backoff)
- **Fallback**: Continue on error (graceful degradation)

If FameScore fails but other sources succeed, Nikita will still attempt CAM building with available data.

### Database Integration

**Current**: Function nodes simulate database operations
**Production**: Replace with Supabase nodes:
- `Save CAM to Database` → Use Supabase Insert node for `cam_records` table
- `Save Assessment` → Use Supabase Insert node for `assessment_results` table

## Installation

### 1. Import Workflow

1. Log in to your n8n instance
2. Go to **Workflows** → **Import from File**
3. Select `cam-processing-workflow.json`
4. Click **Import**

### 2. Configure Webhook

1. Open the workflow
2. Click on **Webhook - CAM Build Trigger** node
3. Copy the webhook URL (e.g., `https://your-n8n.com/webhook/cam-build-trigger`)
4. Update Francis MCP to call this URL instead of direct orchestration

### 3. Update Service URLs

If services are deployed remotely, update these node URLs:
- **Call FameScore API**: Change `http://localhost:8001` to production URL
- **Call Commercial Credit Bureau**: Change `http://localhost:8001` to production URL
- **GST Basic Lookup**: Change `http://localhost:8001` to production URL
- **Udyam Lookup**: Change `http://localhost:8001` to production URL
- **Call Nikita**: Change `http://localhost:8002` to production URL
- **Call Kesha**: Change `http://localhost:8003` to production URL
- **Notify Francis**: Change `http://localhost:8000` to production URL

### 4. Add Supabase Credentials

1. In n8n, go to **Credentials** → **Add Credential**
2. Select **Supabase**
3. Enter your Supabase project URL and API key
4. Replace function nodes with Supabase nodes for database operations

### 5. Configure Error Notifications (Optional)

Add error handling branches:
- Send email/Slack notification if critical nodes fail
- Log errors to monitoring service
- Notify Francis to inform customer of processing delay

## Testing

### Local Testing

With all services running locally (`./start-all-services.sh`):

```bash
curl -X POST http://localhost:5678/webhook/cam-build-trigger \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-123",
    "customer_id": "customer-456",
    "extracted_data": {
      "gstin": "29ABCDE1234F1Z5",
      "pan": "ABCDE1234F",
      "consent_obtained": true,
      "loan_amount_lakhs": 50,
      "loan_purpose": "Working Capital",
      "tenure_months": 36,
      "collateral_available": true,
      "customer_priority": "low_interest"
    }
  }'
```

### Monitor Execution

1. Go to **Executions** tab in n8n
2. Watch the workflow run in real-time
3. Click on each node to see input/output data
4. Check for errors in red nodes

## Production Deployment

### Environment Variables

Set these in n8n environment:
- `DATA_SERVICES_URL`: URL for data-services-mcp
- `NIKITA_MCP_URL`: URL for nikita-mcp
- `KESHA_MCP_URL`: URL for kesha-mcp
- `FRANCIS_MCP_URL`: URL for francis-mcp
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase service role key

### Scaling Considerations

- **Parallel Limits**: n8n executes parallel branches concurrently by default
- **Rate Limiting**: Add "Wait" nodes if API providers have rate limits
- **Queue**: Enable n8n's built-in queue mode for high-volume scenarios
- **Monitoring**: Set up n8n's webhook notifications for failed executions

### Security

1. **API Authentication**: Add authentication headers to HTTP request nodes
2. **Webhook Security**: Enable n8n's webhook authentication
3. **Data Privacy**: Ensure PII is not logged in execution data
4. **Network**: Use VPC/private networking for service-to-service calls

## Workflow Metrics

Expected timings (with mock data):
- Webhook trigger → Extract params: <100ms
- Parallel data collection: ~2-3 seconds
- Merge data: <100ms
- Nikita CAM building: ~500ms
- Save to DB: ~200ms
- Kesha assessment: ~300ms
- Finalize + notify: ~200ms

**Total**: ~3-4 seconds from trigger to customer notification

## Troubleshooting

### Workflow Stuck on "Merge All Data Sources"

**Cause**: One of the parallel API calls didn't complete
**Fix**: Check individual HTTP nodes for errors, increase timeout

### "Cannot read property 'json' of undefined"

**Cause**: Data structure mismatch between nodes
**Fix**: Check previous node's output format, update JSONPath expressions

### Database Save Fails

**Cause**: Invalid data structure or missing Supabase credentials
**Fix**: Validate CAM data structure, verify Supabase connection

### Kesha Returns Empty Matches

**Cause**: Customer doesn't meet minimum lender criteria
**Fix**: This is expected behavior - Kesha will return `ineligible` status

## Future Enhancements

1. **Multi-branch Workflows**: Separate workflows for different loan types
2. **Human-in-Loop**: Add approval nodes for high-value loans
3. **Scheduled Re-assessment**: Periodic checks for improved eligibility
4. **A/B Testing**: Split traffic between different lender ranking algorithms
5. **Analytics**: Send execution metrics to data warehouse
