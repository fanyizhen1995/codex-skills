---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Concurrent multi-LoRA requests diverge under deterministic inference'
canonical_url: https://github.com/sgl-project/sglang/issues/27097
captured_at: '2026-07-12T23:38:53.045500+00:00'
content_hash: 09eb6ca40740caf967222e6a919d5dab60c72f47704ce897fcbe7772d0aca938
---
# [Bug] Concurrent multi-LoRA requests diverge under deterministic inference

URL: https://github.com/sgl-project/sglang/issues/27097
State: closed
Labels: 
Closed at: 2026-07-12T17:06:45Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] This report includes environment info and a reproducible harness description.
- [x] This is a bug report, not a general question.
- [x] This issue is in English.

### Describe the bug

Concurrent multi-LoRA requests can return different text for the same `(adapter, prompt)` under deterministic inference, even though sequential deterministic baselines are stable.

I originally suspected LoRA eviction / slot reuse, but a no-eviction control also diverges. So I am not claiming the root cause is eviction. The narrower observation is:

- `--enable-deterministic-inference`
- `temperature: 0`
- sequential audit baseline is stable across two full repeats
- concurrent stress traffic changes adapter outputs with no HTTP/load/audit errors
- this reproduces both with `--max-loras-per-batch 4` and with `--max-loras-per-batch 16`

The generated adapter outputs are intentionally gibberish because the repro uses synthetic random LoRAs to make wrong-adapter / wrong-state effects easy to detect. The important signal is hash/text mismatch versus a stable deterministic sequential baseline.

### Reproduction

Tested on `sglang` main commit:

```text
a711c57a32a5fbaf51e2822fbb6a1424e1f1d7ce
sglang 0.5.12.post2.dev781+ga711c57a3
torch 2.11.0+cu130
```

Model:

```text
Qwen/Qwen2.5-14B-Instruct
```

Adapters:

- 16 PEFT-format LoRA adapters named `a0` through `a15`
- rank 64, alpha 256
- `lora_dropout=0.0`, `bias=none`, inference mode
- target modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- random bf16 weights generated with fixed seed `20260602`
- per-adapter gain to make adapter mixups easier to detect

Request parameters used by the audit harness:

```json
{
  "temperature": 0,
  "max_tokens": 24,
  "logprobs": true,
  "top_logprobs": 10
}
```

The audit uses 12 short prompts across `base` plus all 16 adapters, so each full audit round has 204 requests.

#### Case 1: deterministic, CUDA graph enabled, max 4 LoRAs per batch

Server:

```bash
MODEL=Qwen/Qwen2.5-14B-Instruct \
MAX_LORAS_PER_BATCH=4 \
CUDA_GRAPH_MAX_BS=160 \
MEM_FRACTION_STATIC=0.85 \
ENABLE_DETERMINISTIC=1 \
LOG_LEVEL=debug \
LOG=/home/gabe/repro/server_30000_cgraph_evict_deterministic.log \
/home/gabe/repro/harness/launch_sglang_server.sh
```

The launcher expands to:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-14B-Instruct \
  --enable-lora \
  --lora-paths a0=/home/gabe/repro/adapters/a0 ... a15=/home/gabe/repro/adapters/a15 \
  --max-loras-per-batch 4 \
  --max-lora-rank 64 \
  --lora-target-modules all \
  --lora-drain-wait-threshold 0.05 \
  --cuda-graph-max-bs 160 \
  --mem-fraction-static 0.85 \
  --log-level debug \
  --port 30000 \
  --enable-deterministic-inference
```

Stable sequential baseline:

```bash
python audit_lora_stress.py \
  --mode baseline \
  --audit-concurrency 1 \
  --warmup-rounds 1 \
  --repeats 2 \
  --out baseline_cgraph_evict_deterministic_warm_seq.jsonl
```

Result:

```json
{
  "type": "summary",
  "mode": "baseline",
  "elapsed_s": 1000.339,
  "items": 204,
  "warmup_rounds": 1,
  "repeats": 2,
  "error_count": 0,
  "stability_mismatches": []
}
```

Concurrent stress:

```bash
python audit_lora_stress.py \
  --mode stress \
  --baseline-in baseline_cgraph_evict_deterministic_warm_seq.jsonl \
  --duration-s 300 \
  --audit-interval-s 15 \
  --load-concurrency 64 \
  --audit-concurrency 32 \
  --stop-on-divergence \
  --out stress_cgraph_evict_deterministic_5m.jsonl
```

Result:

```json
{
  "type": "summary",
  "mode": "stress",
  "elapsed_s": 47.78,
  "rounds": 1,
  "load_ok": 521,
  "load_errors": 0,
  "audit_errors": 0,
  "divergence_count": 64
}
```

Example divergence:

```json
{
  "key": "a10|p0",
  "baseline_hash": "77675ef3dac1e38a",
  "actual_hash": "febade28b4e5c1f7"
}
```

#### Case 2: deterministic, CUDA graph enabled, max 16 LoRAs per batch

This was intended as a no-eviction control, since all 16 adapters can be loaded in the batch.

Server changes:

```bash
MAX_LORAS_PER_BATCH=16
MEM_FRACTION_STATIC=0.75
ENABLE_DETERMINISTIC=1
```

Stable sequential baseline:

```json
{
  "type": "summary",
  "mode": "baseline",
  "elapsed_s": 1013.866,
  "items": 204,
  "warmup_rounds": 1,
  "repeats": 2,
  "error_count": 0,
  "stability_mismatches": []
}
```

Concurrent stress result:

```json
{
  "type": "summary",
  "mode": "stress",
  "elapsed_s": 26.953,
  "rounds": 1,
  "load_ok": 504,
  "load_errors": 0,
  "audit_errors": 0,
  "divergence_count": 146
}
```

Example divergence:

```json
{
  "key": "a10|p0",
  "baseline_hash": "77675ef3dac1e38a",
  "actual_hash": "febade28b4e5c1f7"
}
```

### Expected behavior

For deterministic inference with `temperature=0`, the same `(model, adapter, prompt)` should return the same text under concurrent load when the sequential deterministic baseline is stable. If concurrent multi-LoRA output is not expected to be deterministic, it would help to document the limitation and which backend/settings are affected.

### Actual behavior

Sequential deterministic baselines are stable, but concurrent multi-LoRA stress changes adapter outputs. There are no request/load/audit errors; the responses are successful HTTP 200 completions with different text hashes.

Because the `max_loras_per_batch=16` no-eviction control also diverges, this does not look specific to LoRA eviction or slot reuse.

### Environment

Output of `python -m sglang.check_env`:

```text
Python: 3.10.12 (main, Mar  3 2026, 11:56:32) [GCC 11.4.0]
CUDA available: True
GPU 0: NVIDIA A100-SXM4-80GB
GPU 0 Compute Capability: 8.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.41
CUDA Driver Version: 580.159.03
PyTorch: 2.11.0+cu130
sglang: 0.5.12.post2.dev781+ga711c57a3
sglang-kernel: 0.4.3
flashinfer_python: 0.6.11.post1
flashinfer_cubin: 0.6.11.post1
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0
numpy: 2.2.6
aiohttp: 3.14.0
fastapi: 0.136.3
huggingface_hub: 1.17.0
interegular: 0.3.3
modelscope: 1.37.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.30
pyzmq: 27.1.0
uvicorn: 0.48.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.105.2
litellm: Module Not Found
torchcodec: 0.11.1
Hypervisor vendor: KVM
ulimit soft: 1024
```

Hardware:

```text
GCP a2-ultragpu-1g
NVIDIA A100-SXM4-80GB, 81920 MiB
```

### Notes

- I also ran non-deterministic controls earlier, but those were not sufficient because random synthetic adapters can make batch-sensitive output hard to interpret.
- The deterministic controls above are the cleaner signal: sequential baselines are stable, concurrent stress diverges.
- I have not yet isolated whether this is CUDA graph specific. The next control would be `--disable-cuda-graph` with `--max-loras-per-batch 16`.
