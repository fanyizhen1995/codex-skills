---
source_id: sglang-github-closed-issues-prs
title: '[SM120] Support GLM DSA serving on RTX PRO 6000'
canonical_url: https://github.com/sgl-project/sglang/pull/29580
captured_at: '2026-07-01T02:12:08.967484+00:00'
content_hash: d08d73b5155a3964b5d0d08f672a14904a8748a9b30e37a3106cc87285a79215
---
# [SM120] Support GLM DSA serving on RTX PRO 6000

URL: https://github.com/sgl-project/sglang/pull/29580
State: closed
Labels: deepseek
Closed at: 2026-06-29T23:45:58Z
Merged at: 

## Motivation

Fixes #29562.

This PR adds a native SM120 serving path for GLM DSA / GLM-5.2-NVFP4 on RTX PRO
6000 Blackwell. With the default GLM launch, the patched path starts the TP8
server, captures CUDA graphs, passes `/health`, and completes a minimal
`/generate` request on exact SM120 hardware.

The reporter path had multiple independent blockers:

1. GLM-5.2-NVFP4 ModelOpt metadata excludes `mlp.shared_experts` from FP4
   quantization, but shared-expert fusion remapped those unquantized tensors
   into routed packed FP4 expert slots. That caused the initial `3072` vs
   `6144` loader mismatch.
2. After disabling shared-expert fusion, SGLang still selected `trtllm` DSA
   backends for fp8 KV on SM120. The underlying FlashInfer TRTLLM-gen MLA path
   reports unsupported architecture on SM120.
3. Other DSA backend choices still reached
   `deep_gemm.get_paged_mqa_logits_metadata`, which is unsupported on SM120 in
   the currently pinned `sgl-deep-gemm` wheel.
4. With validated FlashInfer/DeepGEMM source builds, the old decode CUDA graph
   `max_bs=512` default OOMed during graph capture on 96GB RTX PRO 6000. An
   independent `dev-cu13` run also found `full` decode graph capture can hang.
   The current patch keeps SGLang's default `full` decode graph backend for
   consistency with the existing decode path, caps decode `max_bs` at 256 by
   default for this SM120 GLM DSA case, and still lets users explicitly select
   `tc_piecewise` as an alternative decode CUDA graph mode.
5. GLM-5.2-NVFP4 ships `index_topk_pattern: null`; the DSA IndexShare layer
   layout is encoded in `indexer_types`, so SGLang needs to derive the same F/S
   sharing pattern from checkpoint metadata instead of requiring a manual model
   config override.

## Modifications

- `glm4_moe.py`: detect ModelOpt FP4 checkpoints where shared experts are not
  quantized and automatically disable GLM shared-expert fusion for that case.
- `model_config.py`: derive the DSA top-k sharing pattern from
  checkpoint-native `indexer_types` when `index_topk_pattern` is absent,
  preserving explicit pattern precedence and the existing frequency/offset
  fallback.
- `server_args.py`: add `flashinfer_sparse_mla` as a DSA backend choice and
  select it by default for fp8 DSA on SM120. For GLM DSA on SM120, preserve the
  default `full` decode CUDA graph backend, cap the default decode graph
  `max_bs` to 256, and use the derived DSA top-k sharing pattern for the TBO
  guard. Hopper and SM100 paths keep their existing default backend selections.
- `dsa_backend.py`: call FlashInfer sparse MLA with the SM120 contract required
  by the native kernels: BF16 query, packed uint8 KV, page size 64, int32 sparse
  page tables, and `kv_scale_format="arbitrary_fp32"` for GLM.
- `forward_mla.py`: keep TRTLLM-style FP8 RoPE fusion limited to the TRTLLM
  backend so the sparse MLA path uses its own input contract.
- `Dockerfile`: add optional repo+commit source build args for FlashInfer and
  DeepGEMM so the image can use the validated dependency commits before wheels
  are released.

Validated source commits:

- FlashInfer `5f2bdc41f9ffecef9d8ed590e688e7c0f108504f`
  (includes merged SM120 sparse MLA support from
  https://github.com/flashinfer-ai/flashinfer/pull/3395)
- DeepGEMM `2073ddb2814892014c33ef4cd1c7d4c148baf1fe`
  (SM120 support merge)

Released wheel gap checked on SM120:

- `flashinfer-python==0.6.13`, `flashinfer-cubin==0.6.13`, and
  `flashinfer-jit-cache==0.6.13+cu130` import, but the released
  `trtllm_batch_decode_with_kv_cache_mla` signature still lacks
  `kv_scale_format`, so this GLM sparse MLA path needs a FlashInfer source
  build until the next wheel release.
- `sgl-deep-gemm` is still at 0.1.3, so the DeepGEMM SM120 metadata path needs
  the source commit above until a new SGLang DeepGEMM wheel is published.

The Dockerfile source override path pins the validated repos by commit hash:

```bash
--build-arg FLASHINFER_SOURCE_REPO=https://github.com/flashinfer-ai/flashinfer.git
--build-arg FLASHINFER_SOURCE_REF=5f2bdc41f9ffecef9d8ed590e688e7c0f108504f
--build-arg FLASHINFER_CUDA_ARCH_LIST=12.0f
--build-arg DEEPGEMM_SOURCE_REPO=https://github.com/deepseek-ai/DeepGEMM.git
--build-arg DEEPGEMM_SOURCE_REF=2073ddb2814892014c33ef4cd1c7d4c148baf1fe
```

I also validated this repo+commit install sequence on the exact SM120 base
image: DeepGEMM was installed from the pinned GitHub commit as
`deep_gemm 2.5.0+2073ddb`; FlashInfer was installed from the pinned GitHub
commit with `FLASHINFER_CUDA_ARCH_LIST=12.0f`, including `flashinfer-python`,
`flashinfer-cubin`, and `flashinfer-jit-cache` 0.6.13. The final probe printed
`has_kv_scale_format True`,
`deepgemm_metadata_ok Tensor (189, 2) torch.int32 cuda`, and
`repo_commit_install_ok`.

## Accuracy Tests

This PR changes the serving path for a previously unsupported SM120 GLM DSA
configuration. I did not run a full downstream accuracy benchmark such as GSM8K.
The issue-specific accuracy-relevant validation was functional generation on the
exact target hardware:

- default GLM-5.2-NVFP4 TP8 launch reached `/health`
- minimal `/generate` completed with HTTP 200 and 16 completion tokens
- the default backend change is gated to SM120, and focused tests cover the
  SM120 selection path plus existing non-SM120 routing behavior

FlashInfer sparse MLA correctness for the SM120 kernels is covered upstream by
FlashInfer's SM120 sparse MLA test suite in
https://github.com/flashinfer-ai/flashinfer/pull/3395.

## Speed Tests and Profiling

I did not run a throughput benchmark or profiler sweep for this patch. The
performance-relevant validation was that the SM120 path keeps CUDA graphs
enabled:

- old decode CUDA graph `max_bs=512` OOMed during graph capture on 96GB RTX PRO
  6000
- independent `dev-cu13` validation found `full` decode graph capture can hang,
  while `tc_piecewise` decode capture works
- the patched default keeps the `full` decode graph backend for consistency
  with the existing decode path and caps GLM DSA SM120 decode graph `max_bs` to
  256
- explicit `tc_piecewise` remains available as an alternative decode CUDA graph
  mode
- prefill CUDA graph capture completed
- decode CUDA graph capture completed
- FlashInfer autotune completed

## Tests

Exact SM120 hardware:

- 8 x NVIDIA RTX PRO 6000 Blackwell Server Edition
- compute capability SM120
- driver `580.159.03`, CUDA `13.0` host / `13.0.1` container
- base image `lmsysorg/sglang:dev-glm52-nvfp4`
- PyTorch `2.11.0+cu130`

Baseline:

- reporter-style launch failed in the GLM shared-expert fusion loader path with
  the `3072` vs `6144` mismatch
- `--disable-shared-experts-fusion` got past load/KV allocation, then failed in
  `deep_gemm.get_paged_mqa_logits_metadata(...): Unsupported architecture`
- explicit legacy `--dsa-prefill-backend trtllm --dsa-decode-backend trtllm`
  failed with `TllmGenFmhaRunner ... Unsupported architecture`

Patched dependency probe:

```text
torch 2.11.0+cu130
cuda_cap (12, 0)
flashinfer_python 0.6.13
flashinfer-cubin 0.6.13
flashinfer-jit-cache 0.6.13
deep-gemm 2.5.0+2073ddb
deep_gemm 2.5.0+2073ddb
sgl-deep-gemm 0.1.3
has_backend True
has_kv_scale_format True
deepgemm_metadata_ok Tensor (189, 2) torch.int32 cuda
repo_commit_install_ok
```

Patched default launch:

```bash
python3 -m sglang.launch_server \
  --model-path nvidia/GLM-5.2-NVFP4 \
  --tensor-parallel-size 8 \
  --quantization modelopt_fp4 \
  --tool-call-parser glm47 \
  --reasoning-parser glm45 \
  --trust-remote-code \
  --mem-fraction-static 0.8 \
  --host 0.0.0.0 \
  --port 30000
```

Result:

- selected `prefill=flashinfer_sparse_mla`, `decode=flashinfer_sparse_mla`
- auto-disabled incompatible shared-expert fusion
- allocated fp8 KV cache successfully (`368768` tokens/rank, `21.11 GB`/rank)
- FlashInfer autotune completed
- prefill CUDA graph capture completed
- decode CUDA graph capture completed
- `/health` passed
- minimal `/generate` completed with HTTP 200 and 16 completion tokens

Latest SM120 rerun after the `tc_piecewise` decode graph follow-up, on PR head
`cf638d6e6b0b1138128196d2349da18460b06d44`:

- source-pinned dependency image still reports `has_kv_scale_format True` and
  DeepGEMM metadata support
- focused unit checks passed:
  `99 passed, 18 warnings, 10 subtests passed`
- default launch above selected `flashinfer_sparse_mla`
- `cuda_graph_config.decode.backend` defaulted to `tc_piecewise` with
  `max_bs=256`
- all eight ranks loaded `GlmMoeDsaForCausalLM` with `modelopt_fp4` / `NVFP4`
- allocated fp8 KV cache successfully (`368768` tokens/rank, `21.11 GB`/rank)
- prefill CUDA graph capture completed with `backend=tc_piecewise`
- decode CUDA graph capture completed with `backend=tc_piecewise` and
  `bs=[1, 2, 4, ..., 256]`
- `/health` passed
- minimal `/generate` completed with HTTP 200 and 16 completion tokens
- failure grep was clean for `Unsupported architecture`, `TllmGenFmhaRunner`,
  `Traceback`, `OutOfMemory`, `RuntimeError`, `ValueError`, `3072`, and `6144`

Local checks:

```bash
git diff --check
```

```bash
python3 -m py_compile \
  python/sglang/srt/layers/attention/dsa_backend.py \
  python/sglang/srt/server_args.py
python3 scripts/ci/check_registered_tests.py
python3 scripts/ci/check_no_registered_tests_in_package.py
```

Follow-up after independent `dev-cu13` validation of the native path:

```bash
git diff --check
python3 -m py_compile \
  python/sglang/srt/server_args.py \
  test/registered/unit/server_args/test_server_args.py
python3 scripts/ci/check_registered_tests.py
python3 scripts/ci/check_no_registered_tests_in_package.py
```

```bash
PYTHONPATH=python python3 -m pytest \
  test/registered/unit/server_args/test_server_args.py \
  test/registered/unit/models/test_glm4_moe.py \
  test/registered/unit/models/test_deepseek_mla_forward.py -q
# 99 passed, 18 warnings, 10 subtests passed
```

SM120 runtime rerun for the earlier `tc_piecewise` default follow-up:

```bash
python3 -m sglang.launch_server \
  --model-path nvidia/GLM-5.2-NVFP4 \
  --tensor-parallel-size 8 \
  --quantization modelopt_fp4 \
  --tool-call-parser glm47 \
  --reasoning-parser glm45 \
  --trust-remote-code \
  --mem-fraction-static 0.8 \
  --host 0.0.0.0 \
  --port 30000
```

Result: selected `flashinfer_sparse_mla`, defaulted decode CUDA graph backend to
`tc_piecewise`, completed prefill and decode CUDA graph capture, passed
`/health`, returned HTTP 200 for minimal `/generate`, and had a clean failure
grep.

Latest follow-up for GLM-5.2 `indexer_types` metadata and default `full` decode
graph validation, on PR head `005ffc65dc0f72d42a1436c31ef129ed98cccc58`:

- cached GLM-5.2-NVFP4 config has `index_topk_pattern: null` and 78
  `indexer_types` entries describing the `full`/`shared` layer layout
- source-pinned image focused tests passed:
  `97 passed, 18 warnings, 10 subtests passed`
- the default launch above selected `flashinfer_sparse_mla`
- `cuda_graph_config.decode.backend` remained `full` with `max_bs=256`
- prefill CUDA graph capture completed with `backend=tc_piecewise`
- decode CUDA graph capture completed with `backend=full` and
  `bs=[1, 2, 4, ..., 256]`
- `/health` passed
- minimal `/generate` completed with HTTP 200 and 16 completion tokens
- no `index_topk_pattern` override or manual decode backend flag was used
- focused tests cover default `full`, explicit `full`, explicit `tc_piecewise`,
  and explicit disabled decode CUDA graph behavior
- previous explicit `full` checks also passed at `--cuda-graph-max-bs-decode 32`
  and at the PR's automatic `max_bs=256` cap

GitHub Actions:

- `lint` passed on head `cf638d6e6b0b1138128196d2349da18460b06d44`
- the latest amended head `005ffc65dc0f72d42a1436c31ef129ed98cccc58` needs the
  normal GitHub check rerun
- remaining red PR checks are `pr-gate` failures due missing maintainer `run-ci`
  authorization/label, not test job failures

Validation gaps:

- I did not rerun Hopper/H200 or SM100/B200 full-server controls in this patch.
- The backend default change is gated to SM120, and the focused tests cover the
  SM120 selection path plus existing non-SM120 routing behavior.
- Released FlashInfer and `sgl-deep-gemm` wheels still need follow-up releases.
  Until then, the Dockerfile source-pinned build args above are the validated
  way for the SGLang image to carry this path.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit). `git diff --check` and GitHub `lint` passed.
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). Focused unit tests were added/updated for GLM fusion, SM120 DSA routing, sparse MLA call contract, DSA `indexer_types` pattern derivation, and non-SM120 routing.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). No separate user-facing docs are needed; the PR body documents the source-pinned dependency path and wheel gap.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). See the Accuracy Tests and Speed Tests sections for the issue-specific validation and remaining benchmark gap.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28357834679](https://github.com/sgl-project/sglang/actions/runs/28357834679)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28357834575](https://github.com/sgl-project/sglang/actions/runs/28357834575)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28352062088](https://github.com/sgl-project/sglang/actions/runs/28352062088)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28352061942](https://github.com/sgl-project/sglang/actions/runs/28352061942)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
