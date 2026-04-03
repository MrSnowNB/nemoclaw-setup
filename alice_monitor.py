import json
import time
import os
import glob
from pathlib import Path

def find_latest_session():
    session_dir = os.environ.get(
        "OPENCLAW_SESSIONS_DIR",
        str(Path.home() / ".nemoclaw" / "sessions"),
    )
    files = glob.glob(os.path.join(session_dir, "*.jsonl"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def monitor_alice(follow=False):
    """
    Reads Alice's session log and prints formatted interactions.
    If follow is true, it tails the file.
    """
    session_file = find_latest_session()
    if not session_file:
        print("❌ No session files found.")
        return

    print(f"📡 [VIGILANCE BRIDGE] Monitoring {session_file}...")
    
    with open(session_file, "r") as f:
        # Initial read of existing history
        lines = f.readlines()
        for line in lines:
            process_line(line)
        
        if follow:
            # Live monitoring mode
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                process_line(line)

def process_line(line):
    try:
        data = json.loads(line)
        if "type" in data and data["type"] == "message":
            role = data.get("role", "unknown").upper()
            content = data.get("content", "")
            timestamp = data.get("timestamp", "")
            
            # Formatting logic
            color = "\033[94m" # Blue for user
            if role == "ASSISTANT":
                color = "\033[95m" # Magenta for Alice
            elif role == "SIGNAL":
                color = "\033[93m" # Yellow for Engineering signals
                
            print(f"{color}[{timestamp}] {role}: {content}\033[0m")
            
        elif "type" in data and data["type"] == "tool_call":
            tool = data.get("tool", "unknown")
            args = data.get("args", {})
            print(f"\033[92m[TOOL_CALL] {tool}({args})\033[0m")
            
        elif "type" in data and data["type"] == "tool_result":
            tool = data.get("tool", "unknown")
            status = data.get("status", "unknown")
            print(f"\033[92m[TOOL_RESULT] {tool} -> {status}\033[0m")
            
    except:
        pass

if __name__ == "__main__":
    import sys
    follow_mode = "--live" in sys.argv
    monitor_alice(follow=follow_mode)
