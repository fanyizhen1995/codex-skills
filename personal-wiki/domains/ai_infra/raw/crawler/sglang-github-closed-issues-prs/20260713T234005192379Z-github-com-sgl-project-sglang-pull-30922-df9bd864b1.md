---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Skip building the Indexer on skip_topk (shared) layers'
canonical_url: https://github.com/sgl-project/sglang/pull/30922
captured_at: '2026-07-13T23:40:05.192379+00:00'
content_hash: df9bd864b1ffb940198ba1cd38fb939f8cbcede265ce7f84ae67002fb5f5a119
---
# [DSA] Skip building the Indexer on skip_topk (shared) layers

URL: https://github.com/sgl-project/sglang/pull/30922
State: closed
Labels: deepseek, npu
Closed at: 2026-07-13T04:04:22Z
Merged at: 

## Motivation

DSA models with cross-layer index-top-k sharing (e.g. GLM-5.2: `index_topk_freq=4`, `index_skip_topk_offset=3` → 21 full / 57 shared of 78 layers) never run the indexer on `skip_topk` (shared) layers, and the checkpoint carries no indexer weights for them — yet `DeepseekV2AttentionMLA` builds an `Indexer` module on every layer. The shared layers' indexers hold **uninitialized weights that are never used**: ~18.7 MB/layer in bf16 (`wq_b [4096, 2048]` + `wk [128, 6144]` + `weights_proj [32, 6144]`), all `ReplicatedLinear`, so the waste is **per-GPU and does not shard with TP** (~1.07 GB bf16 / ~0.55 GB FP8 per GPU on GLM-5.2).

Keeping never-run modules with uninitialized weights is also a footgun: the `should_run_indexer` docstring already documents a garbling bug from accidentally running them, and the NPU path currently has two ungated call sites that do exactly that on shared layers.

TensorRT-LLM's DSA sharing implementation builds the indexer only on full layers (NVIDIA/TensorRT-LLM#15574), and SGLang's own DeepSeek-V4 code sets `self.indexer = None` on non-C4 layers — this PR applies the same pattern to DSA.

## Modifications

- `deepseek_v2.py`: compute `skip_topk` before constructing the `Indexer`; build it only for `is_nextn or not skip_topk`, else `self.indexer = None`. The NextN layer keeps its indexer (it has checkpoint weights and `should_run_indexer` runs it when no carried top-k is available). The weight loader needs no changes: shared layers have no indexer weights in the checkpoint.
- `deepseek_v2_attention_mla_npu.py`: gate the two previously ungated `m.indexer(...)` call sites with `should_run_indexer()`, mirroring the CUDA `forward_mha`/`forward_mla` paths. Previously these ran **uninitialized** indexer weights on shared layers (fill-only dead work in the MHA path; garbage top-k in the MLA-prepare path).

All CUDA call sites were audited: `forward_mla.py` (2) and `forward_mha.py` (1) are already gated by `should_run_indexer`, and `maybe_capture_indexer_topk` mirroring for shared layers is unchanged.

## Accuracy Tests

8-layer GLM-5.2 config (`indexer_types = F F F S S S F S`, real dims, dummy weights, B200):

| | main | this PR |
|---|---|---|
| Load weight mem usage | 13.63 GB | **13.56 GB** (−70 MB = 4 shared indexers × 18.7 MB) |
| Greedy output ids | `[40472, 76288, 138027, ...]` | **identical** |

Dense-DSA regression (same config without `index_topk_freq`, i.e. DeepSeek-V3.2-style per-layer indexer): 13.63 GB load mem — identical to main, all indexers built, generation OK.

Full GLM-5.2 (78 layers): saves ~0.55 GB (FP8) per GPU, every TP rank.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests) (existing GLM-5.2 / DeepSeek-V3.2 registered tests cover both construction paths; a hermetic unit test for the layer-placement helper lands with the follow-up compact-cache PR).
- [x] Provide accuracy and speed benchmark results.

cc @mattteochen @zRzRzRzRzRzRzR







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29185108004](https://github.com/sgl-project/sglang/actions/runs/29185108004)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29185107929](https://github.com/sgl-project/sglang/actions/runs/29185107929)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
