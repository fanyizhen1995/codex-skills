---
source_id: sglang-github-closed-issues-prs
title: '[CI] Fix CUDA 12 NVIDIA wheel cleanup'
canonical_url: https://github.com/sgl-project/sglang/pull/31035
captured_at: '2026-07-15T23:40:28.384497+00:00'
content_hash: c39ce546e5f65789bccfbb5f5e76ea02d07b0eb038316ada090ab3719a75aab8
---
# [CI] Fix CUDA 12 NVIDIA wheel cleanup

URL: https://github.com/sgl-project/sglang/pull/31035
State: closed
Labels: run-ci
Closed at: 2026-07-15T02:06:12Z
Merged at: 2026-07-15T02:06:12Z

## Motivation

The CUDA 13 cleanup introduced by #29844 uninstalls every installed `nvidia-*-cu12` distribution. CUDA 12 and CUDA 13 NVIDIA component wheels can own the same paths under `site-packages/nvidia/`. For example, both `nvidia-nvshmem-cu12==3.4.5` and `nvidia-nvshmem-cu13==3.4.5` own `nvidia/nvshmem/lib/libnvshmem_host.so.3` in their wheel RECORDs.

Uninstalling the CUDA 12 distribution removes that shared file. The CUDA 13 `dist-info` metadata remains installed, so a subsequent normal dependency installation considers the CUDA 13 wheel satisfied and does not restore the missing payload. `import torch` then fails with `ImportError: libnvshmem_host.so.3: cannot open shared object file`.

Affected CI/UT jobs:

- [First environment-corrupting H20 job](https://github.com/sgl-project/sglang/actions/runs/28709094411/job/85147036563): the log removes 15 CUDA 12 NVIDIA wheels, including NVSHMEM, and then fails to import torch because `libnvshmem_host.so.3` is missing.
- [Later base H20 failure](https://github.com/sgl-project/sglang/actions/runs/28758504924/job/85289402652): the same runner continues failing with the missing NVSHMEM payload.
- [Later nightly H20 failure](https://github.com/sgl-project/sglang/actions/runs/28760994711/job/85276299725): confirms that the damaged runner state persists across jobs.

## Modifications

- Snapshot every installed NVIDIA wheel as an exact `name==version` spec before removing stale `nvidia-*-cu12` wheels from CUDA 13 jobs.
- Uninstall the stale CUDA 12 wheels as before.
- Force-reinstall every remaining NVIDIA wheel at its recorded version with `--force-reinstall --no-deps` so files deleted through overlapping wheel ownership are restored.
- Preserve the existing no-op path when no stale CUDA 12 NVIDIA wheels are installed.

CUDA 13 NVIDIA package names do not use a uniform suffix: some are named like `nvidia-cublas`, while others are named like `nvidia-cudnn-cu13` and `nvidia-nvshmem-cu13`. Recording the installed non-CUDA-12 set avoids a hard-coded package mapping or a package-specific `.so` health check. Exact versions prevent accidental upgrades, and `--no-deps` avoids re-resolving or changing the dependency graph.

## Accuracy Tests

Not applicable. This change only repairs CI dependency installation and does not affect model outputs.

## Speed Tests and Profiling

Not applicable. This change does not affect inference runtime or performance.

## Test Logs

- `bash -n scripts/ci/cuda/ci_install_dependency.sh` and `git diff --check upstream/main...HEAD` passed.
- In a fresh Kubernetes Pod, we installed `nvidia-nvshmem-cu12==3.4.5` and `nvidia-nvshmem-cu13==3.4.5` into the same venv and confirmed that both wheel RECORDs own `nvidia/nvshmem/lib/libnvshmem_host.so.3`.
- **Failure reproduction:** uninstalling only the CUDA 12 wheel leaves the CUDA 13 metadata installed but removes `libnvshmem_host.so.3`. This reproduces the runner corruption.
- **Pass with this PR:** running `remove_stale_cuda12_nvidia_wheels` removes the CUDA 12 wheel, force-reinstalls the exact CUDA 13 wheel version, and leaves both the CUDA 13 metadata and `libnvshmem_host.so.3` present.
- **Pass on an already-clean environment:** running the function again finds no CUDA 12 wheel, performs no reinstall, and leaves the CUDA 13 payload intact.

No permanent test file is included because this is a narrow CI bootstrap repair. The Kubernetes validation exercised the real overlapping CUDA 12/13 wheel transition end to end.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit). Shell-only change; validated with `bash -n` and `git diff --check`.
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). No permanent test was added for this CI bootstrap script; a temporary behavior harness covered both shell branches and a fresh Kubernetes environment verified the real overlapping CUDA 12/13 wheel transition end to end.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). Not applicable; there is no user-facing behavior change.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Not applicable; this only repairs CI dependency installation.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`.
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29253084683](https://github.com/sgl-project/sglang/actions/runs/29253084683)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29253083801](https://github.com/sgl-project/sglang/actions/runs/29253083801)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
