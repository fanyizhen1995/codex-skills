---
source_id: sglang-github-closed-issues-prs
title: '[gRPC] Native server: launcher + HTTP + server args wiring (3/4)'
canonical_url: https://github.com/sgl-project/sglang/pull/23508
captured_at: '2026-07-07T23:35:30.901846+00:00'
content_hash: 5d664d1a08fa0d5dc5072da6ee7a35f4ac3e8bdffa531136de18b9f3d788a70b
---
# [gRPC] Native server: launcher + HTTP + server args wiring (3/4)

URL: https://github.com/sgl-project/sglang/pull/23508
State: closed
Labels: dependencies, run-ci
Closed at: 2026-07-07T21:57:26Z
Merged at: 2026-07-07T21:57:26Z

## Summary
Wires the native gRPC server into the Python entrypoints and server args.

- `server_args.py`: adds `--enable-grpc`, `--grpc-port`, `--grpc-worker-threads`, `--grpc-max-prefill-tokens`, and validates against legacy `--grpc-mode` / `--smg-grpc` flags
- `launch_server.py`: dispatches to `grpc_bridge` when `--enable-grpc` is set
- `http_server.py`: optional `grpc_bridge` wiring for shared routes

## Stack
Part of the phase-1 split of the original PR #22907. Review order:
1. #23506 — Rust crate
2. #23507 — Python bridge entrypoint
3. **(this)** `server-integration`
4. `tests` — integration tests

Base: #23507

## Test plan
- [ ] \`python -m sglang.launch_server --enable-grpc --grpc-port 30001 ...\` starts the gRPC server
- [ ] Existing launches without \`--enable-grpc\` still behave identically (no regressions)
- [ ] \`--enable-grpc\` together with \`--grpc-mode\` / \`--smg-grpc\` / \`--use-ray\` / \`--encoder-only\` is rejected















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28839713327](https://github.com/sgl-project/sglang/actions/runs/28839713327)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28839713168](https://github.com/sgl-project/sglang/actions/runs/28839713168)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
