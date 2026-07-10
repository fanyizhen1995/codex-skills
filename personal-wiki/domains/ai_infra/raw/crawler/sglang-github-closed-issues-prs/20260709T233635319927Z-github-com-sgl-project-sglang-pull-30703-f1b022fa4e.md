---
source_id: sglang-github-closed-issues-prs
title: '[misc] Remove unit test cases that fail the admission criteria (round 2)'
canonical_url: https://github.com/sgl-project/sglang/pull/30703
captured_at: '2026-07-09T23:36:35.319927+00:00'
content_hash: f1b022fa4ea900b5b4ae615b46ede9d614bcd805edfd7ef5d6f1e7a6fd38bb05
---
# [misc] Remove unit test cases that fail the admission criteria (round 2)

URL: https://github.com/sgl-project/sglang/pull/30703
State: closed
Labels: documentation, hicache, run-ci
Closed at: 2026-07-09T23:35:59Z
Merged at: 2026-07-09T23:35:59Z

Continuation of the admission-criteria pruning from #30690, covering 23 unit test files not in the first pass. Every deletion is backed by a stronger kept case or a verified dead-code/dead-patch claim; each was cross-checked by a verification agent.

Also sharpens `.claude/rules/unit-test-admission.md` with a "distinguishing test" section so future pruning does not over-delete: a case that *looks* like a tautology/mirror stays when it guards an external-source literal (OTel spec, protocol field) or a completeness/negative-branch contract that no other case covers. Two concrete examples added (one keep, one delete), drawn from cases that were rescued during this round.

A file-by-file review (6 parallel scanning agents + 5 verification agents) confirmed each candidate. Summary of what was removed and why:

<details>
<summary><code>test/registered/unit/function_call/test_hunyuan_detector.py</code> (8 methods + 1 class removed)</summary>

- `TestHunyuanDetectorAccuracy` (whole class) — every case is a byte-identical duplicate of a `TestHunyuanDetectorDetectAndParse` case. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/parser/test_code_completion_parser.py</code> (2 methods removed)</summary>

- `test_middle_and_end_are_distinct` — asserts two `FimPosition` enum members are unequal; true by construction of any Enum. (tautology)
- `test_dataclass_fields` — constructs a `CompletionTemplate` then reads back the same fields; pure field echo. (tautology)

</details>

<details>
<summary><code>test/registered/unit/parser/test_template_manager.py</code> (1 method removed)</summary>

- `test_minicpm5_not_misclassified_as_qwen` — byte-identical template/vocab/expected-parser row in `test_tool_call_parser_rule_values_via_snippets`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/parser/test_jinja_template_utils.py</code> (1 method removed)</summary>

- `test_detect_m_content_pattern` — identical to `test_detect_msg_content_pattern` except the loop variable `msg`→`m`; detection is AST-based, not string-matched on the var name. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/utils/test_hf_transformers.py</code> (4 methods + 1 class removed)</summary>

- `TestPatchRopeParametersValidation` (whole class, 3 methods) — guards a `rope_theta` injection patch removed in `ca88b7f1d2`; the surviving `_patch_rope_parameters_validation` only guards `standardize_rope_params`. These tests now assert only upstream `transformers` library behavior. (dead-code)
- `TestNormalizeRopeScalingCompat.test_no_op_when_no_rope_scaling` — strict-subset of `test_no_op_when_rope_scaling_is_none` (which covers the explicit-None path). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/observability/test_trace.py</code> (13 methods removed)</summary>

- `TestDataclasses.test_trace_thread_info` / `test_trace_event` / `test_trace_slice_context` — dataclass field-echo mirrors. (mirror)
- `TestDataclasses.test_trace_thread_context` — asserts `len([]) == 0` on input it just supplied. (tautology)
- `TestTraceCustomIdGenerator.test_generates_nonzero_ids` — name claims "nonzero" but only asserts `isinstance(trace_id, int)`; no `> 0` check. (tautology)
- `TestTraceReqContextDisabled.test_all_methods_noop` / `test_trace_set_thread_info_disabled` — call methods with zero assertions. (tautology)
- `TestTraceReqContextEnabled.test_trace_set_root_attrs` / `test_trace_set_root_attrs_no_span` / `test_trace_set_thread_attrs` / `test_trace_req_finish_without_start` — call methods with zero assertions. (tautology)

</details>

<details>
<summary><code>test/registered/unit/observability/test_request_metrics_exporter.py</code> (1 method removed)</summary>

- `TestFileRequestMetricsExporter.test_close_noop_when_no_handler` — calls `.close()`, zero assertions. (tautology)

</details>

<details>
<summary><code>test/registered/unit/utils/test_profile_merger.py</code> (1 method removed)</summary>

- `TestProfileMergerIntegration.test_integration_parameters` — uses `inspect.signature` to check param names; pure signature-shape check with no behavioral assertion. (mirror)

</details>

<details>
<summary><code>test/registered/unit/utils/test_auth.py</code> (3 methods removed)</summary>

- `TestAuthDecision.test_allowed_default` — constructor field echo + default-value restatement. (mirror)
- `TestAuthLevel.test_enum_values` — restates the three enum string literals exactly as written in `auth.py`. (mirror)
- `TestAuthLevelDecorator.test_decorator_preserves_function` — calls wrapped fn, asserts `42`; the decorator's auth behavior is NOT exercised (covered by `test_decorator_sets_auth_level`). (tautology)

</details>

<details>
<summary><code>test/registered/unit/constrained/test_grammar_manager.py</code> (1 method removed)</summary>

- `TestGetReadyGrammarRequests.test_future_exception_creates_invalid_grammar_object` — identical failure mechanism (future raises → `InvalidGrammarObject` + abort) to `TestStrictReasoningPaths.test_future_exception_creates_invalid_grammar`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_store_cache_4d.py</code> (2 methods removed)</summary>

- `test_store_cache_4d_int64_loc` — sets `loc_dtype=torch.int64`, which is the helper default; the same int64 path is covered by the byte-identity tests. (strict-subset)
- `test_store_cache_4d_dtype_bf16` — sets `dtype=torch.bfloat16`, which is the default; identical config to `test_store_cache_4d_ps_gt1_byte_identical`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_swa_unittest.py</code> (1 method removed)</summary>

- `test_swa_memory_pool` — size-accounting mirror (alloc decrements available by 1 per pool); ends with a bare `print(result)` on the `translate_loc_from_full_to_swa` result with zero assertion. The translate path is covered by dedicated tests in `test_multi_ended_allocator.py` + 30 production call sites. (mirror)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_hicache_file_lru_unit.py</code> (1 method removed)</summary>

- `test_concurrent_sets_keep_total_consistent_with_lru` — spawns 8 daemon threads with no deterministic interleaving; both invariants (total consistency, `<= cap`) are covered deterministically by single-threaded tests including `test_pre_reservation_visible_during_write`. (stress)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_swa_lock_release_lifecycle.py</code> (1 method removed)</summary>

- `test_full_lifecycle_inc_dec_swa_dec_lock_balances` — every assertion covered by `test_dec_swa_lock_only_leaf_tombstones_and_frees` + `test_dec_lock_ref_skip_swa_true_drops_full_only`. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_embedding_cache_controller.py</code> (1 method removed)</summary>

- `test_filling_entry_is_not_evictable` — asserts `is_evictable() == False` for FILLING state; transitively covered by `test_filling_entry_is_not_in_evictable_lru_until_ready` (which gates `touch` on `is_evictable()`). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/lora/test_mem_pool_ep_unit.py</code> (2 methods removed)</summary>

- `TestIterLocalExpertWeightsTensor.test_passthrough_without_ep` — tensor path covered by `test_rank1_of_ep2_sees_upper_half`; no-EP identity covered by the dict-class sibling. (strict-subset)
- `TestModuleLevelHelpers.test_keeps_global_expert_ids_defaults_to_false` — asserts the trivial default-False return; the real wiring guard is `test_ep4_flashinfer_cutlass_keeps_global`. (tautology)

</details>

<details>
<summary><code>test/registered/unit/model_loader/test_modelopt_loader.py</code> (3 methods removed)</summary>

- `test_successful_fp8_quantization` — replaces `load_model` with a hand-written `mock_load_model` and asserts on the mock's own calls; the real flow is covered by `test_calibration_workflow_integration`. (mirror)
- `test_engine_with_modelopt_quant_parameter` — strict-subset of `test_engine_with_modelopt_quant_cli_argument` (same assertion plus CLI parsing). (strict-subset)
- `test_mixed_precision_uses_nvfp4_min_capability` — asserts `ModelOptMixedPrecisionConfig.get_min_capability() == ModelOptFp4Config.get_min_capability()`; the source body is literally `return ModelOptFp4Config.get_min_capability()`. (tautology)

</details>

<details>
<summary><code>test/registered/unit/model_loader/test_modelopt_export.py</code> (1 method + 1 dead helper removed)</summary>

- `test_setup_quantization_without_export` — negative branch of `if export_path`; the positive case (`test_setup_quantization_with_export_after_calibration`) is the load-bearing one. (strict-subset)
- `_get_export_info` (dead helper) — never called by any test; references an undefined `self._validate_export`. (dead-code)

</details>

<details>
<summary><code>test/registered/unit/managers/test_io_struct.py</code> (2 methods removed)</summary>

- `test_multiple_input_formats` — asserts only `is_single==True` for single inputs; covered by `test_input_ids_normalization` + `test_input_embeds_normalization`. (tautology)
- `test_input_embeds_single_to_batch_conversion` — strict-subset of `test_input_embeds_with_parallel_sampling` (same single→batch expand for n=2, plus more). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/managers/test_load_snapshot_backends.py</code> (2 methods removed)</summary>

- `test_should_use_zmq_single_node` / `test_should_use_zmq_dp_attention_single_node` — False-branch mirrors of a trivial 2-line predicate; the False branch is covered behaviorally by `test_shm_mode`. (mirror)

</details>

<details>
<summary><code>test/registered/unit/entrypoints/openai/test_protocol.py</code> (2 methods removed)</summary>

- `test_parsed_response_fields_protocol` — isinstance-only against a `runtime_checkable` Protocol; pure library behavior. (tautology)
- `test_model_serialization_roundtrip` — pure pydantic round-trip identity; no sglang-specific normalization exercised (covered by dedicated reasoning-effort / tool-choice tests). (tautology)

</details>

<details>
<summary><code>test/registered/unit/test_runtime_context.py</code> (1 method removed)</summary>

- `test_context_publish_visible_through_legacy_getter` — strict-subset of `test_legacy_setter_publishes_into_context` (identical assertion plus context-getter + `get_context().server_args`). (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/test_precision_baseline_store.py</code> (2 methods removed)</summary>

- `test_from_env_default_revision` — asserts `revision == "main"` with only the repo var set; `test_from_env_reads_required_var` does the same setup and asserts more. (strict-subset)
- `test_retries_on_5xx` — identical retry branch to `test_retries_on_429` (the transient predicate treats 429 and 5xx identically). (strict-subset)

</details>

<details>
<summary><code>.claude/rules/unit-test-admission.md</code> (distinguishing-test section added)</summary>

Adds a "Distinguishing test" subsection under "Not admissible" that draws the line between a true mirror/tautology (delete) and a case that guards a silent-failure path (keep as bookkeeping):

- **Keep** when the assertion guards an external-source literal (e.g. an OTel spec string) — deleting it removes the only guard against silently copying the spec wrong.
- **Keep** when the assertion guards a completeness / negative-branch contract ("all builtins registered", "non-matching id does *not* trigger") that no other case covers.
- **Delete** when the assertion merely echoes an isolated implementation output — changing it breaks nothing outside the line itself.

Two concrete examples (one keep, one delete) added inline.

</details>



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29055923001](https://github.com/sgl-project/sglang/actions/runs/29055923001)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29055922841](https://github.com/sgl-project/sglang/actions/runs/29055922841)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
