---
source_id: sglang-github-closed-issues-prs
title: '[misc] Remove unit test cases that fail the admission criteria'
canonical_url: https://github.com/sgl-project/sglang/pull/30690
captured_at: '2026-07-09T23:36:35.321031+00:00'
content_hash: 3e648f06b15bf7bb41de935fe5e9ce5dd14ffd09c24231e0a3b82edb6b31e283
---
# [misc] Remove unit test cases that fail the admission criteria

URL: https://github.com/sgl-project/sglang/pull/30690
State: closed
Labels: hicache, run-ci, apple-silicon
Closed at: 2026-07-09T22:31:29Z
Merged at: 2026-07-09T22:31:29Z

Prune unit test cases that fail the admission criteria in `.claude/rules/unit-test-admission.md`: happy-path tautologies, mirror tests that restate the implementation, strict-subset duplicates of a richer case, guards for unreachable/dead code paths, and probabilistic stress with no reproduction value. Every case traceable to a bug-fix PR is kept as a regression guard.

<details>
<summary><b>Review follow-up</b> — branches left unguarded after pruning</summary>

A file-by-file review found a few cases where deleting a low-value test left its guarded production branch with no remaining coverage. These are addressed in a follow-up commit:

- **Removed the dead MPT tuple-unpack branch** in `conversation.py`. `messages` is typed `List[List[str]]` and `append_message` always appends lists; the `type(message) is tuple` path (copied from vLLM in InternVL3) has zero producers. Deleting it is consistent with deleting its only test.
- **Restored `test_request_betas_is_accepted_and_logged`** — the `if anthropic_request.betas: logger.info(...)` branch in anthropic serving is exercised by no other kept test.
- **Restored plain-slot None-skip coverage** as `test_plain_slot_with_missing_fb_attr_keeps_sentinel` — the `getattr(fb, name, None); if src is None: continue` skip in `fill_from` for a plain (no `source_fn`/`slice_fn`) copy slot had no remaining direct unit guard.
- **Added one positive `has_tool_call` case per detector family** (PythonicDetector, GptOssDetector, GigaChat3Detector). The deleted Pythonic/GptOss cases were themselves broken — they asserted markers the predicate never matched (`<tool_call>` vs the actual pythonic `[func(kw=v)]` regex / the `<|start|>assistant<|channel|>commentary` bot_token). The new cases use the correct markers.

</details>

<details>
<summary><code>test/registered/unit/parser/test_reasoning_parser.py</code> (52 methods + 2 classes removed)</summary>

- `TestStreamingParseResult` (whole class) — 2-field constructor tautology. (tautology)
- `TestQwen3ForcedReasoningDetector` (whole class) — every case duplicated by `TestIntegrationScenarios`'s equivalents. (strict-subset)
- `TestBaseReasoningFormatDetector.test_init` — attribute-assignment mirror. (mirror)
- `TestDeepSeekR1Detector.test_init` — mirror; force-default already pinned behaviorally elsewhere. (strict-subset)
- `TestDeepSeekR1Detector.test_init_no_stream_reasoning` — constructor kwarg passthrough tautology. (tautology)
- `TestDeepSeekR1Detector.test_detect_and_parse_r1_format` — same failure mode as the base class's force_reasoning case. (strict-subset)
- `TestQwen3Detector.test_init` — mirror. (mirror)
- `TestQwen3Detector.test_detect_and_parse_qwen3_format` — byte-identical scenario to the public-API non-stream test. (strict-subset)
- `TestKimiDetector.test_init` — mirror. (mirror)
- `TestKimiDetector.test_detect_and_parse_kimi_format` — token wiring already covered via the public-API streaming scenario. (strict-subset)
- `TestKimiDetector.test_streaming_kimi_format` — subset of the API-level streaming scenario. (strict-subset)
- `TestKimiK2Detector.test_detect_and_parse_tool_interrupt` — same input/assertions as the API-level tool-interruption test. (strict-subset)
- `TestKimiK2Detector.test_streaming_tool_interrupt` — streaming half of the same duplicate. (strict-subset)
- `TestKimiK2Detector.test_streaming_after_interrupt_is_normal` — already asserted by the same API-level test's chunk list. (strict-subset)
- `TestGlm45Detector.test_init` — mirror. (mirror)
- `TestGlm45Detector.test_detect_and_parse_normal_reasoning` — inherited-body duplicate of the base class case. (strict-subset)
- `TestGlm45Detector.test_detect_and_parse_tool_interrupt` — same scenario as the API-level test. (strict-subset)
- `TestGlm45Detector.test_detect_and_parse_truncated_reasoning` — duplicate of the base class's start-token case. (strict-subset)
- `TestGlm45Detector.test_streaming_normal_flow` — inherited base streaming flow duplicate. (strict-subset)
- `TestGlm45Detector.test_streaming_tool_interrupt_split_tokens` — misnamed (token is never split across chunks); equals the API-level test. (strict-subset)
- `TestHunyuanDetector.test_init` — mirror. (mirror)
- `TestHunyuanDetector.test_detect_and_parse_normal_reasoning` — inherited-body duplicate. (strict-subset)
- `TestHunyuanDetector.test_detect_and_parse_tool_interrupt` — same parse as the integration test minus the registry pin. (strict-subset)
- `TestHunyuanDetector.test_streaming_normal_reasoning` — inherited-body duplicate. (strict-subset)
- `TestHunyuanDetector.test_streaming_tool_interrupt` — subset of the integration streaming test. (strict-subset)
- `TestHunyuanDetector.test_streaming_after_interrupt_is_normal` — already asserted by the integration test. (strict-subset)
- `TestNemotron3Detector.test_init` — mirror. (mirror)
- `TestNemotron3Detector.test_detect_and_parse_complete_reasoning` — inherited-body duplicate, identical tokens. (strict-subset)
- `TestNemotron3Detector.test_force_nonempty_content_no_thinking_tokens` — same wrapper condition as a kept case. (strict-subset)
- `TestGemma4Detector.test_init` — mirror. (mirror)
- `TestGemma4Detector.test_detect_and_parse_reasoning_only` — covered by the complete-reasoning case plus the base truncated case. (strict-subset)
- `TestGemma4Detector.test_streaming_complete_flow` — weaker union-subset of two stronger kept streaming cases. (strict-subset)
- `TestGemma4Detector.test_streaming_full_start_sequence` — unsplit-variant subset of the chunk-split test. (strict-subset)
- `TestGemma4Detector.test_streaming_partial_start_buffered` — literally the first step of another kept test. (strict-subset)
- `TestGemma4Detector.test_streaming_split_end_token` — partial-end-token buffering already pinned by base + buffer-loss-fix tests. (strict-subset)
- `TestGemma4Detector.test_streaming_force_reasoning` — inherited force-streaming behavior, duplicated elsewhere. (strict-subset)
- `TestGemma4Detector.test_streaming_multiple_reasoning_chunks` — repeated invocation of the same branch, no new failure mode. (strict-subset)
- `TestGemma4Detector.test_force_reasoning` — third duplicate of the inherited force+end-split behavior. (strict-subset)
- `TestIntegrationScenarios.test_deepseek_r1_complete_response` — detector-level test has stronger exact assertions; registry/API covered elsewhere. (strict-subset)
- `TestIntegrationScenarios.test_qwen3_streaming_scenario` — same flow as a kept test with weaker assertions. (strict-subset)
- `TestIntegrationScenarios.test_gemma4_complete_response` — duplicate of the kept detector-level test (exact-equality incl. label strip). (strict-subset)
- `TestIntegrationScenarios.test_gemma4_streaming_scenario` — union-subset of the kept Gemma4 streaming tests. (strict-subset)
- `TestBufferLossBugFix.test_partial_start_tag_buffer_preservation` — exercises the same already-fixed return path as the named regression test. (strict-subset)
- `TestBufferLossBugFix.test_multiple_partial_fragments` — same fixed path again, additive dimension only. (strict-subset)
- `TestGptOssDetector.test_detect_and_parse_with_analysis_and_final` — strict subset of the tool-call test. (strict-subset)
- `TestGptOssDetector.test_detect_and_parse_normal_only` — subset of the same. (strict-subset)
- `TestGptOssDetector.test_streaming_with_tool_call` — misnamed (calls non-streaming API); near-identical to another kept case. (strict-subset)
- `TestContinueFinalMessage.test_streaming_returns_empty_when_in_reasoning_and_end_buffered` — identical failure mode to the base class's partial-token case. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/function_call/test_function_call_parser.py</code> (46 methods removed)</summary>

- `TestPythonicDetector.test_parse_streaming_text_before_tool_call` — weaker duplicate of the complete-tool-call streaming test. (strict-subset)
- `TestMistralDetector.test_detect_and_parse_simple_case` — happy-path, weaker input than the kept nested-brackets/text-prefix cases. (tautology)
- `TestBaseFormatDetector.test_tool_name_streaming_with_correct_index` — fully covered by two other cases using harder chunking. (strict-subset)
- `TestBaseFormatDetector.test_multiple_chinese_parameters` — conditional assertions can vacuously pass for the second call. (tautology)
- `TestKimiK2Detector.test_single_tool_call` — strict subset of the multiple-tool-calls case. (strict-subset)
- `TestKimiK2Detector.test_streaming_tool_call` — strict subset of the streaming-multiple-calls case. (strict-subset)
- `TestDeepSeekV4Detector.test_detect_and_parse_json_format` — V4 only overrides wrapper tokens; body logic is inherited from V32 and duplicated there. (strict-subset)
- `TestDeepSeekV4Detector.test_streaming_json_format` — same inherited-logic duplicate. (strict-subset)
- `TestDeepSeekV4Detector.test_detect_and_parse_no_parameters` — duplicate of the V32 case. (strict-subset)
- `TestDeepSeekV4Detector.test_streaming_no_parameters` — duplicate of the V32 regression case. (strict-subset)
- `TestDeepSeekV4Detector.test_streaming_no_parameters_with_whitespace` — duplicate of the V32 case. (strict-subset)
- `TestQwen3CoderDetector.test_single_tool_call` — covered by the multiple-calls case plus the typed-conversion tests. (strict-subset)
- `TestQwen3CoderDetector.test_has_tool_call_detection` — mirror of a one-line substring check. (mirror)
- `TestGlm4MoeDetector.test_single_tool_call` — strict subset of the multiple-calls case. (strict-subset)
- `TestGlm4MoeDetector.test_streaming_tool_call` — strict subset of the streaming-multiple-calls case. (strict-subset)
- `TestGlm47MoeDetector.test_single_tool_call` — same duplicate on the independent detector. (strict-subset)
- `TestGlm47MoeDetector.test_streaming_tool_call` — same duplicate. (strict-subset)
- `TestJsonArrayParser.test_json_detector_has_no_ebnf` — asserts a removed API is absent; no bug escapes if deleted. (dead-code)
- `TestJsonArrayParser.test_parse_streaming_increment_whitespace_handling` — isinstance-only assertion, true for any return value. (tautology)
- `TestJsonArrayParser.test_parse_streaming_increment_nested_objects` — isinstance-only. (tautology)
- `TestJsonArrayParser.test_json_parsing_with_commas` — subset of the three-tool-calls case. (strict-subset)
- `TestJsonArrayParser.test_separator_in_separate_chunk` — isinstance-only. (tautology)
- `TestJsonArrayParser.test_incomplete_json_across_chunks` — isinstance-only. (tautology)
- `TestJsonArrayParser.test_malformed_json_recovery` — isinstance-only; "recovery" is never actually asserted. (tautology)
- `TestJsonArrayParser.test_empty_objects` — isinstance-only. (tautology)
- `TestJsonArrayParser.test_whitespace_handling` — isinstance-only, duplicate intent of another case. (tautology)
- `TestJsonArrayParser.test_multiple_commas_in_chunk` — misnamed (one comma per chunk); strict subset of the three-calls case. (strict-subset)
- `TestJsonArrayParser.test_complete_tool_call_with_trailing_comma` — same trailing-comma shape as the three-calls case. (strict-subset)
- `TestLfm2Detector.test_has_tool_call_true` — `has_tool_call` is a substring check, subset of the partial-marker case. (strict-subset)
- `TestLfm2Detector.test_detect_and_parse_numeric_values` — despite the name, only asserts the function name; adds nothing. (tautology)
- `TestLfm2Detector.test_streaming_json_complete_in_one_chunk` — single-chunk input duplicated by another kept case. (strict-subset)
- `TestLfm2Detector.test_streaming_pythonic_complete_in_one_chunk` — single-chunk pythonic covered by the multiple-calls case. (strict-subset)
- `TestGigaChat3Detector.test_has_tool_call` — mirror of two substring checks. (mirror)
- `TestGigaChat3Detector.test_detect_and_parse_with_content_before` — strict subset of the content-and-eos case. (strict-subset)
- `TestGigaChat3Detector.test_detect_and_parse_with_eos_token` — strict subset of the same case. (strict-subset)
- `TestGigaChat3Detector.test_streaming_json_split_at_quotes` — subsumed by the very-small-chunks case hitting every quote boundary. (strict-subset)
- `TestGigaChat3Detector.test_detect_and_parse_function_call_marker_with_content_before` — both marker forms share one regex; duplicate of the other form's case. (strict-subset)
- `TestGigaChat3Detector.test_detect_and_parse_function_call_marker_with_eos_token` — shared eos-stripping logic, duplicate. (strict-subset)
- `TestGigaChat3Detector.test_detect_and_parse_function_call_marker_invalid_json` — shared JSON validation, duplicate. (strict-subset)
- `TestGigaChat3Detector.test_streaming_function_call_marker_json_split_at_quotes` — shared streaming logic, duplicate. (strict-subset)
- `TestGetStructureConstraint.test_kimi_routes_through_native_with_section_markers` — near-duplicate of a kept case; extra token already pinned elsewhere. (strict-subset)
- `TestQwen25Detector.test_detect_and_parse_single_tool_call` — strict subset of the multiple-tool-calls case. (strict-subset)
- `TestQwen25Detector.test_streaming_single_tool_call` — strict subset of the documented regression case. (strict-subset)
- `TestGemma4Detector.test_has_tool_call` — mirror of a substring check. (mirror)
- `TestGemma4Detector.test_detect_and_parse_tool_index` — `tool_index==0` already exercised by every streaming collector. (strict-subset)
- `TestGemma4Detector.test_parse_gemma4_args_numbers` — same comma-split shape as the booleans case; numeric conversion covered elsewhere. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/parser/test_harmony_parser.py</code> (30 methods + 2 classes removed)</summary>

- `TestEvent` (whole class) — dataclass constructor field tautology. (tautology)
- `TestToken` (whole class) — same. (tautology)
- `TestPrefixHold.test_empty_text` — mirror of an `if not text` guard. (mirror)
- `TestPrefixHold.test_no_matching_prefixes` — implicitly covered by every plain-text-emitting case. (strict-subset)
- `TestIterTokens.test_empty_text` — trivial mirror. (tautology)
- `TestIterTokens.test_single_token` — strict subset of the all-structural-tokens case. (strict-subset)
- `TestCanonicalStrategy.test_init` — mirror of the constructor's token list. (mirror)
- `TestCanonicalStrategy.test_parse_single_analysis_block` — same assertion embedded inside the tool-call-sequence case. (strict-subset)
- `TestCanonicalStrategy.test_parse_single_commentary_block` — covered by the preamble-sequence case. (strict-subset)
- `TestCanonicalStrategy.test_parse_single_final_block` — covered by the complete-reasoning-flow case. (strict-subset)
- `TestCanonicalStrategy.test_parse_tool_call_commentary` — covered by the tool-call-sequence case. (strict-subset)
- `TestCanonicalStrategy.test_parse_tool_call_analysis` — byte-identical input to the built-in-tool-call case, which also exercises the facade. (strict-subset)
- `TestCanonicalStrategy.test_parse_complex_sequence` — strict subset of the tool-call-sequence case. (strict-subset)
- `TestCanonicalStrategy.test_parse_commentary_filler_between_blocks` — strict subset of the repetitive-filler case. (strict-subset)
- `TestTextStrategy.test_init` — mirror of the patterns dict key. (mirror)
- `TestTextStrategy.test_parse_partial_analysis_streaming` — same transition as another case, differing only in text content. (strict-subset)
- `TestHarmonyParser.test_init` — constructor-state mirror. (tautology)
- `TestHarmonyParser.test_streaming_canonical_format` — weak assertions, subsumed by two stronger cases. (strict-subset)
- `TestHarmonyParser.test_streaming_text_format` — only asserts count>0, subsumed by stronger cases. (tautology)
- `TestIntegrationScenarios.test_tool_response_handling` — misnamed (exercises the ordinary commentary path), duplicate of another case. (strict-subset)
- `TestIntegrationScenarios.test_text_fallback_formats` — count-only re-run already covered by two other cases. (strict-subset)
- `TestEdgeCases.test_empty_input` — trivial; incidentally exercised by a property test's `parse("")`. (strict-subset)
- `TestAdditionalEdgeCases.test_prefix_hold_with_empty_token_in_list` — mirror of a guard with no real caller. (mirror)
- `TestAdditionalEdgeCases.test_canonical_commentary_filler_after_call` — assertion stays green even if the filter logic is deleted. (dead-code)
- `TestAdditionalEdgeCases.test_canonical_standalone_structural_token_filtered` — final assertion is `len(events) >= 0`, literally always true. (tautology)
- `TestAdditionalEdgeCases.test_canonical_incomplete_block_returns_partial` — hedged duplicate of an exact-remainder case. (strict-subset)
- `TestAdditionalEdgeCases.test_text_strategy_commentary_channel` — weaker-assertion duplicate of another case. (strict-subset)
- `TestAdditionalEdgeCases.test_canonical_call_with_text_commentary_after` — same non-pinning assertion pattern as another dropped case. (dead-code)
- `TestAdditionalEdgeCases.test_canonical_return_without_final` — assertion is `assertIsInstance(events, list)`, a tautology. (tautology)
- `TestAdditionalEdgeCases.test_canonical_incomplete_parse_block_no_end` — hedged assertion can't distinguish the behavior a property test already pins exactly. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/parser/test_conversation.py</code> (24 methods removed)</summary>

- `TestConversationGetPrompt.test_none_message_in_prompt` — same assertion as another kept case. (strict-subset)
- `TestConversationGetPrompt.test_llama2_with_system` — covered by the combination of two other kept cases. (strict-subset)
- `TestConversationGetPrompt.test_mpt_with_tuple_message` — the tuple-unpack branch it exercises has zero producers under `python/sglang/srt`. (dead-code)
- `TestConversationMethods.test_append_message` — `list.append` tautology. (tautology)
- `TestConversationMethods.test_set_system_message` — setter tautology. (tautology)
- `TestConversationMethods.test_update_last_message` — trivial in-place assignment, no rewrite hazard. (tautology)
- `TestConversationMethods.test_to_openai_api_messages_with_system` — `to_openai_api_messages` has zero callers under `srt`. (dead-code)
- `TestConversationMethods.test_to_openai_api_messages_without_system` — same dead API. (dead-code)
- `TestConversationMethods.test_to_openai_api_messages_skips_none_assistant` — same dead API. (dead-code)
- `TestConversationMethods.test_to_gradio_chatbot` — `to_gradio_chatbot` has zero callers. (dead-code)
- `TestConversationMethods.test_to_gradio_chatbot_pending_response` — same dead API. (dead-code)
- `TestConversationMethods.test_append_image` — thin-wrapper tautology, covered end-to-end elsewhere. (strict-subset)
- `TestConversationMethods.test_append_video` — same. (strict-subset)
- `TestConversationMethods.test_append_audio` — same. (strict-subset)
- `TestConversationMethods.test_dict_serialization` — `Conversation.dict()` has zero callers; not a serialization-compat surface. (dead-code)
- `TestTemplateRegistry.test_unregistered_template_not_found` — dict-membership tautology. (tautology)
- `TestTemplateRegistry.test_register_and_lookup` — dict-insert tautology; integrity already guarded by the duplicate-raises case. (strict-subset)
- `TestGenerateEmbeddingConvs.test_with_image` — strict subset of the image-and-video combination case. (strict-subset)
- `TestGenerateEmbeddingConvs.test_with_video` — same. (strict-subset)
- `TestGenerateEmbeddingConvs.test_multiple_items` — `zip`-loop length tautology. (tautology)
- `TestGetFullMultimodalTextPrompt.test_adds_missing_image_tokens` — strict subset of the exact-placement case. (strict-subset)
- `TestGetFullMultimodalTextPrompt.test_zero_count_with_no_tokens` — same identity property as another kept case. (strict-subset)
- `TestGetFullMultimodalTextPrompt.test_video_tokens` — function is token-string-agnostic; duplicates another case with a different literal. (strict-subset)
- `TestGenerateChatConv.test_string_messages_raises` — the guarded branch is unreachable via any validated request (`messages: List[...]`). (dead-code)

</details>

<details>
<summary><code>test/registered/unit/platforms/test_platform_interface.py</code> (21 methods + 1 class + 1 helper removed)</summary>

- `TestCudaDeviceMixin.test_default_get_device_total_memory_uses_cuda` — patches `torch.cuda.X` then asserts the method called `X`; restates a one-line passthrough. (mirror)
- `TestCudaDeviceMixin.test_default_get_current_memory_usage_uses_cuda` — same delegation-mirror pattern. (mirror)
- `TestCudaDeviceMixin.test_default_set_device_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_default_get_device_name_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_default_get_device_uuid_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_default_empty_cache_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_default_synchronize_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_default_get_available_memory_uses_cuda` — same. (mirror)
- `TestCudaDeviceMixin.test_cuda_platform_identity` — per-platform property echo, covered by the generic identity test. (strict-subset)
- `TestCudaDeviceMixin.test_default_distributed_backend_is_nccl` — echoes the hardcoded `return "nccl"`. (tautology)
- `TestCpuDeviceMixin.test_default_get_device_total_memory_uses_psutil` — delegation-mirror. (mirror)
- `TestCpuDeviceMixin.test_default_get_available_memory_uses_psutil` — delegation-mirror. (mirror)
- `TestCpuDeviceMixin.test_default_set_device_uses_torch_cpu` — delegation-mirror. (mirror)
- `TestCpuDeviceMixin.test_default_synchronize_uses_torch_cpu` — delegation-mirror. (mirror)
- `TestCpuDeviceMixin.test_get_device_uuid_returns_machine` — delegation-mirror. (mirror)
- `TestCpuDeviceMixin.test_cpu_platform_identity` — per-platform property echo, mirror of the CUDA one. (strict-subset)
- `TestCpuDeviceMixin.test_default_empty_cache_calls_gc_collect` — mirror of `gc.collect()`. (mirror)
- `TestCpuDeviceMixin.test_default_distributed_backend_is_gloo` — echoes the hardcoded override. (tautology)
- `TestCpuDeviceMixin.test_get_device_capability_returns_none` — echoes `return None`. (tautology)
- `TestSRTPlatformOverrides` (whole class) — "subclass override returns the override" tests Python inheritance, not sglang code. (dead-code)
- `_StubPlatform` (helper) — served only the removed class; zero remaining references. (dead-code)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_hicache_nixl_storage.py</code> (4 methods + 1 helper removed)</summary>

- `TestNixlUnified.test_concurrent_getter_setter_file_zero_copy` — two daemon threads with `sleep(3.0)`, no deterministic interleaving. (stress)
- `TestNixlUnified.test_concurrent_getter_setter_file_non_zero_copy` — same probabilistic pattern. (stress)
- `TestNixlUnified.test_concurrent_getter_setter_obj_zero_copy` — same, and gated behind an env var CI never sets. (stress)
- `TestNixlUnified.test_concurrent_getter_setter_obj_non_zero_copy` — same. (stress)
- `_run_concurrent_stress` (helper) — served only the four removed stress tests; zero remaining call sites. (dead-code)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_radix_cache_unit.py</code> (11 methods removed)</summary>

- `TestRadixKey.test_init_basic` — constructor field-storage tautology, no boundary. (tautology)
- `TestRadixKey.test_init_with_extra_key` — same assertion kind as `test_init_basic` plus one extra field. (strict-subset)
- `TestRadixKey.test_len` — subsumed by the combined len/iter test. (strict-subset)
- `TestRadixKey.test_iter` — same. (strict-subset)
- `TestRadixKey.test_repr` — mirror of `__repr__`'s string concatenation. (mirror)
- `TestRadixKey.test_repr_long_token_ids` — cosmetic truncation boundary, near-zero guard value. (tautology)
- `TestTreeNode.test_counter_increment` — already asserted by the init-with-id test. (strict-subset)
- `TestTreeNode.test_lt_comparison` — mirror of `__lt__` comparing timestamps. (mirror)
- `TestRadixCache.test_pretty_print_basic` — only verifies "doesn't crash", no assertions. (tautology)
- `TestRadixCache.test_all_values_flatten` — tautology on a debug helper (flatten returns what was inserted). (tautology)
- `TestRadixCache.test_available_and_evictable_str` — only calls `print`, no assertions at all. (tautology)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_unified_radix_cache_unittest.py</code> (18 methods removed)</summary>

- `test_evict_basic` — happy-path evict, covered by the multi-leaf case plus a precise-accounting case. (strict-subset)
- `test_evict_until_empty` — every assertion covered individually by three other kept cases. (strict-subset)
- `test_node_split_at_boundary` — same scenario as another kept case with different arbitrary token lengths. (strict-subset)
- `test_multi_branch_tree` — weaker assertions than a kept case; the third branch gates no new code path. (strict-subset)
- `test_paged_child_key_is_tuple` — return-type tautology; any paged insert test fails first if this breaks. (tautology)
- `test_mamba_evict_result_accounting` — assertions identical to a kept case, only sequence length differs. (strict-subset)
- `test_mamba_internal_tombstone_evict` — subset of a kept case; its extra claim is a comment, not an assertion. (strict-subset)
- `test_swa_insert_and_match` — covered by a kept case running on the same config with stronger assertions. (strict-subset)
- `test_swa_evict_cascades` — weaker form of a kept case that asserts exact zero eviction. (strict-subset)
- `test_swa_evict_cascades_mamba` — sole assertion is `>= 0`, which can never fail. (tautology)
- `test_swa_evict_full_leaf_cascades_all` — subset of a kept case asserting exact all-component zeroing. (strict-subset)
- `test_swa_lock_protects_from_eviction` — duplicate of a kept lock-ref case that also verifies unlock. (strict-subset)
- `test_evict_locked_subtree_skipped` — same failure mode as a kept case, missing the unlock dimension. (strict-subset)
- `test_hicache_node_states` — subset of a kept case asserting the same state transition. (strict-subset)
- `test_hicache_d_leaf_h_leaf_mutual_exclusion` — identical final assertion as a kept case on a narrower scenario. (strict-subset)
- `test_hicache_swa_host_independent_of_full` — asserts an attribute it never touches; can't catch a shared-pool regression. (tautology)
- `test_swa_lru_cushion_bound_is_sliding_window_plus_page_size` — same fixture/action as a kept case; its named "bound" assertion pins a fixture property, not code behavior. (tautology)
- `UnifiedLRUListBoundedRefreshTest.test_bounded_refresh_stops_after_accumulated_meets_window` — the ordering used cannot distinguish correct early-stop from over-walking. (tautology)

</details>

<details>
<summary><code>test/registered/unit/server_args/test_server_args.py</code> (14 methods removed)</summary>

- `TestPrepareServerArgs.test_prepare_server_args` — pure argparse pass-through, no custom parsing logic. (tautology)
- `TestLoadBalanceMethod.test_pd_decode_radix_cache_allows_mooncake` — the per-backend whitelist was removed; duplicate of the alias-normalization case. (strict-subset)
- `TestLoadBalanceMethod.test_pd_decode_radix_cache_allows_ascend` — same; no ascend-specific code path remains. (strict-subset)
- `TestContextParallelServerArgs.test_canonical_prefill_cp_cli_sets_unified_fields` — pure pass-through, subsumed by the case that also validates. (strict-subset)
- `TestPortArgs.test_init_new_with_nccl_port_none` — mock-echo mirror; the behavioral fact is already asserted by the standard-case test. (mirror)
- `TestSSLArgs.test_default_ssl_fields_are_none` — dataclass default re-statement. (tautology)
- `TestSSLArgs.test_ssl_both_keyfile_and_certfile_accepted` — subsumed by two stronger cases. (strict-subset)
- `TestSSLArgs.test_ssl_cli_args_parsed` — pure pass-through, guarded generically elsewhere. (strict-subset)
- `TestSSLArgs.test_enable_ssl_refresh_default_false` — default-declaration tautology. (tautology)
- `TestSSLArgs.test_enable_ssl_refresh_cli_flag` — store_true pass-through; accept-branch kept elsewhere. (strict-subset)
- `TestNgramExternalSamArgs.test_prepare_server_args_parses_external_sam_args` — pure pass-through, no custom parsing. (tautology)
- `TestDecoupledSpecArgs.test_decoupled_spec_role_defaults_to_null` — default re-statement; behavior already covered in `TestPortArgs`. (strict-subset)
- `TestGrpcServerArgs.test_defaults_native_grpc_off_legacy_off` — subsumed by a case with a more adversarial input. (strict-subset)
- `TestTwoBatchOverlapBackend.test_tbo_disabled_is_noop` — asserts the guard's first-line early-return; a misfire would break every default launch and isn't a plausible silent regression. (tautology)

</details>

<details>
<summary><code>test/registered/unit/spec/test_ngram_corpus.py</code> (13 methods + 4 classes removed)</summary>

- `TestNgramCorpusBFS.test_output_shapes` — the golden-output case already asserts full exact arrays; any shape change turns it red first. (strict-subset)
- `TestNgramCorpusProb.test_output_shapes` — same as above. (strict-subset)
- `TestNgramCorpusReset` (whole class) — strict subset of the reset-then-reinsert test's "old data gone" assertion. (strict-subset)
- `TestNgramCorpusSqueeze.test_small_capacity_does_not_crash` — no-crash-only; real eviction behavior is asserted elsewhere. (tautology)
- `TestMaskValidity` (whole class) — identical seed/query/config as the golden mask tests; any diff that breaks it breaks those first. (strict-subset)
- `TestDraftBudgetSaturation` (whole class) — `len == 8` is contract-trivial, implicitly covered by the golden case. (tautology)
- `TestTruncate` (whole class) — slices the numpy result itself and asserts the slice equals itself; no truncation logic is exercised at all. (mirror)
- `TestNgramCorpusExternalSam.test_external_sam_only_chain` — identical assertions to another kept case. (strict-subset)
- `TestNgramCorpusExternalSam.test_shared_prefix_keeps_both_branches` — same scenario as another kept case; the delta is not an exact-fit boundary. (strict-subset)
- `TestNgramCorpusMultiSam.test_remove` — post-remove bookkeeping already asserted by two other kept cases. (strict-subset)
- `TestNgramCorpusMultiSam.test_make_corpus_with_documents` — tests the test file's own helper function. (tautology)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_multi_ended_allocator.py</code> (11 methods removed)</summary>

- `TestMultiEndedAllocator.test_translate_kv_loc_without_out_returns_fresh_tensor` — "returns a fresh tensor" is a torch-indexing implementation detail; the value assertion is retained transitively elsewhere. (tautology)
- `TestUnifiedSWATokenToKVPoolAllocator.test_swa_joint_byte_budget_pre_check` — page_size==1 is a strict subset of the paged variant with the same formula. (strict-subset)
- `TestPagedMultiEndedAllocator.test_paged_translate_kv_loc_token_round_trip` — misnamed (never calls the target function); asserts a non-contract "physical page contiguity". (mirror)
- `TestPagedMultiEndedAllocator.test_paged_allocated_count_returns_tokens` — strict subset of a kept test asserting the same value plus more. (strict-subset)
- `TestLazyCompaction.test_lazy_state_initialized` — constructor-field mirror. (tautology)
- `TestLazyCompaction.test_lazy_alloc_increments_live_page_count` — implicitly covered by a kept boundary-shortcut test. (strict-subset)
- `TestLazyCompaction.test_lazy_free_non_boundary_pushes_hole` — strict subset of the kept inward-walk test. (strict-subset)
- `TestLazyCompaction.test_lazy_hole_set_directional_pop` — the docstring's described behavior no longer exists (now FIFO); remaining assertion covered elsewhere. (dead-code)
- `TestLazyCompaction.test_lazy_pending_reuse_urgent_wait` — CPU-only CI, and `except Exception: skipTest` converts a real bug into a silent skip. (dead-code)
- `TestLazyCompaction.test_lazy_flush_opportunistic_hook` — implicitly covered by a kept churn test that calls the same hook ~1500 times. (strict-subset)
- `TestO3FusedAllocBind.test_helper_exists_and_returns_tensor` — existence/happy-path tautology; value pinned by the kept fast-path test. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/entrypoints/openai/test_serving_chat.py</code> (6 methods removed)</summary>

- `ServingChatTestCase.test_kimi_tool_call_keeps_explicit_reasoning` — same assertion as the default-reasoning case. (strict-subset)
- `ServingChatTestCase.test_kimi_k2_non_streaming_tool_call_id_format` — strict subset of the with-history variant. (strict-subset)
- `ServingChatTestCase.test_kimi_k2_streaming_tool_call_id_format` — strict subset of the streaming with-history variant. (strict-subset)
- `ServingChatTestCase.test_latest_reminder_role_accepted` — happy-path schema acceptance, covered by the end-to-end dsv4 encoding test. (strict-subset)
- `ServingChatTestCase.test_extract_routed_dp_rank_from_header_with_header` — strict subset of the header-overrides-body test. (strict-subset)
- `TestNormalizeToolContent.test_openai_text_parts_flattened` — strict subset of the multiple-text-parts-joined test. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/test_model_overrides.py</code> (6 methods removed)</summary>

- `TestModelOverridableWhitelist.test_arg_defaults_to_not_overridable` — constructor default re-statement; flipping it fails other tests first. (tautology)
- `TestModelOverridableWhitelist.test_non_dataclass_yields_empty_whitelist` — the guard clause exists only for mock fixtures; its removal already fails those tests loudly. (dead-code)
- `TestPublishInstallsSlot.test_empty_stash_publish_runs_gate_as_noop` — the publish path has no gate logic; "install then read back the same object" is a tautology. (tautology)
- `TestGoldenModelOverrides.test_pixtral_forces_bfloat16` — same const-entry mechanism as another kept case, fewer assertions. (strict-subset)
- `TestGoldenModelOverrides.test_declaration_overlay_mechanics` — duplicates another kept case's declare/overlay assertions. (strict-subset)
- `TestGoldenModelOverrides.test_page_size_leaf_materializes_end_state` — the materialization loop is field-agnostic; a second field can't fail independently. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/entrypoints/anthropic/test_serving.py</code> (3 methods + 1 dead fixture removed)</summary>

- `TestAnthropicServing.test_request_thinking_enabled_invokes_apply_reasoning_enabled` — strict subset of the case that also pins the unenforced-budget warning. (strict-subset)
- `TestAnthropicServing.test_request_task_budget_with_remaining_is_accepted` — `AnthropicTaskBudget.remaining` is a declared field that serving code never reads downstream; it is a dead no-op with no guard value. (dead-code)
- `TestAnthropicServing.test_server_tool_only_with_tool_choice_auto_is_allowed` — identical request to a kept case with strictly weaker assertions. (strict-subset)
- `QWEN_SYSTEM_FIRST_TEMPLATE` (dead fixture) — referenced nowhere else in the file. (dead-code)

</details>

<details>
<summary><code>test/registered/unit/hardware_backend/mlx/test_attention_patching.py</code> (2 methods removed)</summary>

- `TestMlxAttentionPatching.test_projection_only_mixer_is_not_attention` — single assertion subsumed by a kept case driving the same predicate through the real patching path. (strict-subset)
- `TestMlxAuxiliaryStateRunnerCache.test_auxiliary_state_component_keeps_new_live_slot_owned_by_radix` — same config/assertions as a kept case that additionally covers stale-track-slot cleanup. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_hicache_staged_write_back_dispatch.py</code> (2 methods removed)</summary>

- `test_hybrid_write_moves_indices_without_page_first_layout` — falsifies a state combination no real pool group can ever produce. (dead-code)
- `test_cache_controller_moves_indices_without_page_first_layout` — same; single host pools can never reach `layer_first + write_back_jit=True`. (dead-code)

</details>

<details>
<summary><code>test/registered/unit/model_executor/test_cuda_graph_buffer_registry.py</code> (8 methods removed)</summary>

- `TestGraphSlot.test_slice_for_before_buffer_alloc_raises` — only pins the exception type; without the guard it still fails loudly (TypeError), no silent-failure mode. (dead-code)
- `TestRegistryRegister.test_register_fill_sentinel_init` — sentinel init isn't load-bearing; the tail is reset on every `fill_from` call, asserted elsewhere. (dead-code)
- `TestRegistryRegister.test_cpu_device_override` — vacuous on a CPU-only registry; override is indistinguishable from the default. (tautology)
- `TestFillFromAndExtract.test_basic_fill_no_padding` — strict subset of the padding case, which covers the same copy path plus more. (strict-subset)
- `TestMissingAndOptionalSlots.test_missing_fb_attr_is_skipped` — the skip branch is exercised by a kept case that also asserts the extract-carry dimension. (strict-subset)
- `TestSourceFnSlots.test_side_input_source_via_fill_context` — strict subset of a kept case driving the identical path through the real factory registration. (strict-subset)
- `TestPoolBackedAlloc.test_same_size_shares_one_allocation` — subsumed by the order-independence test asserting the same sharing in both directions. (strict-subset)
- `TestPoolBackedAlloc.test_different_sizes_do_not_share` — subsumed by the same order-independence test. (strict-subset)

</details>

<details>
<summary><code>test/registered/unit/mem_cache/test_unified_radix_cache_bench.py</code> (3 of 6 CI config entries removed)</summary>

- `FULL_SWA_ps1` config — component/page-size combination redundant with the two other kept configs; the file's pytest-visible assertions are only `num_ops>0`/`ops_per_sec>0` tautologies, with real coverage coming from an embedded `sanity_check()` whose targeted equivalents already live in the companion unit-test file. (tautology + strict-subset)
- `FULL_ps16` config — page_size only has a structural branch at 1 vs >1; 16 duplicates the kept 128 config on the same branch. (strict-subset)
- `FULL_SWA_ps16` config — same page-size duplication on the SWA allocator path. (strict-subset)

</details>






























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29054483691](https://github.com/sgl-project/sglang/actions/runs/29054483691)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29054483567](https://github.com/sgl-project/sglang/actions/runs/29054483567)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
