import os
import time
import json
import asyncio
import websockets
from pathlib import Path

# Neural-Spatial Bridge for Alice_3D
# Acts as the "Nervous System" relay between terminal logs and the 3D frontend

SESSION_DIR = Path("/home/mr-snow/.openclaw/agents/main/sessions/")
BRIDGE_PORT = 8765

async def get_latest_session():
    """Finds the most recently modified .jsonl session file."""
    files = list(SESSION_DIR.glob("*.jsonl"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

async def tail_session(websocket):
    """Tails the session log and pushes state updates to the 3D core."""
    current_session = await get_latest_session()
    if not current_session:
        print("❌ No active sessions found. Waiting...")
        return

    print(f"🔗 Linked to Neural Path: {current_session.name}")
    
    with open(current_session, "r") as f:
        # Go to the end of the file
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)
                continue
            
            try:
                data = json.loads(line)
                
                # Check for Alice's messages
                if data.get("type") == "message" and data["message"]["role"] == "assistant":
                    content = data["message"]["content"]
                    
                    # Extract the text from the content list/string
                    text = ""
                    if isinstance(content, list):
                        for part in content:
                            if part.get("type") == "text":
                                text += part["text"]
                    else:
                        text = content

                    # Look for the Emotion Vector JSON block
                    # Format: {"emotions": {...}}
                    if "{\"emotions\":" in text:
                        try:
                            # Simple extraction of the first JSON block found
                            start = text.find("{\"emotions\":")
                            end = text.find("}", start) + 1
                            # Handle nested objects if necessary but Alice's vector is flat
                            emotion_json = text[start:text.find("}}", start) + 2]
                            emotions = json.loads(emotion_json)
                            
                            # Broadcast the emotion vector to the 3D frontend
                            print(f"🧠 Pulse: {emotions}")
                            await websocket.send(json.dumps({
                                "type": "emotion_update",
                                "data": emotions["emotions"]
                            }))
                        except Exception as e:
                            print(f"⚠️ Failed to parse emotion vector: {e}")

                # Check for tool execution (Visual Pulse)
                if data.get("type") == "custom" and data.get("customType") == "openclaw:tool-call":
                    print("⚡ Analytical Pulse: Tool Execution")
                    await websocket.send(json.dumps({
                        "type": "activity_pulse",
                        "data": {"level": 0.9, "reason": "tool_execution"}
                    }))

            except Exception as e:
                pass

async def bridge_server(websocket, path):
    print(f"✅ Connection established from Neural Frontend")
    try:
        await tail_session(websocket)
    except websockets.ConnectionClosed:
        print("❌ Connection lost from Neural Frontend")

if __name__ == "__main__":
    print(f"🚀 Alice Neural-Spatial Bridge online on port {BRIDGE_PORT}")
    start_server = websockets.serve(bridge_server, "localhost", BRIDGE_PORT)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
