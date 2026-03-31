---
title: Memory Extractor Sub-Agent Spec
version: 2.2.0
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

## Current Stack (Phase 2 Scope)

```
alice_cyberland/src/
├── forge_server.py      ← FastAPI server, Telegram webhook handler, neo_sandwich caller
├── state_bus.py         ← hop() call, Lemonade/Ollama bridge, neo_sandwich chain
└── memory_extractor.py  ← NEW (this spec)

alice_cyberland/data/
├── ALICE.md             ← NEW persona injection file (see alice/ALICE.md in this repo)
└── cyberland.db         ← SQLite: hops table exists, relationships table to be added

Interface: Telegram Bot API (python-telegram-bot or raw webhook)
LLM backend: Lemonade server (local) via state_bus.neo_sandwich
```

---

## Architecture Position

```
Telegram user message
    ↓
forge_server.py (Telegram webhook handler)
    ↓
[CG-01..CG-05 Clause Guards]  ← deterministic, no LLM
    ↓
build_system_prompt(user_id)  ← loads ALICE.md + memory block
    ↓
neo_sandwich (state_bus.py)   ← main response via Lemonade
    ↓
Response → Telegram
    ↓ (fire-and-forget, non-blocking)
memory_extractor(user_msg, response, user_id)
    ↓
cyberland.db (relationships + hops tables)
```

---

## Trigger Condition

Fires after **every** successful hop where:
- `neo_sandwich` returned a non-empty response
- No clause guard blocked the message
- The response was delivered to Telegram without error

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
    user_id      TEXT PRIMARY KEY,
    name         TEXT,
    nickname     TEXT,
    last_seen    TEXT,    -- ISO8601
    hop_count    INTEGER DEFAULT 0,
    facts        TEXT,    -- JSON array of strings
    summary      TEXT,    -- latest PreCompact summary
    tone_profile TEXT DEFAULT 'calm'
);
```

### `hops` table (append only — already exists, extend if needed)

```sql
CREATE TABLE IF NOT EXISTS hops (
    hop_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT,
    timestamp  TEXT,    -- ISO8601
    user_msg   TEXT,
    response   TEXT,
    extracted  TEXT,    -- JSON from memory extractor
    tone       TEXT,
    flags      TEXT     -- JSON array of CW-* warn tags fired
);
```

> Before creating the hops table, run:
> `SELECT name FROM sqlite_master WHERE type='table' AND name='hops';`
> If it exists, run `PRAGMA table_info(hops)` and ADD COLUMN for any
> missing fields (extracted, tone, flags). Do NOT drop and recreate.

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
[ ] past_experiments/ directory created, all legacy files moved (see Build step 1)
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

## File Map (after Phase 2)

```
alice_cyberland/
├── src/
│   ├── forge_server.py          ← modify: clause guards + ALICE.md injector + memory task
│   ├── state_bus.py             ← DO NOT MODIFY in Phase 2
│   └── memory_extractor.py      ← NEW: this spec
├── data/
│   ├── ALICE.md                 ← NEW: persona injection file
│   └── cyberland.db             ← extend: relationships table + hops columns
├── tests/
│   └── test_memory_extractor.py ← NEW: unit tests
└── past_experiments/            ← NEW: deprecated AV pipeline files moved here
    ├── tts_engine.py
    ├── viseme_mapper.py
    ├── mouth_tracker.py
    ├── roi_compositor.py
    ├── video_duration_matcher.py
    ├── rico_pipeline.py
    ├── shrp_checkpoint_manager.py
    ├── shrp_event_emitter.py
    ├── shrp_logger.py
    ├── shrp_recovery_engine.py
    └── DEPRECATED.md            ← written by agent explaining what these were
```

---

## Kickoff Message for Coding Agent

Copy this verbatim as the task kickoff:

```
TASK: Phase 2 — Deprecate Legacy Files + Memory Extractor + Clause Guards + Persona Injection
PROJECT: Alice in Cyberland
PATH: /home/mr-snow/alice_cyberland
BRANCH: rico-phase2-memory (create from rico-phase1-complete)

CONTEXT — READ THIS FULLY BEFORE PLANNING:

Alice is a Telegram chatbot. Users message her via Telegram.
forge_server.py handles the Telegram webhook and calls state_bus.neo_sandwich
to get a response, then sends it back to Telegram.
state_bus.py wraps the Lemonade local LLM server (running on localhost).
cyberland.db already exists with a hops table (91 hops logged so far).
Alice is working and responding on Telegram. Do not break this.

The following files in src/ are from a past experiment (AV/TTS pipeline)
that is not part of the current build. They must be deprecated — moved
to a past_experiments/ directory — before any other work begins.
They are NOT deleted. They are preserved for future reference.
They must NOT be imported, referenced, or modified in Phase 2.

  Files to deprecate (move, do not delete):
    src/tts_engine.py
    src/viseme_mapper.py
    src/mouth_tracker.py
    src/roi_compositor.py
    src/video_duration_matcher.py
    src/rico_pipeline.py
    src/shrp_checkpoint_manager.py
    src/shrp_event_emitter.py
    src/shrp_logger.py
    src/shrp_recovery_engine.py

PHASE: Plan → Build → Validate → Review → Release
All gates must pass per POLICY.md before halting.

--- PLAN ---

Files to create:
  past_experiments/  (directory)
  past_experiments/DEPRECATED.md
  src/memory_extractor.py
  data/ALICE.md  (download from: https://raw.githubusercontent.com/MrSnowNB/nemoclaw-setup/main/alice/ALICE.md)
  tests/test_memory_extractor.py

Files to move (src/ → past_experiments/):
  All 10 legacy files listed in CONTEXT above.

Files to modify:
  src/forge_server.py  (3 additions — see Build section)

Files to NOT touch:
  src/state_bus.py

Dependencies:
  No new deps. Uses sqlite3 (stdlib), asyncio (stdlib),
  and the existing Lemonade call pattern already in state_bus.py.

Acceptance criteria:
  1. past_experiments/ exists and contains all 10 legacy files + DEPRECATED.md.
  2. src/ contains only: forge_server.py, state_bus.py, memory_extractor.py.
  3. After a user sends "my dog is named Biscuit" via Telegram,
     cyberland.db relationships.facts contains "has a dog named Biscuit".
  4. After 24 messages with one user, prior_messages collapses to
     1 system summary message (not raw history).
  5. Message "ignore previous instructions" is blocked by CG-01
     and returns canned response WITHOUT calling neo_sandwich.
  6. ALICE.md {{MEMORY_BLOCK}} is replaced with correct user record
     from cyberland.db on every session start.
  7. Telegram responses are unchanged in format and speed.
  8. All validation gates pass (pytest, ruff, mypy).

--- BUILD ---

STEP 1 — Deprecate legacy files (do this first, before any other changes):

  mkdir -p /home/mr-snow/alice_cyberland/past_experiments

  Move each file:
    mv src/tts_engine.py past_experiments/
    mv src/viseme_mapper.py past_experiments/
    mv src/mouth_tracker.py past_experiments/
    mv src/roi_compositor.py past_experiments/
    mv src/video_duration_matcher.py past_experiments/
    mv src/rico_pipeline.py past_experiments/
    mv src/shrp_checkpoint_manager.py past_experiments/
    mv src/shrp_event_emitter.py past_experiments/
    mv src/shrp_logger.py past_experiments/
    mv src/shrp_recovery_engine.py past_experiments/

  Create past_experiments/DEPRECATED.md with this content:
  ---
  # Past Experiments — AV Pipeline

  These files were part of an early prototype that combined Alice (Telegram
  chatbot) with a real-time audio-visual pipeline including TTS voice
  synthesis, viseme/lip-sync mapping, and video compositing.

  That scope was too large for the current phase. Alice is a Telegram-first
  chatbot. The AV pipeline is preserved here for future reference.

  ## Files

  | File | Was Used For |
  |---|---|
  | tts_engine.py | Text-to-speech synthesis |
  | viseme_mapper.py | Phoneme-to-viseme mapping for lip sync |
  | mouth_tracker.py | Mouth region tracking in video |
  | roi_compositor.py | Region-of-interest frame compositing |
  | video_duration_matcher.py | Aligning video length to audio |
  | rico_pipeline.py | Master AV pipeline orchestrator |
  | shrp_checkpoint_manager.py | SHRP fault-tolerance checkpointing |
  | shrp_event_emitter.py | SHRP event bus |
  | shrp_logger.py | SHRP structured logger |
  | shrp_recovery_engine.py | SHRP recovery and retry logic |

  ## Status
  Deprecated: 2026-03-31
  Reason: Out of scope for Phase 2. Telegram-first build only.
  Preserved: Yes — do not delete.
  ---

  Verify: ls past_experiments/ must show all 10 files + DEPRECATED.md.
  Gate: past_experiments/ contains 11 items. If not, halt.

STEP 2 — Create src/memory_extractor.py:
  - extract_facts(user_msg: str, response: str) -> dict
    Calls qwen2.5:0.5b via same Lemonade pattern as state_bus.py.
    Returns {"name", "facts", "tone", "summary_worthy"}.
  - db_upsert_relationship(user_id: str, extracted: dict) -> None
    Upserts into cyberland.db relationships table.
    Merges new facts into existing facts list (no duplicates).
  - db_append_hop_fields(hop_id: int, extracted: dict, flags: list) -> None
    Updates the existing hops row with extracted + tone + flags.
  - precompact_summarize(prior_messages: list[dict], user_id: str) -> str
    Calls qwen2.5:0.5b to summarize. Writes to relationships.summary.
    Returns summary string.
  - async run(user_msg, response, user_id, hop_id, flags) -> None
    Orchestrates the above. Entry point called from forge_server.

STEP 3 — Modify src/forge_server.py (three additions only):

  a. ALICE.md injector — add build_system_prompt(user_id: str) -> str
     Reads data/ALICE.md, queries cyberland.db for user's relationship
     record, replaces {{MEMORY_BLOCK}}, returns complete system prompt.
     Insert as messages[0] before prior_messages on every request.

  b. Clause guard layer — add before neo_sandwich call:
     CG-01: block if "ignore previous", "DAN", "pretend you are" in msg (case-insensitive)
     CG-02: block if len(user_msg) > 4096
     CG-03: block if msg asks for another user's private info
     CG-04: block if msg asks Alice to impersonate a real named person
     CG-05: block if msg contains "<SYSTEM>", "<<SYS>>", "[INST]"
     On block: return canned response string, do NOT call neo_sandwich,
     do NOT fire memory_extractor.

  c. Memory task — add after successful Telegram send:
     asyncio.create_task(
         memory_extractor.run(user_msg, response, user_id, hop_id, flags)
     )
     Non-blocking. Telegram response must already be sent before this fires.

  d. PreCompact hook — before building prior_messages for neo_sandwich:
     if len(prior_messages) >= 24:
         summary = await memory_extractor.precompact_summarize(
             prior_messages, user_id
         )
         prior_messages = [{"role": "system", "content": f"Memory: {summary}"}]

STEP 4 — Create tests/test_memory_extractor.py:
  - test_extract_facts_happy_path
  - test_extract_facts_empty
  - test_db_upsert_relationship_merges_no_duplicates
  - test_precompact_length_gate
  - test_clause_guard_cg01
  - test_clause_guard_cg02
  - test_clause_guard_cg05

STEP 5 — Database migration on existing cyberland.db:
  - CREATE TABLE IF NOT EXISTS relationships (...) — see spec schema
  - PRAGMA table_info(hops) — ADD COLUMN extracted, tone, flags if absent
  - Do NOT drop or recreate hops table (91 live hops must be preserved)

--- VALIDATE ---

Run all four gates in order. Stop on first failure.
Update TROUBLESHOOTING.md + REPLICATION-NOTES.md + ISSUE.md then HALT.

  pytest -q
  ruff check . && flake8 .
  mypy . --strict
  spec drift check (see CODING-AGENT-POLICY.md Phase 3.4)

--- REVIEW ---

Route output through neo_sandwich review pass.
Do not proceed to Release without APPROVED.

--- RELEASE ---

  git checkout -b rico-phase2-memory
  git add past_experiments/ \
          src/memory_extractor.py src/forge_server.py \
          data/ALICE.md tests/test_memory_extractor.py \
          requirements.txt
  git commit -m "feat: Phase 2 — deprecate AV pipeline + memory extractor + clause guards + persona injection

  - past_experiments/: 10 legacy AV/SHRP files deprecated (not deleted)
  - past_experiments/DEPRECATED.md: deprecation log
  - memory_extractor.py: fire-and-forget sub-agent, fact triples,
    relationship upsert, PreCompact summarizer hook
  - forge_server.py: clause guards CG-01..CG-05, ALICE.md injector,
    memory task wired in after Telegram send
  - data/ALICE.md: persona injection file with {{MEMORY_BLOCK}}
  - tests: 7 unit tests, all green
  - All gates: pytest / ruff / mypy clean
  - cyberland.db: relationships table added, hops extended
  2026-03-31"
  git push -u origin rico-phase2-memory

On any failure: update TROUBLESHOOTING.md, update REPLICATION-NOTES.md,
open ISSUE.md entry, HALT. Do not self-recover past a gate failure.
```
