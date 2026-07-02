---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Add pyproject_rocm.toml for end-to-end ROCm pip installation support'
canonical_url: https://github.com/sgl-project/sglang/pull/14802
captured_at: '2026-07-02T02:12:27.268565+00:00'
content_hash: ae67c43f0f34df553bfa4d00155f57b67332e3892a7981d7ec3a21b7542ad2d4
---
# [Feature] Add pyproject_rocm.toml for end-to-end ROCm pip installation support

URL: https://github.com/sgl-project/sglang/pull/14802
State: closed
Labels: documentation, amd, dependencies
Closed at: 2026-07-01T03:23:37Z
Merged at: 

## Motivation

To enable **end-to-end** `pip install sglang` support for ROCm, this PR adds the necessary **ROCm-specific pyproject file, `pyproject_rocm.toml`**.

## Changes
1. This PR adds a new `pyproject_rocm.toml` which contains all the dependencies required by SGLang for AMD hardware (except AITER, which is required to be installed from source).
2. This PR updates the documentation adding new steps to install SGLang with all the required dependencies. This PR also moves the recommended method (using docker) above the "Install from Source" section.

## Pending Changes

* To update the `sgl-kernel` package URL from [sgl-kernel wheel release](https://github.com/sgl-project/whl/releases) once #14684 is merged: Once #14684 is merged, the `sgl-kernel` package for rocm700 will show up in  [sgl-kernel wheel release](https://github.com/sgl-project/whl/releases). The URLs for these need to be updated in `pyproject_rocm.toml` replacing `<URL TODO>`.

## Next Steps/TODO
* Build and release `sglang-rocm` wheel by adding a github workflow similar to [release_pypi.yml](https://github.com/sgl-project/sglang/blob/main/.github/workflows/release-pypi.yml).

## Hosting the Package
[PyPI](https://pypi.org/) does not allow packages that contain non-PyPI dependencies (`torch`, `torchvision`, `pytorch-triton-rocm`, and `sgl-kernel` in this case). To solve this, there are two options:
  1. Host on a different index (like [pypi.amd.com](https://pypi.amd.com/simple/) or [sgl-whl](https://github.com/sgl-project/sgl-whl)).
  2. Remove `torch`, `torchvision`, `pytorch-triton-rocm`, and `sgl-kernel` from dependencies, making users install them explicitly with `pip install torch --index-url ...` and release wheel for `sglang-rocm` on [PyPI](https://pypi.org/). This would add one extra step to the user installation process.

### Naming the Package
Note that this PR recommends naming the package `sglang-rocm` for all hosting options. The reason for this is how pip resolves dependencies. `--extra-index-url` takes priority when resolving packages, but silently falls back to the default index [PyPI](https://pypi.org/), which can sometimes lead to issues. 

Thus, if we name the package `sglang`, and user tries to install a specific version that's not available on [https://pypi.amd.com/simple](https://pypi.amd.com/simple), but that version is available on [PyPI](https://pypi.org/) (which is the NVIDIA version), the dependency resolver will install the NVIDIA version with no warnings or errors.

Further, pip also recommends having unique package names when possible [Ref](https://github.com/pypa/pip/issues/5045#issuecomment-369521345).
 
## Maintenance
* Once this PR is upstream, `sgl-kernel`'s wheel URL must be updated every time there's a new version of the sgl-kernel released **if the first option for hosting is chosen**.
* **New Torch Version:** If we choose to update the Torch version used, the following changes are required:
  1. **Update `build_rocm.sh`**: This file determines the torch version used to build `sgl-kernel`, and is introduced in #14684.
  2. **Update `pyproject_rocm.toml`:** The torch version specified in `pyproject_rocm.toml` is the version installed when user installs SGLang using the wheel. The versions for `torchvision` and `pytorch-triton-rocm` also need to be updated. To determine these, you can manually install the desired `torch` version, which would install compatible versions of `torchvision` and `pytorch-triton-rocm`, you can make a note of the compatible `torchvision` and `pytorch-triton-rocm` from here. Simply replace the versions of `torch`, 'torchvision`, and `pytorch-triton-rocm` with the new versions.
---
## Usage Instructions/User Experience
The usage instructions change based on where the package is hosted. 

### [Not Available Yet] If SGLang wheel is hosted on [pypi.amd.com](https://pypi.amd.com/simple/)
```bash
# Install AITER from Source
git clone https://github.com/ROCm/aiter.git
cd aiter
git checkout v0.1.7.post5
git submodule update --init --recursive
GPU_ARCH_LIST="gfx950" # Or "gfx942" for MI300x/MI325x
GPU_ARCHS=$GPU_ARCH_LIST python setup.py develop # optionally you can set PREBUILD_KERNELS=1 for gfx942 (MI300x/MI325x) to precompile kernels enabling faster server startup

# Install sglang python package
pip install sglang-rocm --extra-index-url https://pypi.amd.com/simple
```

### [Not Available Yet] If SGLang wheel is hosted on [PyPI](https://pypi.org/)
```bash
# Install AITER from Source
git clone https://github.com/ROCm/aiter.git
cd aiter
git checkout v0.1.7.post5
git submodule update --init --recursive
GPU_ARCH_LIST="gfx950" # Or "gfx942" for MI300x/MI325x
GPU_ARCHS=$GPU_ARCH_LIST python setup.py develop # optionally you can set PREBUILD_KERNELS=1 for gfx942 (MI300x/MI325x) to precompile kernels enabling faster server startup

# Install Torch and Its dependencies
pip install torch==2.10.0.dev20251011 torchvision==0.25.0.dev20251012 pytorch-triton-rocm==3.5.0 --index-url https://download.pytorch.org/whl/nightly/rocm7.0

# Install sgl-kernel (Available after PR #14684 is merged)
pip install sgl-kernel --index-url https://docs.sglang.io/whl/rocm700

# Install SGLang
pip install sglang-rocm
```

### Install from Source
SGLang can be installed from source using the following commands once this PR is merged.
```bash
# Use the last release branch
git clone -b v0.5.6.post1 https://github.com/sgl-project/sglang.git
cd sglang

# Install AITER from Source
git clone https://github.com/ROCm/aiter.git
cd aiter
git checkout v0.1.7.post5
git submodule update --init --recursive
GPU_ARCH_LIST="gfx950" # Or "gfx942" for MI300x/MI325x
GPU_ARCHS=$GPU_ARCH_LIST python setup.py develop # optionally you can set PREBUILD_KERNELS=1 for gfx942 (MI300x/MI325x) to precompile kernels enabling faster server startup

# Install sglang python package
rm -rf python/pyproject.toml && mv python/pyproject_rocm.toml python/pyproject.toml
pip install -e "python[rocm700]"
```
---

## Testing
### Dependency Testing
1. **Mooncake**: Mooncake is [available for pip install](https://kvcache-ai.github.io/Mooncake/getting_started/examples/sglang-integration/hicache-integration-v1.html#install-mooncake) and this PR assumes that the same pip install works for ROCm. This PR has not been tested with Mooncake.
2. **Specific Triton Version:** If you need to pin a specific Triton version like [here](https://github.com/sgl-project/sglang/blob/main/docker/rocm.Dockerfile#L117-L125), then you can remove `pytorch-triton-rocm` and add instructions for the user to manually build Triton from source.

### Environments
Full AMD test suite (from `pr-test-amd.yml`) is run on the following matrix:
* **ROCm Versions**: [7.0]
* **Python Versions**: [3.10, 3.11, 3.12]
* **Hardware**: [MI300x, MI350x]

### Results

- Most test results match the results from CI docker. However, due to small variations in package versions, around 5 tests have different results from CI docker.
---

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.ai/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Update documentation according to [Write documentations](https://docs.sglang.ai/developer_guide/contribution_guide.html#write-documentations).
- [ ] Replace `sgl-kernel` URL with upstream URL.
- [ ] Add GitHub workflow to build and upload sglang wheel to index of choice.
