# Deployment Guide

## Overview

This directory contains all deployment configurations for the MSME loan origination platform. The platform consists of 4 MCP servers that can be deployed using Docker Compose or individually to cloud services.

## Architecture

```
┌─────────────┐
│   Francis   │  Port 8000 - Customer conversation agent
│     MCP     │  (Claude AI integration)
└──────┬──────┘
       │
       ├─→ Data Services MCP (Port 8001) - External API gateway
       ├─→ Nikita MCP (Port 8002) - CAM assembly
       └─→ Kesha MCP (Port 8003) - Credit intelligence
              │
              └─→ Supabase PostgreSQL
```

## Prerequisites

### Required Services

1. **Supabase Account**
   - Create project at https://supabase.com
   - Run database schema from `/database/schema.sql`
   - Copy project URL and anon key

2. **Anthropic API Key**
   - Sign up at https://console.anthropic.com
   - Create API key for Claude
   - Copy key for environment variables

3. **n8n Instance** (Optional but recommended)
   - Self-hosted: https://docs.n8n.io/hosting/
   - Cloud: https://n8n.io
   - Import workflow from `/n8n-workflows/cam-processing-workflow.json`

### Optional (for production)
4. **External API Partnerships**
   - GST API provider
   - Credit Bureau (Experian, CRIF, Equifax)
   - FameScore or equivalent
   - PAN verification service
   - Udyam registration API

## Quick Start (Local Development)

### 1. Clone and Setup

```bash
cd "Final Production Attempt"
cp deployment/.env.example deployment/.env
# Edit .env with your credentials
```

### 2. Start with Shell Scripts

```bash
./start-all-services.sh
```

Services will be available at:
- Francis: http://localhost:8000
- Data Services: http://localhost:8001
- Nikita: http://localhost:8002
- Kesha: http://localhost:8003

### 3. Test the System

Open `web-interface/index.html` in a browser and start a conversation.

## Docker Deployment

### 1. Build and Run with Docker Compose

```bash
cd deployment
docker-compose up -d
```

### 2. Check Service Health

```bash
docker-compose ps
docker-compose logs -f francis-mcp
```

### 3. Stop Services

```bash
docker-compose down
```

## Cloud Deployment Options

### Option 1: Railway.app (Recommended for MVP)

**Why Railway**: Simple deployment, automatic HTTPS, good free tier

#### Deploy Each Service

1. **Create Railway Project**
   ```bash
   npm i -g @railway/cli
   railway login
   railway init
   ```

2. **Deploy Data Services MCP**
   ```bash
   cd services/data-services-mcp
   railway up
   railway variables set PORT=8001
   ```

3. **Deploy Nikita MCP**
   ```bash
   cd ../nikita-mcp
   railway up
   railway variables set PORT=8002
   railway variables set DATA_SERVICES_URL=https://data-services.railway.app
   ```

4. **Deploy Kesha MCP**
   ```bash
   cd ../kesha-mcp
   railway up
   railway variables set PORT=8003
   railway variables set SUPABASE_URL=<your-url>
   railway variables set SUPABASE_KEY=<your-key>
   ```

5. **Deploy Francis MCP**
   ```bash
   cd ../francis-mcp
   railway up
   railway variables set PORT=8000
   railway variables set ANTHROPIC_API_KEY=<your-key>
   railway variables set DATA_SERVICES_URL=https://data-services.railway.app
   railway variables set NIKITA_MCP_URL=https://nikita.railway.app
   railway variables set KESHA_MCP_URL=https://kesha.railway.app
   railway variables set SUPABASE_URL=<your-url>
   railway variables set SUPABASE_KEY=<your-key>
   ```

### Option 2: Render.com

**Why Render**: Easy setup, good for small teams

1. Create account at https://render.com
2. Connect GitHub repository
3. Create 4 Web Services (one for each MCP server)
4. Set environment variables in Render dashboard
5. Deploy

**Render Configuration** (for each service):
```yaml
# render.yaml example for Francis MCP
services:
  - type: web
    name: francis-mcp
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PORT
        value: 8000
      - key: ANTHROPIC_API_KEY
        sync: false
```

### Option 3: AWS ECS/Fargate

**Why AWS**: Production-grade, scalable, enterprise support

#### Setup Steps

1. **Create ECR Repositories**
   ```bash
   aws ecr create-repository --repository-name francis-mcp
   aws ecr create-repository --repository-name data-services-mcp
   aws ecr create-repository --repository-name nikita-mcp
   aws ecr create-repository --repository-name kesha-mcp
   ```

2. **Build and Push Docker Images**
   ```bash
   cd deployment

   # Francis MCP
   docker build -f Dockerfile.francis -t francis-mcp ../services/francis-mcp
   docker tag francis-mcp:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/francis-mcp:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/francis-mcp:latest

   # Repeat for other services
   ```

3. **Create ECS Cluster**
   ```bash
   aws ecs create-cluster --cluster-name mcp-cluster
   ```

4. **Create Task Definitions**
   - Use JSON files in `/deployment/aws/` (create these)
   - Define CPU/memory requirements
   - Set environment variables

5. **Create Services**
   ```bash
   aws ecs create-service \
     --cluster mcp-cluster \
     --service-name francis-mcp \
     --task-definition francis-mcp:1 \
     --desired-count 2 \
     --launch-type FARGATE
   ```

6. **Setup Application Load Balancer**
   - Create ALB
   - Create target groups for each service
   - Configure health checks to `/health` endpoints

### Option 4: Google Cloud Run

**Why Cloud Run**: Serverless, auto-scaling, pay-per-use

```bash
# Deploy Francis MCP
gcloud run deploy francis-mcp \
  --source ../services/francis-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=<key>,PORT=8000

# Repeat for other services
```

### Option 5: DigitalOcean App Platform

**Why DigitalOcean**: Simple, cost-effective, good for small teams

1. Create account at https://digitalocean.com
2. Create App from GitHub
3. Select repository
4. Configure 4 components (one per MCP)
5. Set environment variables
6. Deploy

## Environment Variables Configuration

### Francis MCP (Port 8000)
```bash
PORT=8000
ANTHROPIC_API_KEY=sk-ant-...
DATA_SERVICES_URL=http://data-services-mcp:8001
NIKITA_MCP_URL=http://nikita-mcp:8002
KESHA_MCP_URL=http://kesha-mcp:8003
N8N_WEBHOOK_URL=https://n8n.yourcompany.com/webhook/cam-build-trigger
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
LOG_LEVEL=INFO
```

### Data Services MCP (Port 8001)
```bash
PORT=8001
LOG_LEVEL=INFO
# Add real API keys when replacing mocks
GST_API_KEY=...
CREDIT_BUREAU_API_KEY=...
FAMESCORE_API_KEY=...
```

### Nikita MCP (Port 8002)
```bash
PORT=8002
DATA_SERVICES_URL=http://data-services-mcp:8001
LOG_LEVEL=INFO
```

### Kesha MCP (Port 8003)
```bash
PORT=8003
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
LOG_LEVEL=INFO
```

## Database Setup

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Create new project
3. Wait for provisioning (~2 minutes)

### 2. Run Schema

1. Go to SQL Editor in Supabase dashboard
2. Copy contents of `/database/schema.sql`
3. Execute
4. Verify tables created:
   - conversations
   - cam_records
   - assessment_results
   - lenders
   - kesha_cam_view (view)

### 3. Configure Row Level Security (RLS)

```sql
-- Enable RLS on sensitive tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cam_records ENABLE ROW LEVEL SECURITY;

-- Create policies (example)
CREATE POLICY "Enable read for authenticated users"
ON conversations FOR SELECT
TO authenticated
USING (true);
```

## n8n Workflow Setup

### 1. Import Workflow

1. Log in to n8n
2. Go to Workflows
3. Click "Import from File"
4. Select `/n8n-workflows/cam-processing-workflow.json`
5. Click Import

### 2. Configure Nodes

Update HTTP Request node URLs:
- Replace `http://localhost:8001` with production URL
- Replace `http://localhost:8002` with production URL
- Replace `http://localhost:8003` with production URL

### 3. Add Supabase Credentials

1. Go to Credentials
2. Add new Supabase credential
3. Enter project URL and service role key
4. Replace function nodes with Supabase nodes

### 4. Activate Workflow

1. Open workflow
2. Click "Activate" toggle
3. Copy webhook URL
4. Set as `N8N_WEBHOOK_URL` in Francis MCP

## Monitoring and Logging

### Health Check Endpoints

All services expose `/health`:
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Centralized Logging (Recommended)

#### Option 1: Supabase Logs
- Built-in logs in Supabase dashboard
- Limited retention on free tier

#### Option 2: Logflare
```bash
# Install Logflare
pip install logflare

# Add to each main.py
import logflare
logflare.setup(api_key="your-key", source_token="your-token")
```

#### Option 3: Sentry
```bash
pip install sentry-sdk

# Add to each main.py
import sentry_sdk
sentry_sdk.init(dsn="your-dsn")
```

### Application Performance Monitoring

#### New Relic
```bash
pip install newrelic

# Run with New Relic
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program python main.py
```

#### Datadog
```bash
pip install ddtrace

# Run with Datadog
ddtrace-run python main.py
```

## Scaling Considerations

### Horizontal Scaling

All MCP servers are stateless and can be scaled horizontally:

```bash
# Docker Compose
docker-compose up -d --scale francis-mcp=3 --scale data-services-mcp=2

# Kubernetes
kubectl scale deployment francis-mcp --replicas=3
```

### Database Connection Pooling

Add to each service using Supabase:
```python
from supabase import create_client, Client

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options={
        'pool_size': 10,
        'pool_recycle': 3600
    }
)
```

### Rate Limiting

Add rate limiting middleware:
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.on_event("startup")
async def startup():
    await FastAPILimiter.init()

@app.post("/process-message", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
```

## Security Checklist

- [ ] Change all default credentials
- [ ] Enable HTTPS/TLS for all services
- [ ] Set up API key rotation
- [ ] Configure CORS properly (not `*` in production)
- [ ] Enable Supabase RLS policies
- [ ] Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Implement request validation
- [ ] Add authentication middleware
- [ ] Enable audit logging
- [ ] Set up security monitoring (Snyk, Dependabot)
- [ ] Configure network security groups/firewalls
- [ ] Implement rate limiting
- [ ] Use service mesh for internal communication (Istio, Linkerd)

## Backup and Disaster Recovery

### Database Backups

Supabase provides automatic daily backups. For additional safety:

```bash
# Manual backup
pg_dump -h db.xxx.supabase.co -U postgres -d postgres > backup.sql

# Restore
psql -h db.xxx.supabase.co -U postgres -d postgres < backup.sql
```

### Application Backups

- Keep code in version control (Git)
- Tag releases: `git tag -a v1.0.0 -m "Production release"`
- Maintain deployment runbooks
- Document configuration changes

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs francis-mcp

# Check environment variables
docker-compose exec francis-mcp env

# Restart service
docker-compose restart francis-mcp
```

### Database Connection Fails

```bash
# Test connection
psql -h db.xxx.supabase.co -U postgres -d postgres

# Check firewall rules
# Verify SUPABASE_URL and SUPABASE_KEY
```

### Claude API Errors (Francis)

- Verify ANTHROPIC_API_KEY is set
- Check API quota at https://console.anthropic.com
- Review rate limits (Claude defaults to tier-based limits)

### Services Can't Communicate

```bash
# Check network
docker network inspect deployment_mcp-network

# Verify service URLs in environment variables
# Use service names (not localhost) in Docker Compose
```

## Cost Estimation (Monthly)

### Development/MVP (Low Traffic)
- **Supabase**: Free tier (500MB, 50K API calls)
- **Railway**: ~$5-10/month per service = $40/month
- **Anthropic Claude API**: ~$50/month (pay-per-use)
- **n8n Cloud**: Free tier or $20/month
- **Total**: ~$110-130/month

### Production (Medium Traffic)
- **Supabase**: Pro tier $25/month
- **Railway**: ~$20/month per service = $160/month
- **Anthropic Claude API**: ~$200/month
- **n8n Cloud**: $50/month
- **Monitoring**: $50/month (Sentry + Datadog)
- **Total**: ~$485/month

### Enterprise (High Traffic)
- **AWS ECS**: ~$500/month (with ALB, RDS, etc.)
- **Anthropic Claude API**: ~$1000/month
- **n8n Self-hosted**: Included in AWS costs
- **Monitoring & Security**: ~$300/month
- **Total**: ~$1800/month

## Support and Maintenance

### Regular Maintenance Tasks

- **Weekly**: Review error logs, check API quotas
- **Monthly**: Update dependencies, security patches
- **Quarterly**: Performance optimization, cost review

### Updating Dependencies

```bash
cd services/francis-mcp
pip install --upgrade anthropic fastapi uvicorn
pip freeze > requirements.txt
# Test thoroughly before deploying
```

### Rolling Updates

```bash
# Zero-downtime deployment
docker-compose up -d --no-deps --build francis-mcp
```

## Production Readiness Checklist

- [ ] All services deployed and accessible
- [ ] Database schema created and tested
- [ ] Environment variables configured
- [ ] n8n workflow imported and activated
- [ ] Health checks passing
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Security hardening completed
- [ ] Load testing performed
- [ ] Documentation updated
- [ ] Team trained on runbooks
- [ ] Incident response plan in place

## Getting Help

- Review logs in Supabase dashboard
- Check service health endpoints
- Review n8n execution logs
- Contact support:
  - Supabase: https://supabase.com/support
  - Anthropic: https://support.anthropic.com
  - Railway: https://railway.app/help
