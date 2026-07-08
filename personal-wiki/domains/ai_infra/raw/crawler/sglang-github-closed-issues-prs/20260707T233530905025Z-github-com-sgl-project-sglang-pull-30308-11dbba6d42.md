---
source_id: sglang-github-closed-issues-prs
title: 'docs(install): add nightly install + docker tag guidance, and auto-bump version
  on release tag'
canonical_url: https://github.com/sgl-project/sglang/pull/30308
captured_at: '2026-07-07T23:35:30.905025+00:00'
content_hash: 11dbba6d4266063f919e901c50a527951b92d0f22be4b794cabf77772abf9a47
---
# docs(install): add nightly install + docker tag guidance, and auto-bump version on release tag

URL: https://github.com/sgl-project/sglang/pull/30308
State: closed
Labels: documentation
Closed at: 2026-07-07T19:10:06Z
Merged at: 2026-07-07T19:10:06Z

## Motivation

The `docs_new` install pages pin a release version in a few places — the `git clone -b vX.Y.Z …sglang.git` "install from source" line, and now a version-pinned `lmsysorg/sglang:vX.Y.Z` Docker example — that were only ever updated by hand and drifted out of date between releases. There was also no documented way to install **nightly** builds via pip/uv, and no note that the `latest`/`dev` Docker tags are **mutable**. This PR automates the version bump and fills those documentation gaps.

## Modifications

- **New workflow `.github/workflows/bot-bump-docs-version.yml`** — triggers on the same conditions as `release-docker.yml` (a pushed `v[0-9]+.*` tag, plus manual `workflow_dispatch`). It resolves the version, checks out `main`, runs the bump script, and opens a PR via the existing `scripts/release/commit_and_pr.sh` (using `GH_PAT_FOR_PULL_REQUEST`, matching the other `bot-bump-*` workflows). Because `main` is protected, it opens a PR rather than pushing directly.
- **New script `scripts/release/bump_docs_install_version.py`** — updates the pinned version in the install docs: the `git clone -b v<version> …sglang.git` line and the `lmsysorg/sglang:v<version>` Docker example, in both `docs_new/docs/get-started/install.mdx` and `docs_new/docs/hardware-platforms/amd_gpu.mdx`. Reuses `scripts/release/utils.py` for version validation/comparison, is idempotent, and intentionally leaves mutable tags (`latest`, `dev`, and suffixed variants like `-cu130`/`-runtime`) untouched.
- **`docs_new/docs/get-started/install.mdx`**:
  - *Method 1*: added a **Nightly builds** subsection (uv, CUDA 13 default + CUDA 12 variant) that installs from the SGLang nightly wheel index with `--prerelease=allow --index-strategy unsafe-best-match` so uv selects the nightly pre-release across PyPI and the wheel index.
  - *Method 3*: added a `<Note>` explaining that `latest`/`dev` are mutable tags and recommending pinning an immutable `lmsysorg/sglang:v<version>` for reproducible deployments.
- **`scripts/release/README.md`** — documented the new script and the files it updates.

## Accuracy Tests

N/A — documentation and release/CI automation only; no model, kernel, or runtime code is changed.

## Speed Tests and Profiling

N/A — see above.

## Checklist

- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Accuracy / speed benchmarks — N/A (docs + CI automation only).

🤖 Generated with [Claude Code](https://claude.com/claude-code)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28832181981](https://github.com/sgl-project/sglang/actions/runs/28832181981)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28832181747](https://github.com/sgl-project/sglang/actions/runs/28832181747)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
