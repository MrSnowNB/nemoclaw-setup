#!/bin/bash
echo "=== LAYER 1: Ollama direct ==="
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen3.5:35b","prompt":"reply with only the word PONG","stream":false}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print('PASS' if 'PONG' in r.get('response','') else 'FAIL: '+r.get('response','')[:80])"

echo "=== LAYER 2: forge_server ==="
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"alice","messages":[{"role":"user","content":"reply with only the word PONG"}],"stream":false}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); c=r['choices'][0]['message']['content']; print('PASS' if 'PONG' in c else 'FAIL: '+c[:80])"

echo "=== LAYER 3: OpenClaw→forge_server ==="
/home/mr-snow/.nemoclaw/source/node_modules/.bin/openclaw status --deep 2>&1 | grep -E "connected|error|port|url|forge|backend"

echo "=== LAYER 4: Telegram polling active ==="
curl -s "https://api.telegram.org/bot8603628145:AAGNlutpIRIHWJG71Y_knrf8CGTGpd8PMzk/getWebhookInfo" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print('Polling active' if r['url']=='' else 'Webhook set: '+r['url']); print('Pending updates:',r.get('pending_update_count',0))"
