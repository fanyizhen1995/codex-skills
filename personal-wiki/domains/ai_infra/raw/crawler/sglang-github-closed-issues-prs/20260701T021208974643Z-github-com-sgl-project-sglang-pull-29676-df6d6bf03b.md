---
source_id: sglang-github-closed-issues-prs
title: '[Docs] Add --prerelease=allow so uv installs the latest sglang'
canonical_url: https://github.com/sgl-project/sglang/pull/29676
captured_at: '2026-07-01T02:12:08.974643+00:00'
content_hash: df6d6bf03bd6746d294f62618b10818b0bbd6ed42db168628fd816f8bcec64c3
---
# [Docs] Add --prerelease=allow so uv installs the latest sglang

URL: https://github.com/sgl-project/sglang/pull/29676
State: closed
Labels: documentation
Closed at: 2026-06-29T21:13:35Z
Merged at: 2026-06-29T21:13:35Z

## Motivation

The recommended `uv pip install sglang` in the get-started docs silently installs **sglang 0.5.9** instead of the latest release.

Root cause:
- sglang **0.5.10+** depend on `flash-attn-4` (`>=4.0.0b4` / `>=4.0.0b9`).
- On PyPI, `flash-attn-4` only publishes **pre-releases** (`4.0.0b3` … `4.0.0b19`); the only non-pre-release, `0.0.1`, is below the required range, so nothing stable satisfies the constraint.
- **uv refuses pre-releases by default**, so it backtracks to **0.5.9** — the last release that does not depend on `flash-attn-4`.
- `pip` reaches the latest because it accepts the only-available pre-release. That is why `pip install sglang` works but `uv pip install sglang` quietly installs an old version.

## Modifications

Add `--prerelease=allow` to the `uv pip install sglang` commands so the recommended uv path resolves to the latest sglang, matching pip. (Only `allow` works — `if-necessary` / `explicit` do not, because `flash-attn-4` is a transitive dependency.)

- `docs_new/docs/get-started/install.mdx` — Method 1 default block + CUDA 12 block
- `docs_new/docs/get-started/quickstart.mdx` — Installation (Pip / uv) tab

Verification (native resolve, linux / cp311):

| command | resolves to |
| --- | --- |
| `uv pip install sglang` | `sglang==0.5.9` |
| `uv pip install --prerelease=allow sglang` | `sglang==0.5.13.post1` (+ `flash-attn-4==4.0.0b19`, `sglang-kernel==0.4.3`, `torch==2.11.0`) |

## Accuracy Tests

N/A — documentation only.

## Speed Tests and Profiling

N/A — documentation only.

## Checklist

- [x] Format your code according to the Format code with pre-commit.
- [ ] Add unit tests — N/A (documentation only).
- [x] Update documentation.
- [ ] Provide accuracy and speed benchmark results — N/A (documentation only).
- [x] Follow the SGLang code style guidance.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28402765080](https://github.com/sgl-project/sglang/actions/runs/28402765080)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28402764914](https://github.com/sgl-project/sglang/actions/runs/28402764914)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
