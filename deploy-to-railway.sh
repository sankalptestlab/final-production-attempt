#!/bin/bash

# Quick deployment script for Railway
# Deploys all 4 services and shows URLs

echo "🚂 Deploying MSME Loan Platform to Railway..."
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not installed."
    echo ""
    echo "Install it with:"
    echo "  npm i -g @railway/cli"
    echo ""
    echo "Then run:"
    echo "  railway login"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway."
    echo ""
    echo "Run: railway login"
    exit 1
fi

echo "✅ Railway CLI ready"
echo ""

# Array to store service URLs
declare -A SERVICE_URLS

# Function to deploy a service
deploy_service() {
    SERVICE_NAME=$1
    SERVICE_DIR=$2
    PORT=$3

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Deploying $SERVICE_NAME..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    cd "$SERVICE_DIR"

    # Create new Railway project for this service
    railway init --name "$SERVICE_NAME"

    # Set environment variables
    railway variables set PORT=$PORT

    if [ "$SERVICE_NAME" = "francis-mcp" ]; then
        echo "Setting Francis environment variables..."
        railway variables set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
        railway variables set SUPABASE_URL="$SUPABASE_URL"
        railway variables set SUPABASE_KEY="$SUPABASE_KEY"
        railway variables set N8N_WEBHOOK_URL="$N8N_WEBHOOK_URL"
    fi

    if [ "$SERVICE_NAME" = "kesha-mcp" ]; then
        echo "Setting Kesha environment variables..."
        railway variables set SUPABASE_URL="$SUPABASE_URL"
        railway variables set SUPABASE_KEY="$SUPABASE_KEY"
    fi

    # Deploy
    echo ""
    echo "Deploying to Railway..."
    railway up

    # Get the URL
    echo ""
    echo "Getting service URL..."
    URL=$(railway domain)

    if [ -z "$URL" ]; then
        echo "⚠️  No domain assigned. Creating one..."
        railway domain
        URL=$(railway domain)
    fi

    SERVICE_URLS[$SERVICE_NAME]="https://$URL"

    echo ""
    echo "✅ $SERVICE_NAME deployed!"
    echo "   URL: https://$URL"
    echo ""

    cd - > /dev/null
}

# Load environment variables from .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Deploy all services
deploy_service "francis-mcp" "services/francis-mcp" 8000
deploy_service "data-services-mcp" "services/data-services-mcp" 8001
deploy_service "nikita-mcp" "services/nikita-mcp" 8002
deploy_service "kesha-mcp" "services/kesha-mcp" 8003

# Display summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ALL SERVICES DEPLOYED!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Copy these URLs to update your n8n workflow:"
echo ""
echo "Francis MCP:        ${SERVICE_URLS[francis-mcp]}"
echo "Data Services MCP:  ${SERVICE_URLS[data-services-mcp]}"
echo "Nikita MCP:         ${SERVICE_URLS[nikita-mcp]}"
echo "Kesha MCP:          ${SERVICE_URLS[kesha-mcp]}"
echo ""
echo "🔗 Update n8n workflow HTTP nodes with these URLs"
echo ""
echo "Example replacements in n8n:"
echo "  http://localhost:8000 → ${SERVICE_URLS[francis-mcp]}"
echo "  http://localhost:8001 → ${SERVICE_URLS[data-services-mcp]}"
echo "  http://localhost:8002 → ${SERVICE_URLS[nikita-mcp]}"
echo "  http://localhost:8003 → ${SERVICE_URLS[kesha-mcp]}"
echo ""
echo "💾 Save these URLs - you'll need them!"
echo ""
