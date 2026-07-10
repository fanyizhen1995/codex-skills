---
source_id: sglang-github-closed-issues-prs
title: '[DSV4] Fix draft SWA transfer for disaggregated MTP'
canonical_url: https://github.com/sgl-project/sglang/pull/30461
captured_at: '2026-07-09T23:36:35.325259+00:00'
content_hash: 9a411df85a03123fe8aee65fc60e6224a7c6eb9d2406793b50bbb33823f6a7b1
---
# [DSV4] Fix draft SWA transfer for disaggregated MTP

URL: https://github.com/sgl-project/sglang/pull/30461
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-09T05:18:34Z
Merged at: 2026-07-09T05:18:34Z

## Motivation

When both prefill and decode enable EAGLE for DeepSeek V4, prefill builds prompt SWA state for the draft NextN layer. Disaggregation already registers the draft pool's contiguous KV buffers, but the DSV4 NextN layer has compression ratio 0 and stores its state in the paged SWA pool, or in the SWA-ring prefix of the unified KV pool. Those buffers were not registered, so decode started with missing or stale draft prompt state until newly generated tokens refilled the sliding window.

This is the DSV4/SWA counterpart of #23539. The draft worker shares the target request pool and SWA allocator mapping; unified mode also uses matching ring geometry. Therefore the draft buffers can reuse the existing SWA transport types. They are registered as a separate positional component so they do not become part of the target model's heterogeneous DSV4 state layout. This change is limited to the non-NPU DSV4 path.

## Modifications

- Register paged draft NextN state as an additional `StateType.SWA` component and unified draft ring buffers as an additional `StateType.SWA_RING` component.
- Validate the existing DSV4 invariants used for shared indexing: SWA-only draft layers, matching pool mode and geometry, and a shared paged SWA mapping.
- Reuse the existing state-component wire format and SWA transfer dispatch; no draft-specific state type or backend changes are added.
- Add focused CPU coverage for paged and unified draft-state registration.

## Accuracy Tests

- A 20-sample GSM8K smoke test on a 1P1D DSV4 deployment with real bilateral EAGLE completed with non-empty responses and no KV registration or transfer failures.
- Patched result: 90% strict match and 95% flexible match. This small smoke test is a functional check, not a statistical accuracy claim.

## Speed Tests and Profiling

With EAGLE top-k 1, 3 speculative steps, and 4 draft tokens:

The strongest improvement appears in the early decode window, before locally generated tokens replace the transferred 128-token draft SWA prompt state. After aligning each DP rank at its first stable decode batch:

| Stable decode window | Main AL | Patched AL | Change |
|---|---:|---:|---:|
| First 8 verify steps | 2.4844 | 2.9219 | +17.61% |
| First 16 verify steps | 2.5625 | 2.9531 | +15.24% |
| First 32 verify steps | 2.6094 | 2.9531 | +13.17% |

This time-segmented result directly matches the failure mode: the missing prompt SWA state hurts draft proposals most at the beginning, and its impact decays as newly generated tokens fill the local SWA window.

Across the full requests, the improvement is diluted by later decode steps after the local SWA window has been refilled:

| Metric | Main | Patched | Change |
|---|---:|---:|---:|
| Request-weighted acceptance length | 2.8054 | 2.9139 | +3.87% |
| Request-weighted acceptance rate | 60.18% | 63.80% | +3.62 pp |

The workload is intentionally small, so these numbers validate the expected direction rather than establish an end-to-end throughput claim.

## Validation

- `python -m pytest -q test/registered/unit/disaggregation/test_disaggregation_wire.py test/registered/unit/disaggregation/test_minimax_sparse_disagg_state_kv_args.py` (18 passed, 2 subtests passed)
- `pre-commit run --all-files --show-diff-on-failure`

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Documentation is not required for this internal state-transfer fix.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28919874867](https://github.com/sgl-project/sglang/actions/runs/28919874867)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28919874782](https://github.com/sgl-project/sglang/actions/runs/28919874782)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
