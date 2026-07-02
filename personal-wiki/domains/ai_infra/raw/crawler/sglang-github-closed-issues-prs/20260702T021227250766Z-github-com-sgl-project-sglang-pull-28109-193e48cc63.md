---
source_id: sglang-github-closed-issues-prs
title: Relax apache-tvm-ffi dependency constraints
canonical_url: https://github.com/sgl-project/sglang/pull/28109
captured_at: '2026-07-02T02:12:27.250766+00:00'
content_hash: 193e48cc63250797da10fdba8011633f0b6a47bc653f78bd872fec5fa76c88c3
---
# Relax apache-tvm-ffi dependency constraints

URL: https://github.com/sgl-project/sglang/pull/28109
State: closed
Labels: dependencies
Closed at: 2026-07-02T01:55:53Z
Merged at: 

 ## Motivation

  Unpin `apache-tvm-ffi` for DeepSeek V4 dependency work while keeping the dependency constrained to the compatible `0.1.x` ABI range.

  RCA: SGLang’s direct pin can be relaxed, but full dependency resolution still selects `apache-tvm-ffi==0.1.9` today because the published
`sgl-deep-gemm==0.1.2` wheel metadata pins `apache-tvm-ffi==0.1.9`. This PR also fixes SGLang’s DeepGEMM wheel build wrapper so future `sgl-
deep-gemm` releases do not reintroduce that exact pin.

  ## Modifications

  - Relax `apache-tvm-ffi` in `python/pyproject.toml` to `apache-tvm-ffi>=0.1.9,<0.2`.
  - Keep `python/pyproject_other.toml` aligned with the same range.
  - Update `scripts/build_sgl_deep_gemm.sh` to rewrite DeepGEMM’s `sgl_deep_gemm/pyproject.toml` from `apache-tvm-ffi==0.1.9` to `apache-tvm-
ffi>=0.1.9,<0.2` before building future `sgl-deep-gemm` wheels.

  ## Accuracy Tests

  N/A. This only changes Python package dependency metadata and the DeepGEMM wheel build wrapper; it does not change model outputs, kernels, or
model forward code.

  ## Speed Tests and Profiling

  N/A. This does not affect inference runtime paths.

  ## Checklist

  - [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-
code-with-pre-commit).
  - [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-
unit-tests).
  - [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-
documentations).
  - [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/
contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-
the-speed).
  - [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

  Test plan:
  - `bash -n scripts/build_sgl_deep_gemm.sh`
  - TOML parse for `python/pyproject.toml` and `python/pyproject_other.toml`
  - Simulated the DeepGEMM pyproject rewrite against a fresh `sgl-project/DeepGEMM` dev checkout; verified it rewrites `apache-tvm-ffi==0.1.9`
to `apache-tvm-ffi>=0.1.9,<0.2`
  - `uv pip compile python/pyproject.toml --python-version 3.12 --python-platform x86_64-manylinux_2_28 --torch-backend cu130 --no-annotate
--no-header -o /tmp/sglang-pyproject-resolved-after-fix.txt`
  - `uv pip compile python/pyproject.toml --all-extras --python-version 3.12 --python-platform x86_64-manylinux_2_28 --torch-backend cu130
--no-annotate --no-header -o /tmp/sglang-pyproject-all-extras-resolved-after-fix.txt`
  - `uv pip compile python/pyproject.toml --python-version 3.12 --python-platform x86_64-manylinux_2_28 --torch-backend cu130 --overrides
<apache-tvm-ffi==0.1.12 override> --no-annotate --no-header -o /tmp/sglang-pyproject-tvm-ffi-012-override-after-fix.txt`
  - `uv build --sdist python --out-dir /tmp/sglang-build-test-after-fix...`
  - Verified generated `PKG-INFO` has `Requires-Dist: apache-tvm-ffi<0.2,>=0.1.9`
  - Clean venv install/import of `apache-tvm-ffi>=0.1.9,<0.2`; resolved `apache-tvm-ffi==0.1.12`, `uv pip check` passed, `import tvm_ffi`
passed
  - Editable install dry-run for `python` base dependencies on Linux/CUDA/Python 3.12
  - Editable install dry-run for `python[all,checkpoint-engine,dev,diffusion,fastokens,http2,ray,runai,test,tracing]` on Linux/CUDA/Python 3.12
  - `python3 test/registered/unit/tools/test_get_version_tag.py`
  - `python3 scripts/ci/check_no_registered_tests_in_package.py`
  - `git diff --check`







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27450945597](https://github.com/sgl-project/sglang/actions/runs/27450945597)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27450945492](https://github.com/sgl-project/sglang/actions/runs/27450945492)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
