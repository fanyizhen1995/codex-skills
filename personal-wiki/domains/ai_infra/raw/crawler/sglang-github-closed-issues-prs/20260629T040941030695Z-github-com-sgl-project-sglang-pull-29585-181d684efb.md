---
source_id: sglang-github-closed-issues-prs
title: '[Test] Add unit tests for srt/kv_canary (#20865)'
canonical_url: https://github.com/sgl-project/sglang/pull/29585
captured_at: '2026-06-29T04:09:41.030695+00:00'
content_hash: 181d684efb54c4e0ad5846448b810d9d68858ef4dabf33b5f3de8a9a9025afa0
---
# [Test] Add unit tests for srt/kv_canary (#20865)

URL: https://github.com/sgl-project/sglang/pull/29585
State: closed
Labels: npu
Closed at: 2026-06-28T23:14:46Z
Merged at: 

154 tests covering the srt/kv_canary KV cache verification subsystem.

No server, no GPU, no model loading.
Ref: #20865

## Motivation

Added seven new test files under `test/registered/unit/kv_canary/` covering the pure-logic layer of SGLang's KV cache canary verification system.

`srt/kv_canary/` currently has no dedicated unit tests. The kv_canary subsystem detects KV cache correctness violations at runtime by writing canary tokens into KV cache slots and verifying them on subsequent reads. It covers configuration parsing, capacity arithmetic, device state allocation, sweep plan building, forward-batch input extraction, and buffer group management. Regressions in these files silently disable or misconfigure the verification pipeline.

Two behavioral bugs were caught empirically during test development:

1. `CanaryConfig.from_env()` applies `.lower()` before mode validation — `"NONE"` is accepted, not rejected. The initial assumption was wrong; the test was corrected to assert success.
2. `PlanInput.fill_from_forward_batch()` fills only `[:bs]` elements of `extend_seq_lens`, not the full capacity-sized tensor. Padding slots correctly stay zero. Tests corrected to assert `[:bs]` only.

## Coverage

`config.py` (27 tests):
- `CanaryMode` enum — member count, str subclass, all string values.
- `CanaryConfig.from_env()` — mode=none/log/raise, uppercase accepted, whitespace stripped, invalid mode raises ValueError, health_check/warn modes raise on invalid config.
- Default field values — ring_capacity, stats_print_every_n_steps, enable_verify_token_assert, enable_write_input_assert, real_kv_hash_mode all/none/partial, sweep_interval.
- Env var overrides — each field overridden independently via patched env.
- Frozen dataclass rejects mutation.

`capacities.py` (23 tests):
- `CanaryLaunchCapacities.from_args()` arithmetic — per_forward_verify_capacity = pool_slot_count * 3, verified for small/large pool sizes.
- write_entry_capacity — no spec tokens uses one per bs, spec tokens scale correctly, zero draft tokens treated as no-spec, chunked None gives math.inf limit, chunked size limits extend tokens.
- write_req_capacity — equals pool when no cuda graph, uses cuda_graph_max when larger, uses pool when larger than cuda graph.
- Validation — non-positive pool_slot_count raises, negative cuda_graph_max_bs raises, non-positive max_prefill_tokens raises, non-positive max_seq_len raises, negative spec_draft_tokens raises, negative/zero req_to_token_pool_size raises.
- Post-init validation — zero verify/write_entry/write_req capacity raises.
- Frozen dataclass rejects mutation.

`state.py` (29 tests):
- `ViolationLog.allocate()` — violation_ring shape/dtype/zero-init, write_index shape/dtype/zero-init, ring capacity matches config, zero/negative ring_capacity raises, frozen dataclass rejects mutation, VIOLATION_FIELDS const used.
- `CanaryDeviceState.allocate()` — kernel_run_counters shape/dtype/zero-init, slot_run_counters shape matches num_tags/dtype/zero-init, enable_chain_position_assert shape/dtype/one-init, violation_log ring capacity matches config, req_to_verify_expected_tokens allocated when enabled/None when disabled/dtype correct, missing alloc_size raises when verify enabled, missing max_context_len raises when verify enabled, zero/negative num_tags raises, frozen dataclass rejects mutation.

`sweep_plan_builder.py` (12 tests):
- `_swa_translate()` — empty indices returns same object, sequential lookup, single element, repeated indices, output dtype is int64, int32 LUT cast to int64, negative anchor values preserved as passthrough, mixed negative and positive, -1/-2 preserved.

`expected_inputs.py` (16 tests):
- `ExpectedInputs.allocate()` — tokens/positions shape, dtype, separate tensor objects, capacity=1, frozen dataclass rejects mutation.
- `ExpectedInputs.slice()` — returns ExpectedInputs instance, correct shape, full capacity same as original, zero returns empty, data shared with original (view semantics), writes through slice visible in original, dtype preserved.

`plan_input.py` (25 tests):
- `PlanInput.allocate()` — all tensors zero-init, shape/dtype for extend_seq_lens/prefix_lens/req_pool_indices/valid_lens, frozen dataclass rejects mutation.
- `PlanInput.zero()` — clears all tensors.
- `PlanInput.fill_from_forward_batch()` — DECODE: req_pool_indices copied, prefix_lens from positions, extend_seq_lens all ones, padding tail zeroed; EXTEND: prefix_lens from extend_prefix_lens, extend_seq_lens from extend_seq_lens; TARGET_VERIFY: prefix_lens from seq_lens, extend_seq_lens is draft_token_num; DRAFT_EXTEND_V2: extend_seq_lens copied, prefix = seq - extend; unknown mode raises NotImplementedError; valid_lens copied when present, stays zero when None.
- Batch size guard — equal to capacity accepted, larger than capacity raises RuntimeError.

`buffer_group.py` (22 tests):
- `PoolKind` enum — IntEnum, member count, FULL/SWA values, FULL < SWA ordering.
- `CanaryBufferGroup` fields — kind full/swa, k_head/k_tail stored, v_head/v_tail None when not set, swa_index_lut stored/None for full group, real_kv_sources_k/v empty tuple defaults, kv_token_id_vs_position offset 0/1, frozen dataclass rejects mutation.
- `CanaryBufferGroup.has_v_half` — True when v_head set, False when v_head None, returns bool.

All files registered via:
```python
register_cpu_ci(est_time=5, suite="base-a-test-cpu")
```

## Test plan

```
python3 test/registered/unit/kv_canary/test_config.py -v
```

```
test_all_fields_accessible (__main__.TestCanaryConfigFieldAccess) ... ok
test_frozen_dataclass_rejects_mutation (__main__.TestCanaryConfigFieldAccess) ... ok
test_default_enable_verify_token_assert (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_default_enable_write_input_assert (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_default_ring_capacity (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_default_stats_print_every_n_steps (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_real_kv_hash_mode_all (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_real_kv_hash_mode_none (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_real_kv_hash_mode_partial (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_sweep_interval_from_server_args (__main__.TestCanaryConfigFromEnvDefaults) ... ok
test_invalid_mode_health_check_raises (__main__.TestCanaryConfigFromEnvMode) ... ok
test_invalid_mode_raises_value_error (__main__.TestCanaryConfigFromEnvMode) ... ok
test_invalid_mode_warn_raises (__main__.TestCanaryConfigFromEnvMode) ... ok
test_mode_log (__main__.TestCanaryConfigFromEnvMode) ... ok
test_mode_none (__main__.TestCanaryConfigFromEnvMode) ... ok
test_mode_raise (__main__.TestCanaryConfigFromEnvMode) ... ok
test_mode_uppercase_is_accepted (__main__.TestCanaryConfigFromEnvMode) ... ok
test_mode_with_whitespace_stripped (__main__.TestCanaryConfigFromEnvMode) ... ok
test_enable_verify_token_assert_from_env (__main__.TestCanaryConfigFromEnvOverrides) ... ok
test_enable_write_input_assert_from_env (__main__.TestCanaryConfigFromEnvOverrides) ... ok
test_ring_capacity_from_env (__main__.TestCanaryConfigFromEnvOverrides) ... ok
test_stats_print_every_n_steps_from_env (__main__.TestCanaryConfigFromEnvOverrides) ... ok
test_is_str_subclass (__main__.TestCanaryModeEnum) ... ok
test_log_value (__main__.TestCanaryModeEnum) ... ok
test_members_count (__main__.TestCanaryModeEnum) ... ok
test_none_value (__main__.TestCanaryModeEnum) ... ok
test_raise_value (__main__.TestCanaryModeEnum) ... ok

----------------------------------------------------------------------
Ran 27 tests in 0.004s
```

```
python3 test/registered/unit/kv_canary/test_capacities.py -v
```

```
test_is_frozen (__main__.TestFrozenDataclass) ... ok
test_negative_any_field_raises (__main__.TestPostInitValidation) ... ok
test_zero_verify_capacity_raises (__main__.TestPostInitValidation) ... ok
test_zero_write_entry_capacity_raises (__main__.TestPostInitValidation) ... ok
test_zero_write_req_capacity_raises (__main__.TestPostInitValidation) ... ok
test_negative_cuda_graph_max_bs_raises (__main__.TestValidationErrors) ... ok
test_negative_req_to_token_pool_size_raises (__main__.TestValidationErrors) ... ok
test_negative_spec_draft_tokens_raises (__main__.TestValidationErrors) ... ok
test_nonpositive_max_prefill_tokens_raises (__main__.TestValidationErrors) ... ok
test_nonpositive_max_seq_len_raises (__main__.TestValidationErrors) ... ok
test_nonpositive_pool_slot_count_raises (__main__.TestValidationErrors) ... ok
test_nonpositive_req_to_token_pool_size_raises (__main__.TestValidationErrors) ... ok
test_verify_capacity_is_three_times_pool_slot_count (__main__.TestVerifyCapacityArithmetic) ... ok
test_verify_capacity_with_large_pool (__main__.TestVerifyCapacityArithmetic) ... ok
test_verify_capacity_with_small_pool (__main__.TestVerifyCapacityArithmetic) ... ok
test_chunked_none_gives_inf_limit (__main__.TestWriteEntryCapacityArithmetic) ... ok
test_chunked_size_limits_extend_tokens (__main__.TestWriteEntryCapacityArithmetic) ... ok
test_no_spec_tokens_uses_one_per_bs (__main__.TestWriteEntryCapacityArithmetic) ... ok
test_spec_tokens_scale_write_entry (__main__.TestWriteEntryCapacityArithmetic) ... ok
test_spec_zero_draft_tokens_treated_as_no_spec (__main__.TestWriteEntryCapacityArithmetic) ... ok
test_req_capacity_equals_pool_when_no_cuda_graph (__main__.TestWriteReqCapacityArithmetic) ... ok
test_req_capacity_uses_cuda_graph_max_when_larger (__main__.TestWriteReqCapacityArithmetic) ... ok
test_req_capacity_uses_pool_when_larger_than_cuda_graph (__main__.TestWriteReqCapacityArithmetic) ... ok

----------------------------------------------------------------------
Ran 23 tests in 0.000s
```

```
python3 test/registered/unit/kv_canary/test_state.py -v
```

```
test_enable_chain_position_assert_dtype (__main__.TestCanaryDeviceStateAllocate) ... ok
test_enable_chain_position_assert_initialised_to_one (__main__.TestCanaryDeviceStateAllocate) ... ok
test_enable_chain_position_assert_shape (__main__.TestCanaryDeviceStateAllocate) ... ok
test_frozen_dataclass_rejects_mutation (__main__.TestCanaryDeviceStateAllocate) ... ok
test_kernel_run_counters_dtype (__main__.TestCanaryDeviceStateAllocate) ... ok
test_kernel_run_counters_initialised_to_zero (__main__.TestCanaryDeviceStateAllocate) ... ok
test_kernel_run_counters_shape (__main__.TestCanaryDeviceStateAllocate) ... ok
test_missing_alloc_size_raises_when_verify_enabled (__main__.TestCanaryDeviceStateAllocate) ... ok
test_missing_max_context_len_raises_when_verify_enabled (__main__.TestCanaryDeviceStateAllocate) ... ok
test_negative_num_tags_raises (__main__.TestCanaryDeviceStateAllocate) ... ok
test_req_to_verify_expected_tokens_allocated_when_enabled (__main__.TestCanaryDeviceStateAllocate) ... ok
test_req_to_verify_expected_tokens_dtype (__main__.TestCanaryDeviceStateAllocate) ... ok
test_req_to_verify_expected_tokens_none_when_disabled (__main__.TestCanaryDeviceStateAllocate) ... ok
test_slot_run_counters_dtype (__main__.TestCanaryDeviceStateAllocate) ... ok
test_slot_run_counters_initialised_to_zero (__main__.TestCanaryDeviceStateAllocate) ... ok
test_slot_run_counters_shape_matches_num_tags (__main__.TestCanaryDeviceStateAllocate) ... ok
test_violation_log_ring_capacity_matches_config (__main__.TestCanaryDeviceStateAllocate) ... ok
test_zero_num_tags_raises (__main__.TestCanaryDeviceStateAllocate) ... ok
test_frozen_dataclass_rejects_mutation (__main__.TestViolationLogAllocate) ... ok
test_negative_ring_capacity_raises (__main__.TestViolationLogAllocate) ... ok
test_ring_capacity_one (__main__.TestViolationLogAllocate) ... ok
test_violation_ring_dtype (__main__.TestViolationLogAllocate) ... ok
test_violation_ring_initialised_to_zero (__main__.TestViolationLogAllocate) ... ok
test_violation_ring_shape (__main__.TestViolationLogAllocate) ... ok
test_violation_ring_uses_violation_fields_const (__main__.TestViolationLogAllocate) ... ok
test_violation_write_index_dtype (__main__.TestViolationLogAllocate) ... ok
test_violation_write_index_initialised_to_zero (__main__.TestViolationLogAllocate) ... ok
test_violation_write_index_shape (__main__.TestViolationLogAllocate) ... ok
test_zero_ring_capacity_raises (__main__.TestViolationLogAllocate) ... ok

----------------------------------------------------------------------
Ran 29 tests in 0.011s
```

```
python3 test/registered/unit/kv_canary/test_sweep_plan_builder.py -v
```

```
test_all_negative_all_preserved (__main__.TestSwaTranslateAnchorPassthrough) ... ok
test_mixed_negative_and_positive (__main__.TestSwaTranslateAnchorPassthrough) ... ok
test_negative_minus_one_is_preserved (__main__.TestSwaTranslateAnchorPassthrough) ... ok
test_negative_minus_two_is_preserved (__main__.TestSwaTranslateAnchorPassthrough) ... ok
test_zero_positive_index_maps_correctly (__main__.TestSwaTranslateAnchorPassthrough) ... ok
test_empty_indices_returns_empty (__main__.TestSwaTranslateEmpty) ... ok
test_empty_indices_same_object_returned (__main__.TestSwaTranslateEmpty) ... ok
test_int32_lut_is_cast_to_int64 (__main__.TestSwaTranslateLutDataTypes) ... ok
test_output_dtype_is_int64 (__main__.TestSwaTranslateNormal) ... ok
test_repeated_indices (__main__.TestSwaTranslateNormal) ... ok
test_sequential_lookup (__main__.TestSwaTranslateNormal) ... ok
test_single_element (__main__.TestSwaTranslateNormal) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.007s
```

```
python3 test/registered/unit/kv_canary/test_expected_inputs.py -v
```

```
test_capacity_one (__main__.TestExpectedInputsAllocate) ... ok
test_frozen_dataclass_rejects_mutation (__main__.TestExpectedInputsAllocate) ... ok
test_positions_dtype (__main__.TestExpectedInputsAllocate) ... ok
test_positions_shape (__main__.TestExpectedInputsAllocate) ... ok
test_tokens_and_positions_are_separate_tensors (__main__.TestExpectedInputsAllocate) ... ok
test_tokens_dtype (__main__.TestExpectedInputsAllocate) ... ok
test_tokens_shape (__main__.TestExpectedInputsAllocate) ... ok
test_slice_data_shared_with_original (__main__.TestExpectedInputsSlice) ... ok
test_slice_dtype_preserved (__main__.TestExpectedInputsSlice) ... ok
test_slice_full_capacity_same_as_original (__main__.TestExpectedInputsSlice) ... ok
test_slice_is_view_of_original_positions (__main__.TestExpectedInputsSlice) ... ok
test_slice_is_view_of_original_tokens (__main__.TestExpectedInputsSlice) ... ok
test_slice_returns_expected_inputs_instance (__main__.TestExpectedInputsSlice) ... ok
test_slice_shape (__main__.TestExpectedInputsSlice) ... ok
test_slice_zero_returns_empty (__main__.TestExpectedInputsSlice) ... ok
test_writes_through_slice_visible_in_original (__main__.TestExpectedInputsSlice) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.002s
```

```
python3 test/registered/unit/kv_canary/test_plan_input.py -v
```

```
test_decode_extend_seq_lens_all_ones (__main__.TestFillFromForwardBatchDecode) ... ok
test_decode_padding_tail_zeroed (__main__.TestFillFromForwardBatchDecode) ... ok
test_decode_prefix_lens_from_positions (__main__.TestFillFromForwardBatchDecode) ... ok
test_decode_req_pool_indices_copied (__main__.TestFillFromForwardBatchDecode) ... ok
test_draft_extend_v2_extend_seq_lens_copied (__main__.TestFillFromForwardBatchDraftExtendV2) ... ok
test_draft_extend_v2_prefix_is_seq_minus_extend (__main__.TestFillFromForwardBatchDraftExtendV2) ... ok
test_extend_prefix_lens_from_extend_prefix_lens (__main__.TestFillFromForwardBatchExtend) ... ok
test_extend_seq_lens_from_extend_seq_lens (__main__.TestFillFromForwardBatchExtend) ... ok
test_target_verify_extend_seq_lens_is_draft_token_num (__main__.TestFillFromForwardBatchTargetVerify) ... ok
test_target_verify_prefix_lens_from_seq_lens (__main__.TestFillFromForwardBatchTargetVerify) ... ok
test_unknown_mode_raises_not_implemented (__main__.TestFillFromForwardBatchUnknownMode) ... ok
test_valid_lens_copied_when_present (__main__.TestFillFromForwardBatchValidLens) ... ok
test_valid_lens_stays_zero_when_none (__main__.TestFillFromForwardBatchValidLens) ... ok
test_all_tensors_initialised_to_zero (__main__.TestPlanInputAllocate) ... ok
test_extend_seq_lens_dtype (__main__.TestPlanInputAllocate) ... ok
test_extend_seq_lens_shape (__main__.TestPlanInputAllocate) ... ok
test_frozen_dataclass_rejects_mutation (__main__.TestPlanInputAllocate) ... ok
test_prefix_lens_dtype (__main__.TestPlanInputAllocate) ... ok
test_prefix_lens_shape (__main__.TestPlanInputAllocate) ... ok
test_req_pool_indices_dtype (__main__.TestPlanInputAllocate) ... ok
test_req_pool_indices_shape (__main__.TestPlanInputAllocate) ... ok
test_valid_lens_shape (__main__.TestPlanInputAllocate) ... ok
test_batch_equal_to_capacity_is_accepted (__main__.TestPlanInputBatchSizeGuard) ... ok
test_batch_larger_than_capacity_raises_runtime_error (__main__.TestPlanInputBatchSizeGuard) ... ok
test_zero_clears_all_tensors (__main__.TestPlanInputZero) ... ok

----------------------------------------------------------------------
Ran 25 tests in 0.005s
```

```
python3 test/registered/unit/kv_canary/test_buffer_group.py -v
```

```
test_frozen_dataclass_rejects_mutation (__main__.TestCanaryBufferGroupFields) ... ok
test_k_head_stored (__main__.TestCanaryBufferGroupFields) ... ok
test_k_tail_stored (__main__.TestCanaryBufferGroupFields) ... ok
test_kind_full (__main__.TestCanaryBufferGroupFields) ... ok
test_kind_swa (__main__.TestCanaryBufferGroupFields) ... ok
test_kv_token_id_vs_position_offset_one (__main__.TestCanaryBufferGroupFields) ... ok
test_kv_token_id_vs_position_offset_zero (__main__.TestCanaryBufferGroupFields) ... ok
test_real_kv_sources_k_empty_tuple (__main__.TestCanaryBufferGroupFields) ... ok
test_real_kv_sources_v_empty_tuple (__main__.TestCanaryBufferGroupFields) ... ok
test_swa_index_lut_none_for_full_group (__main__.TestCanaryBufferGroupFields) ... ok
test_swa_index_lut_stored (__main__.TestCanaryBufferGroupFields) ... ok
test_v_head_none_when_not_set (__main__.TestCanaryBufferGroupFields) ... ok
test_v_tail_none_when_not_set (__main__.TestCanaryBufferGroupFields) ... ok
test_has_v_half_false_returns_bool (__main__.TestCanaryBufferGroupHasVHalf) ... ok
test_has_v_half_false_when_v_head_none (__main__.TestCanaryBufferGroupHasVHalf) ... ok
test_has_v_half_true_returns_bool (__main__.TestCanaryBufferGroupHasVHalf) ... ok
test_has_v_half_true_when_v_head_set (__main__.TestCanaryBufferGroupHasVHalf) ... ok
test_full_less_than_swa (__main__.TestPoolKindEnum) ... ok
test_full_value (__main__.TestPoolKindEnum) ... ok
test_is_int_enum (__main__.TestPoolKindEnum) ... ok
test_members_count (__main__.TestPoolKindEnum) ... ok
test_swa_value (__main__.TestPoolKindEnum) ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.001s
```

## Accuracy Tests
N/A — test-only change. No kernel or model-forward code is touched.

## Speed Tests and Profiling
N/A — this PR only adds unit tests and does not affect the inference path.

## Checklist
- [x] Format your code according to the Format code with pre-commit.
- [x] Add unit tests according to the Run and add unit tests.
- [ ] Update documentation according to Write documentations.
- [ ] Provide accuracy and speed benchmark results according to Test the accuracy and Benchmark the speed.
- [x] Follow the SGLang code style guidance.

## Review and Merge Process
Ping Merge Oncalls to start the process. See the PR Merge Process.
Get approvals from CODEOWNERS and other reviewers.
Trigger CI tests with comments or contact authorized users to do so.
Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28338042182](https://github.com/sgl-project/sglang/actions/runs/28338042182)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28338042096](https://github.com/sgl-project/sglang/actions/runs/28338042096)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
