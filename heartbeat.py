#!/usr/bin/env python3
"""
Tool Test Loop Heartbeat Monitor
Status: ACTIVE | Interval: 5 min | Purpose: Prevent loop stall
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

# Configuration
MEMORY_DIR = Path("/home/mr-snow/.openclaw/workspace/memory")
LOG_FILE = MEMORY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
HEARTBEAT_INTERVAL_MINUTES = 5
STALL_THRESHOLD_MINUTES = 5

def log_status(message: str):
    """Append a timestamped status message to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
    line = f"\n## {timestamp} - Heartbeat: {message}\n"
    # Ensure directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line)

def check_progress():
    """Check if the tool test loop is progressing."""
    now = datetime.now()
    if not LOG_FILE.exists():
        log_status("Initializing log file.")
        return
        
    try:
        mtime = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        time_diff = now - mtime
        
        log_status(f"Last activity: {time_diff.total_seconds():.0f}s ago")
        
        if time_diff.total_seconds() > STALL_THRESHOLD_MINUTES * 60:
            # Stall detected
            log_status("⚠️ STALL DETECTED - Loop inactive >5 minutes")
    except Exception as e:
        log_status(f"Error checking progress: {e}")

if __name__ == "__main__":
    print(f"📡 Heartbeat Monitor Started. Targeting {LOG_FILE}")
    while True:
        check_progress()
        time.sleep(HEARTBEAT_INTERVAL_MINUTES * 60)
