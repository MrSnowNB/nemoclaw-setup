---
title: Open Issues
version: 1.0.0
owner: MrSnowNB
status: living
updated: 2026-03-30
---

# Open Issues

> Agent must append to this file before halting on any failure.
> Do not close issues manually. Mark as `resolved` only after human confirms fix is stable.

---

## Issue Schema

```yaml
- id: ISSUE-XXX
  date: YYYY-MM-DD HH:MM UTC
  status: open | investigating | resolved
  blocking: true | false
  summary: "One sentence description"
  trouble_ref: TROUBLE-XXX
  action_required: "What human needs to do"
  resolved_date: null
  resolution_notes: null
```

---

## Issues

### ISSUE-001 — NemoClaw Gateway Boot Failure

```yaml
id: ISSUE-001
date: 2026-03-30 18:33 UTC
status: investigating
blocking: true
summary: NemoClaw OpenShell gateway fails to start due to ephemeral storage pressure on NVMe
trouble_ref: TROUBLE-004
action_required: |
  1. Confirm NVMe file transfer to backup drive is complete.
  2. Run: docker system prune -a --volumes
  3. Run: openshell gateway destroy --name nemoclaw
  4. Run: nemoclaw onboard
  5. Report output here to close this issue.
resolved_date: null
resolution_notes: null
```
