# Replication Notes - Phase 2 Memory Extractor

## Steps Taken
1. Checked out new branch `rico-phase2-memory`.
2. Created `src/memory_extractor.py` and modified `src/forge_server.py` with Phase 2 capabilities (Clause Guards, memory injection).
3. Created test suite `tests/test_memory_extractor.py` passing 100%.
4. Migrated SQLite database to include `relationships` and altered `hop` table.
5. Initiated CI gate check protocol.

## Step to Reproduce Failure
1. Execute `ruff check .` in the root repository.
2. Observe 67 legacy module errors triggering the hard halt sequence.

2026-03-31: Lint/type gates scoped to src/ tests/ per POLICY.md v1.1.0.
   past_experiments/ excluded — contains deprecated AV/SHRP files.

## Symlink Warning
The `src/` directory is an external symlink resolving to `/home/mr-snow/Documents/Testing the Beast/Alice in Cyberland/src`. Therefore, the active files (`src/forge_server.py`, `src/memory_extractor.py`, and `src/state_bus.py`) physically reside outside this repository.
