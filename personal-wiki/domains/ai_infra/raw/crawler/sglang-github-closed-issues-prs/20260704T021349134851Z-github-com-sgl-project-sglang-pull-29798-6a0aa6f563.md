---
source_id: sglang-github-closed-issues-prs
title: 'fix: avoid DSA indexer CPU seq lens fallback'
canonical_url: https://github.com/sgl-project/sglang/pull/29798
captured_at: '2026-07-04T02:13:49.134851+00:00'
content_hash: 6a0aa6f56367e4b21fd1f391a000c54f6fc5e6f5d51602f66122841b29e6600f
---
# fix: avoid DSA indexer CPU seq lens fallback

URL: https://github.com/sgl-project/sglang/pull/29798
State: closed
Labels: 
Closed at: 2026-07-03T05:50:24Z
Merged at: 2026-07-03T05:50:24Z

## Summary

Fixes DSA eager fallback crashes in GLM-5.2 NVFP4 MTP/EAGLE draft decode when the decode batch falls outside the captured CUDA graph range and `seq_lens_cpu` is absent.

The fix keeps the DSA multistep draft backend on its existing GPU-only path (`needs_cpu_seq_lens=False`) and handles only the eager fallback gaps:
- the DSA indexer empty-batch guard uses `forward_batch.seq_lens.numel()` instead of asserting on the CPU mirror;
- draft-extend prepares the host-side lengths required by DSA metadata planning only when CUDA graph replay cannot be used.

This is only relevant when a decode step exceeds `--cuda-graph-max-bs` / `--cuda-graph-max-bs-decode` and runs outside CUDA graph replay. For batches covered by CUDA graph capture, this PR does not request `seq_lens_cpu` and should not add a D2H synchronization.

## Reproduction

Hardware / model:
- B200 node (local)
- Model: NVIDIA official GLM-5.2 NVFP4 checkpoint

Server parameters:
```bash
python -m sglang.launch_server \
  --model-path <glm52-nvfp4> \
  --trust-remote-code \
  --host 0.0.0.0 \
  --port 10100 \
  --tp 4 \
  --dp 2 \
  --quantization modelopt_fp4 \
  --attention-backend dsa \
  --moe-runner-backend flashinfer_trtllm \
  --speculative-algorithm NEXTN \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --cuda-graph-max-bs 8
```

Important: the following workaround flags were intentionally **not** used:
- `--disable-flashinfer-autotune`
- `--enforce-disable-flashinfer-allreduce-fusion`
- `--disable-custom-all-reduce`

Client workload:
- Endpoint: `/v1/chat/completions`
- `total=192`
- `concurrency=32`
- `batch_size=64`
- input length around 1600 tokens
- `max_tokens=512`
- `extra_body={"chat_template_kwargs":{"enable_thinking":false}}`

Observed failures before this fix:
```text
AssertionError
  File "sglang/srt/layers/attention/dsa/dsa_indexer.py", line 1848
    assert forward_batch.seq_lens_cpu is not None
```

After fixing the indexer guard, the same fallback path also exposed the missing draft-extend metadata:
```text
AssertionError: All of them must not be None
  File "sglang/srt/layers/attention/dsa_backend.py", line 735
    forward_batch.extend_seq_lens_cpu is not None
```

The server log showed decode running outside graph replay, e.g. `Decode batch ... cuda graph: False`, because `--cuda-graph-max-bs` was 8 while the active decode batch was larger.

## Why this shape

An earlier local workaround was to set `DeepseekSparseAttnMultiStepBackend.needs_cpu_seq_lens=True`. That fixes the assertion but makes all spec-v2 DSA draft decode materialize a CPU sequence-length mirror, including CUDA graph replay cases and FP8-style deployments that do not need it.

This PR instead keeps the common graph path GPU-only and populates CPU metadata only in the over-graph eager fallback, immediately before DSA metadata planning.

## Validation

- `openspec validate fix-dsa-indexer-eager-empty-batch --strict`
- `python3 -m py_compile python/sglang/srt/layers/attention/dsa/dsa_indexer.py python/sglang/srt/speculative/base_spec_worker.py`
- `git diff --check`
- B200 live reproduction after fix (local deploy build):
  - NVIDIA official NVFP4, `dp=2`, `tp=4`, MTP/NEXTN enabled
  - `--cuda-graph-max-bs 8`
  - no `--disable-flashinfer-autotune`, no `--enforce-disable-flashinfer-allreduce-fusion`, no `--disable-custom-all-reduce`
  - health smoke: HTTP 200, chat `1+1` returned `2`
  - decode repro: `total=192`, `concurrency=32`, `batch_size=64`; all requests returned HTTP 200
  - post-run health: HTTP 200
  - log contained `Decode batch ... cuda graph: False` and no `seq_lens_cpu` / `All of them must not be None` / scheduler crash














<sub>✨ Presented to you with <a href=" ">Mind Lab</a > — A Lab for Experiential Intelligence.</sub>
















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28633325652](https://github.com/sgl-project/sglang/actions/runs/28633325652)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28633325530](https://github.com/sgl-project/sglang/actions/runs/28633325530)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
