---
source_id: sglang-github-closed-issues-prs
title: Update AMD local registry address
canonical_url: https://github.com/sgl-project/sglang/pull/29763
captured_at: '2026-07-01T02:12:08.957356+00:00'
content_hash: f6672216be936edcf9b9a25ea0e2a49b02cdcd5c7b31d70445300cb9ca630785
---
# Update AMD local registry address

URL: https://github.com/sgl-project/sglang/pull/29763
State: closed
Labels: amd
Closed at: 2026-06-30T15:35:14Z
Merged at: 

## Summary
- Update the AMD ROCm nightly local registry mirror and AMD CI pull prefix from `10.245.143.50:5000` to `10.44.14.109:5000`.
- Remove the Miles ROCm nightly local-registry mirror jobs because those workflows do not otherwise use the MI300 runner; their publish jobs build and push on `amd-docker-scale`.

## Testing
- Local analysis: searched the AMD release and CI paths for hard-coded local registry references and MI300 runner usage.
- Local cheap checks: `rg -n "10\.245\.143\.50:5000" .` found no remaining old registry references.
- Local cheap checks: `git diff --check` passed.
- Local cheap checks: `bash -n scripts/ci/amd/amd_ci_start_container.sh scripts/ci/amd/amd_ci_start_container_disagg.sh` passed.
- Commit hooks passed, including YAML syntax and duplicate workflow job name checks.

## Verification Plan
- The remaining registry verification surface is the non-Miles AMD ROCm nightly mirror path plus AMD CI jobs that pull via `LOCAL_DOCKER_REGISTRY`.
- Miles nightly verification is YAML/static validation only; no local-registry mirror remains there.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28455911185](https://github.com/sgl-project/sglang/actions/runs/28455911185)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28455911015](https://github.com/sgl-project/sglang/actions/runs/28455911015)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
