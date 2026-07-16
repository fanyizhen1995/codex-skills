---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Base-mode non-deterministic output under cancel/retry + long-context
  concurrent traffic'
canonical_url: https://github.com/sgl-project/sglang/issues/24845
captured_at: '2026-07-13T23:40:05.155763+00:00'
content_hash: a468e5b9622fb3221a58b59fb5e128d8629bdd4084905fbd26b0c9fc3fd4b9aa
---
# [Bug] Base-mode non-deterministic output under cancel/retry + long-context concurrent traffic

URL: https://github.com/sgl-project/sglang/issues/24845
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:21Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

**Version:** SGLang 0.5.10.post1
**Model:** meta-llama/Meta-Llama-3.1-8B-Instruct
**Hardware reproduced on:** NVIDIA RTX A6000 48GB, single GPU
This is a correctness issue, identical prompts at `temperature=0` produce different outputs across re-runs; the divergence is not explainable by batch-FP near-tie noise.

---

## Summary

The trace is a small 11-event workload, three rapid cancel-and-retry attempts on one request (`r1` → `r1_retry0` → `r1_retry1` → final `r1_retry2`), plus three independent concurrent streaming requests (`r2`, `r3`, `r4`), plus one long 8192-token streaming request (`r5`) at +2 s. This produces non-deterministic output across re-runs against a freshly started SGLang server in **plain base mode** (no LoRA, no speculative decoding, no `--enable-deterministic-inference`, no hierarchical cache). 

Five back-to-back replays of the same trace at `temperature=0` produce different output text on the *uncancelled* concurrent requests (`r2`, `r4`, `r5`). At the first character-level divergence between two replays the **top-1 vs top-2 logprob gap is 0.125**, which is two orders of magnitude above the 0.001 threshold typically used to filter near-tie batch-FP noise. So this is not "different argmax on a near-tie".

The model thinks one continuation is meaningfully more likely, and yet two runs of the same prompt at the same temperature pick different ones.

A self-contained reproducer (`repro_sglang_hicache_preempt_kv.py`,~280 lines, only `aiohttp` + stdlib) is attached.

> **Note on the trace shape.** Every send in this trace has `prefix_len=0` and a unique deterministic prompt — there is **no shared-prefix family**.
> The divergence is on requests (`r2`, `r4`, `r5`) that share no prefix with the cancelled retries of `r1`. So the mechanism cannot be "shared-prefix KV reuse" the way #23392 documents.

---

## Reproduced configurations

5 trials per configuration against a fresh server, same trace, same
model, same hardware. `gap` is the top-1 minus top-2 logprob at the
first character-divergence position between two diverged runs of the
same `request_id`, mirroring the gap calculation at
[`fuzzer/core/runner.py:_determinism_probe`](#).

| config (server flags beyond `--model-path` / `--port`) | diverged rids | real (gap ≥ 0.001) | near-tie | trigger present? |
|---|---:|---:|---:|---|
| **`(none — plain base mode)`**, `--context-length 65536`, `--mem-fraction-static 0.55` | 4 | **3** *(r2, r4, r5 @ 0.125)* | 1 | ✅ |
| `--enable-hierarchical-cache --hicache-write-policy write_through --hicache-ratio 2.0 --hicache-io-backend kernel`, ctx 65536, mem 0.55 | 3 | **2** *(r2, r3 @ 0.125)* | 1 | ✅ |
| same hicache flags, `--context-length 32768`, `--mem-fraction-static 0.85` | 3 | **1** *(r2 @ 0.125)* | 2 | ✶ weak |

**Reading:** the bug surfaces in *plain base mode at long context*. Adding
`--enable-hierarchical-cache` does not change the verdict; dropping the
context length to 32K weakens the signal but does not eliminate it.
The trigger is **cancel/retry + concurrent independent traffic at long
context**, not hicache.

---

## Trace shape (full event list)

| offset (ms) | action | request_id | prompt_len | max_tokens | prefix_len | stream |
|---:|:--|:--|---:|---:|---:|:--:|
| 0    | SEND   | `r1`         | 512  | 512 | 0 | ✓ |
| 12   | CANCEL | `r1`         | —    | —   | — | — |
| 27   | SEND   | `r1_retry0`  | 512  | 512 | 0 | ✓ |
| 62   | CANCEL | `r1_retry0`  | —    | —   | — | — |
| 75   | SEND   | `r1_retry1`  | 512  | 512 | 0 | ✓ |
| 89   | CANCEL | `r1_retry1`  | —    | —   | — | — |
| 100  | SEND   | `r1_retry2`  | 512  | 512 | 0 | ✓ |
| 100  | SEND   | `r2`         | 512  | 512 | 0 | ✓ |
| 200  | SEND   | `r3`         | 512  | 512 | 0 | ✓ |
| 300  | SEND   | `r4`         | 512  | 512 | 0 | ✓ |
| 2000 | SEND   | `r5`         | 8192 | 16  | 0 | ✓ |

All sends use `temperature=0`, `prefix_len=0`, and unique deterministic
prompts (the reproducer builds prompts from a stable hash of the
request_id, so prompts are byte-identical across re-runs).

---

## Why this looks like a actual bug rather than near-tie batch noise

1. **The logprob gap at the first divergence is 0.125, not ~0.** The threshold below which divergence is normally attributed to batch-FP non-associativity is 0.001 (2 orders of magnitude smaller).
2. **Multiple independent concurrent requests diverge in the same trace.** If this were a single-token near-tie occasionally tipping one way or the other, the rate of "two runs disagree" should be low  per request and uncorrelated across requests. Here three different rids `r2`, `r4`, `r5` diverge in the same configuration in 5 replays.
3. **The divergence is on uncancelled requests, not on the cancelled retries.** `r1_retry2` (the surviving retry) does not appear in the diverged set; the requests that diverge are `r2`, `r4`, `r5`, which share no prefix with `r1*`. so clearly whatever state difference is causing the divergence is bleeding from the cancel/retry workload to  concurrent workload that should be isolated from it.
4. **Sample B in some cases is degenerate.** For example one  reproduction of `r3` produces the same token repeating
   (`u1277_4441 u1277_4441 u1277_4441 …`) instead of progressing, which is consistent with the request decoding from a frozen KV state rather than its own continuation. This shape is hard to explain as sampling noise.

---

## Files

- `repro_sglang_hicache_preempt_kv.py` — standalone reproducer
  (`aiohttp` + stdlib only, no project-internal imports)
- `finding_00005_1351531223.json` — the original campaign finding
  (`status=CONFIRMED`, included for completeness)

### Reproduction

[repro_sglang_hicache_preempt_kv.py](https://gist.github.com/Yunzez/1ecca1b4409b6cbe13711bfb6443a6d2#file-repro_sglang_hicache_preempt_kv-py)
[finding_00005_1351531223.json](https://gist.github.com/Yunzez/0da58e8927831f61cb97261839629420#file-finding_00005_1351531223-json)
[hicache_long_sglang.log](https://gist.github.com/Yunzez/80c41dd9d5550a914175fa187f9503d8#file-hicache_long_sglang-log)
[hicache_long_repro.log](https://gist.github.com/Yunzez/df422ecb155eac44bffa8379ff5ba341#file-hicache_long_repro-log)
## Steps to reproduce

### 1. Start a server with the minimal triggering configuration

```bash
python3 -m sglang.launch_server \
    --model-path meta-llama/Meta-Llama-3.1-8B-Instruct \
    --port 30761 \
    --mem-fraction-static 0.55 \
    --context-length 65536
```

`--mem-fraction-static 0.55` is what we used to leave host-RAM headroom for the 8192-token `r5` request on a 48 GB A6000; Possible tune as needed for larger GPUs.

### 2. Run the standalone reproducer

```bash
pip install aiohttp

python3 repro_sglang_hicache_preempt_kv.py \
    --base-url http://localhost:30761 \
    --repeat 5
```

The script auto-discovers the served model from `/v1/models`, replays the 11-event trace 5 times back-to-back, and reports per-`request_id`:

- whether multiple distinct outputs were observed across the 5 trials,
- the modal-vs-divergent count (e.g. `modal=3/5`),
- the top-1 vs top-2 logprob gap at the first character-divergence between two diverged trials.


### 3. Expected output

```
[repro] base_url = http://localhost:30761
[repro] served model = meta-llama/Meta-Llama-3.1-8B-Instruct
[repro] repeating trace 5 times (8 sends + 3 cancels per trial; logprobs=5)

[repro] trial 1/5 starting ...
[repro] trial 1/5 done in 4.2s — 8/8 ok, 0 cancelled
...
============================================================
  5 request_ids produced output across 5 trials
  4 diverged (multiple unique outputs)
============================================================
  r2             observed 5/5 trials, 2 unique outputs (modal=4/5)
    A:  u1460_4445 u1460_4449 u1460_4449 ...
    B:  u1460_4448 u1460_4449 u1460_4449 ...
    top1−top2 gap @ first diverge: 0.125000  → real divergence
  r3             observed 5/5 trials, 2 unique outputs (modal=3/5)
    ...
    top1−top2 gap @ first diverge: 0.000000  → near-tie (FP-noise candidate)
  r4             observed 5/5 trials, 2 unique outputs (modal=4/5)
    A:  u5915_4448 u5915_4448 u5915_4448 ...
    B:  u5915_4448 u5915_444  u5915_444  ...
    top1−top2 gap @ first diverge: 0.125000  → real divergence
  r5             observed 5/5 trials, 2 unique outputs (modal=4/5)
    A:  u5609_4445 u5609_4448 u5609_...
    B:  u5609_4449 u5609_4441 u5609_...
    top1−top2 gap @ first diverge: 0.125000  → real divergence

REPRODUCED
```

`r3` showing a near-tie gap (`0.000000`) on the same trace makes the cross-rid pattern important: **multiple independent concurrent requests diverge with real gaps simultaneously**. This is the part that does not look like ordinary batch-FP noise.

---

### Environment

check_env
Python: 3.12.3 (main, Mar 3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0: NVIDIA RTX A6000
GPU 0 Compute Capability: 8.6
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 590.48.01
PyTorch: 2.9.1+cu129
sglang: 0.5.10.post1
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
flashinfer_jit_cache: 0.6.7.post3+cu129
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.135.3
huggingface_hub: 1.9.2
interegular: 0.3.3
modelscope: 1.35.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.24
pyzmq: 27.1.0
uvicorn: 0.44.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.92.0
litellm: Module Not Found
torchcodec: 0.9.1
NVIDIA Topology:
�[4mGPU0 NIC0 NIC1 NIC2 CPU Affinity NUMA Affinity GPU NUMA ID�[0m
GPU0 X NODE NODE SYS 16-31 1 N/A
NIC0 NODE X PIX SYS
NIC1 NODE PIX X SYS
NIC2 SYS SYS SYS X

Legend:

X = Self
SYS = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
PHB = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
PXB = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
PIX = Connection traversing at most a single PCIe bridge
NV# = Connection traversing a bonded set of # NVLinks

NIC Legend:

NIC0: mlx5_2
NIC1: mlx5_3
NIC2: mlx5_bond_0

ulimit soft: 1024
