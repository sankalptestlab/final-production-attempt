#!/bin/bash

# Startup script for all MCP servers
# Run this to start the entire system locally

echo "🚀 Starting MSME Loan Origination System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "📦 Loading environment variables from .env..."
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  No .env file found. Services may not have credentials.${NC}"
    echo ""
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: ANTHROPIC_API_KEY not set. Francis will use fallback mode.${NC}"
    echo ""
fi

# Function to start a service in background
start_service() {
    SERVICE_NAME=$1
    PORT=$2
    DIR=$3
    LOG_NAME=$4  # Simple name without spaces for log files

    echo -e "${BLUE}Starting $SERVICE_NAME on port $PORT...${NC}"

    cd "$SCRIPT_DIR/$DIR"

    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv venv
    fi

    # Install dependencies using venv's pip directly
    ./venv/bin/pip install -q -r requirements.txt 2>&1 | grep -v "WARNING: You are using pip"

    # Determine which main file to use (use main_modular.py for Francis if available)
    MAIN_FILE="main.py"
    if [ "$LOG_NAME" = "francis" ] && [ -f "main_modular.py" ]; then
        MAIN_FILE="main_modular.py"
    fi

    # Start the service with environment variables using venv's python directly
    nohup ./venv/bin/python $MAIN_FILE > "$SCRIPT_DIR/logs/${LOG_NAME}.log" 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > "$SCRIPT_DIR/logs/${LOG_NAME}.pid"

    echo -e "${GREEN}✓ $SERVICE_NAME started (PID: $SERVICE_PID)${NC}"
    echo ""

    cd "$SCRIPT_DIR"
}

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Start all services
start_service "Francis MCP" 8000 "services/francis-mcp" "francis"
start_service "Data Services MCP" 8001 "services/data-services-mcp" "data-services"
start_service "Nikita MCP" 8002 "services/nikita-mcp" "nikita"
start_service "Kesha MCP" 8003 "services/kesha-mcp" "kesha"

# Wait a bit for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Check if services are running
echo ""
echo "📊 Service Status:"
echo ""

check_service() {
    NAME=$1
    PORT=$2

    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $NAME: http://localhost:$PORT (healthy)"
    else
        echo -e "❌ $NAME: http://localhost:$PORT (not responding)"
        echo "   Check logs/$3.log for errors"
    fi
}

check_service "Francis MCP     " 8000 "francis"
check_service "Data Services   " 8001 "data-services"
check_service "Nikita MCP      " 8002 "nikita"
check_service "Kesha MCP       " 8003 "kesha"

echo ""
echo "🌐 Web Interface: Open web-interface/index.html in your browser"
echo ""
echo "📝 View logs:"
echo "   tail -f logs/francis.log"
echo "   tail -f logs/data-services.log"
echo ""
echo "To stop all services, run: ./stop-all-services.sh"
echo ""
echo "✅ System ready!"
