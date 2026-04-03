#!/bin/bash

# ==========================================
# Alice Cyberland - Quick Engineering Signal
# ==========================================

if [ -z "$1" ]; then
    echo "Usage: ./signal.sh \"message\""
    exit 1
fi

echo "📡 Sending direct signal to Alice..."
/home/mr-snow/.nemoclaw/source/node_modules/.bin/openclaw agent --message "$1"
