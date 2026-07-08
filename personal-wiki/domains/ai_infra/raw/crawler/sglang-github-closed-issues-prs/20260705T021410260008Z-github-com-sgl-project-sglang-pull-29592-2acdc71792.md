---
source_id: sglang-github-closed-issues-prs
title: 'chore: update CI test est_time values'
canonical_url: https://github.com/sgl-project/sglang/pull/29592
captured_at: '2026-07-05T02:14:10.260008+00:00'
content_hash: 2acdc7179265ee179846036fc1cc4a6b19de939c82fd7e7733de7d4a41300ce8
---
# chore: update CI test est_time values

URL: https://github.com/sgl-project/sglang/pull/29592
State: closed
Labels: quant, lora, Multi-modal, deepseek, speculative-decoding, hicache, blackwell, npu
Closed at: 2026-07-04T06:56:28Z
Merged at: 

## Summary

Refreshes `est_time` literals from [`sgl-project/sglang-ci-stats`](https://github.com/sgl-project/sglang-ci-stats)'s `model.json` (per-(suite, file) p90 over recent successful CI runs on `main`).

This keeps the LPT load-balancing algorithm accurate for partitioning tests across parallel CI jobs, and serves as the static fallback when `compute_partitions` cannot fetch the live model at PR time.

### Significant est_time changes (106 of 510 updates)

| File | Suite | Old (s) | New (s) | Δ |
| --- | --- | ---: | ---: | ---: |
| `test_deepseek_v3_cutedsl_4gpu.py` | `base-c-test-4-gpu-gb300` | 1800 | 472 | -1328 (-74%) |
| `test_vlm_models.py` | `extra-a-test-1-gpu-large` | 317 | 1603 | +1286 (+406%) |
| `test_scripted_core_4gpu.py` | `extra-b-test-4-gpu-h100` | 900 | 115 | -785 (-87%) |
| `test_tbo_shared_experts_fusion.py` | `extra-b-test-deepep-8-gpu-h200` | 900 | 183 | -717 (-80%) |
| `test_unified_radix_cache_kl_cp.py` | `extra-b-test-4-gpu-h100` | 950 | 292 | -658 (-69%) |
| `test_gemma4_dflash_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 96 | -624 (-87%) |
| `test_e2e_tp.py` | `extra-a-test-2-gpu-large` | 600 | 64 | -536 (-89%) |
| `test_e2e_pp.py` | `extra-a-test-2-gpu-large` | 600 | 67 | -533 (-89%) |
| `test_deepseek_v3_fp4.py` | `base-c-test-4-gpu-b200` | 960 | 442 | -518 (-54%) |
| `test_e2e_spec_eagle.py` | `extra-a-test-1-gpu-small` | 600 | 86 | -514 (-86%) |
| `test_gemma4_mtp_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 208 | -512 (-71%) |
| `test_deepseek_v4_flash_fp4_megamoe_b200.py` | `extra-b-test-deepep-4-gpu-b200` | 900 | 394 | -506 (-56%) |
| `test_pcg_with_speculative_decoding_dflash.py` | `base-b-test-1-gpu-small` | 531 | 72 | -459 (-86%) |
| `test_fa_skip_kv_cache_piecewise_nan.py` | `base-b-test-1-gpu-large` | 600 | 144 | -456 (-76%) |
| `test_deepseek_v3_fp4_4gpu_extra.py` | `extra-b-test-4-gpu-b200` | 960 | 509 | -451 (-47%) |
| `test_qwen35_fp4_mtp.py` | `base-c-test-4-gpu-b200` | 740 | 1187 | +447 (+60%) |
| `test_streaming_session.py` | `base-b-test-1-gpu-large` | 691 | 264 | -427 (-62%) |
| `test_bcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 107 | -424 (-80%) |
| `test_pcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 108 | -423 (-80%) |
| `test_pcg_glm5_fp8_tp8.py` | `base-c-test-8-gpu-h200` | 900 | 482 | -418 (-46%) |
| `test_e2e_pd.py` | `extra-a-test-2-gpu-large` | 600 | 186 | -414 (-69%) |
| `test_zaya.py` | `extra-a-test-1-gpu-large` | 420 | 7 | -413 (-98%) |
| `test_disaggregation_basic.py` | `base-b-test-2-gpu-large` | 730 | 400 | -330 (-45%) |
| `test_spec_ngram.py` | `base-b-test-1-gpu-large` | 400 | 78 | -322 (-80%) |
| `test_self_e2e_perturb_real_kv_unused_cache.py` | `extra-a-test-1-gpu-small` | 60 | 375 | +315 (+525%) |
| `test_spec_eagle_fa3.py` | `base-b-test-1-gpu-large` | 600 | 290 | -310 (-52%) |
| `test_deepseek_v32_fp4_mtp_tp.py` | `base-c-test-4-gpu-b200` | 400 | 709 | +309 (+77%) |
| `test_self_e2e_bench_speed.py` | `extra-a-test-1-gpu-large` | 600 | 293 | -307 (-51%) |
| `test_disaggregation_dp_attention.py` | `base-c-test-8-gpu-h20` | 443 | 155 | -288 (-65%) |
| `test_pcg_glm5_fp4.py` | `base-c-test-4-gpu-b200` | 900 | 617 | -283 (-31%) |
| `test_dsv31_dcp8_gsm8k.py` | `extra-b-test-8-gpu-h200` | 600 | 324 | -276 (-46%) |
| `test_update_weights_from_disk_blackwell.py` | `extra-b-test-4-gpu-b200` | 320 | 594 | +274 (+86%) |
| `test_scripted_swa_1gpu.py` | `extra-a-test-1-gpu-large` | 400 | 127 | -273 (-68%) |
| `test_qwen35_deterministic.py` | `extra-b-test-4-gpu-h100` | 360 | 99 | -261 (-72%) |
| `test_deepseek_v4_flash_fp4_b200_cp.py` | `extra-b-test-deepep-4-gpu-b200` | 235 | 495 | +260 (+111%) |
| `test_deepseek_v3_cp_single_node.py` | `extra-b-test-deepep-8-gpu-h200` | 500 | 251 | -249 (-50%) |
| `test_int8_mamba_checkpoint_e2e.py` | `extra-b-test-4-gpu-h100` | 400 | 162 | -238 (-60%) |
| `test_streaming_session_extra.py` | `extra-a-test-1-gpu-large` | 691 | 454 | -237 (-34%) |
| `test_spec_eagle_parity.py` | `base-b-test-1-gpu-large` | 360 | 126 | -234 (-65%) |
| `test_dflash.py` | `base-b-test-1-gpu-small` | 302 | 527 | +225 (+75%) |
| `test_deepseek_v32_fp4_mtp_dp.py` | `base-c-test-4-gpu-b200` | 400 | 610 | +210 (+52%) |
| `test_token_id_retokenize_e2e.py` | `base-b-test-1-gpu-large` | 300 | 94 | -206 (-69%) |
| `test_disaggregation_dsv4.py` | `base-c-test-deepep-8-gpu-h200` | 500 | 296 | -204 (-41%) |
| `test_scripted_core_1gpu.py` | `extra-a-test-1-gpu-small` | 300 | 100 | -200 (-67%) |
| `test_self_e2e_perturb_real_kv_used.py` | `extra-a-test-1-gpu-small` | 60 | 260 | +200 (+333%) |
| `test_disaggregation_aarch64.py` | `base-c-test-4-gpu-gb300` | 300 | 103 | -197 (-66%) |
| `test_eagle_reject_sampling.py` | `base-b-test-2-gpu-large` | 300 | 104 | -196 (-65%) |
| `test_spec_ngram_extra.py` | `extra-a-test-1-gpu-large` | 400 | 212 | -188 (-47%) |
| `test_spec_standalone.py` | `base-b-test-1-gpu-large` | 406 | 224 | -182 (-45%) |
| `test_spec_standalone_extra.py` | `extra-a-test-1-gpu-large` | 406 | 224 | -182 (-45%) |
| `test_scripted_runtime_core.py` | `base-b-test-1-gpu-small` | 460 | 281 | -179 (-39%) |
| `test_deepseek_v3_fp4_mtp_small.py` | `base-b-test-4-gpu-b200` | 340 | 519 | +179 (+53%) |
| `test_deepseek_v4_flash_fp4_b200.py` | `base-c-test-deepep-4-gpu-b200` | 465 | 633 | +168 (+36%) |
| `test_step3p5_flash_chain_mtp.py` | `extra-b-test-8-gpu-h200` | 480 | 314 | -166 (-35%) |
| `test_ministral4_models.py` | `extra-a-test-2-gpu-large` | 200 | 364 | +164 (+82%) |
| `test_autoround_quantization.py` | `extra-a-test-1-gpu-large` | 120 | 284 | +164 (+137%) |
| `test_lora_nemotron_3_super_120b_a12b_logprob_diff.py` | `extra-b-test-4-gpu-b200` | 100 | 256 | +156 (+156%) |
| `test_deepseek_v4_flash_fp4_h200.py` | `base-c-test-deepep-8-gpu-h200` | 370 | 524 | +154 (+42%) |
| `test_dp_attention.py` | `base-b-test-2-gpu-large` | 420 | 572 | +152 (+36%) |
| `test_frozen_kv_mtp.py` | `base-b-test-1-gpu-large` | 300 | 150 | -150 (-50%) |
| `test_self_e2e_pp_perturb.py` | `extra-a-test-2-gpu-large` | 220 | 358 | +138 (+63%) |
| `test_moe_ep_extra.py` | `extra-a-test-2-gpu-large` | 279 | 146 | -133 (-48%) |
| `test_moe_ep.py` | `base-b-test-2-gpu-large` | 279 | 150 | -129 (-46%) |
| `test_hicache_storage_mooncake_backend.py` | `base-b-test-2-gpu-large` | 236 | 364 | +128 (+54%) |
| `test_hicache_storage_3fs_backend.py` | `base-c-test-4-gpu-h100` | 300 | 174 | -126 (-42%) |
| `test_deepseek_v4_flash_fp8_h200.py` | `extra-b-test-deepep-8-gpu-h200` | 280 | 165 | -115 (-41%) |
| `test_lora_moe_tp_logprob_diff.py` | `extra-a-test-2-gpu-large` | 200 | 87 | -113 (-56%) |
| `test_nvfp4_gemm.py` | `base-c-test-4-gpu-b200` | 350 | 460 | +110 (+31%) |
| `test_self_e2e_perturb_req_to_token.py` | `extra-a-test-1-gpu-small` | 60 | 168 | +108 (+180%) |
| `test_mxfp4_sm90_cutlass.py` | `base-b-test-1-gpu-large` | 120 | 14 | -106 (-88%) |
| `test_phase_checker.py` | `base-b-test-1-gpu-small` | 120 | 15 | -105 (-88%) |
| `test_lplb_distributed.py` | `base-b-test-2-gpu-large` | 120 | 19 | -101 (-84%) |
| `test_qwen3_next_models_mtp.py` | `base-c-test-4-gpu-h100` | 290 | 390 | +100 (+34%) |
| `test_quark_mxfp4.py` | `base-b-test-1-gpu-small` | 103 | 7 | -96 (-93%) |
| `test_customized_info_streaming.py` | `base-b-test-1-gpu-small` | 120 | 24 | -96 (-80%) |
| `test_return_indexer_topk.py` | `extra-b-test-8-gpu-h200` | 270 | 184 | -86 (-32%) |
| `test_metrics.py` | `base-b-test-1-gpu-small` | 74 | 156 | +82 (+111%) |
| `test_hicache_storage.py` | `base-b-test-1-gpu-small` | 99 | 176 | +77 (+78%) |
| `test_gpt_oss_4gpu_bf16.py` | `base-c-test-4-gpu-h100` | 220 | 296 | +76 (+35%) |
| `test_basic_sanity.py` | `base-a-test-1-gpu-small` | 160 | 85 | -75 (-47%) |
| `test_reward_models.py` | `base-b-test-1-gpu-small` | 166 | 234 | +68 (+41%) |
| `test_hicache_storage_runtime_attach_detach.py` | `base-b-test-2-gpu-large` | 139 | 206 | +67 (+48%) |
| `test_self_e2e_pd_baseline.py` | `extra-a-test-2-gpu-large` | 180 | 113 | -67 (-37%) |
| `test_no_extra_forked_cuda_context.py` | `base-b-test-2-gpu-large` | 120 | 58 | -62 (-52%) |
| `test_torch_compile_moe.py` | `base-b-test-1-gpu-large` | 130 | 190 | +60 (+46%) |
| `test_triton_attention_backend.py` | `base-b-test-1-gpu-large` | 177 | 236 | +59 (+33%) |
| `test_lora_drainer.py` | `extra-a-test-1-gpu-small` | 100 | 48 | -52 (-52%) |
| `test_self_unit_canary_mock_wiring.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_install.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_oracle.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_sampler_hookpoint.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_gemma4_fused_routing.py` | `base-b-test-1-gpu-small` | 60 | 9 | -51 (-85%) |
| `test_self_e2e_baseline.py` | `extra-a-test-1-gpu-small` | 60 | 110 | +50 (+83%) |
| `test_topk_padded_region.py` | `base-b-test-1-gpu-large` | 60 | 10 | -50 (-83%) |
| `test_lora_qwen3_5_4b_logprob_diff.py` | `extra-a-test-1-gpu-large` | 90 | 42 | -48 (-53%) |
| `test_adaptive_speculative.py` | `base-b-test-1-gpu-large` | 160 | 112 | -48 (-30%) |
| `test_generation_models.py` | `extra-a-test-1-gpu-large` | 150 | 196 | +46 (+31%) |
| `test_engine_child_pids.py` | `base-b-test-1-gpu-small` | 77 | 36 | -41 (-53%) |
| `test_cutedsl_moe.py` | `extra-b-test-4-gpu-b200` | 24 | 65 | +41 (+171%) |
| `test_self_unit_pool_patcher.py` | `extra-a-test-1-gpu-small` | 45 | 8 | -37 (-82%) |
| `test_self_unit_runner_health.py` | `extra-a-test-1-gpu-small` | 45 | 8 | -37 (-82%) |
| `test_sm120_flash_mla.py` | `base-b-test-1-gpu-large` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_per_forward.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_swa_divergence.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_sweep.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_triton_sliding_window.py` | `extra-a-test-1-gpu-large` | 93 | 128 | +35 (+38%) |

🤖 Generated with GitHub Actions











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28342417172](https://github.com/sgl-project/sglang/actions/runs/28342417172)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28342417100](https://github.com/sgl-project/sglang/actions/runs/28342417100)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
