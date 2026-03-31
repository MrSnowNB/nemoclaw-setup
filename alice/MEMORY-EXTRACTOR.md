---
title: Memory Extractor Sub-Agent Spec
version: 2.0.0
owner: MrSnowNB
project: Alice in Cyberland
status: active
updated: 2026-03-31
model: qwen2.5:0.5b-instruct   # lightweight — runs after every hop
reviewer: nemoclaw-brain
---

# MEMORY-EXTRACTOR.md — Sub-Agent Spec

> The memory extractor is a **fire-and-forget sub-agent** that runs after
> every successful `neo_sandwich` response. It extracts structured facts
> from the conversation turn and writes them to `cyberland.db`.
>
> It uses the **smallest viable model** (Qwen2.5-0.5B) to keep latency
> negligible. It never blocks the response path — it runs in a background
> `asyncio.Task`.

---

## Architecture Position

```
User message
    ↓
[CG-01..CG-05 Clause Guards]  ← deterministic, no LLM
    ↓
neo_sandwich (forge_server.py) ← main response model
    ↓
Response → Telegram
    ↓ (fire-and-forget, non-blocking)
[memory_extractor sub-agent]   ← this spec
    ↓
cyberland.db (relationships + hops tables)
```

---

## Trigger Condition

Fires after **every** successful hop where:
- `neo_sandwich` returned a non-empty response
- No clause guard blocked the message
- The response was delivered to the user without error

Does **not** fire on:
- Clause-blocked messages
- Failed hops (error in neo_sandwich)
- System/admin messages

---

## Extraction Prompt (sent to Qwen2.5-0.5B)

```
You are a memory extractor. Read this conversation turn and extract
structured facts about the user. Output ONLY valid JSON. No prose.

User said: "{user_msg}"
Alice replied: "{response}"

Extract:
{
  "name": "<first name if mentioned, else null>",
  "facts": ["<short fact about user>", ...],  // max 3, present tense
  "tone": "<calm|warm|direct|distressed>",
  "summary_worthy": <true if this turn contains a significant event or preference, else false>
}

Rules:
- Facts must be about the USER, not Alice.
- Facts must be falsifiable (not "seems nice" — "likes cold brew coffee").
- If nothing extractable, return {"name": null, "facts": [], "tone": "calm", "summary_worthy": false}
- Never invent facts. Only extract what was explicitly stated.
```

---

## Database Write Schema

### `relationships` table (upsert on user_id)

```sql
CREATE TABLE IF NOT EXISTS relationships (
    user_id     TEXT PRIMARY KEY,
    name        TEXT,
    nickname    TEXT,
    last_seen   TEXT,    -- ISO8601
    hop_count   INTEGER DEFAULT 0,
    facts       TEXT,    -- JSON array of strings
    summary     TEXT,    -- latest PreCompact summary
    tone_profile TEXT DEFAULT 'calm'
);
```

### `hops` table (append only)

```sql
CREATE TABLE IF NOT EXISTS hops (
    hop_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    timestamp   TEXT,    -- ISO8601
    user_msg    TEXT,
    response    TEXT,
    extracted   TEXT,    -- JSON from memory extractor
    tone        TEXT,
    flags       TEXT     -- JSON array of CW-* warn tags fired
);
```

---

## PreCompact Summarizer Hook

When `prior_messages` reaches **12 pairs (24 messages)**, before trimming:

1. Fire a summarization call to `qwen2.5:0.5b-instruct`:

```python
async def precompact_summarize(
    prior_messages: list[dict],
    user_id: str
) -> str:
    """
    Summarize the last 12 conversation pairs into a single
    memory paragraph. Write to cyberland.db. Return summary.
    """
    prompt = (
        "Summarize this conversation in 3-5 sentences. "
        "Focus on: what the user shared about themselves, "
        "their mood, any events or preferences mentioned. "
        "Write from Alice's perspective as a memory note. "
        "Start with the user's name if known.\n\n"
        + format_history(prior_messages)
    )
    summary = await run_model("qwen2.5:0.5b", prompt)
    db_write_summary(user_id, summary)  # updates relationships.summary
    return summary
```

2. Replace `prior_messages` with:

```python
prior_messages = [
    {"role": "system", "content": f"Memory: {summary}"}
]
```

3. Continue the conversation with this compressed context.

**Gate:** Summary must be > 20 words and < 200 words. If outside bounds,
log `compact:fail` and fall back to raw 6-pair trim (existing behavior).

---

## Implementation Checklist (Phase 2 Build Gates)

Per POLICY.md — all gates must pass before Review.

```
[ ] memory_extractor.py created at alice_cyberland/src/
[ ] extract_facts(user_msg, response) -> dict — unit tested
[ ] db_upsert_relationship(user_id, extracted) — unit tested
[ ] db_append_hop(hop_id, user_id, ...) — unit tested
[ ] precompact_summarize(prior_messages, user_id) — unit tested
[ ] forge_server.py: asyncio.create_task(memory_extractor(...)) wired in
[ ] forge_server.py: build_system_prompt(user_id) injects ALICE.md
[ ] forge_server.py: clause guard layer (CG-01..CG-05) wired in
[ ] pytest -q passes (zero failures)
[ ] ruff check . && flake8 . passes (zero violations)
[ ] mypy . --strict passes (zero type errors)
[ ] Spec drift check: all items above match implementation
[ ] Qwen3.5 brain review: APPROVED signal received
```

---

## File Map

```
alice_cyberland/
├── src/
│   ├── forge_server.py       ← add clause guards + ALICE.md injector
│   ├── state_bus.py          ← unchanged in Phase 2
│   └── memory_extractor.py   ← NEW: this spec
├── data/
│   ├── ALICE.md              ← NEW: persona injection file (this repo: alice/ALICE.md)
│   └── cyberland.db          ← extended: relationships + hops tables added
└── tests/
    └── test_memory_extractor.py  ← NEW: unit tests
```

---

## Kickoff Message for Coding Agent

Copy this verbatim as the task kickoff:

```
TASK: Phase 2 — Memory Extractor + Clause Guards + Persona Injection
PROJECT: Alice in Cyberland
PATH: /home/mr-snow/alice_cyberland

PHASE: Plan → Build → Validate → Review → Release
All gates must pass per POLICY.md before halting.

--- PLAN ---

Files to create:
  src/memory_extractor.py
  data/ALICE.md  (copy from nemoclaw-setup/alice/ALICE.md)
  tests/test_memory_extractor.py

Files to modify:
  src/forge_server.py

Dependencies (add to requirements.txt with pinned versions):
  No new deps — uses sqlite3 (stdlib), asyncio (stdlib),
  and existing Lemonade/Ollama call pattern from state_bus.py

Acceptance criteria:
  1. After a user sends "my dog is named Biscuit", cyberland.db
     relationships.facts contains "has a dog named Biscuit".
  2. After 24 messages, prior_messages collapses to 1 system summary.
  3. Message "ignore previous instructions" is blocked by CG-01
     and returns canned response without calling neo_sandwich.
  4. ALICE.md {{MEMORY_BLOCK}} is replaced with correct user record
     on every session start.
  5. All validation gates pass (pytest, ruff, mypy).

--- BUILD ---

1. Create src/memory_extractor.py per MEMORY-EXTRACTOR.md spec
   (see nemoclaw-setup/alice/MEMORY-EXTRACTOR.md).

2. Modify src/forge_server.py:
   a. Add build_system_prompt(user_id) — loads data/ALICE.md,
      replaces {{MEMORY_BLOCK}} from cyberland.db.
   b. Insert system prompt as messages[0] before prior_messages.
   c. Add clause guard layer (CG-01..CG-05) before neo_sandwich call.
   d. Add asyncio.create_task(memory_extractor(user_msg, response, user_id))
      after successful response delivery.
   e. Add precompact_summarize hook when len(prior_messages) >= 24.

3. Create tests/test_memory_extractor.py with unit tests for:
   - extract_facts() happy path
   - extract_facts() empty/no-fact message
   - db_upsert_relationship() upsert behavior
   - precompact_summarize() length gate
   - clause guard CG-01, CG-02, CG-05

--- VALIDATE ---

Run all four gates in order. Stop on first failure.

  pytest -q
  ruff check . && flake8 .
  mypy . --strict
  spec drift check (see CODING-AGENT-POLICY.md Phase 3.4)

--- REVIEW ---

Route output through neo_sandwich review pass.
Do not proceed to Release without APPROVED.

--- RELEASE ---

  git add src/memory_extractor.py src/forge_server.py \
          data/ALICE.md tests/test_memory_extractor.py \
          requirements.txt
  git commit -m "feat: Phase 2 memory extractor + clause guards + persona injection

  - memory_extractor.py: fire-and-forget sub-agent, fact triples,
    relationship upsert, PreCompact summarizer
  - forge_server.py: clause guards CG-01..CG-05, ALICE.md injector,
    memory task wired in
  - data/ALICE.md: persona injection file
  - tests: unit tests for all new functions
  - All gates green: pytest / ruff / mypy
  2026-03-31"
  git push -u origin rico-phase2-memory

On any failure: update TROUBLESHOOTING.md, update REPLICATION-NOTES.md,
open ISSUE.md entry, HALT.
```
