---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix Quark MXFP4 MTP load when nextn layer is bf16 (GLM-5.2): de…'
canonical_url: https://github.com/sgl-project/sglang/pull/30379
captured_at: '2026-07-09T23:36:35.339595+00:00'
content_hash: 384ba8dbc157efa192f209b88cbc872fccb9859e8e9cbaa40ab0d0946aaf3d50
---
# [AMD] Fix Quark MXFP4 MTP load when nextn layer is bf16 (GLM-5.2): de…

URL: https://github.com/sgl-project/sglang/pull/30379
State: closed
Labels: deepseek
Closed at: 2026-07-09T06:13:09Z
Merged at: 


<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Serving GLM-5.2-MXFP4 (AMD Quark) with MTP/EAGLE enabled crashes at model load.
Quark records the MTP/nextn layer's excluded (bf16) weights and per-module
quant schemes under the **checkpoint** prefix `model.layers.<N>.*` (e.g.
`model.layers.78.eh_proj`). But SGLang builds the draft/MTP runtime modules
under different names — MTP-specific weights under `model.*`, the decoder block
under `model.decoder.*`, and the fused routed experts are queried by the coarse
module prefix `model.decoder.mlp.experts`.
Because of this prefix/granularity mismatch:
- `exclude_layers` lookups miss, so bf16 MTP weights get built as MXFP4 →
  shape/dtype mismatch at load (e.g. `eh_proj` `[6144, 6144] uint8` vs
  `[6144, 12288] bf16`; draft-worker fused-MoE `tensor a (3072) must match
  tensor b (6144)`).
- `layer_quant_config` scheme lookups also miss and silently fall back to the
  wrong scheme.
The existing DeepSeek NextN mapper only handles the 61-layer case
(`model.layers.61 -> model.decoder`), which does not apply to GLM-5.2 (78
layers).

## Modifications

- Add `GlmMoeDsaForCausalLMNextN` (in `glm4_moe.py`) and route GLM DSA draft
  models to it instead of reusing `DeepseekV3ForCausalLMNextN`.
- Extract `_resolve_nextn_quant_config()` in the base NextN class so GLM can
  override the quant-config resolution cleanly (base behavior unchanged).
- In the GLM override, remap MTP `exclude_layers` and `layer_quant_config`
  keys from checkpoint names to the runtime names SGLang queries:
  - `model.layers.<N>.{eh_proj,enorm,hnorm,shared_head.norm}` → `model.*`
  - other decoder-block weights → `model.decoder.*`
  - when any routed expert of the MTP layer is excluded, also add the coarse
    fused-MoE prefix `model.decoder.mlp.experts`
  This keeps **mixed precision**: excluded MTP modules stay bf16 while the rest
  of the draft modules use their Quark quant config.
- Copy the `quant_config` (including the nested `quant_config` dict) before the
  remap so a shared/cached instance is never mutated in place.
- Add a GPU-free unit test (`test_nextn_quark_exclude.py`) covering the remap,
  the fused-MoE coarse prefix, and the no-mutation guarantee.

## Accuracy Tests


bf16 is the faithful representation of the excluded GLM-5.2 nextn weights, so
MTP accept rate and main-path accuracy are unaffected.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28922188565](https://github.com/sgl-project/sglang/actions/runs/28922188565)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28922188379](https://github.com/sgl-project/sglang/actions/runs/28922188379)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
