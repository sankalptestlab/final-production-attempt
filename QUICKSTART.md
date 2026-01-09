# Quick Start Guide

## ✅ Prerequisites Complete
- [x] .env file created with your credentials
- [x] Services updated to load environment variables
- [x] Git initialized with .gitignore

## Next Steps

### 1. Set Up Supabase Database (5 minutes)

**Go to Supabase SQL Editor:**
https://supabase.com/dashboard/project/eilpavtmwtrkiktkkbks/editor/sql

**Copy and run the schema:**
```bash
# Copy the entire file
cat database/schema.sql | pbcopy

# Or open it
open database/schema.sql
```

Paste into Supabase SQL editor and click **Run**.

**Verify tables created:**
- conversations
- cam_records
- assessment_results
- lenders (with 5 pre-populated lenders)
- kesha_cam_view (view for PII isolation)

### 2. Start All Services (30 seconds)

```bash
cd "/Users/sankalpkapur/ClaudeProjects/Final Production Attempt"
./start-all-services.sh
```

Services will start on:
- Francis (Claude AI agent): http://localhost:8000
- Data Services (mock APIs): http://localhost:8001
- Nikita (CAM builder): http://localhost:8002
- Kesha (lender matching): http://localhost:8003

### 3. Test the System

**Open the web interface:**
```bash
open web-interface/index.html
```

**Try a conversation:**
```
You: I need a business loan
Francis: [responds in English or any language you use]

You: My GSTIN is 29ABCDE1234F1Z5
Francis: [extracts GSTIN]

You: PAN is ABCDE1234F
Francis: [asks for consent]

You: Yes I consent
Francis: [asks amount]

You: 50 lakhs for working capital
Francis: [processes and triggers CAM build]
```

### 4. Test Multilingual (Optional)

Try any Indian language:

**Hindi:**
```
मुझे 50 लाख का बिजनेस लोन चाहिए
```

**Tamil:**
```
எனக்கு 50 லட்சம் வணிகக் கடன் வேண்டும்
```

Francis will automatically respond in the same language!

### 5. Check Logs

```bash
# View all logs
ls logs/

# Watch Francis logs
tail -f logs/francis-mcp.log

# Watch all services
tail -f logs/*.log
```

### 6. Stop Services

```bash
./stop-all-services.sh
```

## Common Issues

### Services won't start
- Check if ports 8000-8003 are available: `lsof -i :8000`
- Verify .env file exists and has correct values

### Claude API errors
- Verify ANTHROPIC_API_KEY in .env
- Check quota: https://console.anthropic.com/settings/limits

### Database connection fails
- Verify SUPABASE_URL and SUPABASE_KEY in .env
- Check if schema.sql ran successfully

## Next: Set Up n8n Workflow (Optional)

1. Go to your n8n instance
2. Import `n8n-workflows/cam-processing-workflow.json`
3. Update HTTP request URLs to your service URLs
4. Activate workflow
5. Update N8N_WEBHOOK_URL in .env

## Development

**Hot-reload Francis (update without restart):**
```bash
cd services/francis-mcp
python main_modular.py

# Edit routes/conversation.py - changes apply in ~1s!
```

**Run tests:**
```bash
cd tests
pip install -r requirements.txt
pytest -v
```

## What's Running

Check health endpoints:
```bash
curl http://localhost:8000/health  # Francis
curl http://localhost:8001/health  # Data Services
curl http://localhost:8002/health  # Nikita
curl http://localhost:8003/health  # Kesha
```

All should return:
```json
{"status": "healthy", "service": "...", "timestamp": "..."}
```

---

**You're ready to go! 🚀**

Questions? Check:
- README.md - Full documentation
- MULTILINGUAL.md - Language support
- MODULAR_ARCHITECTURE.md - Code structure
- deployment/README.md - Cloud deployment
