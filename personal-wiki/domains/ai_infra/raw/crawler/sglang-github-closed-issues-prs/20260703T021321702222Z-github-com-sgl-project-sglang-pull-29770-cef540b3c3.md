---
source_id: sglang-github-closed-issues-prs
title: 'chore: cleanup garbage code'
canonical_url: https://github.com/sgl-project/sglang/pull/29770
captured_at: '2026-07-03T02:13:21.702222+00:00'
content_hash: cef540b3c3bfdef172c68827472e7d81c4f225b7ba75b91466c6563d81761d41
---
# chore: cleanup garbage code

URL: https://github.com/sgl-project/sglang/pull/29770
State: closed
Labels: documentation, quant, amd, dependencies, Multi-modal, sgl-kernel, npu, run-ci, diffusion, model-gateway, mthreads, run-ci-extra
Closed at: 2026-07-02T08:14:01Z
Merged at: 2026-07-02T08:14:01Z

## Summary
- Remove hard-disabled/dead cleanup paths in DSA index buffer writes, EPLB detail accumulation, Hunyuan forward state plumbing, multimodal hashing, playground router code, and small benchmark/test helpers.
- Replace low-signal AI-ish wording such as `smoke`/`placeholder`/`dead code` in comments, docstrings, logs, and docs where it is not an API/file/test selector.
- Apply focused unused-import/unused-local cleanup from ruff on touched files, and make the AMD dummy-grok config copy explicit.

## Notes
- I intentionally left `smoke` where it is a CLI choice, file/test name, or registered selector, and left `bitwise` where it describes actual bit operations or exact equality.
- I also left the two CPU C++ `#if 0` alternative implementations untouched because those are algorithm references in kernel code, not obvious low-value debris.

## Validation
- `python3 -m ruff check --select F401,F841,F821,UP037 $(git diff --name-only -- '*.py')`
- `python3 -m py_compile $(git diff --name-only -- '*.py')`
- `bash -n scripts/ci/amd/amd_ci_install_dependency.sh scripts/ci/slurm/launch_mi355x.sh`
- `git diff --check`
- `cargo fmt --check --manifest-path sgl-model-gateway/Cargo.toml` (passes; rustfmt prints existing nightly-only config warnings)
- SGLang review-corpus sweep for cleanup/dead-code/tests/CI/model/Rust touched areas























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28572717194](https://github.com/sgl-project/sglang/actions/runs/28572717194)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28572716962](https://github.com/sgl-project/sglang/actions/runs/28572716962)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
