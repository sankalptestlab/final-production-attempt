# Quick Start with n8n Cloud

## The Problem

Your n8n is on **cloud**: `https://sankalpskitchen.app.n8n.cloud`
Your services are on **localhost**: `http://localhost:8000-8003`

**n8n cloud CANNOT call localhost!** ❌

## The Solution (Pick One)

### Option 1: Deploy to Railway (30 min) - Recommended

**Fastest production deployment:**

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Deploy everything with one command
./deploy-to-railway.sh
```

This will:
- Deploy all 4 services to Railway
- Give you public URLs for each
- Show you exactly what to update in n8n

**Then:** Update n8n workflow HTTP nodes with the Railway URLs.

---

### Option 2: Use ngrok (5 min) - Quick Test

**Test locally with public URLs:**

```bash
# Install ngrok (free tier = 1 endpoint only)
brew install ngrok

# Sign up at ngrok.com, then:
ngrok config add-authtoken <your-token>

# Expose Francis only (for testing)
ngrok http 8000

# Copy the https URL shown (e.g., https://abc123.ngrok-free.app)
```

**Then:** Update Francis URL in n8n workflow.

**Note:** Free ngrok only allows 1 tunnel. Full workflow needs 4 tunnels ($8/month).

---

### Option 3: Use Local n8n (10 min) - Development

**Run everything locally:**

```bash
# Install n8n locally
npm install -g n8n

# Start n8n
n8n start

# Import your workflow
# Go to http://localhost:5678
# Import: n8n-workflows/cam-processing-workflow.json
```

**Then:** Use localhost URLs (already configured).

---

## Step-by-Step: Connect n8n Cloud (Assuming Railway)

### 1. Deploy Services

```bash
./deploy-to-railway.sh
```

You'll get URLs like:
- Francis: `https://francis-mcp-production.up.railway.app`
- Data Services: `https://data-services-production.up.railway.app`
- Nikita: `https://nikita-production.up.railway.app`
- Kesha: `https://kesha-production.up.railway.app`

### 2. Update n8n Workflow

Open: https://sankalpskitchen.app.n8n.cloud/workflow/Zapj8uxxrcscr3Xu

**For EACH HTTP Request node**, change the URL:

| Node Name | Old URL | New URL |
|-----------|---------|---------|
| Call FameScore API | `http://localhost:8001/famescore-report` | `https://data-services-production.up.railway.app/famescore-report` |
| Call Commercial Bureau | `http://localhost:8001/pull-credit-bureau` | `https://data-services-production.up.railway.app/pull-credit-bureau` |
| GST Basic Lookup | `http://localhost:8001/lookup-gst-basic` | `https://data-services-production.up.railway.app/lookup-gst-basic` |
| Udyam Lookup | `http://localhost:8001/lookup-udyam` | `https://data-services-production.up.railway.app/lookup-udyam` |
| Call Nikita - Build CAM | `http://localhost:8002/build-cam` | `https://nikita-production.up.railway.app/build-cam` |
| Call Kesha - Assess | `http://localhost:8003/assess` | `https://kesha-production.up.railway.app/assess` |
| Notify Francis | `http://localhost:8000/receive-assessment` | `https://francis-production.up.railway.app/receive-assessment` |

### 3. Get n8n Webhook URL

In the workflow:
1. Click the **Webhook node** (first node)
2. Copy the **Production URL**
   - Example: `https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger`

### 4. Update Francis Environment

In Railway dashboard → Francis service → Variables:
```
N8N_WEBHOOK_URL=https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger
```

### 5. Test!

```bash
# Open the deployed Francis URL
open https://francis-mcp-production.up.railway.app

# Or test locally pointing to Railway services
# Update local .env:
# N8N_WEBHOOK_URL=https://sankalpskitchen.app.n8n.cloud/webhook/cam-build-trigger
./start-all-services.sh
open web-interface/index.html
```

Send a complete message:
```
"My GSTIN is 29ABCDE1234F1Z5, PAN is ABCDE1234F, I consent to credit bureau check, need 50 lakh for working capital"
```

Check n8n executions to see the workflow run!

---

## What Happens

```
User → Francis (Railway) → n8n Cloud Webhook
                              ↓
                     Parallel API Calls:
                     - Data Services (Railway)
                     - GST Lookup (Railway)
                     - Bureau Check (Railway)
                     - Udyam Lookup (Railway)
                              ↓
                     Nikita (Railway) - Build CAM
                              ↓
                     Kesha (Railway) - Assess & Match
                              ↓
                     Francis (Railway) - Show Results
```

---

## Costs

**Railway Free Tier:**
- 500 hours/month shared
- 4 services × 24/7 = 2,880 hours/month
- **Won't fit in free tier**

**Railway Paid:**
- ~$5/service/month
- 4 services = **$20/month**

**Alternative: Render (also ~$20/month)**

---

## Next Steps

1. **Choose deployment method** (Railway recommended)
2. **Deploy services** (`./deploy-to-railway.sh`)
3. **Update n8n workflow** with new URLs
4. **Set webhook URL** in Francis
5. **Test end-to-end**
6. **Set up Supabase database** (if not done)
7. **Go live!** 🚀

---

## Troubleshooting

**"Connection refused" in n8n:**
- Services not deployed or unhealthy
- Check Railway logs

**Webhook not triggering:**
- Wrong webhook URL in Francis env
- Check Francis logs: Railway → francis-mcp → Logs

**CORS errors:**
- Add n8n domain to CORS allow list
- In main.py: `allow_origins=["https://sankalpskitchen.app.n8n.cloud"]`

---

Ready to deploy? Run:
```bash
./deploy-to-railway.sh
```
