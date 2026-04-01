#!/usr/bin/env python3
"""
Simplified WebSocket test for Alice in Cyberland
"""

import asyncio
import websockets

async def test_connection():
    try:
        uri = "ws://localhost:8080/ws/chat"
        print(f"Connecting to {uri}...")

        async with websockets.connect(uri) as websocket:
            print("✅ Successfully connected!")
            # Just connecting is success
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("🎉 R3.2: WebSocket connectivity - PASSED")
    else:
        print("💥 R3.2: WebSocket connectivity - FAILED")
