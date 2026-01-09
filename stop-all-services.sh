#!/bin/bash

# Shutdown script for all MCP servers

echo "🛑 Stopping MSME Loan Origination System..."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Function to stop a service
stop_service() {
    SERVICE_NAME=$1
    LOG_NAME=$2
    PID_FILE="$SCRIPT_DIR/logs/${LOG_NAME}.pid"

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo -e "${GREEN}✓${NC} Stopped $SERVICE_NAME (PID: $PID)"
            rm "$PID_FILE"
        else
            echo -e "${RED}⚠${NC} $SERVICE_NAME not running (stale PID file removed)"
            rm "$PID_FILE"
        fi
    else
        echo -e "${RED}⚠${NC} $SERVICE_NAME PID file not found"
    fi
}

# Stop all services
stop_service "Francis MCP" "francis"
stop_service "Data Services MCP" "data-services"
stop_service "Nikita MCP" "nikita"
stop_service "Kesha MCP" "kesha"

# Kill any remaining python processes on these ports (backup)
echo ""
echo "🔍 Checking for orphaned processes..."

for port in 8000 8001 8002 8003; do
    PID=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill $PID 2>/dev/null
        echo -e "${GREEN}✓${NC} Killed process on port $port (PID: $PID)"
    fi
done

echo ""
echo "✅ All services stopped!"
