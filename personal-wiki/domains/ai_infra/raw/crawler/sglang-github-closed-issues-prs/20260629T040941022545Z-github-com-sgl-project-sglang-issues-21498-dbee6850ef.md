---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Upgrade default Cuda version to 13.0'
canonical_url: https://github.com/sgl-project/sglang/issues/21498
captured_at: '2026-06-29T04:09:41.022545+00:00'
content_hash: dbee6850efa135361268ae72298e23e0c112e09e7432ac635dd1ffc797dba59d
---
# [Feature] Upgrade default Cuda version to 13.0

URL: https://github.com/sgl-project/sglang/issues/21498
State: closed
Labels: high priority
Closed at: 2026-05-06T09:15:12Z
Merged at: 

### Motivation

Torch 2.11 will set Cuda 13.0 as the default version. So it's necessary for SGLang to shift default cuda version from Cuda 12.9 to Cuda 13.0

We plan to do the migration after release of 0.5.10 version for SGLang

### Checklist

It involves multiple steps to fully shift all the Cuda dependencies from 12.9 to 13.0:
- [x] Ramp up 13.0 environment on all CI runners, and modify CI-related scripts/workflows #23119 
     - [x] Change default cuda-python to cuda 13.0 in `pyproject.toml` 
     - [x] Change packages to cuda 13 version in [ci_install_dependency.sh](https://github.com/sgl-project/sglang/blob/main/scripts/ci/cuda/ci_install_dependency.sh) 
- [x] After CI gets stable on Cuda 13, shift docker images to cuda 13 #23593
     - [x] Modifty Dockerfiles ([sglang](https://github.com/sgl-project/sglang/blob/main/docker/Dockerfile), [sgl-kernel](https://github.com/sgl-project/sglang/blob/main/sgl-kernel/Dockerfile))
     - [x] Modify docker release workflows, so that the default image tag is pointed to cu13 images. ([release-docker.yml](https://github.com/sgl-project/sglang/blob/main/.github/workflows/release-docker.yml), [release-docker-dev.yml](https://github.com/sgl-project/sglang/blob/main/.github/workflows/release-docker-dev.yml))
- [x] Redirect default sglang wheel to Cuda 13 version #24176  #24183 
    - [x] Change default cuda version in [update_nightly_whl_index.py](https://github.com/sgl-project/sglang/blob/main/scripts/update_nightly_whl_index.py)
    - [x] Build up a support matrix (cu129/cu130) for nightly sglang wheel in [release-pypi-nightly.tml](https://github.com/sgl-project/sglang/blob/main/.github/workflows/release-pypi-nightly.yml)
- [x] Redirect default sglang-kernel wheel to Cuda 13 version #24162
     - [x] Modify [release-whl-kernel.yml](https://github.com/sgl-project/sglang/blob/main/.github/workflows/release-whl-kernel.yml), so that the cu130 wheels will be uploaded to pypi instead of cu129 wheels
     - [x] Modify [update_kernel_whl_index.py](https://github.com/sgl-project/sglang/blob/main/scripts/update_kernel_whl_index.py), so that the default cuda version on whl index is shifted to cuda 13.0
     - [x] Bump a new version for sglang kernel, to test its functionality on cuda-13 #24170
     - [x] Update document #24181 
- [x] Update documents https://docs.sglang.io/get_started/install.html  #24516
- [x] Upgrade Torch to 2.11 https://github.com/sgl-project/sglang/pull/21247
- [ ] Upgrade to Cuda 13.1 （optional, might depend on the next torch version) 

All these steps should be finished in the listed order.
Cuda 12.9 image/kernels will still be under maintenance. It's just they are not the default option.

### Related resources

- Torch 2.11 release blog https://pytorch.org/blog/pytorch-2-11-release-blog/
- https://github.com/sgl-project/sglang/issues/20486

_No response_
