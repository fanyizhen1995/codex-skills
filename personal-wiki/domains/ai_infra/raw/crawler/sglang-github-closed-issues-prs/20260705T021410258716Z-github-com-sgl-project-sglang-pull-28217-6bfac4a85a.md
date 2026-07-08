---
source_id: sglang-github-closed-issues-prs
title: 'chore: update CI test est_time values'
canonical_url: https://github.com/sgl-project/sglang/pull/28217
captured_at: '2026-07-05T02:14:10.258716+00:00'
content_hash: 6bfac4a85aeb9c97f175b63a2e164fe990fa206c85c47cb1aff190c0c19754b6
---
# chore: update CI test est_time values

URL: https://github.com/sgl-project/sglang/pull/28217
State: closed
Labels: quant, lora, Multi-modal, deepseek, speculative-decoding, hicache, blackwell, npu
Closed at: 2026-07-04T06:56:43Z
Merged at: 

## Summary

Refreshes `est_time` literals from [`sgl-project/sglang-ci-stats`](https://github.com/sgl-project/sglang-ci-stats)'s `model.json` (per-(suite, file) p90 over recent successful CI runs on `main`).

This keeps the LPT load-balancing algorithm accurate for partitioning tests across parallel CI jobs, and serves as the static fallback when `compute_partitions` cannot fetch the live model at PR time.

### Significant est_time changes (104 of 466 updates)

| File | Suite | Old (s) | New (s) | Δ |
| --- | --- | ---: | ---: | ---: |
| `test_deepseek_v3_cutedsl_4gpu.py` | `base-c-test-4-gpu-gb300` | 1800 | 531 | -1269 (-70%) |
| `test_scripted_core_4gpu.py` | `extra-b-test-4-gpu-h100` | 900 | 138 | -762 (-85%) |
| `test_awq.py` | `base-b-test-1-gpu-large` | 160 | 913 | +753 (+471%) |
| `test_tbo_shared_experts_fusion.py` | `extra-b-test-deepep-8-gpu-h200` | 900 | 230 | -670 (-74%) |
| `test_unified_radix_cache_kl_cp.py` | `base-c-test-4-gpu-h100` | 400 | 1047 | +647 (+162%) |
| `test_e2e_pp.py` | `extra-a-test-2-gpu-large` | 600 | 71 | -529 (-88%) |
| `test_e2e_tp.py` | `extra-a-test-2-gpu-large` | 600 | 74 | -526 (-88%) |
| `test_deepseek_v3_fp4.py` | `base-c-test-4-gpu-b200` | 960 | 439 | -521 (-54%) |
| `test_e2e_spec_eagle.py` | `extra-a-test-1-gpu-small` | 600 | 99 | -501 (-84%) |
| `test_gemma4_mtp_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 226 | -494 (-69%) |
| `test_deepseek_v4_flash_fp4_megamoe_b200.py` | `extra-b-test-deepep-4-gpu-b200` | 900 | 415 | -485 (-54%) |
| `test_pcg_with_speculative_decoding_dflash.py` | `base-b-test-1-gpu-small` | 531 | 74 | -457 (-86%) |
| `test_self_e2e_perturb_real_kv_unused_cache.py` | `extra-a-test-1-gpu-small` | 60 | 491 | +431 (+718%) |
| `test_deepseek_v4_flash_fp4_h200.py` | `base-c-test-deepep-8-gpu-h200` | 370 | 799 | +429 (+116%) |
| `test_deepseek_v3_fp4_4gpu_extra.py` | `extra-b-test-4-gpu-b200` | 960 | 541 | -419 (-44%) |
| `test_streaming_session.py` | `base-b-test-1-gpu-large` | 691 | 274 | -417 (-60%) |
| `test_zaya.py` | `extra-a-test-1-gpu-large` | 420 | 7 | -413 (-98%) |
| `test_e2e_pd.py` | `extra-a-test-2-gpu-large` | 600 | 198 | -402 (-67%) |
| `test_pcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 172 | -359 (-68%) |
| `test_qwen35_fp4_flashinfer.py` | `base-c-test-4-gpu-b200` | 720 | 390 | -330 (-46%) |
| `test_spec_ngram.py` | `base-b-test-1-gpu-large` | 400 | 78 | -322 (-80%) |
| `test_self_e2e_bench_speed.py` | `extra-a-test-1-gpu-large` | 600 | 313 | -287 (-48%) |
| `test_disaggregation_dp_attention.py` | `base-c-test-8-gpu-h20` | 443 | 157 | -286 (-65%) |
| `test_gpt_oss_sm120.py` | `extra-a-test-1-gpu-small` | 345 | 628 | +283 (+82%) |
| `test_deepseek_v3_cp_single_node.py` | `extra-b-test-deepep-8-gpu-h200` | 500 | 227 | -273 (-55%) |
| `test_marlin_moe.py` | `base-b-test-1-gpu-small` | 108 | 370 | +262 (+243%) |
| `test_scripted_swa_1gpu.py` | `extra-a-test-1-gpu-large` | 400 | 142 | -258 (-64%) |
| `test_deepseek_v3_fp4_mtp_small.py` | `base-b-test-4-gpu-b200` | 340 | 596 | +256 (+75%) |
| `test_unified_radix_cache_hicache_pp_kl.py` | `base-c-test-4-gpu-h100` | 400 | 654 | +254 (+64%) |
| `test_step3p5_flash_chain_mtp.py` | `extra-b-test-8-gpu-h200` | 480 | 725 | +245 (+51%) |
| `test_deepseek_v32_fp4_mtp_tp.py` | `base-c-test-4-gpu-b200` | 400 | 641 | +241 (+60%) |
| `test_spec_eagle_parity.py` | `base-b-test-1-gpu-large` | 360 | 151 | -209 (-58%) |
| `test_token_id_retokenize_e2e.py` | `base-b-test-1-gpu-large` | 300 | 94 | -206 (-69%) |
| `test_deepseek_v32_indexcache.py` | `extra-b-test-8-gpu-h200` | 450 | 649 | +199 (+44%) |
| `test_disaggregation_basic.py` | `base-b-test-2-gpu-large` | 560 | 362 | -198 (-35%) |
| `test_spec_ngram_extra.py` | `extra-a-test-1-gpu-large` | 400 | 202 | -198 (-50%) |
| `test_scripted_core_1gpu.py` | `extra-a-test-1-gpu-small` | 300 | 106 | -194 (-65%) |
| `test_spec_standalone_extra.py` | `extra-a-test-1-gpu-large` | 406 | 217 | -189 (-47%) |
| `test_disaggregation_aarch64.py` | `base-c-test-4-gpu-gb300` | 300 | 112 | -188 (-63%) |
| `test_spec_standalone.py` | `base-b-test-1-gpu-large` | 406 | 218 | -188 (-46%) |
| `test_hicache_storage_mooncake_backend.py` | `base-b-test-2-gpu-large` | 236 | 423 | +187 (+79%) |
| `test_deepep_small.py` | `base-c-test-deepep-4-gpu-h100` | 478 | 664 | +186 (+39%) |
| `test_self_e2e_perturb_real_kv_used.py` | `extra-a-test-1-gpu-small` | 60 | 245 | +185 (+308%) |
| `test_dflash.py` | `base-b-test-1-gpu-small` | 302 | 482 | +180 (+60%) |
| `test_deepseek_v4_flash_fp4_b200.py` | `base-c-test-deepep-4-gpu-b200` | 465 | 629 | +164 (+35%) |
| `test_ministral4_models.py` | `extra-a-test-2-gpu-large` | 200 | 361 | +161 (+80%) |
| `test_frozen_kv_mtp.py` | `base-b-test-1-gpu-large` | 300 | 145 | -155 (-52%) |
| `test_deepseek_v4_flash_fp4_b200_cp.py` | `extra-b-test-deepep-4-gpu-b200` | 235 | 387 | +152 (+65%) |
| `test_scripted_runtime_core.py` | `base-b-test-1-gpu-small` | 460 | 312 | -148 (-32%) |
| `test_deepseek_v32_fp4_mtp_dp.py` | `base-c-test-4-gpu-b200` | 400 | 546 | +146 (+36%) |
| `test_gptqmodel_dynamic.py` | `extra-a-test-1-gpu-large` | 100 | 244 | +144 (+144%) |
| `test_vlm_models.py` | `extra-a-test-1-gpu-large` | 317 | 175 | -142 (-45%) |
| `test_disaggregation_hybrid_attention.py` | `extra-b-test-8-gpu-h200` | 310 | 446 | +136 (+44%) |
| `test_moe_ep.py` | `base-b-test-2-gpu-large` | 279 | 145 | -134 (-48%) |
| `test_mimo_v2.py` | `base-c-test-8-gpu-h200` | 400 | 267 | -133 (-33%) |
| `test_moe_ep_extra.py` | `extra-a-test-2-gpu-large` | 279 | 156 | -123 (-44%) |
| `test_lora_nemotron_3_super_120b_a12b_logprob_diff.py` | `extra-b-test-4-gpu-b200` | 100 | 222 | +122 (+122%) |
| `test_qwen3_next_models.py` | `base-c-test-4-gpu-h100` | 250 | 369 | +119 (+48%) |
| `test_hicache_storage_3fs_backend.py` | `base-c-test-4-gpu-h100` | 300 | 183 | -117 (-39%) |
| `test_self_e2e_pp_perturb.py` | `extra-a-test-2-gpu-large` | 220 | 328 | +108 (+49%) |
| `test_mxfp4_sm90_cutlass.py` | `base-b-test-1-gpu-large` | 120 | 12 | -108 (-90%) |
| `test_phase_checker.py` | `base-b-test-1-gpu-small` | 120 | 15 | -105 (-88%) |
| `test_lora_moe_tp_logprob_diff.py` | `extra-a-test-2-gpu-large` | 200 | 96 | -104 (-52%) |
| `test_bench_serving_1gpu_large.py` | `extra-a-test-1-gpu-large` | 286 | 390 | +104 (+36%) |
| `test_self_e2e_perturb_req_to_token.py` | `extra-a-test-1-gpu-small` | 60 | 163 | +103 (+172%) |
| `test_customized_info_streaming.py` | `base-b-test-1-gpu-small` | 120 | 22 | -98 (-82%) |
| `test_quark_mxfp4.py` | `base-b-test-1-gpu-small` | 103 | 7 | -96 (-93%) |
| `test_unified_radix_cache_kl_swa.py` | `base-b-test-2-gpu-large` | 250 | 338 | +88 (+35%) |
| `test_gpt_oss_4gpu_mxfp4.py` | `base-c-test-4-gpu-b200` | 220 | 139 | -81 (-37%) |
| `test_basic_sanity.py` | `base-a-test-1-gpu-small` | 160 | 83 | -77 (-48%) |
| `test_torch_compile_moe.py` | `base-b-test-1-gpu-large` | 130 | 203 | +73 (+56%) |
| `test_reward_models.py` | `base-b-test-1-gpu-small` | 166 | 238 | +72 (+43%) |
| `test_constrained_decoding_spec_reasoning.py` | `base-b-test-2-gpu-large` | 137 | 206 | +69 (+50%) |
| `test_hicache_storage_runtime_attach_detach.py` | `base-b-test-2-gpu-large` | 139 | 207 | +68 (+49%) |
| `test_gpt_oss_4gpu_mxfp4.py` | `base-c-test-4-gpu-h100` | 220 | 152 | -68 (-31%) |
| `test_triton_attention_backend.py` | `base-b-test-1-gpu-large` | 177 | 243 | +66 (+37%) |
| `test_hicache_storage.py` | `base-b-test-1-gpu-small` | 99 | 159 | +60 (+61%) |
| `test_no_extra_forked_cuda_context.py` | `base-b-test-2-gpu-large` | 120 | 62 | -58 (-48%) |
| `test_lora_drainer.py` | `extra-a-test-1-gpu-small` | 100 | 46 | -54 (-54%) |
| `test_self_unit_oracle.py` | `extra-a-test-1-gpu-small` | 60 | 7 | -53 (-88%) |
| `test_self_unit_canary_mock_wiring.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_install.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_sampler_hookpoint.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_gemma4_fused_routing.py` | `base-b-test-1-gpu-small` | 60 | 9 | -51 (-85%) |
| `test_generation_models.py` | `extra-a-test-1-gpu-large` | 150 | 198 | +48 (+32%) |
| `test_lora_qwen3_5_4b_logprob_diff.py` | `extra-a-test-1-gpu-large` | 90 | 43 | -47 (-52%) |
| `test_update_weights_from_distributed.py` | `extra-a-test-2-gpu-large` | 137 | 183 | +46 (+34%) |
| `test_metrics.py` | `base-b-test-1-gpu-small` | 74 | 119 | +45 (+61%) |
| `test_engine_child_pids.py` | `base-b-test-1-gpu-small` | 77 | 34 | -43 (-56%) |
| `test_cutedsl_moe.py` | `extra-b-test-4-gpu-b200` | 24 | 65 | +41 (+171%) |
| `test_self_e2e_baseline.py` | `extra-a-test-1-gpu-small` | 60 | 100 | +40 (+67%) |
| `test_multi_instance_release_memory_occupation.py` | `extra-b-test-4-gpu-h100` | 57 | 96 | +39 (+68%) |
| `test_torch_compile.py` | `extra-a-test-1-gpu-large` | 126 | 164 | +38 (+30%) |
| `test_self_unit_pool_patcher.py` | `extra-a-test-1-gpu-small` | 45 | 8 | -37 (-82%) |
| `test_epd_disaggregation.py` | `base-c-test-4-gpu-h100` | 97 | 133 | +36 (+37%) |
| `test_sm120_flash_mla.py` | `base-b-test-1-gpu-large` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_health.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_per_forward.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_swa_divergence.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_sweep.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_eagle_dp_attention.py` | `extra-b-test-4-gpu-h100` | 99 | 134 | +35 (+35%) |
| `test_triton_sliding_window.py` | `extra-a-test-1-gpu-large` | 93 | 127 | +34 (+37%) |
| `test_lora_gpt_oss_20b_logprob_diff.py` | `extra-b-test-4-gpu-b200` | 90 | 124 | +34 (+38%) |
| `test_multi_lora_backend.py` | `base-b-test-1-gpu-large` | 99 | 131 | +32 (+32%) |

🤖 Generated with GitHub Actions











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27518352775](https://github.com/sgl-project/sglang/actions/runs/27518352775)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27518352719](https://github.com/sgl-project/sglang/actions/runs/27518352719)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
