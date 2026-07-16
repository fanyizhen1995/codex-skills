---
source_id: sglang-github-closed-issues-prs
title: '[ROCm] Support radix-cache with mamba-extra-buffer for Qwen3.5'
canonical_url: https://github.com/sgl-project/sglang/pull/27141
captured_at: '2026-07-15T23:40:28.371746+00:00'
content_hash: a8fdf2d63d13afe2ea0861347e6b1cd418ae00a638e60a8d3f2cb6425bf84911
---
# [ROCm] Support radix-cache with mamba-extra-buffer for Qwen3.5

URL: https://github.com/sgl-project/sglang/pull/27141
State: closed
Labels: amd, run-ci
Closed at: 2026-07-15T09:08:39Z
Merged at: 

## Motivation

Hybrid Gated-DeltaNet + MoE models (Qwen3.5 / Qwen3.6, `Qwen3_5MoeForConditionalGeneration`) currently **cannot run
radix prefix caching and speculative decoding together on ROCm**:

- `--mamba-scheduler-strategy no_buffer` **auto-disables radix cache** whenever speculative decoding is on for these models
  on ROCm (the `is_hip()` stopgap added in #22908).
- `--mamba-scheduler-strategy extra_buffer` — the only mode that supports radix branching **with** spec/overlap scheduling
  — is gated to CUDA/MUSA/NPU by an `assert is_cuda() or is_musa() or is_npu()` in `_handle_mamba_radix_cache`
  (`server_args.py`). The gate was introduced for CUDA in #14792 and extended to MUSA in #23654 and NPU in #23891.

So on ROCm today it is **spec XOR radix, never both** — which is a large loss for shared-prefix (agentic/RAG) traffic.
This PR adds ROCm to the whitelist, closing the open AMD-owned tracker **#23299** and replacing the **#22908** stopgap.

**Why it is safe on ROCm (no kernel work required):**
- The default GDN compute path is the hardware-agnostic `TritonGDNKernel` (`gdn_backend.py`). The CUDA-only `gdn_cutedsl`
  / `gdn_flashinfer` backends hard-`raise "requires CUDA"` and are **not** on the HIP path.
- The vendored FLA kernels are AMD-aware (`fla/utils.py` maps device `hip → cuda`; `torch.cuda` probes are guarded by
  `is_nvidia` short-circuits), and AMD takes the safer `ieee` precision branch (tf32 gated on `is_nvidia`). The SSM
  recurrent state is fp32.
- The Qwen3.5 arch already passes `support_mamba_cache_extra_buffer=True` into the handler — **the assert is the sole blocker.**
- #20791 showed the **Triton FLA path** (exactly the one ROCm runs) holds **GSM8K 0.990 across `extra_buffer`, `no_buffer`,
  and `no_buffer`+disable-radix**, while only the CUDA-only FlashInfer backend regressed — i.e. the path ROCm enables is the
  numerically-robust one for GDN state reuse.

---

## Modifications

**Two changes:**

**1. Enablement (one line)** — add `is_hip()` to the `extra_buffer` device whitelist in `_handle_mamba_radix_cache`
(`python/sglang/srt/server_args.py`), mirroring the `+is_musa()` / `+is_npu()` one-liners in #23654 / #23891:
```diff
             assert (
-                is_cuda() or is_musa() or is_npu()
-            ), "Mamba extra_buffer is only supported on CUDA and MUSA and NPU devices with FLA backend"
+                is_cuda() or is_musa() or is_npu() or is_hip()
+            ), "Mamba extra_buffer is only supported on CUDA, MUSA, NPU, and ROCm/HIP devices with FLA backend"
```
No kernel changes: ROCm already runs the hardware-agnostic `TritonGDNKernel` + AMD-aware FLA Triton kernels by default
(the CUDA-only `gdn_cutedsl`/`gdn_flashinfer` backends hard-`raise` and are never selected on HIP), so the assert is the
only blocker.

**2. CI gate** — `test/registered/amd/accuracy/mi35x/test_qwen35_extra_buffer_mtp_mi35x.py`: the AMD counterpart of the
CUDA gate `test_qwen35_fp4_mtp_v2.py`. Launches Qwen3.5-397B-A17B on MI35x with `extra_buffer` + radix + NEXTN spec
(`SGLANG_ENABLE_SPEC_V2=1`, triton attn, aiter), runs GSM8K (5-shot, `run_eval`), and asserts:
- **GSM8K `score ≥ 0.93`** (5-shot, **greedy, thinking disabled, `num_threads=1`** — the 5-shot exemplars are the CoT
  scaffold). The eval is run **sequentially**, which is the decisive choice for a non-flaky gate on this stack: a
  controlled sweep on one fixed 397B-FP8 server varying *only* `num_threads` gave **threads=1 → 0.97/0.97, threads=8 →
  0.97, threads=32 → 0.89/0.88/0.93** (see Accuracy Tests). High eval concurrency injects ~8 pts of batch-composition
  non-determinism; sequential removes it. Sequential 397B-C is stable at **0.96–0.97** (five runs), so 0.93 leaves a
  ~3-pt margin (CUDA gate is 0.95; relaxed for the non-deterministic AMD path). Radix prefix reuse is still exercised at
  threads=1 — the shared 5-shot prefix gives ~0.93–0.99 cache hit. `max_tokens=4096` gives headroom for the few long-CoT
  questions (2048 truncated ~2/run). NB thinking-ON + temp 0.6 is noisier still (over-reasons ~5.8k tok/q, truncates).
- **`avg_spec_accept_length > 2.0`** — confirms speculative decoding is genuinely active *with radix on* (measures ~3.1).
  Together these prove the feature works *and* preserves accuracy. (Cache-fidelity is validated out-of-band — see Accuracy
  Tests: KL cache-hit-vs-fresh ≈ cold-vs-cold floor, `radix_cache` token-match.)

Uses **explicit cuda-graph / concurrency / prefill caps** (`--cuda-graph-max-bs 64 --max-running-requests 64
--chunked-prefill-size 32768 --max-prefill-tokens 32768`): without them, server defaults (`cuda_graph_max_bs=512`) make
the GDN speculative path SIGABRT under eval load — **caught and fixed by actually running this test on MI350x** (TP2/EP2,
FP8): server stable, `avg_spec_accept_length=3.13`, GSM8K 0.970, `Ran 1 test … OK`, no crash. The registered test uses
`Qwen/Qwen3.5-397B-A17B` at **TP=8**, identical to the sibling `test_qwen35_eval_mi35x.py` on this lane; our local
validation ran TP2/EP2 + FP8 (2-GPU availability), and since bf16/TP8 ≥ FP8/TP2 accuracy the 0.93 gate keeps its margin.
Registered to the existing `nightly-amd-accuracy-8-gpu-mi35x-qwen35` suite via `register_amd_ci`, so it joins the
already-wired Qwen3.5 MI35x lane with no `.github/workflows` change. **This exceeds the MUSA/NPU enablements** (which
shipped with no CI coverage).

**Optional follow-ups (not in this PR — happy to add on request):** (a) drop the now-redundant `#22908` ROCm
silent-radix-disable arm in the `no_buffer`+spec branch; (b) an explicit `is_hip()` branch in `gdn_backend.py`'s
`causal_conv1d` dispatch (today it correctly rides the Triton base import); (c) doc updates in `qwen3.md` /
`server_arguments.md` that still say `extra_buffer` is NVIDIA-only.

Usage (config C): `--mamba-scheduler-strategy extra_buffer --page-size 64 --attention-backend triton
--speculative-algorithm NEXTN --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4`,
env `SGLANG_ENABLE_SPEC_V2=1`. (`page_size 64` satisfies `FLA_CHUNK_SIZE`; `mamba_track_interval` 256 divisible by it.)

---

## Accuracy Tests

Hardware: AMD **MI350x (gfx950)**, image `lmsysorg/sglang:v0.5.12.post1-rocm720-mi35x`. Models: Qwen3.5-397B-A17B-FP8
(TP2/EP2) and Qwen3.6-35B-A3B-FP8 (TP1). C = `extra_buffer`+radix+spec; A′ = `no_buffer`+spec (radix auto-off, today's
baseline).

**GSM8K (official `sglang.test.run_eval`, 5-shot CoT, `enable_thinking=false`, greedy), config C:**

| model | precision | TP | harness | GSM8K |
|---|---|---|---|---|
| Qwen3.5-397B-A17B | FP8 | 2 | sequential (`num_threads=1`), 100 ex | **0.96 / 0.98 / 0.97** (3 runs) |
| Qwen3.5-397B-A17B | FP8 | 2 | sequential (`num_threads=1`), 100 ex, `run_eval` | **0.97 / 0.97** |
| Qwen3.6-35B-A3B   | FP8 | 1 | sequential, 100 ex | **0.98 / 0.98** |
| Qwen3.6-35B-A3B   | bf16| 1 | sequential, 100 ex | **0.98 / 0.96** |

On a stable (sequential) eval the radix+spec config is **0.96–0.98 across every model/precision** — no degradation from
enabling radix, and **FP8 ties-or-beats bf16** (FP8 was the most run-to-run stable: 0 correctness flips across 2 runs).

**The earlier noisy numbers were an eval-concurrency artifact, not the feature.** A controlled sweep on *one fixed*
397B-FP8 server (config C), varying **only `num_threads`** (same model, questions, greedy, max_tokens):

| `num_threads` | GSM8K (per run) | latency/100ex |
|---|---|---|
| 1  | **0.97, 0.97** | ~135 s |
| 8  | **0.97**       | ~47 s |
| 32 | **0.89, 0.88, 0.93** | ~36 s |

```bash
# vary only --num-threads on the same server:
docker exec -e PYTHONPATH=/sgl-workspace/sglang/python <server> python3 -m sglang.test.run_eval \
  --port <P> --eval-name gsm8k --num-examples 100 --num-threads {1|8|32} --max-tokens 4096 \
  --temperature 0 --chat-template-kwargs '{"enable_thinking": false}'
```

- **The 0.84–0.94 swings reported informally for this config were entirely high-concurrency (`threads=32`) noise.** This
  ROCm MoE/aiter stack is non-deterministic at the logit level — concurrent requests form varying dynamic batches, and
  batch-composition-dependent reductions flip a handful of knife-edge greedy tokens, moving the score ~8 pts. It is a
  **pre-existing stack property unrelated to this PR** (`--enable-deterministic-inference` does not yet cover the ROCm
  MoE/aiter path — tracked separately); radix+spec does not add to it. Hence the CI gate evaluates at `num_threads=1`.
  **The same config C on the smaller Qwen3.6-35B-A3B does *not* scatter** (0.97/0.98/0.98 at threads=32) — if the swing
  were a radix+spec defect it would show there too; it is an eval-concurrency-at-scale effect, confirming the feature is sound.
- **No state corruption** across 700 run-questions: every wrong answer has coherent on-topic reasoning — none are garbage,
  loops, or incoherence. Per-question dumps show the failures are (a) `max_tokens` **truncation** (recoverable by raising
  the cap), (b) one isolated final-line digit slip (reasoning correctly derived 163, the answer line emitted 1163; not
  reproduced), and (c) **deterministic model errors on genuinely ambiguous GSM8K wording** (e.g. "0.75 bags per *invited*
  guest" vs *attendee*) that are **identical across FP8/bf16/397B** — i.e. model limitations, *not* a radix+spec effect.
- **Cache-fidelity (KL / logprob — the CUDA gate's ROCm analog).** CUDA's #14792 gates cache-hit-vs-fresh logprob
  divergence at `kl_div < 0.008`. That literal bar isn't reproducible here — **not because of the cache**, but because the
  **cold-vs-cold floor** (two identical fresh prefills) is already ~0.086: the ROCm MoE/aiter path is non-deterministic at
  the logit level run-to-run (pre-existing; `--enable-deterministic-inference` doesn't yet cover it). So the correct test
  is *relative* — does cache-resume diverge **more** than the floor? Multi-prompt (1k–8k tok), config C: **FLOOR (cold,cold)
  0.086 vs SIGNAL (cold,warm) 0.096 → signal/floor ≈ 1.11** → the cache's contribution to divergence is ≈ 0. And sglang's
  **own** `test_deterministic --test-mode radix_cache` (the maintainers' cached-vs-uncached prefill check): cached and
  uncached prefill **select the same token** (logprobs differ ~0.04–0.12 = the stack floor) → **argmax/output preserved**,
  which is *why* GSM8K is unaffected. This is the targeted check for the radix-specific risk (GDN state-resume corruption,
  cf. #20791); the GSM8K gate is the task-level confirmation.
- 5/5 reasoning-aware smoke; 512-prompt @ c=32 stress → re-smoke 5/5 (no state corruption). Loads with no OOM at TP2/EP2.

---

## Speed Tests and Profiling

C vs A′, identical model/TP/concurrency/EAGLE(3/1/4); only the scheduler mode differs.

**Prefill-bound (the shared-prefix workload this targets) — Qwen3.5-397B, 16 384-tok shared prefix, 16-tok output, c=64, 256 reqs:**

| metric | A′ (radix off) | **C (radix+spec)** | C vs A′ |
|---|---|---|---|
| total token throughput | 21 127 tok/s | **116 516 tok/s** | **5.5×** |
| median TTFT | 16 549 ms | **2 813 ms** | **5.9× faster** |
| median E2E | 52 594 ms | **4 368 ms** | **12.0× faster** |
| live cache hit | ~0 | **~0.99** | — |

**Moderate shared-prefix — Qwen3.5-397B, 4 096-tok prefix, 256-out, c=32:**

| metric | A′ | **C** | Δ |
|---|---|---|---|
| output throughput | 656 tok/s | **783 tok/s** | **+19%** |
| median TTFT | 457 ms | **368 ms** | **−19%** |
| median ITL | 27.2 ms | **18.6 ms** | **−32%** |

```bash
docker exec -e PYTHONPATH=/sgl-workspace/sglang/python <server> python3 -m sglang.bench_serving \
  --backend sglang --dataset-name generated-shared-prefix --gsp-num-groups 8 --gsp-prompts-per-group 32 \
  --gsp-system-prompt-len 16384 --gsp-question-len 128 --gsp-output-len 16 --num-prompts 256 --max-concurrency 64
```

Cost: `extra_buffer` allocates ~2× mamba state vs `no_buffer`; on non-shared-prefix traffic expect a small net cost
(the win scales with prefix length × hit rate × prefill:decode ratio). Spec acceptance length is **unchanged between C and
A′** (workload-dependent in absolute terms: ~2.5 on this prefill-bound bench, ~3.1 on the GSM8K decode workload).

---

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
      (`black` 26.1.0 / `isort` 7.0.0 / `ruff` 0.15.1 pass; a full `pre-commit run --all-files` in a dev env is recommended before merge.)
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
      (`test/registered/amd/accuracy/mi35x/test_qwen35_extra_buffer_mtp_mi35x.py`, joins the existing `nightly-amd-accuracy-8-gpu-mi35x-qwen35` suite — exceeds the MUSA/NPU enablements, which shipped no CI coverage.)
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
      (`docs/basic_usage/qwen3.md`, `docs/advanced_features/server_arguments.md` still say `extra_buffer` is NVIDIA-only — left as an optional follow-up to keep this PR minimal.)
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
      (Above, MI350x: Qwen3.5-397B and Qwen3.6-35B. Validated on MI350x/gfx950 only — MI300X/MI325X unvalidated.)
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).
      (Mirrors the existing AMD accuracy tests on this lane.)

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

---

cc @HaiShaw @kkHuang-amd @hubertlu-tw (assignees of #23299) · @Hanming-Lu (#14792 author of extra_buffer)
Related: #23299 (this feature) · #22908 (stopgap replaced) · #14792 / #23654 / #23891 (CUDA/MUSA/NPU precedent) ·
#20791 (GDN state-correctness methodology; Triton path robust)



















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29390760809](https://github.com/sgl-project/sglang/actions/runs/29390760809)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29390760749](https://github.com/sgl-project/sglang/actions/runs/29390760749)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
