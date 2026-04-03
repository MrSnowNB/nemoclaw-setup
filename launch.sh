#!/bin/bash

# ==========================================
# Alice Cyberland - CLI-ONLY AUTONOMOUS STACK
# ==========================================

# Kill existing
echo "🛑 Cleaning up existing processes..."
pkill -f "uvicorn core.forge_server:app"
# We don't kill gateway here because it's systemd managed

# 1. Start the forge_server (uvicorn)
echo "🚀 Starting forge_server (uvicorn) on port 18080..."
export PYTHONPATH="/home/mr-snow/alice_cyberland"
/home/mr-snow/alice_cyberland/venv_stable/bin/python3 -m uvicorn core.forge_server:app --port 18080 --host 127.0.0.1 > forge_server.log 2>&1 &
UVICORN_PID=$!

echo "✅ Alice stack is initializing..."
echo "Forge (Uvicorn) PID: $UVICORN_PID"

# Wait a few seconds for initialization
sleep 5

lsof -i :18080

echo "------------------------------------------"
echo "Alice is now active."
echo "------------------------------------------"
