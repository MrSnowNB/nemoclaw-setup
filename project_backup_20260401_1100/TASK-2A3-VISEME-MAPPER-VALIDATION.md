---
task_id: "2A.3-Validation"
name: "Validation Testing for VisemeMapper"
status: "complete"
priority: "critical"
dependencies: ["2A.3"]
---

## Objective

Thoroughly validate and debug the VisemeMapper component. Log all test results, detected visemes, and edge case behaviors. Save output and test scripts for reproducibility, and commit all diagnostics to GitHub.

## Steps

### 1. Isolated Test Script

Create `tests/test_viseme_mapper_comprehensive.py`. This test should:

- Load sample input text covering all phonemic classes (e.g., "She bought cheap toys for a quick laugh.").
- Use your VisemeMapper to convert input phonemes/words to viseme classes and timings.
- Save the result as both a YAML/JSON file (`outputs/debug/viseme_map_test_result.yaml`) and a human-readable log (`outputs/logs/viseme_mapper_debug.log`).

### 2. Log Mapping and Errors

- For every mapped phoneme/word, log:
  - Input token
  - Phoneme
  - Viseme class assigned
  - Start/end times (if available)
  - Any warnings for unmapped or ambiguous tokens

- Catch and log any exceptions with full stack trace to `outputs/logs/viseme_mapper_exceptions.log`.

### 3. Edge Case Coverage

- Include at least one test input with:
  - Unusual/uncommon words
  - Non-English characters (should be skipped/gracefully ignored)
  - Silent/empty input (should log a warning but not crash)

- Save all outputs, even for failure cases.

### 4. Artifacts for GitHub Backup

Commit and push:
- Test script: `tests/test_viseme_mapper_comprehensive.py`
- Log: `outputs/logs/viseme_mapper_debug.log`
- Exception log: `outputs/logs/viseme_mapper_exceptions.log`
- Result file: `outputs/debug/viseme_map_test_result.yaml`

Commit Message:
```
[Policy] 2A.3 VisemeMapper validation: mapping results, error logs, edge case coverage, and debug artifacts
```

### 5. Policy on Failure

If any assertions fail (output missing, crashed on edge case, mapping incomplete), update TROUBLESHOOTING.md before halting and create ISSUE-2A3.md; do not proceed to the next phase until fixed.

---

## Validation Gate (GATE_2A.3-Validation)

Assertions:
- [ ] All core phonemes mapped to viseme classes as expected
- [ ] Edge cases handled gracefully
- [ ] Logs and output file created (and committed)
- [ ] No unhandled exceptions
- [ ] Human/manual review possible from output

---

## On Success

- Mark TASK-2A3-VISEME-MAPPER-VALIDATION.md as "complete"
- Proceed to 2A.4 (ROI compositor component)
