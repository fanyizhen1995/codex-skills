---
source_id: sglang-github-closed-issues-prs
title: '[AMD][DeepSeek V4] Fix default FlashMLA sparse prefill off on ROCm/HIP'
canonical_url: https://github.com/sgl-project/sglang/pull/29982
captured_at: '2026-07-03T02:13:21.694488+00:00'
content_hash: 15905e82bb1985b0a27d8e67817c356182ecf0a931d8757bfbb1860210e693b5
---
# [AMD][DeepSeek V4] Fix default FlashMLA sparse prefill off on ROCm/HIP

URL: https://github.com/sgl-project/sglang/pull/29982
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-02T23:00:09Z
Merged at: 2026-07-02T23:00:09Z

## Motivation

#29775 flipped `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` to **default-on** for all DeepSeek-V4 runs. Starting with the first `main` nightly that included it, the **AMD MI355X 1P1D disaggregation nightly** ([`Nightly Test (AMD MI355X 2N 1P1D Disagg)`](https://github.com/sgl-project/sglang/actions/workflows/nightly-amd-mi355x-disagg.yml)) regressed for **DeepSeek-V4-Flash** while **DeepSeek-V4-Pro stayed green**.

Failing run: [#28565894749](https://github.com/sgl-project/sglang/actions/runs/28565894749) (scheduled, `main`, 2026-07-02). Every `dsv4flash` job (fp8/fp4, base/mtp/dp8ep8) failed; every `dsv4pro` job passed.

### Evidence it is the sparse prefill path

- The 07-01 nightly ([#28494350421](https://github.com/sgl-project/sglang/actions/runs/28494350421)) was green and already contained the `transformers` 5.12.1 bump (#29393), ruling that out. The regression window is the commits merged between the 07-01 and 07-02 runs; #29775 (merged 2026-07-01) is the DSV4-specific change that flips this default.
- On the decode worker the disagg **warmup returns garbage**: `output_ids: [0, 0, 201, 0, 410, 0, 12389, 0]` (near-all-zero). The subsequent PD `/generate` then fails to serve (decode times out -> 500 -> router 502 -> `PD path not serving; aborting`), and the GSM8K gate reports `Accuracy: <not found in bench.log>`.
- DeepSeek-V4-Pro on the same MI355X nodes is unaffected, i.e. the dense prefill path (the pre-#29775 default) is correct on ROCm.

## Modification

Make the default **platform-conditional** using the existing `_default_hip` callable-default pattern already used in `environ.py` (e.g. `SGLANG_DP_USE_REDUCE_SCATTER = EnvBool(_default_hip)`):

- **CUDA:** default **on** — preserves the #29775 optimization.
- **ROCm/HIP:** default **off** — restores the dense prefill path that was green on the MI355X nightly.

Explicitly setting `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` still overrides the default, so the sparse path remains available on ROCm for validation/opt-in.

```python
SGLANG_OPT_FLASHMLA_SPARSE_PREFILL = EnvBool(lambda: not _default_hip())
```

This is a conservative mitigation to unbreak the nightly; it does not touch NVIDIA behavior. cc @YAMY1234 — happy to flip ROCm back to default-on once the FlashMLA sparse prefill kernel is validated for the Flash variant on MI355X.

## Accuracy Test

- No accuracy impact on CUDA (default unchanged).
- On ROCm the default reverts to the dense prefill path that produced correct GSM8K accuracy in the prior green nightlies (e.g. [#28494350421](https://github.com/sgl-project/sglang/actions/runs/28494350421)).

## Checklist

- [x] Minimal, platform-scoped change; explicit env override preserved.
- [ ] Re-run the MI355X disagg nightly to confirm DeepSeek-V4-Flash is restored.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28626803369](https://github.com/sgl-project/sglang/actions/runs/28626803369)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28626803260](https://github.com/sgl-project/sglang/actions/runs/28626803260)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
