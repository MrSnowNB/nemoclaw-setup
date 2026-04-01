import sqlite3, uuid, time, ollama, traceback
from pathlib import Path
from typing import List, Tuple, Callable

DB = Path('/home/mr-snow/alice_cyberland/project/data/cyberland.db')

_ALICE_MD_PATH = Path('/home/mr-snow/alice_cyberland/alice/ALICE.md')
_ALICE_PERSONA = _ALICE_MD_PATH.read_text() if _ALICE_MD_PATH.exists() else "You are Alice, a curious and empathetic guide in Cyberland. Give a helpful, direct response."

SYSTEM_PROMPTS = {
    "lore":  "Classify the intent of this input in under 10 words. Output only the classification label.",
    "alice": _ALICE_PERSONA,
    "neo":   "You are Neo, an adversarial reviewer. Find flaws, errors, or risks in this text. Be brief and ruthless. Output only your critique or 'APPROVED' if no issues found.",
    "forge": "You are Forge, a router. Output only the agent name that should handle this: alice, axiom, or iris.",
    "axiom": "You are Axiom. Execute code tasks precisely. Output only results.",
    "iris":  "You are Iris. Analyze visual or structured data. Output only findings."
}

def init():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS hop (
            id INTEGER PRIMARY KEY,
            chain_id TEXT, seq INTEGER,
            agent TEXT, input TEXT, output TEXT, ms INTEGER
        )""")

def hop(agent, model, input_text, chain_id=None, seq=0, history: list = None):
    chain_id = chain_id or str(uuid.uuid4())
    start = time.time()
    
    # Unwrap structured content blocks if list
    if isinstance(input_text, list):
        input_text = next(
            (b.get("text","").split("\n\n")[-1].strip()
             for b in input_text
             if isinstance(b,dict) and b.get("type")=="text"),
            str(input_text)
        )
    
    messages = []
    if agent in SYSTEM_PROMPTS:
        messages.append({"role": "system", "content": SYSTEM_PROMPTS[agent]})
    
    if history:
        history_window = [m for m in history if m['role'] == 'system']
        history_window += [m for m in history if m['role'] != 'system'][-6:]
        messages.extend(history_window)
    
    messages.append({"role": "user", "content": input_text})
    print(f"[DEBUG] Full message payload for {agent}: {messages}", flush=True)
    
    try:
        print(f"[HOP START] {agent} | Model: {model}...", flush=True)
        client = ollama.Client(host="http://127.0.0.1:11434", timeout=300)
        resp = client.chat(
            model=model,
            messages=messages,
            options={"num_predict": 2048, "keep_alive": -1, "think": False}, # Disable thinking for content extraction
        )
        print(f"[DEBUG] Raw response object: {resp}", flush=True)
        out = resp['message']['content'].strip()
        if not out:
            thinking = getattr(resp['message'], 'thinking', None) or ''
            out = thinking[:500].strip() if thinking else ''
            print(f"[HOP WARNING] {agent} returned empty content! thinking_fallback={bool(out)}", flush=True)
            if not out:
                raise ValueError(f"[DEAD HOP] {agent}:{model} returned no content and no thinking. Aborting chain.")
    except Exception as e:
        print(f"[HOP ERROR] {agent} failed: {e}", flush=True)
        traceback.print_exc()
        out = f"[HOP FAILED] {e}"
    
    ms = int((time.time()-start)*1000)
    try:
        with sqlite3.connect(DB) as c:
            c.execute("INSERT INTO hop VALUES (NULL,?,?,?,?,?,?)",
                      (str(chain_id), seq, str(agent), str(input_text), str(out), ms))
    except Exception as db_e:
        print(f"[DB ERROR] Failed to log hop to database: {db_e}")
    return out

def chain(steps: List[Tuple[str,str]], input_text: str, history: list = None) -> str:
    cid = str(uuid.uuid4())
    res = input_text
    for i,(agent,model) in enumerate(steps):
        res = hop(agent, model, res, cid, i, history)
    return res

def score(hops: List[str], metric: Callable) -> str:
    return max(hops, key=metric)

# ── Named flows ────────────────────────────────────────────────
def neo_sandwich(user_input: str, history: list = None) -> str:
    # Fast 2-step path: nemotron critic removed — causes guaranteed VRAM eviction
    # on every request (23GB qwen + 24GB nemotron cannot both stay hot on GPU 0)
    print(f"\n[FAST PATH] 2-stage chain for: {user_input[:50]}...", flush=True)
    return chain([
        ("lore",  "granite4:micro-h"),
        ("alice", "qwen3.5:35b"),
    ], user_input, history)

init()
