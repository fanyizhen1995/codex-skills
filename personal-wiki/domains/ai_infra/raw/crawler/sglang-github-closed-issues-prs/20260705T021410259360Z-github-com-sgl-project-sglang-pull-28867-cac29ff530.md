---
source_id: sglang-github-closed-issues-prs
title: 'chore: update CI test est_time values'
canonical_url: https://github.com/sgl-project/sglang/pull/28867
captured_at: '2026-07-05T02:14:10.259360+00:00'
content_hash: cac29ff5309fde348ef5b1313365b9c5a4fbd536c401a8c426b0a8432cd46f98
---
# chore: update CI test est_time values

URL: https://github.com/sgl-project/sglang/pull/28867
State: closed
Labels: quant, lora, Multi-modal, deepseek, speculative-decoding, hicache, blackwell, npu
Closed at: 2026-07-04T06:56:37Z
Merged at: 

## Summary

Refreshes `est_time` literals from [`sgl-project/sglang-ci-stats`](https://github.com/sgl-project/sglang-ci-stats)'s `model.json` (per-(suite, file) p90 over recent successful CI runs on `main`).

This keeps the LPT load-balancing algorithm accurate for partitioning tests across parallel CI jobs, and serves as the static fallback when `compute_partitions` cannot fetch the live model at PR time.

### Significant est_time changes (99 of 494 updates)

| File | Suite | Old (s) | New (s) | Δ |
| --- | --- | ---: | ---: | ---: |
| `test_deepseek_v3_cutedsl_4gpu.py` | `base-c-test-4-gpu-gb300` | 1800 | 512 | -1288 (-72%) |
| `test_scripted_core_4gpu.py` | `extra-b-test-4-gpu-h100` | 900 | 122 | -778 (-86%) |
| `test_tbo_shared_experts_fusion.py` | `extra-b-test-deepep-8-gpu-h200` | 900 | 184 | -716 (-80%) |
| `test_gemma4_dflash_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 102 | -618 (-86%) |
| `test_deepseek_v4_flash_fp4_megamoe_b200.py` | `extra-b-test-deepep-4-gpu-b200` | 900 | 317 | -583 (-65%) |
| `test_deepseek_v3_fp4.py` | `base-c-test-4-gpu-b200` | 960 | 427 | -533 (-56%) |
| `test_e2e_pp.py` | `extra-a-test-2-gpu-large` | 600 | 68 | -532 (-89%) |
| `test_e2e_tp.py` | `extra-a-test-2-gpu-large` | 600 | 72 | -528 (-88%) |
| `test_gemma4_mtp_31b_extra.py` | `extra-a-test-2-gpu-large` | 720 | 217 | -503 (-70%) |
| `test_e2e_spec_eagle.py` | `extra-a-test-1-gpu-small` | 600 | 109 | -491 (-82%) |
| `test_pcg_with_speculative_decoding_dflash.py` | `base-b-test-1-gpu-small` | 531 | 72 | -459 (-86%) |
| `test_fa_skip_kv_cache_piecewise_nan.py` | `base-b-test-1-gpu-large` | 600 | 144 | -456 (-76%) |
| `test_deepseek_v3_fp4_4gpu_extra.py` | `extra-b-test-4-gpu-b200` | 960 | 508 | -452 (-47%) |
| `test_e2e_pd.py` | `extra-a-test-2-gpu-large` | 600 | 186 | -414 (-69%) |
| `test_zaya.py` | `extra-a-test-1-gpu-large` | 420 | 7 | -413 (-98%) |
| `test_streaming_session.py` | `base-b-test-1-gpu-large` | 691 | 278 | -413 (-60%) |
| `test_self_e2e_perturb_real_kv_unused_cache.py` | `extra-a-test-1-gpu-small` | 60 | 438 | +378 (+630%) |
| `test_pcg_with_speculative_decoding.py` | `base-b-test-2-gpu-large` | 531 | 169 | -362 (-68%) |
| `test_disaggregation_basic.py` | `base-b-test-2-gpu-large` | 730 | 378 | -352 (-48%) |
| `test_qwen35_fp4_flashinfer.py` | `base-c-test-4-gpu-b200` | 720 | 381 | -339 (-47%) |
| `test_spec_ngram.py` | `base-b-test-1-gpu-large` | 400 | 77 | -323 (-81%) |
| `test_spec_eagle_fa3.py` | `base-b-test-1-gpu-large` | 600 | 302 | -298 (-50%) |
| `test_self_e2e_bench_speed.py` | `extra-a-test-1-gpu-large` | 600 | 308 | -292 (-49%) |
| `test_disaggregation_dp_attention.py` | `base-c-test-8-gpu-h20` | 443 | 156 | -287 (-65%) |
| `test_update_weights_from_disk_blackwell.py` | `extra-b-test-4-gpu-b200` | 320 | 600 | +280 (+88%) |
| `test_scripted_swa_1gpu.py` | `extra-a-test-1-gpu-large` | 400 | 123 | -277 (-69%) |
| `test_gpt_oss_sm120.py` | `extra-a-test-1-gpu-small` | 345 | 614 | +269 (+78%) |
| `test_deepseek_v3_cp_single_node.py` | `extra-b-test-deepep-8-gpu-h200` | 500 | 232 | -268 (-54%) |
| `test_qwen35_deterministic.py` | `extra-b-test-4-gpu-h100` | 360 | 97 | -263 (-73%) |
| `test_deepseek_v3_fp4_mtp_small.py` | `base-b-test-4-gpu-b200` | 340 | 580 | +240 (+71%) |
| `test_streaming_session_extra.py` | `extra-a-test-1-gpu-large` | 691 | 470 | -221 (-32%) |
| `test_deepseek_v32_fp4_mtp_tp.py` | `base-c-test-4-gpu-b200` | 400 | 618 | +218 (+55%) |
| `test_spec_eagle_parity.py` | `base-b-test-1-gpu-large` | 360 | 142 | -218 (-61%) |
| `test_dflash.py` | `base-b-test-1-gpu-small` | 302 | 518 | +216 (+72%) |
| `test_disaggregation_aarch64.py` | `base-c-test-4-gpu-gb300` | 300 | 92 | -208 (-69%) |
| `test_int8_mamba_checkpoint_e2e.py` | `base-c-test-4-gpu-h100` | 400 | 192 | -208 (-52%) |
| `test_spec_ngram_extra.py` | `extra-a-test-1-gpu-large` | 400 | 194 | -206 (-52%) |
| `test_token_id_retokenize_e2e.py` | `base-b-test-1-gpu-large` | 300 | 94 | -206 (-69%) |
| `test_scripted_core_1gpu.py` | `extra-a-test-1-gpu-small` | 300 | 98 | -202 (-67%) |
| `test_spec_standalone.py` | `base-b-test-1-gpu-large` | 406 | 213 | -193 (-48%) |
| `test_spec_standalone_extra.py` | `extra-a-test-1-gpu-large` | 406 | 213 | -193 (-48%) |
| `test_disaggregation_dsv4.py` | `base-c-test-deepep-8-gpu-h200` | 500 | 311 | -189 (-38%) |
| `test_self_e2e_perturb_real_kv_used.py` | `extra-a-test-1-gpu-small` | 60 | 244 | +184 (+307%) |
| `test_deepseek_v4_flash_fp4_b200.py` | `base-c-test-deepep-4-gpu-b200` | 465 | 648 | +183 (+39%) |
| `test_scripted_runtime_core.py` | `base-b-test-1-gpu-small` | 460 | 277 | -183 (-40%) |
| `test_deepseek_v4_flash_fp4_b200_cp.py` | `extra-b-test-deepep-4-gpu-b200` | 235 | 400 | +165 (+70%) |
| `test_frozen_kv_mtp.py` | `base-b-test-1-gpu-large` | 300 | 139 | -161 (-54%) |
| `test_deepseek_v4_flash_fp4_h200.py` | `base-c-test-deepep-8-gpu-h200` | 370 | 526 | +156 (+42%) |
| `test_deepseek_v3_mtp.py` | `base-c-test-8-gpu-h200` | 300 | 452 | +152 (+51%) |
| `test_ministral4_models.py` | `extra-a-test-2-gpu-large` | 200 | 347 | +147 (+74%) |
| `test_dp_attention.py` | `base-b-test-2-gpu-large` | 420 | 553 | +133 (+32%) |
| `test_moe_ep.py` | `base-b-test-2-gpu-large` | 279 | 146 | -133 (-48%) |
| `test_moe_ep_extra.py` | `extra-a-test-2-gpu-large` | 279 | 146 | -133 (-48%) |
| `test_hicache_storage_mooncake_backend.py` | `base-b-test-2-gpu-large` | 236 | 364 | +128 (+54%) |
| `test_deepseek_v4_flash_fp8_h200.py` | `extra-b-test-deepep-8-gpu-h200` | 280 | 166 | -114 (-41%) |
| `test_self_e2e_pp_perturb.py` | `extra-a-test-2-gpu-large` | 220 | 333 | +113 (+51%) |
| `test_bench_serving_1gpu_large.py` | `extra-a-test-1-gpu-large` | 286 | 399 | +113 (+40%) |
| `test_hicache_storage_3fs_backend.py` | `base-c-test-4-gpu-h100` | 300 | 190 | -110 (-37%) |
| `test_lora_moe_tp_logprob_diff.py` | `extra-a-test-2-gpu-large` | 200 | 90 | -110 (-55%) |
| `test_mxfp4_sm90_cutlass.py` | `base-b-test-1-gpu-large` | 120 | 11 | -109 (-91%) |
| `test_phase_checker.py` | `base-b-test-1-gpu-small` | 120 | 15 | -105 (-88%) |
| `test_self_e2e_perturb_req_to_token.py` | `extra-a-test-1-gpu-small` | 60 | 163 | +103 (+172%) |
| `test_lplb_distributed.py` | `base-b-test-2-gpu-large` | 120 | 20 | -100 (-83%) |
| `test_customized_info_streaming.py` | `base-b-test-1-gpu-small` | 120 | 22 | -98 (-82%) |
| `test_quark_mxfp4.py` | `base-b-test-1-gpu-small` | 103 | 7 | -96 (-93%) |
| `test_qwen3_next_models.py` | `base-c-test-4-gpu-h100` | 250 | 343 | +93 (+37%) |
| `test_basic_sanity.py` | `base-a-test-1-gpu-small` | 160 | 73 | -87 (-54%) |
| `test_unified_radix_cache_kl_swa.py` | `base-b-test-2-gpu-large` | 250 | 337 | +87 (+35%) |
| `test_gpt_oss_4gpu_mxfp4.py` | `base-c-test-4-gpu-b200` | 220 | 137 | -83 (-38%) |
| `test_metrics.py` | `base-b-test-1-gpu-small` | 74 | 151 | +77 (+104%) |
| `test_constrained_decoding_spec_reasoning.py` | `base-b-test-2-gpu-large` | 137 | 210 | +73 (+53%) |
| `test_hicache_storage.py` | `base-b-test-1-gpu-small` | 99 | 170 | +71 (+72%) |
| `test_no_extra_forked_cuda_context.py` | `base-b-test-2-gpu-large` | 120 | 53 | -67 (-56%) |
| `test_hicache_storage_runtime_attach_detach.py` | `base-b-test-2-gpu-large` | 139 | 206 | +67 (+48%) |
| `test_reward_models.py` | `base-b-test-1-gpu-small` | 166 | 231 | +65 (+39%) |
| `test_self_e2e_pd_baseline.py` | `extra-a-test-2-gpu-large` | 180 | 116 | -64 (-36%) |
| `test_lora_nemotron_3_super_120b_a12b_logprob_diff.py` | `extra-b-test-4-gpu-b200` | 100 | 162 | +62 (+62%) |
| `test_torch_compile_moe.py` | `base-b-test-1-gpu-large` | 130 | 192 | +62 (+48%) |
| `test_triton_attention_backend.py` | `base-b-test-1-gpu-large` | 177 | 237 | +60 (+34%) |
| `test_epd_disaggregation.py` | `base-c-test-4-gpu-h100` | 97 | 153 | +56 (+58%) |
| `test_lora_drainer.py` | `extra-a-test-1-gpu-small` | 100 | 45 | -55 (-55%) |
| `test_self_unit_oracle.py` | `extra-a-test-1-gpu-small` | 60 | 7 | -53 (-88%) |
| `test_self_unit_install.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_self_unit_sampler_hookpoint.py` | `extra-a-test-1-gpu-small` | 60 | 8 | -52 (-87%) |
| `test_gemma4_fused_routing.py` | `base-b-test-1-gpu-small` | 60 | 9 | -51 (-85%) |
| `test_self_unit_canary_mock_wiring.py` | `extra-a-test-1-gpu-small` | 60 | 9 | -51 (-85%) |
| `test_lora_qwen3_5_4b_logprob_diff.py` | `extra-a-test-1-gpu-large` | 90 | 42 | -48 (-53%) |
| `test_torch_compile.py` | `extra-a-test-1-gpu-large` | 126 | 173 | +47 (+37%) |
| `test_self_e2e_baseline.py` | `extra-a-test-1-gpu-small` | 60 | 106 | +46 (+77%) |
| `test_generation_models.py` | `extra-a-test-1-gpu-large` | 150 | 195 | +45 (+30%) |
| `test_embedding_models.py` | `base-b-test-1-gpu-small` | 136 | 180 | +44 (+32%) |
| `test_engine_child_pids.py` | `base-b-test-1-gpu-small` | 77 | 35 | -42 (-55%) |
| `test_cutedsl_moe.py` | `extra-b-test-4-gpu-b200` | 24 | 64 | +40 (+167%) |
| `test_self_unit_pool_patcher.py` | `extra-a-test-1-gpu-small` | 45 | 8 | -37 (-82%) |
| `test_self_unit_runner_health.py` | `extra-a-test-1-gpu-small` | 45 | 8 | -37 (-82%) |
| `test_sm120_flash_mla.py` | `base-b-test-1-gpu-large` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_per_forward.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_swa_divergence.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |
| `test_self_unit_runner_sweep.py` | `extra-a-test-1-gpu-small` | 45 | 9 | -36 (-80%) |

🤖 Generated with GitHub Actions











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27923684306](https://github.com/sgl-project/sglang/actions/runs/27923684306)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27923684184](https://github.com/sgl-project/sglang/actions/runs/27923684184)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
