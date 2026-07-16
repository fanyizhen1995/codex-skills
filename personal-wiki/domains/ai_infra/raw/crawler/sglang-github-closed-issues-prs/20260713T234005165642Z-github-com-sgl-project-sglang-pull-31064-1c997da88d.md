---
source_id: sglang-github-closed-issues-prs
title: 'fix: include OpenSSL headers in runtime image'
canonical_url: https://github.com/sgl-project/sglang/pull/31064
captured_at: '2026-07-13T23:40:05.165642+00:00'
content_hash: 1c997da88d7d6e914b136605e4cfc8f565b16b37e606c7890226a0e4123e3138
---
# fix: include OpenSSL headers in runtime image

URL: https://github.com/sgl-project/sglang/pull/31064
State: closed
Labels: 
Closed at: 2026-07-13T20:09:42Z
Merged at: 2026-07-13T20:09:42Z

<!-- codex-pr-description:start -->
The SGLang runtime image now installs `libssl-dev` instead of only `libssl3`. This supplies the OpenSSL headers and linker metadata required when the HiCache native hash extension JIT-compiles at runtime.

### How This Was Implemented

- Replace the runtime-stage `libssl3` package with `libssl-dev`.
- Rely on `libssl-dev`'s exact-version dependency to retain the matching `libssl3` runtime library.
- Leave the builder and unrelated runtime dependencies unchanged.

<details>
<summary>Walkthrough</summary>

#### Mental model

The HiCache native hash loader compiles `hash_binding.cpp` with `torch.utils.cpp_extension.load`. That source includes `openssl/sha.h` and links `-lcrypto`, so the production image needs both the runtime library and its development files.

#### Boundaries and limitations

This only changes the CUDA production runtime image package set. It does not change hashing behavior or precompile the extension.

</details>

### Validation

- `pre-commit run --files docker/Dockerfile`
- `git diff --check`
- Full runtime image build not run locally; it is covered by the repository image CI.
<!-- codex-pr-description:end -->











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29279629183](https://github.com/sgl-project/sglang/actions/runs/29279629183)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29279628771](https://github.com/sgl-project/sglang/actions/runs/29279628771)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
