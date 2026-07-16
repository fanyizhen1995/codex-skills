---
source_id: sglang-github-closed-issues-prs
title: '[EAGLE] Fuse topk=1 draft argmax, position advance, and token store into Triton
  kernels'
canonical_url: https://github.com/sgl-project/sglang/pull/30292
captured_at: '2026-07-10T23:37:20.322945+00:00'
content_hash: 29a86bb4f96371eb354a4fb595a37bc0cf27d0de0d9a5baf7959f097ea74d6e9
---
# [EAGLE] Fuse topk=1 draft argmax, position advance, and token store into Triton kernels

URL: https://github.com/sgl-project/sglang/pull/30292
State: closed
Labels: 
Closed at: 2026-07-10T14:08:23Z
Merged at: 

## Motivation

This stacked GLM-5.2 MTP draft optimization branch targets three repeated costs inside EAGLE/MTP speculative decoding under CUDA graph replay:

1. **`topk=1` draft postprocess**: PyTorch eager `argmax` over 129k-151k draft logits has too little parallelism at small decode batch sizes, and the chain-shaped draft tree still paid extra tensor/list materialization.
2. **Draft-model vocab-parallel embedding**: the TP local embedding path emitted separate mask pointwise kernels, `F.embedding`/`indexSelectSmallIndex`, and `masked_fill_kernel` for every draft forward.
3. **Draft capture eager input staging**: multi-step draft CUDA graph capture routes per-step forwards through the eager runner; staging graph-stable draft buffers into the eager registry records redundant copy nodes in the captured graph.

The goal is to reduce draft-loop launch count and remove redundant copies without changing the speculative decoding semantics.

## Modifications

### 1. Fuse `topk=1` draft postprocess

- Add `speculative/triton_ops/topk1.py` with a split-reduction argmax path (`draft_topk1_postprocess`).
- Split the vocab across CTAs, then finalize the winning split with torch-compatible argmax tie-breaking.
- Fuse position advance and, on the CUDA fast path, the draft-token column store into the finalize kernel.
- In `eagle_worker_v2.draft_forward`, special-case `topk == 1` as a chain:
  - materialize the `(bs, num_steps)` draft-token matrix directly,
  - skip `select_top_k_tokens`, per-step token lists, and post-loop `torch.cat`,
  - keep non-CUDA / rejection-sampling fallback behavior intact.

### 2. Fuse TP vocab-parallel embedding in the draft model

- Add a fused Triton vocab-parallel embedding kernel for the standard unquantized path.
- The fused kernel directly writes zero rows for out-of-shard token ids and gathers local rows for in-shard ids.
- Enable the fused path only when the safe conditions hold:
  - `tp_size > 1`,
  - CUDA contiguous int32/int64 token ids,
  - unquantized embedding method,
  - CUDA fp16/bf16/fp32 2D weight with contiguous columns.
- Keep existing PyTorch/compiled fallback for CPU/NPU, TP1, quantized/custom embedding methods, unsupported layouts, or when disabled.
- Add kill-switch: `SGLANG_OPT_USE_TRITON_VOCAB_PARALLEL_EMBEDDING=0`.

### 3. Remove redundant eager input staging during draft CUDA graph capture

- Add `ForwardBatch.skip_eager_input_staging` to explicitly mark batches backed by persistent graph buffers.
- Set this flag for EAGLE draft and frozen-KV MTP draft CUDA graph capture batches.
- Change `EagerRunner.load_batch` so generic capture mode still stages by default; no-copy is used only for:
  - the global `SGLANG_EAGER_INPUT_NO_COPY` override, or
  - an explicit `skip_eager_input_staging` batch.
- Rename the capture-specific env to `SGLANG_EAGER_INPUT_NO_COPY_IN_DRAFT_CAPTURE`.

Why this is safe for draft capture: those `ForwardBatch` fields are views into the draft graph runner's persistent `self.buffers`; replay refreshes contents in-place, so captured tensor addresses remain stable. Generic capture mode alone does not prove that aliasing contract, so it continues to stage.

## Accuracy Tests

Server:
```bash
sglang serve \
  --model-path zai-org/GLM-5.2-FP8 \
  --tp 8 \
  --dp 8 \
  --enable-dp-attention \
  --moe-a2a-backend deepep \
  --mem-fraction-static 0.85 \
  --max-running-requests 256 \
  --host 0.0.0.0
```

## Speed Tests and Profiling

B300 perf with GLM5.2-FP8

| Section | main | PR | speedup |
| --- | ---: | ---: | ---: |
| `draft` GPU range total | 1.138ms | 0.958ms | 1.19x |
| `draft_postprocess` + `vocab` GPU range total | 60.7us | 13.9us | 4.37x |

main:
<img width="1772" height="528" alt="Screenshot 2026-07-08 at 12 12 32" src="https://github.com/user-attachments/assets/5bd83d7d-76e0-49ee-b75b-09bbe9056264" />

PR:
<img width="1525" height="525" alt="Screenshot 2026-07-08 at 12 12 48" src="https://github.com/user-attachments/assets/07594769-21b7-4dfa-9547-c91597efa268" />

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). N/A: internal kernel fast paths with env kill-switches.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).
