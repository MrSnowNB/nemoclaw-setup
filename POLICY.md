---
title: NemoClaw Project Policy
version: 1.0.0
owner: MrSnowNB
hardware: HP Z8 Fury G5 (Xeon w7-3455, 512 GiB RAM, 4x RTX A6000 48GB)
status: active
updated: 2026-03-30
---

# NemoClaw Project Policy

## File Format

- All files are Markdown with YAML frontmatter **or** pure YAML.
- No exceptions. No plain text. No JSON config files without a YAML equivalent.

## Task Rules

- Each task must be **atomic** — one clear action, one expected outcome.
- Each task must be **testable** — a pass/fail condition must be defined before work begins.
- Each task must be **gated** — it cannot begin until the previous task's validation passes.

## Lifecycle

Tasks move through these phases **sequentially only**. No skipping.

```
Plan → Build → Validate → Review → Release
```

| Phase | Definition |
|---|---|
| **Plan** | Task is written, scope defined, gate conditions stated |
| **Build** | Implementation only — no validation work |
| **Validate** | All gates must pass before advancing |
| **Review** | Human reviews output before merge/release |
| **Release** | Merge, deploy, or hand-off |

## Validation Gates

All four gates must be green before a task moves to Review.

| Gate | Command | Pass Condition |
|---|---|---|
| `unit` | `pytest -q` | Zero failures, zero errors |
| `lint` | `ruff check . && flake8 .` | Zero violations |
| `type` | `mypy . && pyright .` | Zero type errors |
| `docs` | spec drift check | No undocumented public interfaces |

## Failure Handling Protocol

On **any** failure or uncertainty, the agent must execute these steps in order, then stop:

1. **Capture logs** — collect full error output, stack trace, environment context.
2. **Update `TROUBLESHOOTING.md`** — append new entry with all seven fields (see schema below).
3. **Update `REPLICATION-NOTES.md`** — append entry under the appropriate section.
4. **Open `ISSUE.md`** — record the open issue with timestamp and blocking status.
5. **`halt_and_wait_human`** — stop all work. Do not attempt a fix. Do not retry. Wait.

> The agent must never retry a failing step more than once without human confirmation.

## On Uncertainty

If the agent is uncertain about correctness, scope, or safety of the next action:
- Update living docs with current state.
- Open an ISSUE.md entry.
- Halt and wait for human input.
