---
title: Troubleshooting Log
version: 1.0.0
owner: MrSnowNB
status: living
updated: 2026-03-30
---

# Troubleshooting Log

> **This is a living document.** The agent must append a new entry before halting on any failure.
> Never delete or modify existing entries. Only append.

---

## Entry Schema

Every entry must include all seven fields:

```yaml
- id: TROUBLE-XXX
  date: YYYY-MM-DD
  context: "What was being attempted"
  symptom: "What was observed"
  error_snippet: |
    paste exact error here
  probable_cause: "Root cause hypothesis"
  quick_fix: "Immediate workaround"
  permanent_fix: "Correct long-term resolution"
  prevention: "How to avoid next time"
```

---

## Entries

### TROUBLE-001 — Dependency Resolution Loop

```yaml
id: TROUBLE-001
date: 2026-03-30
context: pip install resolving package dependencies for vLLM or NeMo stack
symptom: pip hangs indefinitely or raises ResolutionImpossible / backtracking warnings
error_snippet: |
  ERROR: Cannot install package-a==1.2 and package-b==3.1 because these package
  versions have conflicting dependencies.
probable_cause: Transitive dependency version conflicts between indirect deps not pinned
quick_fix: pip install --constraint constraints.txt
permanent_fix: |
  1. Run `pip-compile requirements.in --output-file requirements.txt` to resolve.
  2. Pin all indirect deps in constraints.txt.
  3. Add constraints.txt to version control.
prevention: Always generate constraints.txt at environment creation time. Never install without it.
```

---

### TROUBLE-002 — Embedding Model OOM

```yaml
id: TROUBLE-002
date: 2026-03-30
context: Loading or running embedding model inside NemoClaw sandbox or vLLM
symptom: CUDA OOM error during model load or inference batch
error_snippet: |
  torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate X GiB.
  GPU memory: Y GiB free, Z GiB total.
probable_cause: Batch size too large, full fp32 precision, or sequence length exceeding available VRAM
quick_fix: |
  1. Reduce batch_size by 50%.
  2. Enable truncation: tokenizer(text, truncation=True, max_length=512).
  3. Cast model to fp16: model.half()
permanent_fix: |
  1. Set max_length in model config.
  2. Pin batch_size in config file, not code.
  3. Use --kv-cache-dtype fp8 in vLLM serve command.
prevention: Always profile VRAM with nvidia-smi before setting batch size. Use fp16 by default.
```

---

### TROUBLE-003 — Socket Port Conflicts in Local Orchestrator

```yaml
id: TROUBLE-003
date: 2026-03-30
context: Starting local orchestrator or vLLM serve when default port is already bound
symptom: Server fails to start with address already in use error
error_snippet: |
  OSError: [Errno 98] Address already in use: ('0.0.0.0', 8000)
probable_cause: Previous process did not cleanly release the port binding
quick_fix: |
  1. find and kill: lsof -ti:8000 | xargs kill -9
  2. Retry server start.
permanent_fix: |
  Implement randomized port bind with retries in orchestrator startup:
    import socket, random
    for _ in range(10):
        port = random.randint(8100, 8900)
        with socket.socket() as s:
            if s.connect_ex(('localhost', port)) != 0:
                break  # port is free
prevention: Never hardcode port 8000 in orchestrator config. Always use port-probe-with-retry pattern.
```

---

### TROUBLE-004 — NemoClaw OpenShell Gateway Ephemeral Storage Eviction

```yaml
id: TROUBLE-004
date: 2026-03-30
context: Running nemoclaw onboard on HP Z8 Fury G5, Docker root on NVMe under storage pressure
symptom: Gateway fails after 3 retries with K8s namespace not ready
error_snippet: |
  × K8s namespace not ready
  ╰─▶ timed out waiting for namespace 'openshell' to exist
  eviction_manager: must evict pod(s) to reclaim ephemeral-storage
  eviction_manager: unable to evict any pods from the node
probable_cause: |
  Docker root partition (default /var/lib/docker) is low on free space.
  K3s inside the OpenShell container cannot allocate ephemeral storage for
  kube-system pods (coredns, metrics-server, local-path-provisioner).
  Eviction manager loops but cannot evict critical pods, so namespace never creates.
quick_fix: |
  1. df -h to confirm low disk on Docker root partition.
  2. docker system prune -a --volumes to reclaim space.
  3. openshell gateway destroy --name nemoclaw
  4. nemoclaw onboard (retry)
permanent_fix: |
  Move Docker root to a partition with >= 200 GB free:
  Edit /etc/docker/daemon.json: {"data-root": "/path/to/large/drive/docker"}
  sudo systemctl restart docker
prevention: |
  Before any NemoClaw install, verify df -h shows >= 50 GB free on Docker root partition.
  Add this check to the pre-flight section of REPLICATION-NOTES.md.
```
