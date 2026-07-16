---
source_id: sglang-github-closed-issues-prs
title: 'chore: update CI test est_time values'
canonical_url: https://github.com/sgl-project/sglang/pull/30192
captured_at: '2026-07-10T23:37:20.319024+00:00'
content_hash: f576509fba887128db1c71c980725966b5f052f97816c04de419adcf1ce3297f
---
# chore: update CI test est_time values

URL: https://github.com/sgl-project/sglang/pull/30192
State: closed
Labels: quant, lora, Multi-modal, deepseek, speculative-decoding, hicache, blackwell, npu, apple-silicon
Closed at: 2026-07-10T22:38:43Z
Merged at: 

## Summary

Refreshes `est_time` literals from [`sgl-project/sglang-ci-stats`](https://github.com/sgl-project/sglang-ci-stats)'s `model.json` (per-(suite, file) p90 over recent successful CI runs on `main`).

This keeps the LPT load-balancing algorithm accurate for partitioning tests across parallel CI jobs, and serves as the static fallback when `compute_partitions` cannot fetch the live model at PR time.

### Significant est_time changes (116 of 556 updates)

| File | Suite | Old (s) | New (s) | Δ |
| --- | --- | ---: | ---: | ---: |
| `test_deepseek_v3_cutedsl_4gpu.py` | `base-c-test-4-gpu-gb300` | 1800 | 470 | -1330 (-74%) |
| `test_scripted_core_4gpu.py` | `extra-b-test-4-gpu-h100` | 900 | 114 | -786 (-87%) |
| `test_tbo_shared_experts_fusion.py` | `extra-b-test-deepep-8-gpu-h200` | 900 | 184 | -716 (-80%) |
| `test_unified_radix_cache_kl_cp.py` | `extra-b-test-4-gpu-h100` | 950 | 286 | -664 (-70%) |
| `test_gemma4_dflash_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 99 | -621 (-86%) |
| `test_deepseek_v3_fp4.py` | `base-c-test-4-gpu-b200` | 960 | 352 | -608 (-63%) |
| `test_disaggregation_hisparse.py` | `extra-b-test-deepep-8-gpu-h200` | 1000 | 403 | -597 (-60%) |
| `test_e2e_tp.py` | `extra-a-test-2-gpu-large` | 600 | 65 | -535 (-89%) |
| `test_e2e_pp.py` | `extra-a-test-2-gpu-large` | 600 | 73 | -527 (-88%) |
| `test_e2e_spec_eagle.py` | `extra-a-test-1-gpu-small` | 600 | 84 | -516 (-86%) |
| `test_gemma4_mtp_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 217 | -503 (-70%) |
| `test_deepseek_v4_flash_fp4_megamoe_b200.py` | `extra-b-test-deepep-4-gpu-b200` | 900 | 423 | -477 (-53%) |
| `test_pcg_glm52_fp4.py` | `base-c-test-4-gpu-b200` | 900 | 438 | -462 (-51%) |
| `test_fa_skip_kv_cache_piecewise_nan.py` | `base-b-test-1-gpu-large` | 600 | 138 | -462 (-77%) |
| `test_pcg_glm52_fp8_tp8.py` | `base-c-test-8-gpu-h200` | 900 | 442 | -458 (-51%) |
| `test_pcg_with_speculative_decoding_dflash.py` | `base-b-test-1-gpu-small` | 531 | 80 | -451 (-85%) |
| `test_pcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 90 | -441 (-83%) |
| `test_streaming_session.py` | `base-b-test-1-gpu-large` | 691 | 254 | -437 (-63%) |
| `test_deepseek_v3_fp4_4gpu_extra.py` | `extra-b-test-4-gpu-b200` | 960 | 538 | -422 (-44%) |
| `test_e2e_pd.py` | `extra-a-test-2-gpu-large` | 600 | 181 | -419 (-70%) |
| `test_bcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 115 | -416 (-78%) |
| `test_zaya.py` | `extra-a-test-1-gpu-large` | 420 | 7 | -413 (-98%) |
| `test_dsv31_dcp8_gsm8k.py` | `extra-b-test-8-gpu-h200` | 600 | 209 | -391 (-65%) |
| `test_deepseek_v4_flash_fp4_b200_cp.py` | `extra-b-test-deepep-4-gpu-b200` | 235 | 615 | +380 (+162%) |
| `test_qwen35_fp4_mtp.py` | `base-c-test-4-gpu-b200` | 740 | 1114 | +374 (+51%) |
| `test_unified_radix_cache_kl_dsv4_pp.py` | `extra-b-test-8-gpu-h200` | 900 | 567 | -333 (-37%) |
| `test_self_e2e_perturb_real_kv_unused_cache.py` | `extra-a-test-1-gpu-small` | 60 | 391 | +331 (+552%) |
| `test_deepseek_v4_flash_fp4_b200.py` | `base-c-test-deepep-4-gpu-b200` | 465 | 796 | +331 (+71%) |
| `test_disaggregation_dsv4.py` | `base-c-test-deepep-8-gpu-h200` | 500 | 171 | -329 (-66%) |
| `test_disaggregation_basic.py` | `base-b-test-2-gpu-large` | 730 | 407 | -323 (-44%) |
| `test_spec_ngram.py` | `base-b-test-1-gpu-large` | 400 | 79 | -321 (-80%) |
| `test_page_major_gpt_oss.py` | `extra-a-test-1-gpu-large` | 420 | 105 | -315 (-75%) |
| `test_spec_eagle_fa3.py` | `base-b-test-1-gpu-large` | 600 | 289 | -311 (-52%) |
| `test_qwen35_fp4_flashinfer.py` | `base-c-test-4-gpu-b200` | 720 | 412 | -308 (-43%) |
| `test_disaggregation_dp_attention.py` | `base-c-test-8-gpu-h20` | 443 | 156 | -287 (-65%) |
| `test_scripted_swa_1gpu.py` | `extra-a-test-1-gpu-large` | 400 | 124 | -276 (-69%) |
| `test_vlm_input_format.py` | `base-b-test-1-gpu-large` | 747 | 475 | -272 (-36%) |
| `test_self_e2e_bench_speed.py` | `extra-a-test-1-gpu-large` | 600 | 329 | -271 (-45%) |
| `test_qwen35_deterministic.py` | `extra-b-test-4-gpu-h100` | 360 | 95 | -265 (-74%) |
| `test_streaming_session_extra.py` | `extra-a-test-1-gpu-large` | 691 | 440 | -251 (-36%) |
| `test_dsa_glm52_hisparse.py` | `extra-b-test-8-gpu-h200` | 720 | 482 | -238 (-33%) |
| `test_spec_eagle_parity.py` | `base-b-test-1-gpu-large` | 360 | 125 | -235 (-65%) |
| `test_deepseek_v3_cp_single_node.py` | `extra-b-test-deepep-8-gpu-h200` | 500 | 267 | -233 (-47%) |
| `test_int8_mamba_checkpoint_e2e.py` | `extra-b-test-4-gpu-h100` | 400 | 176 | -224 (-56%) |
| `test_eagle_reject_sampling.py` | `base-b-test-2-gpu-large` | 300 | 76 | -224 (-75%) |
| `test_page_major_qwen_hybrid.py` | `extra-a-test-1-gpu-large` | 300 | 85 | -215 (-72%) |
| `test_token_id_retokenize_e2e.py` | `base-b-test-1-gpu-large` | 300 | 91 | -209 (-70%) |
| `test_spec_standalone.py` | `base-b-test-1-gpu-large` | 406 | 203 | -203 (-50%) |
| `test_update_weights_from_disk_blackwell.py` | `extra-b-test-4-gpu-b200` | 320 | 522 | +202 (+63%) |
| `test_self_e2e_perturb_real_kv_used.py` | `extra-a-test-1-gpu-small` | 60 | 261 | +201 (+335%) |
| `test_dflash.py` | `base-b-test-1-gpu-small` | 302 | 503 | +201 (+67%) |
| `test_scripted_core_1gpu.py` | `extra-a-test-1-gpu-small` | 300 | 100 | -200 (-67%) |
| `test_spec_ngram_extra.py` | `extra-a-test-1-gpu-large` | 400 | 205 | -195 (-49%) |
| `test_spec_standalone_extra.py` | `extra-a-test-1-gpu-large` | 406 | 212 | -194 (-48%) |
| `test_unlimited_ocr_server.py` | `base-b-test-1-gpu-large` | 240 | 49 | -191 (-80%) |
| `test_disaggregation_aarch64.py` | `base-c-test-4-gpu-gb300` | 300 | 121 | -179 (-60%) |
| `test_scripted_runtime_core.py` | `base-b-test-1-gpu-small` | 460 | 285 | -175 (-38%) |
| `test_autoround_quantization.py` | `extra-a-test-1-gpu-large` | 120 | 294 | +174 (+145%) |
| `test_deepseek_v4_flash_fp4_h200.py` | `base-c-test-deepep-8-gpu-h200` | 370 | 535 | +165 (+45%) |
| `test_lora_nemotron_3_super_120b_a12b_logprob_diff.py` | `extra-b-test-4-gpu-b200` | 100 | 262 | +162 (+162%) |
| `test_frozen_kv_mtp.py` | `base-b-test-1-gpu-large` | 300 | 141 | -159 (-53%) |
| `test_ministral4_models.py` | `extra-a-test-2-gpu-large` | 200 | 353 | +153 (+76%) |
| `test_flashinfer_a2a.py` | `base-c-test-4-gpu-gb300` | 500 | 651 | +151 (+30%) |
| `test_moe_ep.py` | `base-b-test-2-gpu-large` | 279 | 135 | -144 (-52%) |
| `test_moe_ep_extra.py` | `extra-a-test-2-gpu-large` | 279 | 135 | -144 (-52%) |
| `test_deepseek_v4_flash_fp8_h200.py` | `extra-b-test-deepep-8-gpu-h200` | 280 | 137 | -143 (-51%) |
| `test_vlm_models.py` | `extra-a-test-1-gpu-large` | 317 | 180 | -137 (-43%) |
| `test_hicache_storage_mooncake_backend.py` | `base-b-test-2-gpu-large` | 236 | 363 | +127 (+54%) |
| `test_lora_moe_tp_logprob_diff.py` | `extra-a-test-2-gpu-large` | 200 | 88 | -112 (-56%) |
| `test_qwen3_next_models_mtp.py` | `base-c-test-4-gpu-h100` | 290 | 401 | +111 (+38%) |
| `test_self_e2e_perturb_req_to_token.py` | `extra-a-test-1-gpu-small` | 60 | 170 | +110 (+183%) |
| `test_mxfp4_sm90_cutlass.py` | `base-b-test-1-gpu-large` | 120 | 11 | -109 (-91%) |
| `test_hicache_storage_3fs_backend.py` | `base-c-test-4-gpu-h100` | 300 | 192 | -108 (-36%) |
| `test_nvfp4_gemm.py` | `base-c-test-4-gpu-b200` | 350 | 458 | +108 (+31%) |
| `test_disaggregation_hybrid_attention.py` | `extra-b-test-8-gpu-h200` | 310 | 416 | +106 (+34%) |
| `test_phase_checker.py` | `base-b-test-1-gpu-small` | 120 | 15 | -105 (-88%) |
| `test_self_e2e_pp_perturb.py` | `extra-a-test-2-gpu-large` | 220 | 322 | +102 (+46%) |
| `test_lplb_distributed.py` | `base-b-test-2-gpu-large` | 120 | 19 | -101 (-84%) |
| `test_quark_mxfp4.py` | `base-b-test-1-gpu-small` | 103 | 7 | -96 (-93%) |
| `test_customized_info_streaming.py` | `base-b-test-1-gpu-small` | 120 | 24 | -96 (-80%) |
| `test_disaggregation_decode_radix_cache.py` | `base-c-test-8-gpu-h20` | 300 | 390 | +90 (+30%) |
| `test_reward_models.py` | `base-b-test-1-gpu-small` | 166 | 256 | +90 (+54%) |
| `test_gpt_oss_4gpu_mxfp4.py` | `base-c-test-4-gpu-b200` | 220 | 133 | -87 (-40%) |
| `test_gpt_oss_4gpu_bf16.py` | `base-c-test-4-gpu-h100` | 220 | 295 | +75 (+34%) |
| `test_hicache_storage_runtime_attach_detach.py` | `base-b-test-2-gpu-large` | 139 | 213 | +74 (+53%) |
| `test_metrics.py` | `base-b-test-1-gpu-small` | 74 | 147 | +73 (+99%) |
| `test_basic_sanity.py` | `base-a-test-1-gpu-small` | 160 | 93 | -67 (-42%) |
| `test_hicache_storage.py` | `base-b-test-1-gpu-small` | 99 | 166 | +67 (+68%) |
| `test_self_e2e_pd_baseline.py` | `extra-a-test-2-gpu-large` | 180 | 113 | -67 (-37%) |
| `test_no_extra_forked_cuda_context.py` | `base-b-test-2-gpu-large` | 120 | 54 | -66 (-55%) |
| `test_basic_sanity_dflash.py` | `base-a-test-1-gpu-small` | 200 | 135 | -65 (-32%) |
| `test_torch_compile_moe.py` | `base-b-test-1-gpu-large` | 130 | 188 | +58 (+45%) |
| `test_function_call_parser.py` | `base-a-test-cpu` | 15 | 70 | +55 (+367%) |
| `test_lora_qwen3_5_4b_logprob_diff.py` | `extra-a-test-1-gpu-large` | 90 | 37 | -53 (-59%) |
| `test_self_unit_oracle.py` | `extra-a-test-1-gpu-small` | 60 | 7 | -53 (-88%) |
| `test_gemma4_fused_routing.py` | `base-b-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_canary_mock_wiring.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_install.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_lora_drainer.py` | `extra-a-test-1-gpu-small` | 100 | 49 | -51 (-51%) |
| `test_self_unit_sampler_hookpoint.py` | `extra-a-test-1-gpu-small` | 60 | 9 | -51 (-85%) |
| `test_topk_padded_region.py` | `base-b-test-1-gpu-large` | 60 | 9 | -51 (-85%) |
| `test_adaptive_speculative.py` | `base-b-test-1-gpu-large` | 160 | 109 | -51 (-32%) |
| `test_self_e2e_baseline.py` | `extra-a-test-1-gpu-small` | 60 | 110 | +50 (+83%) |
| `test_generation_models.py` | `extra-a-test-1-gpu-large` | 150 | 198 | +48 (+32%) |
| `test_vmm_utils.py` | `base-b-test-2-gpu-large` | 60 | 14 | -46 (-77%) |
| `test_http2_server.py` | `base-b-test-1-gpu-small` | 150 | 105 | -45 (-30%) |
| `test_cutedsl_moe.py` | `extra-b-test-4-gpu-b200` | 24 | 67 | +43 (+179%) |
| `test_engine_child_pids.py` | `base-b-test-1-gpu-small` | 77 | 35 | -42 (-55%) |
| `test_torch_compile.py` | `extra-a-test-1-gpu-large` | 126 | 165 | +39 (+31%) |
| `test_flash_mla_backends.py` | `base-b-test-1-gpu-large` | 45 | 6 | -39 (-87%) |
| `test_self_unit_pool_patcher.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_health.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_per_forward.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_swa_divergence.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_sweep.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_radix_attention.py` | `base-b-test-1-gpu-small` | 100 | 131 | +31 (+31%) |

🤖 Generated with GitHub Actions











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28761011364](https://github.com/sgl-project/sglang/actions/runs/28761011364)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28761011271](https://github.com/sgl-project/sglang/actions/runs/28761011271)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
