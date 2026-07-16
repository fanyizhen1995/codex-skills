---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Fix Qwen MoE CUDA graph padding rows'
canonical_url: https://github.com/sgl-project/sglang/pull/30895
captured_at: '2026-07-13T23:40:05.162479+00:00'
content_hash: f644ec91730eb931f0858a57406159d9ea1424eb57bba19932ecd16a3fe703cc
---
# [Bugfix] Fix Qwen MoE CUDA graph padding rows

URL: https://github.com/sgl-project/sglang/pull/30895
State: closed
Labels: 
Closed at: 2026-07-13T22:11:22Z
Merged at: 

## Motivation

CUDA graph decode can pad a real batch to a captured batch size. In the
standard (non-DeepEP) Qwen2/Qwen3.5 MoE path, the real token count was not
forwarded to `TopK`, and the shared-expert merge could leave non-zero output in
graph-only rows. Those synthetic rows then entered the post-expert TP
collective.

With online weight updates and post-resume graph recapture, this caused a
multi-rank decode hang after a padded graph replay. Disabling CUDA graph
padding avoided the failure, but also gave up the intended graph coverage.

## Modifications

- Thread `ForwardBatch` through the standard and dual-stream routed-expert
  paths.
- Pass `num_token_non_padded` to `TopK`, matching the existing DeepEP path.
- Zero graph-only rows after routed and shared experts are merged and before
  the post-expert TP all-reduce.
- Add a deterministic CPU regression test for both the TopK metadata and the
  final padded output rows.

## Accuracy Tests

Pure SGLang model-level regression:

```text
python3 test/registered/unit/models/test_qwen2_moe_padding.py -v

test_standard_moe_path_masks_and_zeroes_padded_rows ... ok
Ran 1 test in 0.001s
OK
```

The test invokes the real `Qwen2MoeSparseMoeBlock.forward` control flow with
lightweight test doubles. It verifies that `TopK` receives the same
`num_token_non_padded` tensor and that only the graph-only output tail is zero.

Two-node GB200 integration A/B, using 8 SGLang ranks with padding-enabled
decode graphs and online weight updates:

| Variant | Result |
| --- | --- |
| TopK padded-row masking only | Second rollout hung at 51 real requests replaying the size-64 graph |
| TopK masking + output-tail zeroing | Two rollouts and two training updates completed |

Successful two-update metrics:

| Metric | Update 0 | Update 1 |
| --- | ---: | ---: |
| Mean response length | 18,736.00 | 6,699.26 |
| OPD reverse-KL | 0.044982 | 0.013613 |
| Grad norm | 0.313641 | 0.154027 |
| OIS | 1.0000002 | 1.0000001 |
| ESS | 0.9999980 | 0.9999998 |
| TIS | 1.0000207 | 0.9999925 |

The successful run crossed padded graph buckets at 255, 127, 65, 52, 51, and
50 real requests after the first weight update, then completed the second
update. No FlashInfer source change was used.

## Speed Tests and Profiling

No standalone microbenchmark was run. The added tail mask is device-side and
is captured as part of the decode CUDA graph when padded-token metadata is
enabled.

## Checklist

- [x] Format code with Black and isort; run Ruff checks.
- [x] Add a registered CPU unit test.
- [ ] Documentation update (not needed for this model-forward bug fix).
- [x] Provide accuracy/integration results above.
- [x] Follow the SGLang code style guidance.








<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29168512812](https://github.com/sgl-project/sglang/actions/runs/29168512812)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29168512737](https://github.com/sgl-project/sglang/actions/runs/29168512737)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
