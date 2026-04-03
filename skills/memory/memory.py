#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# OpenClaw Workspace paths — resolve from $OPENCLAW_WORKSPACE or ~/.openclaw/workspace
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", Path.home() / ".openclaw" / "workspace"))
USER_FILE = WORKSPACE / "USER.md"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
RECOUNT_FILE = WORKSPACE / "memory/recount.md"

SCHEMA = {
    "name": "memory",
    "description": "Durable long-term memory for Alice. Use this to 'Learn' facts about Mark or update project status. (Claude-style)",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["learn_fact", "recount"],
                "description": "Use 'learn_fact' for specific durable info, 'recount' for session summaries."
            },
            "fact": {
                "type": "string",
                "description": "The fact or information to remember."
            },
            "category": {
                "type": "string",
                "enum": ["personal", "project"],
                "description": "Personal (USER.md) vs Project (MEMORY.md)."
            },
            "summary": {
                "type": "string",
                "description": "For 'recount' action: high-level summary of the session."
            }
        },
        "required": ["action"]
    }
}

def learn_fact(fact, category):
    target = USER_FILE if category == "personal" else MEMORY_FILE
    if not target.exists():
        return f"Error: {target} not found."
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    line = f"\n- [{timestamp}] {fact}\n"
    
    # Simple append to 'Known Facts' or 'History' section
    with open(target, "a") as f:
        f.write(line)
    
    return f"Successfully learned: {fact} (Category: {category})"

def recount_session(summary):
    if not RECOUNT_FILE.parent.exists():
        RECOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### Session Recount: {timestamp}\n{summary}\n---\n"
    
    with open(RECOUNT_FILE, "a") as f:
        f.write(entry)
    
    return "Session recount successfully archived."

if __name__ == "__main__":
    if "--schema" in sys.argv:
        print(json.dumps(SCHEMA))
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--fact")
    parser.add_argument("--category", default="project")
    parser.add_argument("--summary")
    args = parser.parse_args()

    try:
        if args.action == "learn_fact":
            if not args.fact:
                print("Error: 'fact' argument required for 'learn_fact' action.")
                sys.exit(1)
            print(learn_fact(args.fact, args.category))
        elif args.action == "recount":
            if not args.summary:
                print("Error: 'summary' argument required for 'recount' action.")
                sys.exit(1)
            print(recount_session(args.summary))
        else:
            print(f"Unknown action: {args.action}")
            sys.exit(1)
    except Exception as e:
        print(f"Skill error: {e}")
        sys.exit(1)
