---
source_id: sglang-github-closed-issues-prs
title: Gate Rust extension builds
canonical_url: https://github.com/sgl-project/sglang/pull/30927
captured_at: '2026-07-12T23:38:53.055615+00:00'
content_hash: 11633a6fcdbc70636b9c5f3062bcecbe4d7b46aa0399d2810b99d085bc33c799
---
# Gate Rust extension builds

URL: https://github.com/sgl-project/sglang/pull/30927
State: closed
Labels: dependencies, npu, run-ci
Closed at: 2026-07-12T12:44:59Z
Merged at: 2026-07-12T12:44:59Z

## Summary
- add `SGLANG_BUILD_RUST_EXTS` as a build-time selector for setuptools-rust extensions
- keep the default behavior as building all declared Rust extensions
- allow `SGLANG_BUILD_RUST_EXTS=none` to skip Rust extension builds, with explicit extension IDs such as `grpc` for selective builds
- exclude stale native gRPC extension binaries from package data when the extension is skipped

We use an env var renamed from `SGLANG_RUST_EXTS_ALLOWLIST` to the clearer `SGLANG_BUILD_RUST_EXTS`. Co-authored-by: Jialin Ouyang <jialino@meta.com>.

## Test
- `python3 -m py_compile python/setup.py python/sglang/srt/environ.py`
- `SGLANG_BUILD_RUST_EXTS=none CARGO=/bin/false RUSTC=/bin/false uv sync --frozen --reinstall-package sglang --no-install-project`



















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29190990309](https://github.com/sgl-project/sglang/actions/runs/29190990309)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29190990187](https://github.com/sgl-project/sglang/actions/runs/29190990187)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
