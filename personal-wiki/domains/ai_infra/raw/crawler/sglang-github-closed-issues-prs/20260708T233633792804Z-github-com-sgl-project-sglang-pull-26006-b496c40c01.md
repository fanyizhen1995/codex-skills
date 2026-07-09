---
source_id: sglang-github-closed-issues-prs
title: '[server] add --uds flag for Unix Domain Socket binding (#14258)'
canonical_url: https://github.com/sgl-project/sglang/pull/26006
captured_at: '2026-07-08T23:36:33.792804+00:00'
content_hash: b496c40c0179c547a2286f488fe5e828a223385dd959b9f6fd310b5653f3267e
---
# [server] add --uds flag for Unix Domain Socket binding (#14258)

URL: https://github.com/sgl-project/sglang/pull/26006
State: closed
Labels: documentation, run-ci
Closed at: 2026-07-08T10:01:36Z
Merged at: 

## Summary

Adds a new `--uds <PATH>` flag to `sglang serve` (and `python -m sglang.launch_server`) that binds the public HTTP request-intake listener to a Unix domain socket instead of a TCP host/port. Unblocks integration with orchestrators like [Docker Model Runner](https://github.com/docker/model-runner) that proxy inference requests over UDS.

- **Scope:** public HTTP only — both the uvicorn path and the Granian `--enable-http2` path. All internal SGLang services (gRPC bootstrap, ZMQ, NCCL, disaggregation, DP controller) continue to use TCP on `127.0.0.1` regardless of `--uds`.
- **Validation:** `--uds` is mutually exclusive with non-default `--host` / `--port`, refused on Windows, validated in `ServerArgs.__post_init__`.
- **Safety:** stale UDS files at the requested path are auto-unlinked before bind; non-socket files and live sockets are refused with clear errors. Granian's own stale-socket cleanup is left to handle the `--enable-http2` path.

Addresses sgl-project/sglang#14258 (issue is currently auto-closed for inactivity; please reopen and link this PR).

## Example

```bash
sglang serve --model-path Qwen/Qwen2.5-7B-Instruct --uds /run/sglang/sglang.sock
curl --unix-socket /run/sglang/sglang.sock http://localhost/v1/models
```

## Changes

| File | What |
|---|---|
| `python/sglang/srt/server_args.py` | New `uds: Optional[str]` field, `--uds` argparse entry, `__post_init__` validation. `from_cli_args` falls back to dataclass defaults for fields without argparse entries (handles `default` and `default_factory`). |
| `python/sglang/srt/entrypoints/http_server.py` | Three private helpers — `_uvicorn_bind_kwargs`, `_format_listen_addr`, `_prepare_uds_path`. Three uvicorn call sites and the Granian call site rewired. Startup log prints `unix:<path>` when UDS is active. |
| `test/registered/unit/server_args/test_server_args_uds.py` | 6 unit tests for the field + validation + CLI parsing. CPU CI (`base-a-test-cpu`). |
| `test/registered/unit/utils/test_http_server_uds_helpers.py` | 9 unit tests for the three private helpers, including a real-socket liveness check and a `TimeoutError` simulation. CPU CI. |
| `test/registered/openai_server/basic/test_uds_server.py` | Integration test: launches a real `sglang serve --uds` against the default small test model, hits `/v1/models` and `/v1/chat/completions` over `AF_UNIX` via a custom `http.client.HTTPConnection`. CUDA `base-b 1-gpu-small` + AMD `stage-b-test-1-gpu-small-amd`. Skipped on Windows. |
| `docs_new/docs/advanced_features/server_arguments.mdx` | New row documenting `--uds`. |

## Non-goals (deferred)

- `--uds-permissions` flag (default umask only).
- TCP + UDS dual-bind.
- UDS for auxiliary servers (`engine_info_bootstrap_server`, `mini_3fs_metadata_server`, gRPC HTTP sidecar).
- UDS in `--grpc-mode`.
- Windows support.

## Test plan

- [x] `test/registered/unit/server_args/test_server_args_uds.py` — 6/6 pass locally
- [x] `test/registered/unit/utils/test_http_server_uds_helpers.py` — 9/9 pass locally
- [x] No regression in `test/registered/unit/server_args/test_server_args.py` — 51/51 pass locally
- [ ] `test/registered/openai_server/basic/test_uds_server.py` — runs on the registered CUDA + AMD CI suites (requires GPU)
- [ ] Manual verification: `sglang serve --model-path <m> --uds /tmp/s.sock` then `curl --unix-socket /tmp/s.sock http://localhost/v1/models`
- [ ] Manual verification with `--enable-http2 --uds /tmp/s.sock` and `curl --http2-prior-knowledge --unix-socket /tmp/s.sock ...`

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































































































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28709094411](https://github.com/sgl-project/sglang/actions/runs/28709094411)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28709094314](https://github.com/sgl-project/sglang/actions/runs/28709094314)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
