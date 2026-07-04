---
source_id: sglang-github-closed-issues-prs
title: '[spec] Stop draft workers from clobbering the global server_args'
canonical_url: https://github.com/sgl-project/sglang/pull/29355
captured_at: '2026-07-04T02:13:49.140460+00:00'
content_hash: 45cb802d86248522552fc74c66165dece76da2e883e1c6adee77820fa1aaaea7
---
# [spec] Stop draft workers from clobbering the global server_args

URL: https://github.com/sgl-project/sglang/pull/29355
State: closed
Labels: 
Closed at: 2026-07-03T02:57:18Z
Merged at: 

## Motivation

`ModelRunner.__init__` writes a process-global `server_args`
(`set_global_server_args_for_scheduler`), read both during construction
(`initialize()` → `torchao_config`, `init_*_capturer()` → `enable_return_*`) and
at runtime (`use_mla_backend` via `cp_utils`, `draft_utils`, …). A **draft worker**
for speculative decoding runs in the same process as its target and clobbers that
global with its own `ServerArgs`.

EAGLE gets away with this because it passes the *same* `ServerArgs` object to its
draft worker. DFLASH passes a deepcopied/mutated copy (different attention backend,
context length), so it wrapped draft-worker construction in a save/restore dance:

```python
saved_server_args = get_global_server_args()
self._draft_worker = TpModelWorker(server_args=draft_server_args, ...)
set_global_server_args_for_scheduler(saved_server_args)
```

## Changes

- **`model_runner.py`**: centralize the dance into `ModelRunner`. A draft runner
  installs its own args for the duration of construction (so every in-construction
  read still sees its own config) via `init_global_server_args`, then restores the
  target's args at the end of `__init__` via `maybe_restore_global_server_args`.
  No-op for a target runner.
- **`dflash_worker_v2.py`**: drop the now-redundant external save/restore.
- **`draft_utils.py`**: `DraftBackendFactory` selected the draft's attention backend
  via `get_global_server_args().use_mla_backend`; read
  `self.draft_model_runner.use_mla_backend` directly instead — a per-runner property
  belongs to the runner, not a process global.

## Net effect

Behavior-preserving relative to `main` for both EAGLE and DFLASH — the global
state seen during construction and at runtime is unchanged; DFLASH's save/restore
is simply moved out of the spec worker and into `ModelRunner`, so any future draft
worker built from a mutated `ServerArgs` is handled automatically. No change for
non-speculative runs.

## Checklist

- [x] Pre-commit hooks pass (isort/ruff/black/codespell).
- [ ] Spec-v2 e2e (EAGLE + DFLASH) on GPU.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28210743272](https://github.com/sgl-project/sglang/actions/runs/28210743272)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28210743217](https://github.com/sgl-project/sglang/actions/runs/28210743217)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
