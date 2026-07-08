---
source_id: sglang-github-closed-issues-prs
title: '[MLX] Add correctness tests for qwen2_moe and qwen3_moe'
canonical_url: https://github.com/sgl-project/sglang/pull/29440
captured_at: '2026-07-07T23:35:30.919492+00:00'
content_hash: 7e0dfbc896971408fbb59e056849631bd0388d40630738c13df137e6d37c2994
---
# [MLX] Add correctness tests for qwen2_moe and qwen3_moe

URL: https://github.com/sgl-project/sglang/pull/29440
State: closed
Labels: apple-silicon
Closed at: 2026-07-07T03:32:12Z
Merged at: 2026-07-07T03:32:12Z

## What

Correctness coverage for the Qwen MoE families (qwen2_moe / qwen3_moe) on the MLX
backend, per the Model Support section of #19137. The MLX backend runs these through
`mlx_lm`, so this adds correctness coverage on that path (no `srt/models` changes).

## Tests

- **`test/registered/unit/hardware_backend/mlx/test_mlx_reference_correctness.py`** (new)
  In-process reference-equivalence guard. Drives `MlxModelRunner` greedy decode and
  asserts it matches **unpatched `mlx_lm`** token for token (up to and including EOS),
  and that a request decoded inside a multi-request `decode_batch` matches its solo
  decode (slot isolation). Model selectable via `SGLANG_MLX_TEST_MODEL`.
- **`test/registered/mlx/models_e2e/test_qwen2_moe_mlx_correctness.py`**,
  **`test/registered/mlx/models_e2e/test_qwen3_moe_mlx_correctness.py`**
  Black-box serving smoke tests. Launch a real `SGLANG_USE_MLX=1` server and assert,
  over `/v1/chat/completions`: non-empty generation, `2+2 -> 4`, capital of France
  -> `Paris`.

All register on the CPU suite and skip where `mlx` is absent (no Apple Silicon CI
runner exists yet), so they are inert on current CI and run on Apple Silicon locally.

## Results

### Reference equivalence: `test_mlx_reference_correctness.py` on qwen2_moe (Qwen1.5-MoE-A2.7B-Chat-4bit)

The MLX runner's greedy output is an exact token-for-token match against unpatched
`mlx_lm` on every prompt:

| prompt | identical tokens | decoded output (both engines) |
|---|:---:|---|
| List the first 10 prime numbers, comma separated. | 39 / 39 | `2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31` |
| What is the capital of France? Answer in one word. | 3 / 3 | `Paris.` |
| Write one short sentence about the ocean. | 28 / 28 | `The ocean is a vast body of water that covers most of our planet and is home to diverse ecosystems and a rich variety of life.` |

Batched decode is isolated: a prompt decoded inside a multi-request batch produces the
same tokens as decoded alone. Local run:

```
test_batched_decode_matches_solo ... ok
test_greedy_matches_reference_exact ... ok
----------------------------------------------------------------------
Ran 2 tests in 13.507s

OK
```

### Smoke tests (qwen2_moe and qwen3_moe)

Both pass in local runs: server launches under `SGLANG_USE_MLX=1`, and
`/v1/chat/completions` returns non-empty output with `2+2 -> 4` and capital of France
-> `Paris`. This revision only adds CI registration (validated by the
`check-registered-tests` hook); the assertion logic is unchanged from the original
runs. The reference test above also covers qwen3_moe (Qwen3-30B-A3B-4bit) via
`SGLANG_MLX_TEST_MODEL`; the exact-match was run on qwen2_moe, and the 30B weights need
a larger-memory machine to run locally. Reviewers on Apple Silicon should re-run before
merge.

## Follow-ups for first-class MoE support (#19137, not in this PR)

- Radix-cache-on correctness for MoE: every test here runs with the radix cache off;
  the radix path needs the scheduler, so that test will be server based.
- Batched concurrent prefill: decode already batches across requests, but the serving
  path prefills one request at a time. Batching it is worth doing for these families.







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28837854567](https://github.com/sgl-project/sglang/actions/runs/28837854567)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28837854475](https://github.com/sgl-project/sglang/actions/runs/28837854475)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
