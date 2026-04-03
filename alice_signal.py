import requests
import sys
import json

# Engineering Constants
TOKEN = "8603628145:AAGNlutpIRIHWJG71Y_knrf8CGTGpd8PMzk"
CHAT_ID = "8689455578"

def send_alice_signal(message):
    """
    Sends a direct engineering signal to Alice's Telegram session.
    This bypasses the local Gateway and speaks directly to the agent.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"📡 [ANTIGRAVITY SIGNAL]\n\n{message}",
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    signal_msg = sys.argv[1] if len(sys.argv) > 1 else "Connection established. Verify 'exec' status."
    result = send_alice_signal(signal_msg)
    print(json.dumps(result, indent=2))
