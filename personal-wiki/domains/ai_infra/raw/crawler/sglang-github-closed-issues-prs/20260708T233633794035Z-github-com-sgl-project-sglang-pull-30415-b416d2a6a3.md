---
source_id: sglang-github-closed-issues-prs
title: Enable RDNA3/4 (gfx1100/gfx1201) for ROCm kernels
canonical_url: https://github.com/sgl-project/sglang/pull/30415
captured_at: '2026-07-08T23:36:33.794035+00:00'
content_hash: b416d2a6a3728bb5fb85f53fb9422a0bfc1f8bdbcdcab649a426527c387017a8
---
# Enable RDNA3/4 (gfx1100/gfx1201) for ROCm kernels

URL: https://github.com/sgl-project/sglang/pull/30415
State: closed
Labels: amd, sgl-kernel
Closed at: 2026-07-07T23:42:51Z
Merged at: 2026-07-07T23:42:51Z

Minimal enablement to build/run sgl-kernel and SGLang on RDNA3/4.

  - `sgl-kernel/setup_rocm.py`: add `gfx1100`, `gfx1201` to `supported_archs` (multi-arch 
  `;`-split machinery already present).
  - `quantization/__init__.py`: make `QuarkConfig` import non-fatal.
  - `quark_w4a4_mxfp4.py` / `quark_int4fp8_moe.py`: gate `aiter` imports behind `SGLANG_USE_AITER` 















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28885752021](https://github.com/sgl-project/sglang/actions/runs/28885752021)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28885751800](https://github.com/sgl-project/sglang/actions/runs/28885751800)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
