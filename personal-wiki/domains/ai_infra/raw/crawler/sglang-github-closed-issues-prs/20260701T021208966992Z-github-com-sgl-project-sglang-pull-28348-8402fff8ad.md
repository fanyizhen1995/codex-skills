---
source_id: sglang-github-closed-issues-prs
title: '[AMD]: Enable NIXL PD disaggregation for ROCm(1/n) '
canonical_url: https://github.com/sgl-project/sglang/pull/28348
captured_at: '2026-07-01T02:12:08.966992+00:00'
content_hash: 8402fff8adb6a12053d3b103ac645ea9d1d941107a6ca0e10e9ec86327b5673d
---
# [AMD]: Enable NIXL PD disaggregation for ROCm(1/n) 

URL: https://github.com/sgl-project/sglang/pull/28348
State: closed
Labels: amd
Closed at: 2026-06-30T04:23:10Z
Merged at: 2026-06-30T04:23:10Z

  Build UCX (--with-rocm) and upstream ai-dynamo/nixl from source so SGLang prefill/decode disaggregation can use --disaggregation-transfer-backend nixl on ROCm. Disabled by default; enable with --build-arg
  ENABLE_NIXL=1.

  Validated end-to-end on MI35x/ROCm 7.2: clean-image build, import resolves with plugins [POSIX, UCX], and a real 1P1D GSM8K run (accuracy 0.970, invalid 0.000) with all ranks reporting NIXL KVManager
  backend UCX.

  Motivation

  PD (prefill/decode) disaggregation can move KV cache over https://github.com/ai-dynamo/nixl, but the ROCm image ships no NIXL build, so --disaggregation-transfer-backend nixl is unusable on AMD GPUs. This
  adds an optional, reproducible NIXL build to docker/rocm.Dockerfile using the same upstream ai-dynamo/nixl that the CUDA path uses — no SGLang code changes, fully backward compatible (off by default).

  Modifications

  - docker/rocm.Dockerfile (+48): optional stage gated by --build-arg ENABLE_NIXL=1 (default 0, no change to existing builds). When enabled it:
    - Installs build deps (autoconf/automake/libtool, pkg-config, rdma-core, libibverbs/librdmacm-dev) + python build tooling (meson, ninja, pybind11, meson-python, patchelf, pyyaml).
    - Builds UCX from source (openucx v1.19.x) --with-rocm=/opt/rocm --with-verbs --with-dm --enable-mt → /opt/ucx.
    - Builds nixl from source (ai-dynamo/nixl @ c28061f) with meson -Ducx_path=/opt/ucx -Dwheel_variant=rocm -Denable_plugins=UCX,POSIX.
    - Symlinks nixl → nixl_rocm in site-packages and wires LD_LIBRARY_PATH=/opt/ucx/lib into /etc/bash.bashrc.
  - Three build fixes vs a naive build of this commit:
    a. --no-build-isolation --no-deps — nixl's build-system.requires pins torch==2.11.*, which under PEP 517 isolation pulls a multi-GB CUDA torch into a throwaway env and hangs the build. Reuses the image's
  ROCm torch instead.
    b. taskflow provided via a hand-written pkgconfig/taskflow.pc — the pinned taskflow.wrap source_hash no longer matches the regenerated GitHub archive, and meson's lowercase taskflow lookup is
  case-sensitive so the cmake-installed Taskflow config won't resolve.
    c. -Dwheel_variant=rocm names the import package nixl_rocm; SGLang imports plain nixl, hence the symlink.
  - No runtime overrides required beyond LD_LIBRARY_PATH (plugins auto-discover via $ORIGIN RPATH; backend defaults to UCX).

  Accuracy Tests

  Real 1P1D PD disaggregation on DeepSeek-R1-MXFP4, MI35x / ROCm 7.2, using the Dockerfile-built nixl:

  - Topology: prefill TP4 (GPU 0–3), decode TP4 (GPU 4–7), router front-end.
  - All 8 ranks logged NIXL KVManager initialized with backend: UCX; both warmups returned 200.
  - GSM8K: accuracy 0.970, invalid 0.000.

  Reference: deprecated AMD RIXL fork 0.950–0.955; manually-built upstream nixl 0.975. The Dockerfile-built nixl (0.970) is on par, confirming upstream nixl carries KV correctly on ROCm with zero SGLang code
  changes.

  Speed Tests and Profiling

  No inference-path code is changed (Docker build only). For reference, the same 1P1D setup over this backend sustains ~6.4 req/s / ~1.6k output tok/s, TPOT median ~17 ms (random ISL1024/OSL512, conc 32) —
  consistent across RIXL and upstream-nixl backends, i.e. no transfer-path penalty.


## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28382202290](https://github.com/sgl-project/sglang/actions/runs/28382202290)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28382201881](https://github.com/sgl-project/sglang/actions/runs/28382201881)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
