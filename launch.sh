#!/bin/bash

# ==========================================
# Alice Cyberland - Full Stack (Polling) - FIXED
# ==========================================

# 1. Start the forge_server (uvicorn)
echo "Starting forge_server (uvicorn)..."
export PYTHONPATH="/home/mr-snow/alice_cyberland/project:/home/mr-snow/alice_cyberland/project/src"
/home/mr-snow/alice_cyberland/project/venv/bin/python3 -m uvicorn src.forge_server:app --port 8080 --host 127.0.0.1 --app-dir /home/mr-snow/alice_cyberland/project &
UVICORN_PID=$!

# 2. Start OpenClaw in polling mode (Gateway)
echo "Starting OpenClaw gateway (Telegram Polling)..."
/home/mr-snow/.nemoclaw/source/node_modules/.bin/openclaw gateway --force &
OPENCLAW_PID=$!

echo "Full stack is initializing..."
echo "Uvicorn PID: $UVICORN_PID"
echo "OpenClaw PID: $OPENCLAW_PID"

# Wait a few seconds for initialization
sleep 5

echo "Alice is now listening in Telegram (Polling Mode)."

# Cleanup on exit
trap "echo 'Shutting down Alice stack...'; kill $UVICORN_PID $OPENCLAW_PID; exit" SIGINT SIGTERM
wait
