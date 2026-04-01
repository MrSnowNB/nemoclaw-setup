import sqlite3, uuid, time, ollama
from pathlib import Path
from typing import List, Tuple, Callable

DB = Path('/home/mr-snow/alice_cyberland/project/data/cyberland.db')

SYSTEM_PROMPTS = {
    "lore":  "Classify the intent of this input in under 10 words. Output only the classification label.",
    # DEPRECATED 2026-03-31: replaced by ALICE.md injection in forge_server.py
    # "alice": "You are Alice, a curious and empathetic guide. Give a helpful, direct response.",
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
    
    try:
        resp = ollama.chat(
            model=model,
            messages=messages,
            options={"num_predict": 512},
            think=False,
            timeout=120  # 2 minutes — enough for cold model load
        )
        out = resp['message']['content'].strip()
        if not out:
            out = f"[EMPTY OUTPUT - agent:{agent} model:{model}]"
    except Exception as e:
        out = f"[HOP FAILED] {e}"
    
    ms = int((time.time()-start)*1000)
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO hop VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                  (str(chain_id), seq, str(agent), str(input_text), str(out), ms, None, None, None))
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
    return chain([
        ("lore",  "granite4:micro-h"),
        ("alice", "qwen3.5:35b"),
        ("neo",   "nemotron-cascade-2"),
        ("alice", "qwen3.5:35b"),
    ], user_input, history)

init()
