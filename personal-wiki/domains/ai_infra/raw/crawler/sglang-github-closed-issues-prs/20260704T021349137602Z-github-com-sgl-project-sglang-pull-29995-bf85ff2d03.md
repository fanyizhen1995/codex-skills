---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Remove the ServerArgs clone + global save/restore hack from DFlashWorkerV2'
canonical_url: https://github.com/sgl-project/sglang/pull/29995
captured_at: '2026-07-04T02:13:49.137602+00:00'
content_hash: bf85ff2d035bef2aafb9f30a0c9d2367d02f5c1fcabdbce285182402fa8a842d
---
# [Spec] Remove the ServerArgs clone + global save/restore hack from DFlashWorkerV2

URL: https://github.com/sgl-project/sglang/pull/29995
State: closed
Labels: speculative-decoding, run-ci, bypass-fastfail
Closed at: 2026-07-03T06:37:05Z
Merged at: 2026-07-03T06:37:05Z

## Motivation

`DFlashWorkerV2.__init__` deep-copied `ServerArgs`, mutated the clone (draft attention backend, `skip_tokenizer_init`, `context_length`), and built its draft `TpModelWorker` from it. Since `ModelRunner.__init__` publishes its `server_args` as the scheduler-process global, the clone clobbered the global args, forcing a hacky save/restore around the constructor:

```python
saved_server_args = get_global_server_args()
self._draft_worker = TpModelWorker(server_args=draft_server_args, ...)
set_global_server_args_for_scheduler(saved_server_args)
```

Every other spec worker (EAGLE etc.) passes the scheduler's *same* `ServerArgs` object, making the re-publication a no-op by identity. This PR makes DFLASH follow that pattern by routing each clone-mutation through a proper per-draft mechanism.

## Modifications

- **Draft attention backend**: resolution/fallback moved to `_resolve_dflash_draft_attention_backend` in `arg_groups/speculative_hook.py` (ServerArgs normalization phase), writing the final value into `speculative_draft_attention_backend`. `ModelRunner._get_attention_backend` already applies that field for draft workers (single backend for all draft modes), which is what the old prefill/decode-clearing achieved. A FIXME notes that even this field write should eventually become an explicit parameter.
- **Context length**: new explicit `context_length` parameter on `TpModelWorker` → `ModelConfig.from_server_args` — a target-derived override for draft workers, same category as the existing `memory_pool_config` parameter. DFlash passes the target's `context_len`; `ModelConfig._derive_context_length` already expects this ("Target model's context_length" wording). Follow-up: `eagle_worker_v2.py` / `standalone_worker_v2.py` / `frozen_kv_mtp_worker_v2.py` / `multi_layer_eagle_worker_v2.py` still mutate the shared `server_args.context_length` in place and could migrate to this parameter.
- **Tokenizer**: `TpModelWorker` now skips tokenizer init for draft workers. A draft worker's tokenizer was always a byte-identical duplicate of the target's (`tokenizer_path` points at the target model); DFLASH resolves its mask token via the target tokenizer. Side effect: STANDALONE's draft-vs-target `get_vocab()` comparison silently skips, but it was vacuous (it compared the same tokenizer loaded twice).
- **`ModelRunner`**: the global publication (and the `use_mla_backend` write into it) is gated on `not is_draft_worker`, so a draft init can never clobber target-derived global state (matters for an MHA draft on an MLA target).
- **`DFlashWorkerV2.__init__`**: the deepcopy, backend normalization, and save/restore are deleted; the draft worker is constructed from the shared `server_args` plus `context_length=target.context_len`.

## Accuracy Tests

DFLASH e2e on H200 (`meta-llama/Llama-3.1-8B-Instruct` + `z-lab/LLaMA3.1-8B-Instruct-DFlash-UltraChat`, `SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1` — required on main too, since the draft config derives 40960 < 131072):

```
few_shot_gsm8k --num-questions 200: Accuracy: 0.780  Invalid: 0.000
Decode: accept len: ~3.0, accept rate: ~0.22, cuda graph: True
```

Startup logs confirm behavior parity: draft backend `fa3` applied via the `is_draft_worker` override, draft `max_position_embeddings` overridden to 131072, mask token resolved (128002) through the target tokenizer.

An EAGLE3 smoke test on the same box hits two startup failures that reproduce byte-identically on unmodified `main` (verified via a `main` git worktree): the draft context-length `ValueError` without the env var, and a flashinfer cute-dsl rmsnorm dtype error during cuda-graph capture — both pre-existing, unrelated to this PR; the EAGLE draft-worker construction path through the modified code completes identically to main.

🤖 Generated with [Claude Code](https://claude.com/claude-code)























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28633766557](https://github.com/sgl-project/sglang/actions/runs/28633766557)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28633766381](https://github.com/sgl-project/sglang/actions/runs/28633766381)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
