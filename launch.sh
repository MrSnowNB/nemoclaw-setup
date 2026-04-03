#!/bin/bash

# ==========================================
# Alice Cyberland - CLI-ONLY AUTONOMOUS STACK
# ==========================================

# 1. Start the forge_server (uvicorn)
echo "🚀 Starting forge_server (uvicorn) on port 18080..."
export PYTHONPATH="/home/mr-snow/alice_cyberland"
/home/mr-snow/alice_cyberland/venv_stable/bin/python3 -m uvicorn core.forge_server:app --port 18080 --host 127.0.0.1 &
UVICORN_PID=$!

# 2. Start OpenClaw Gateway
echo "🛰️ Starting OpenClaw Gateway..."
/home/mr-snow/.nemoclaw/source/node_modules/.bin/openclaw gateway --force &
OPENCLAW_PID=$!

echo "✅ Alice CLI stack is initializing..."
echo "Forge (Uvicorn) PID: $UVICORN_PID"
echo "OpenClaw PID: $OPENCLAW_PID"

# Wait a few seconds for initialization
sleep 3

echo "------------------------------------------"
echo "Alice is now active in CLI-ONLY mode."
echo "Use './chat.sh' to interact or './alice_monitor.py --live' to watch logs."
echo "------------------------------------------"

# Cleanup on exit
trap "echo '🛑 Shutting down Alice stack...'; kill $UVICORN_PID $OPENCLAW_PID; exit" SIGINT SIGTERM
wait
