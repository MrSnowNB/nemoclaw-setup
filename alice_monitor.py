import json
import time
import os
from pathlib import Path


def find_latest_session():
    session_dir = os.environ.get(
        "OPENCLAW_SESSIONS_DIR",
        str(Path.home() / ".nemoclaw" / "sessions"),
    )
    files = list(Path(session_dir).rglob("messages.jsonl"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def monitor_alice(follow=False):
    """
    Reads Alice's session log and prints formatted interactions.
    If follow is true, it tails the file.
    """
    session_file = find_latest_session()
    if not session_file:
        print("No session files found.")
        return

    print(f"Monitoring {session_file}...")

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
    line = line.strip()
    if not line:
        return
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return

    role = data.get("role", "")
    content = data.get("content", "")
    timestamp = data.get("timestamp", "")

    if not role:
        return

    # Formatting logic
    role_upper = role.upper()
    color = "\033[94m"  # Blue for user
    if role_upper == "ASSISTANT":
        color = "\033[95m"  # Magenta for assistant
    elif role_upper == "TOOL":
        color = "\033[92m"  # Green for tool
    elif role_upper == "SYSTEM":
        color = "\033[93m"  # Yellow for system

    # Handle tool calls in the entry
    tool_calls = data.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            name = tc.get("name", "unknown")
            args = tc.get("arguments", {})
            print(f"\033[92m[{timestamp}] TOOL_CALL: {name}({args})\033[0m")
    elif data.get("tool_call_id"):
        print(f"\033[92m[{timestamp}] TOOL_RESULT: {content[:200]}\033[0m")
    else:
        print(f"{color}[{timestamp}] {role_upper}: {content}\033[0m")


if __name__ == "__main__":
    import sys
    follow_mode = "--live" in sys.argv
    monitor_alice(follow=follow_mode)
