---
source_id: sglang-github-closed-issues-prs
title: '[misc] Remove unit test cases that fail the admission criteria (round 3)'
canonical_url: https://github.com/sgl-project/sglang/pull/30713
captured_at: '2026-07-10T23:37:20.332031+00:00'
content_hash: 31dfa81e197112c3bcd14b6b74ecd20fe774c6baef04df55b19fe7c69a6c51e3
---
# [misc] Remove unit test cases that fail the admission criteria (round 3)

URL: https://github.com/sgl-project/sglang/pull/30713
State: closed
Labels: run-ci, apple-silicon
Closed at: 2026-07-10T02:42:52Z
Merged at: 2026-07-10T02:42:52Z

Continuation of the admission-criteria pruning (#30690, #30703), covering the final 19 unit test files. Every deletion was identified by a scanning agent and confirmed by a verification agent reading both the test body and the stronger kept case. This completes the sweep — all 244 files under `test/registered/unit/` have now been audited.

Summary of what was removed and why:

<details>
<summary><code>test/registered/unit/layers/test_conv_layer.py</code> (1 method removed)</summary>

- `TestConv2dLayer.test_default_disables_linear` — strict-subset of `test_basic_patch_embedding` (same config, same `assertFalse(enable_linear)`, plus forward correctness). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/layers/test_mamba_state_scatter_triton.py</code> (1 class + 2 dead helpers removed)</summary>

- `TestMambaStateScatterPerf` (whole class) — the only method (`test_perf_report_old_vs_fused`) had zero assertions; it only `print()`s a perf report.
- `_time_cuda_ms` + `_dtype_from_str` (dead helpers) — only callers were the removed perf test.

</details>

<details>
<summary><code>test/registered/unit/batch_invariant_ops/test_batch_invariant_ops.py</code> (1 method removed)</summary>

- `test_without_batch_invariant_mode` — zero assertions; only `print()`s diffs. (tautology)

</details>

<details>
<summary><code>test/registered/unit/tokenizer/test_tiktoken_tokenizer.py</code> (6 methods removed)</summary>

- `test_image_processor_returns_dict` — isinstance-only against `return {"pixel_values": [image]}`. (tautology)
- `test_image_processor_has_pixel_values_key` — key-presence-only; `test_image_processor_wraps_image_in_list` asserts key+value. (strict-subset)
- `test_encode_delegates_to_tokenizer` / `test_decode_delegates_to_tokenizer` — pure delegation mirrors of 1-line pass-throughs. (mirror)
- `test_batch_decode_list_of_lists` — passthrough branch; the non-trivial flat-list wrapping is guarded by `test_batch_decode_flat_list_wraps_each`. (mirror)
- `test_special_token_values` — echoes the literal string assignments two lines above in the module. (mirror)

</details>

<details>
<summary><code>test/registered/unit/entrypoints/openai/test_serving_completions.py</code> (2 methods removed)</summary>

- `test_single_string_prompt` — string-branch passthrough mirror; stronger type-dispatch cases exist. (mirror)
- `test_echo_with_string_prompt_streaming` — `_get_echo_text` returns `request.prompt` for strings; covered by token-ids/list echo cases. (mirror)

</details>

<details>
<summary><code>test/registered/unit/observability/test_metrics_utils.py</code> (1 method removed)</summary>

- `test_integration_tse_through_generate_buckets` — asserts `generate_buckets(["tse",...]) == two_sides_exponential_buckets(...)`, which is literally the implementation `return` line. (mirror)

</details>

<details>
<summary><code>test/registered/unit/managers/test_profile_merger_http_api.py</code> (4 methods removed)</summary>

- `test_http_api_parameter_flow` / `test_profile_req_merge_profiles_json_serialization` — near-identical mirrors of the deserialization test (full-dict round-trip / `json.dumps` echo). (mirror)
- `test_http_api_backward_compatibility` / `test_http_api_parameter_combinations` — default-false re-check and parametrized re-run of cases covered by `test_profile_req_merge_profiles_default_value` / `test_http_api_parameter_validation`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/constrained/test_base_grammar_backend.py</code> (7 methods removed)</summary>

- `test_set_and_get_cache` — echoes `self.cache[key] = value`. (tautology)
- `test_register_and_use` — echoes `GRAMMAR_BACKEND_REGISTRY[name] = init_func`. (tautology)
- `test_maybe_init_reasoning_noop` — asserts a `pass` body doesn't raise. (tautology)
- `test_is_terminated_default` — asserts `return False`. (tautology)
- `test_reset_clears_cache` — strict-subset of `test_reset_then_miss`. (strict-subset)
- `test_all_dispatch_methods_unsupported` — strict-subset of `test_init_value_dispatch_routes_all_types`. (strict-subset)
- `test_custom_registered_backend` — strict-subset of `test_custom_backend_receives_args`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/eplb/test_compute_logical_to_rank_dispatch_physical_map.py</code> (1 method removed)</summary>

- `test_no_minus_one_in_output` — `assertFalse(any(result==-1))` is fully subsumed by `assertTrue(all(result>=0))` in `test_all_values_are_valid_physical_expert_ids`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/function_call/test_parallel_tool_calls.py</code> (1 method removed)</summary>

- `test_simple_parallel_tool_calls` — strict-subset of `test_parallel_tool_calls_with_array_parameters` (same two-tool structure, plus param checks). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/disaggregation/test_disaggregation_wire.py</code> (1 method removed)</summary>

- `TestGroupConcurrentContiguous.test_both_empty` — strict-subset of `test_empty_src_nonempty_dst` (same empty-source short-circuit). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/layers/test_pooler_score_and_pool.py</code> (1 method removed)</summary>

- `test_no_delimiter_indices_falls_back` — strict-subset of `test_single_item_returns_scores` (isinstance assertion implied by `.shape` access). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/parser/test_reasoning_content_without_parser.py</code> (2 methods removed)</summary>

- `test_no_parser_text_passthrough` / `test_no_parser_streaming_passthrough` — inline a copy of the `serving_chat.py` `if reasoning_parser:` guard inside the test and assert their own simulation; no production code runs. (tautology)

</details>

<details>
<summary><code>test/registered/unit/test_runai_utils.py</code> (1 method removed)</summary>

- `test_load_format_enum` — echoes `LoadFormat.RUNAI_STREAMER.value == "runai_streamer"`; an isolated internal identifier with no external spec. (tautology)

</details>

<details>
<summary><code>test/registered/unit/hardware_backend/mlx/test_tp_worker_routing.py</code> (1 method removed)</summary>

- `test_sync_multi_token_continuation_routes_to_extend` — routes through the identical `_route_extend_request` helper as the 1-token case; helper has zero length dependency and `extend()` is mocked. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/hardware_backend/mlx/test_mlx_pool_dtype.py</code> (1 method removed)</summary>

- `test_pool_bytes_per_slot_halves_for_bf16_quantized_model` — reduces to the library identity `bf16.size*2 == fp32.size`; no SGLang code property pinned. (tautology)

</details>

<details>
<summary><code>test/registered/unit/hardware_backend/mlx/test_runner_init_contract.py</code> (1 method removed)</summary>

- `test_stub_initialize_requires_no_extra_args` — same failure surface as `test_stub_initialize_binds_like_base_call` (both detect a required param beyond `self`); the kept case models the production call site. (mirror)

</details>

<details>
<summary><code>test/registered/unit/managers/test_vocab_boundary_finish.py</code> (1 method removed)</summary>

- `test_token_above_vocab_size_is_out_of_bounds` — `VOCAB_SIZE+12345` exercises the same `>= vocab_size` branch as the boundary-equals case. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/layers/quantization/test_quark_utils.py</code> (1 method removed)</summary>

- `test_zero_exponent_is_one` — asserts index 127→1.0, already one entry in `test_known_powers_of_two`; self-labeled "pass on both buggy and fixed code". (strict-subset)

</details>









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29058999330](https://github.com/sgl-project/sglang/actions/runs/29058999330)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29058999120](https://github.com/sgl-project/sglang/actions/runs/29058999120)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
