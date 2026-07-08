---
source_id: sglang-github-closed-issues-prs
title: '[AMD] ci: run multimodal_gen unit suite on AMD'
canonical_url: https://github.com/sgl-project/sglang/pull/30309
captured_at: '2026-07-07T23:35:30.900792+00:00'
content_hash: c4a7860a8d6ac8403f5c55ef7a14b5feb0974b00f097939e0cbe73b890ce4a9c
---
# [AMD] ci: run multimodal_gen unit suite on AMD

URL: https://github.com/sgl-project/sglang/pull/30309
State: closed
Labels: amd, run-ci
Closed at: 2026-07-07T23:02:59Z
Merged at: 2026-07-07T23:02:59Z

## Motivation
The `multimodal_gen` `unit` suite is portable, CPU-style unit tests (config, sampling params, storage, loaders, VAE/attention helpers, etc.) that don't require NVIDIA hardware. The CUDA workflow already runs them via `multimodal-gen-unit-test`, but the AMD workflows only ran the `server` diffusion suite — so these tests were an AMD coverage gap on ROCm.

## Change
**1. Run the mm_gen `unit` suite on AMD** — add a `multimodal-gen-unit-test-amd` job (`run_suite.py --suite unit`) inside the ROCm CI container, on **both** ROCm lanes:
- `pr-test-amd.yml` — **ROCm 7.0.0**: `multimodal-gen-unit-test-amd`
- `pr-test-amd-rocm720.yml` — **ROCm 7.2.0**: `multimodal-gen-unit-test-amd-rocm720`

Both are wired into the `target_stage_select` dropdown and the `pr-test-amd*-finish` gate.

**2. Count it in the CI Coverage Overview** — `scripts/ci/utils/ci_coverage_report.py`:
- `_MM_GEN_SUBDIR_BACKENDS["unit"]` → `("CUDA", "AMD")` (was CUDA-only) so the daily coverage report credits AMD for the ~50 `unit/` files now running on ROCm (AMD enabled ≈ 389 → ~439).
- Add rules for the restructured subdirs that previously `matched no backend rule` and were dropped entirely — `single_test_file`, `single_test_file/component_accuracy`, `unit/realtime`, `unit/sana_wm`, `unit/progressive_resolution` (→ CUDA where they run today; AMD parity for standalone server files is follow-up) and `unit/musa/layers` (→ MUSA).

### CUDA-only exclusion
`test_ltx2_vae_channels_last.py` is skipped via `-k "not ltx2_vae_channels_last"`: it asserts CUDA `channels_last_3d` memory-format behavior (`y.is_contiguous(memory_format=torch.channels_last_3d)`) that the ROCm conv path doesn't reproduce. The rest of the suite is portable. (Mirrors how the AMD server job uses `-k "not flux_2"`.)

## Tests added to AMD coverage
**50 `multimodal_gen/unit` test files** now run on AMD → **676 passed, 1 skipped, 5 deselected** (the excluded `ltx2_vae_channels_last`), per the pytest summary.

<details>
<summary>Per-file test-function counts (50 files, 647 test functions pre-parametrization)</summary>

| Test file | # test funcs |
|-----------|-------------:|
| `test_server_args.py` | 117 |
| `test_disagg_roles.py` | 47 |
| `test_cosmos3.py` | 37 |
| `test_ideogram4.py` | 36 |
| `test_rollout_api.py` | 34 |
| `test_cfg_parallel_warmup.py` | 34 |
| `test_sampling_params.py` | 26 |
| `test_nvtx_pytorch_hooks.py` | 25 |
| `test_sp_shard.py` | 22 |
| `test_consistency_metrics.py` | 19 |
| `test_vae_spatial_parallel_decode.py` | 18 |
| `test_transformer_quant.py` | 18 |
| `test_input_validation.py` | 18 |
| `test_encoder_world_folding.py` | 18 |
| `test_vae_loader.py` | 16 |
| `test_layerwise_offload.py` | 15 |
| `test_storage.py` | 9 |
| `test_resolve_prompts.py` | 9 |
| `test_multi_output_grouping.py` | 9 |
| `test_latent_upsampler_group_norm_silu.py` | 8 |
| `test_cuda_attention_backend.py` | 8 |
| `test_decoding_stage_parallelism.py` | 7 |
| `test_cache_dit_integration.py` | 7 |
| `test_text_encoder_loader.py` | 6 |
| `test_scheduler_rollout_unit.py` | 6 |
| `test_pipeline_executor.py` | 6 |
| `test_disagg_trace.py` | 6 |
| `test_turbo_wan_backend.py` | 5 |
| `test_openai_utils.py` | 5 |
| `test_ipc_array.py` | 5 |
| `test_component_loading_order.py` | 5 |
| `test_precision_consistency.py` | 4 |
| `test_parallel_linear_weight_loading.py` | 4 |
| `test_fp32_layernorm.py` | 4 |
| `test_cfg_gating.py` | 4 |
| `test_wan_ti2v_helpers.py` | 3 |
| `test_text_encoding_cache.py` | 3 |
| `test_lora_commit_as_base.py` | 3 |
| `test_launch_server_shutdown.py` | 3 |
| `test_diffusion_generator_shutdown.py` | 3 |
| `test_cli_generate_common.py` | 3 |
| `test_pipeline_stage_profiling.py` | 2 |
| `test_output_saving.py` | 2 |
| `test_lora_pipeline.py` | 2 |
| `test_zimage_pipeline_config.py` | 1 |
| `test_video_sparse_attention.py` | 1 |
| `test_qwen_image_layered.py` | 1 |
| `test_lora_inference_mode.py` | 1 |
| `test_lora_format_adapter.py` | 1 |
| `test_cfg_policy.py` | 1 |

</details>

## Test — both ROCm lanes green
| Lane | Run | Result | Test runtime | Full job |
|------|-----|--------|--------------|----------|
| ROCm 7.0.0 | https://github.com/sgl-project/sglang/actions/runs/28893667717 | ✅ success | ~2m05s | ~10m55s |
| ROCm 7.2.0 | https://github.com/sgl-project/sglang/actions/runs/28894795328 | ✅ success | ~2m14s | ~10m12s |

(*Test runtime* = the `Run diffusion unit tests` step; *Full job* includes container start + dependency install.)

Initial ROCm 7.0.0 run before the exclusion (https://github.com/sgl-project/sglang/actions/runs/28845749022) was **678 passed / 1 skipped / 3 failed** in ~71s, where the only 3 failures were exactly the `ltx2_vae_channels_last` tests now excluded.
