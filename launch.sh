#!/bin/bash
# Alice Cyberland - Master Orchestrator

echo "🛑 Total system clear..."
pkill -9 -f nemoclaw
pkill -9 -f uvicorn
pkill -9 -f telegram_cli.py
# Stop any user-level services if they exist
systemctl --user stop openclaw-gateway.service 2>/dev/null

# Clean logs
echo "🧹 Cleaning logs..."
> forge_server.log
> nemoclaw_bot.log

export PYTHONPATH="/home/mr-snow/alice_cyberland"
VENV="/home/mr-snow/alice_cyberland/venv_stable/bin/python3"

# 1. Start Forge Server (Proxy)
echo "🚀 Starting forge_server..."
$VENV -m uvicorn core.forge_server:app --port 18080 --host 127.0.0.1 > forge_server.log 2>&1 &
FORGE_PID=$!
sleep 3

# 2. Start NemoClaw Bot with Persona & Agency
# We use alice/ALICE.md as the verified persona path.
echo "🤖 Starting Alice (nemoclaw)..."
$VENV -m nemoclaw \
  --transport telegram \
  --persona /home/mr-snow/alice_cyberland/alice/ALICE.md \
  --config /home/mr-snow/.openclaw/openclaw.json \
  > nemoclaw_bot.log 2>&1 &
BOT_PID=$!

echo "✅ Stack initialized."
echo "Forge PID: $FORGE_PID | Bot PID: $BOT_PID"
echo "Monitoring logs for conflicts..."
sleep 5
tail -n 10 nemoclaw_bot.log
