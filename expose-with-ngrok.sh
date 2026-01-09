#!/bin/bash

# Expose local services to internet using ngrok
# This allows n8n cloud to call your local services

echo "🌐 Exposing local services to internet with ngrok..."
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo ""
    echo "Install it with:"
    echo "  brew install ngrok"
    echo ""
    echo "Then sign up at https://ngrok.com and run:"
    echo "  ngrok config add-authtoken <your-token>"
    exit 1
fi

echo "Starting ngrok tunnels for all services..."
echo ""

# Start ngrok for Francis (8000)
ngrok http 8000 --log=stdout > /tmp/ngrok-francis.log &
sleep 2

# Start ngrok for Data Services (8001)
ngrok http 8001 --log=stdout > /tmp/ngrok-data.log &
sleep 2

# Start ngrok for Nikita (8002)
ngrok http 8002 --log=stdout > /tmp/ngrok-nikita.log &
sleep 2

# Start ngrok for Kesha (8003)
ngrok http 8003 --log=stdout > /tmp/ngrok-kesha.log &
sleep 2

echo "✅ ngrok tunnels started!"
echo ""
echo "🔗 Your public URLs (use these in n8n cloud):"
echo ""
echo "   View all tunnels at: http://localhost:4040"
echo ""
echo "To stop ngrok, run:"
echo "   pkill ngrok"
