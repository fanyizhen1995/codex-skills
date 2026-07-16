---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Reorganize runtime utility modules'
canonical_url: https://github.com/sgl-project/sglang/pull/30447
captured_at: '2026-07-10T23:37:20.326589+00:00'
content_hash: 088d0c1bdf9601cf8829f4c536bc9767f04c19ac3816c88b9521cf1ce82869c9
---
# [diffusion] Reorganize runtime utility modules

URL: https://github.com/sgl-project/sglang/pull/30447
State: closed
Labels: quant, Multi-modal, npu, run-ci, diffusion
Closed at: 2026-07-10T07:53:01Z
Merged at: 2026-07-10T07:53:01Z

## Summary
- split `runtime/models/utils.py` into owner-specific runtime utility modules
- move vision preprocessing helpers from `runtime/models/vision_utils.py` to `runtime/utils/vision.py`
- package `server_args`, `server_args_auto_tune`, and `server_args_disagg` under `runtime/server_args/` while preserving the public `runtime.server_args` import surface

## Motivation
The previous `runtime/models/utils.py` mixed weight metadata helpers, AITER platform capability checks, DiT math helpers, and scheduler latent conversion. `vision_utils.py` also lived under models even though it is used by configs, pipelines, and stages as generic image/video preprocessing. This keeps shared utilities closer to their ownership boundary.

## Validation
- `pre-commit run --files $(git diff --cached --name-only --diff-filter=ACMR | xargs)` via commit hook / explicit staged-file run

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29073155708](https://github.com/sgl-project/sglang/actions/runs/29073155708)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29073155668](https://github.com/sgl-project/sglang/actions/runs/29073155668)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
