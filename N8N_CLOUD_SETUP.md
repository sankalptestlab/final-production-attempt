# n8n Cloud Setup Guide

## Current Situation

- ✅ n8n Cloud: `https://sankalpskitchen.app.n8n.cloud`
- ✅ Services Running: localhost:8000-8003
- ❌ **Problem**: n8n cloud cannot call localhost URLs!

## Solution Options

### Option 1: Deploy Services to Cloud (Recommended for Production)

**Quick Deploy to Railway (15 minutes):**

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login to Railway
railway login

# 3. Deploy Francis MCP
cd services/francis-mcp
railway up
# Note the URL (e.g., https://francis-mcp-production.up.railway.app)

# 4. Deploy Data Services
cd ../data-services-mcp
railway up
# Note the URL

# 5. Deploy Nikita
cd ../nikita-mcp
railway up
# Note the URL

# 6. Deploy Kesha
cd ../kesha-mcp
railway up
# Note the URL
```

**Then update n8n workflow with these URLs.**

---

### Option 2: Use ngrok to Expose Local Services (Testing Only)

**Note:** ngrok free tier only allows 1 endpoint. You need paid plan ($8/month) for 4 tunnels.

```bash
# Install ngrok
brew install ngrok

# Sign up at ngrok.com and get auth token
ngrok config add-authtoken <your-token>

# For paid plan (4 tunnels):
./expose-with-ngrok.sh

# For free tier (1 tunnel at a time) - just test Francis:
ngrok http 8000
# Copy the https URL (e.g., https://abc123.ngrok.io)
```

---

## Step-by-Step: Connect n8n Cloud to Services

### 1. Get n8n Webhook URL

In your n8n cloud workflow:

1. Open: https://sankalpskitchen.app.n8n.cloud/workflow/Zapj8uxxrcscr3Xu
2. Click on the **Webhook node** (first node)
3. Copy the **Production URL**
   - Should look like: `https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger`
   - Or: `https://sankalpskitchen.app.n8n.cloud/webhook-test/cam-build-trigger`

### 2. Update Local .env File

```bash
# Edit .env file
nano .env

# Change this line:
N8N_WEBHOOK_URL=https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger
```

### 3. Update n8n Workflow Nodes

For **EACH HTTP Request node** in n8n workflow, update the URL:

**If using Railway (deployed services):**
- **Call FameScore API**: Change `http://localhost:8001/famescore-report` to `https://data-services-production.up.railway.app/famescore-report`
- **Call Commercial Bureau**: Change `http://localhost:8001/pull-credit-bureau` to `https://data-services-production.up.railway.app/pull-credit-bureau`
- **Call GST Lookup**: Change `http://localhost:8001/lookup-gst-basic` to `https://data-services-production.up.railway.app/lookup-gst-basic`
- **Call Udyam**: Change `http://localhost:8001/lookup-udyam` to `https://data-services-production.up.railway.app/lookup-udyam`
- **Call Nikita**: Change `http://localhost:8002/build-cam` to `https://nikita-production.up.railway.app/build-cam`
- **Call Kesha**: Change `http://localhost:8003/assess` to `https://kesha-production.up.railway.app/assess`
- **Notify Francis**: Change `http://localhost:8000/receive-assessment` to `https://francis-production.up.railway.app/receive-assessment`

**If using ngrok (testing):**
- Use the ngrok URLs (e.g., `https://abc123.ngrok.io`)

### 4. Test the Integration

```bash
# Restart Francis with updated webhook URL
./stop-all-services.sh
./start-all-services.sh

# Test conversation
open web-interface/index.html

# Send a complete message with all required data
# Example: "My GSTIN is 29ABCDE1234F1Z5, PAN is ABCDE1234F, I need 50 lakh loan, I consent to credit check"
```

Francis should trigger the n8n cloud workflow!

---

## Quick Reference

### Current Setup
```
Browser → Francis (localhost:8000) → n8n Cloud → ❌ Can't reach localhost!
```

### Fixed Setup (Railway)
```
Browser → Francis (Railway) → n8n Cloud → All Services (Railway) ✅
```

### Fixed Setup (ngrok)
```
Browser → Francis (localhost) → n8n Cloud → ngrok → localhost ✅
```

---

## Environment Variables Needed

### For Francis MCP (Railway)
```bash
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://eilpavtmwtrkiktkkbks.supabase.co
SUPABASE_KEY=sb_secret_...
N8N_WEBHOOK_URL=https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger
DATA_SERVICES_URL=https://data-services-production.up.railway.app
NIKITA_MCP_URL=https://nikita-production.up.railway.app
KESHA_MCP_URL=https://kesha-production.up.railway.app
```

Set these in Railway dashboard for each service.

---

## Troubleshooting

### n8n workflow fails with "Connection refused"
- Services aren't publicly accessible
- Deploy to Railway or use ngrok

### Webhook not triggering
- Check webhook URL in .env
- Check Francis logs: `tail -f logs/francis.log`
- Verify n8n webhook is "Production" not "Test"

### Services deployed but n8n can't reach them
- Check Railway service URLs are correct
- Verify services are healthy: `curl https://your-service.railway.app/health`
- Check CORS settings allow n8n domain

---

## Cost Estimate

### Railway Deployment
- 4 services × $5/month = **$20/month**
- Or use free tier: 500 hrs/month shared across services

### ngrok Paid Plan
- **$8/month** for 3+ endpoints
- Good for testing, not production

### Recommended
- Deploy to Railway for production
- Use ngrok for quick local testing

---

## Next Steps

**Choose your path:**

**Path A: Production (Railway - 30 min)**
1. Deploy 4 services to Railway (see above)
2. Update n8n workflow with Railway URLs
3. Set environment variables in Railway
4. Test end-to-end

**Path B: Quick Test (ngrok - 5 min)**
1. Install ngrok
2. Expose Francis: `ngrok http 8000`
3. Update n8n workflow Francis URL only
4. Test basic conversation (CAM build won't work)

**Path C: Full Local (n8n Desktop - 10 min)**
1. Install n8n desktop: https://docs.n8n.io/hosting/installation/desktop-app/
2. Import workflow to local n8n
3. Keep all localhost URLs
4. Run everything locally

Which path do you want to take?
