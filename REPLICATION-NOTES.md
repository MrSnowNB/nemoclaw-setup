---
title: Replication Notes
version: 1.0.0
owner: MrSnowNB
hardware: HP Z8 Fury G5 (Xeon w7-3455 / 512 GiB RAM / 4x RTX A6000 48GB)
status: living
updated: 2026-03-30
---

# Replication Notes

> **This is a living document.** Append entries on every environment delta, recurring error, or flaky test.
> Never delete. Never modify existing entries. Only append.

---

## Hardware Baseline

| Component | Value |
|---|---|
| CPU | Intel Xeon w7-3455, 24C/48T, up to 4.80 GHz, Sapphire Rapids |
| RAM | 503 GiB (~512 GB) |
| GPU | 4x NVIDIA RTX A6000, 48 GB GDDR6 ECC each |
| Total VRAM | 192 GB |
| Driver | 580.126.09 |
| CUDA | 13.0 |
| OS | Ubuntu (Linux) |
| Docker | Running (confirmed pre-install) |

---

## Replicable Setup Checklist

Complete every item in order before running any install step.

- [ ] `df -h` — confirm >= 50 GB free on Docker root partition (default: `/var/lib/docker`)
- [ ] `docker system df` — confirm Docker is not consuming excess space
- [ ] `nvidia-smi` — confirm all 4 GPUs visible and driver loaded
- [ ] `docker info | grep "Docker Root Dir"` — note actual Docker root path
- [ ] `node --version` — must be >= 22.16.0 (nvm installed by NemoClaw installer)
- [ ] `python --version` — must be >= 3.12 (for vLLM uv venv)
- [ ] HuggingFace cache dir confirmed: `~/.cache/huggingface/hub/`
- [ ] Ports 8000 and 8001 free: `lsof -ti:8000; lsof -ti:8001`
- [ ] Ports 8080 and 18789 free (OpenShell gateway + NemoClaw dashboard)
- [ ] UFW rules added for Docker bridge subnets to reach vLLM ports
- [ ] Both model downloads complete (verify with `huggingface-cli scan-cache`)

---

## Known Pitfalls to Avoid Next Run

1. **Do not run `nemoclaw onboard` on a low-disk NVMe.** The K3s bootstrap inside the OpenShell container requires ephemeral storage headroom. Failure manifests as a namespace timeout, not a disk error message. See TROUBLE-004.

2. **Download both models before starting NemoClaw onboarding.** The download is large and competes with Docker I/O. Do the download first while the NVMe is free.

3. **Do not use `--tensor-parallel-size 4` for the 30B model.** It runs on a single A6000. TP=1 is correct.

4. **Port 8000 must be explicitly allowed through UFW for Docker bridge subnets** — the sandbox can't reach the host vLLM endpoint without it.

5. **Do not set `--cpu-offload-gb` higher than available free RAM minus ~80 GB OS headroom.** On this machine, max safe value is ~350 GB combined across both vLLM instances.

---

## Environment Deltas Log

### 2026-03-30 — Initial Setup

- Node.js upgraded from v20.19.5 (npm 11) to v22.22.2 (npm 10.9.7) via nvm during NemoClaw install
- NemoClaw CLI v0.1.0 installed at `/home/mr-snow/.nvm/versions/node/v22.22.2/bin/nemoclaw`
- OpenShell CLI v0.0.16 installed
- NemoClaw onboarding failed 3x due to ephemeral storage eviction on NVMe (TROUBLE-004)
- Resolution: clearing NVMe storage, retrying after `docker system prune -a --volumes`

---

## Recurring Errors

> Append new entries here as they are encountered.

| Date | Error Summary | TROUBLE Ref | Status |
|---|---|---|---|
| 2026-03-30 | K8s namespace not ready — ephemeral storage eviction | TROUBLE-004 | Resolving |

---

## Flaky Tests

> None recorded yet. Append entries as discovered.
