#!/bin/bash

echo "STARTING R0.4: WebSocket Server Test"

# Kill any existing uvicorn servers
echo "Killing existing servers..."
pkill -f 'uvicorn.*chat_server' || echo "No existing servers found"

# Start server
echo "Starting server on port 8080..."
python -m uvicorn src.chat_server:app --host 0.0.0.0 --port 8080 > outputs/logs/server_r0_final.log 2>&1 &
SERVER_PID=$!

# Wait for startup
sleep 5

# Test health check
echo "Testing health check..."
if curl -f -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "✅ Server responds to HTTP requests"
else
    echo "❌ Server does not respond to HTTP requests"
    pkill -f 'uvicorn.*chat_server'
    exit 1
fi

# Test for Alice content
echo "Testing for Alice content..."
if curl -s http://localhost:8080/ | grep -q 'Alice'; then
    echo "✅ Homepage contains 'Alice' - PASS"
else
    echo "❌ Homepage does not contain 'Alice' - FAIL"
    curl -s http://localhost:8080/ | head -10 > outputs/logs/homepage_debug.html
    pkill -f 'uvicorn.*chat_server'
    exit 1
fi

# Clean shutdown
echo "Cleaning up test server..."
pkill -f 'uvicorn.*chat_server'

echo "R0.4: WebSocket Server Test - PASSED"
