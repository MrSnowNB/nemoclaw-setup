from fastapi import FastAPI, Request
import ollama, time, uuid

app = FastAPI()
client = ollama.Client(host="http://127.0.0.1:11434", timeout=300)

async def get_out(request):
    body = await request.json()
    msg = body.get("messages", [{"role": "user", "content": "hi"}])[-1]["content"]
    resp = client.chat(model="qwen3.5:35b", messages=[{"role": "user", "content": msg}], options={"num_predict": 1024})
    return resp['message']['content'] or getattr(resp['message'], 'thinking', '')[:500]

@app.post("/v1/chat/completions")
async def chat(request: Request):
    out = await get_out(request)
    return {"id": f"chat-{uuid.uuid4().hex[:8]}", "object": "chat.completion", "created": int(time.time()), 
            "model": "qwen3.5:35b", "choices": [{"index": 0, "message": {"role": "assistant", "content": out}, "finish_reason": "stop"}]}

@app.post("/v1/responses")
async def responses(request: Request):
    out = await get_out(request)
    return {
        "id": f"resp-{uuid.uuid4().hex[:8]}", "object": "response",
        "output": [{"type": "message", "role": "assistant", "content": [{"type": "text", "text": out}]}]
    }
