---
title: Model Download and vLLM Configuration
version: 1.0.0
owner: MrSnowNB
hardware: HP Z8 Fury G5 (4x RTX A6000 48GB / 512 GiB RAM)
models:
  - nvidia/Nemotron-3-Super-120B-A12B
  - nvidia/nemotron-3-nano-30b-a3b
status: active
updated: 2026-03-30
---

# Model Download and vLLM Configuration

## Purpose

This document defines the exact steps for downloading and serving the two Nemotron models
used in the NemoClaw agent stack. Follow in order. Do not skip steps. Gate each step.

---

## Phase 1 — Plan

| # | Task | Gate |
|---|---|---|
| 1.1 | Verify disk space for model cache | `df -h ~/.cache` shows >= 200 GB free |
| 1.2 | Verify HuggingFace CLI installed | `huggingface-cli --version` exits 0 |
| 1.3 | Verify HuggingFace login (for gated models) | `huggingface-cli whoami` returns username |
| 1.4 | Verify all 4 GPUs visible | `nvidia-smi -L` shows 4 devices |
| 1.5 | Verify ports 8000 and 8001 are free | `lsof -ti:8000 && lsof -ti:8001` returns nothing |

---

## Phase 2 — Build (Download Models)

### Step 2.1 — Install Prerequisites

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Create venv with Python 3.12
uv venv vllm-env --python 3.12 --seed
source vllm-env/bin/activate

# Install vLLM
uv pip install vllm --torch-backend=auto

# Install HuggingFace CLI
uv pip install -U huggingface-hub
```

**Gate:** `python -c "import vllm; print(vllm.__version__)"` must exit 0.

---

### Step 2.2 — HuggingFace Login

```bash
huggingface-cli login
# Enter your HF token when prompted.
# Token needs read access to nvidia/ org models.
```

**Gate:** `huggingface-cli whoami` returns your username.

---

### Step 2.3 — Download Primary Model (120B)

```bash
# Main agent model — Nemotron 3 Super 120B
# MoE: 120B total params, 12B active per forward pass
# Expected disk: ~87 GB
huggingface-cli download nvidia/Nemotron-3-Super-120B-A12B \
    --local-dir ~/.cache/huggingface/hub/Nemotron-3-Super-120B-A12B
```

**Gate:** `huggingface-cli scan-cache | grep Nemotron-3-Super-120B` shows entry with non-zero size.

---

### Step 2.4 — Download Sub-Agent Model (30B)

```bash
# Sub-agent model — Nemotron 3 Nano 30B-A3B
# MoE: 30B total params, 3B active per forward pass
# Expected disk: ~60 GB
huggingface-cli download nvidia/nemotron-3-nano-30b-a3b \
    --local-dir ~/.cache/huggingface/hub/nemotron-3-nano-30b-a3b
```

**Gate:** `huggingface-cli scan-cache | grep nemotron-3-nano-30b` shows entry with non-zero size.

---

## Phase 3 — Validate (Smoke Test Load)

### Step 3.1 — Test 120B Loads Without OOM

```bash
python -c "
import subprocess, sys
result = subprocess.run([
    'python', '-m', 'vllm.entrypoints.openai.api_server',
    '--model', 'nvidia/Nemotron-3-Super-120B-A12B',
    '--tensor-parallel-size', '4',
    '--max-num-seqs', '1',
    '--max-model-len', '1024',
    '--gpu-memory-utilization', '0.5',
    '--port', '8000',
], timeout=120, capture_output=True, text=True)
print(result.stdout[-2000:])
print(result.stderr[-2000:])
"
```

Alternatively, start the server and hit it:

```bash
curl http://localhost:8000/v1/models
# Expected: JSON response listing Nemotron-3-Super-120B-A12B
```

**Gate:** Server responds with model listing. No CUDA OOM in logs.

---

### Step 3.2 — Test 30B Loads Without OOM

```bash
curl http://localhost:8001/v1/models
# Expected: JSON response listing nemotron-3-nano-30b-a3b
```

**Gate:** Server responds with model listing. No CUDA OOM in logs.

---

## Phase 4 — Full Production Serve Commands

### Serve 120B (Main Agent — Port 8000)

```bash
vllm serve nvidia/Nemotron-3-Super-120B-A12B \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.92 \
    --kv-cache-dtype fp8 \
    --enable-prefix-caching \
    --swap-space 64 \
    --cpu-offload-gb 200 \
    --max-num-seqs 32 \
    --max-model-len 32768 \
    --host 0.0.0.0 \
    --port 8000
```

### Serve 30B (Sub-Agents — Port 8001)

```bash
vllm serve nvidia/nemotron-3-nano-30b-a3b \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.90 \
    --kv-cache-dtype fp8 \
    --enable-prefix-caching \
    --swap-space 32 \
    --cpu-offload-gb 100 \
    --max-num-seqs 16 \
    --max-model-len 32768 \
    --host 0.0.0.0 \
    --port 8001
```

---

## Phase 5 — Wire NemoClaw to Local vLLM

After both servers are confirmed healthy, configure NemoClaw to use them:

```bash
# Point main agent at 120B
openshell inference set \
    --provider vllm-local \
    --model nvidia/Nemotron-3-Super-120B-A12B \
    --base-url http://host.openshell.internal:8000/v1

# Sub-agent model override (in agent config file)
# agents.defaults.subagents.model: nvidia/nemotron-3-nano-30b-a3b
# agents.defaults.subagents.baseUrl: http://host.openshell.internal:8001/v1
```

### UFW Rules (Required for Docker Bridge Access)

```bash
sudo ufw allow proto tcp from 172.18.0.0/16 to any port 8000
sudo ufw allow proto tcp from 172.17.0.0/16 to any port 8000
sudo ufw allow proto tcp from 172.18.0.0/16 to any port 8001
sudo ufw allow proto tcp from 172.17.0.0/16 to any port 8001
```

**Gate:** From inside the sandbox container, `curl http://host.openshell.internal:8000/v1/models` returns model listing.

---

## Failure Handling

If any step fails:

1. Copy the full error output.
2. Append to `TROUBLESHOOTING.md` using the entry schema.
3. Append to `REPLICATION-NOTES.md` under Recurring Errors.
4. Open a new entry in `ISSUE.md`.
5. Stop. Wait for human input.

---

## Phase 6 — Gemma-4-31B-it Setup (Ollama Engine)

### Step 6.1 — Download 8-bit GGUF Model

```bash
# Model — Gemma-4-31B-it (Instruction Tuned)
# Quantization: Q8_0 GGUF
# Expected disk: ~35 GB
huggingface-cli download unsloth/gemma-4-31B-it-GGUF gemma-4-31B-it-Q8_0.gguf \
    --local-dir ~/.cache/huggingface/hub/gemma-4-31B-it-GGUF --local-dir-use-symlinks False
```

### Step 6.2 — Create Ollama Model

Create a `Modelfile` in the root directory:

```bash
cat <<EOF > Modelfile
FROM /home/mr-snow/.cache/huggingface/hub/gemma-4-31B-it-GGUF/gemma-4-31B-it-Q8_0.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
EOF

ollama create gemma4-31b-it -f Modelfile
```

### Step 6.3 — Serve & Test

```bash
# Ollama runs as a service, but you can test via:
ollama run gemma4-31b-it "Hello, who are you?"
```

**Gate:** `ollama list` shows `gemma4-31b-it`.
