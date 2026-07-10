---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Add NVFP4 FA4 attention path'
canonical_url: https://github.com/sgl-project/sglang/pull/25511
captured_at: '2026-07-09T23:36:35.329892+00:00'
content_hash: 6080ccdc966c29e448bcaa05e5d87563f4733cf5612cff3b00afeed3fae01218
---
# [diffusion] Add NVFP4 FA4 attention path

URL: https://github.com/sgl-project/sglang/pull/25511
State: closed
Labels: blackwell, run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-07-09T11:39:45Z
Merged at: 

## Summary

Add an opt-in Blackwell diffusion attention path that quantizes dense Q/K to NVFP4 and calls the block-scaled FlashAttention-4 FP4 kernel. The path is enabled with `SGLANG_DIFFUSION_NVFP4_FA4=1` (or `FASTVIDEO_NVFP4_FA4=1`) and requires a `flash_attn.cute` build with `mSFQ/mSFK` support, such as `hao-ai-lab/flash-attention-fp4@fp4`.

This also wires the mSFQ/mSFK/mSFV arguments through the FA4 JIT wrapper, keeps FA3 guarded, handles the forked FA4 varlen signature for non-FP4 BF16 runs, and adds a Blackwell-only check test for the NVFP4 FA4 path.

## Attribution

This is an SGLang adaptation of the NVFP4 Q/K + FA4 attention path from FastVideo [#1221](https://github.com/hao-ai-lab/FastVideo/pull/1221). 

## 5s Video Check

Validated on `ion-b200` with 1x B200 (`CUDA_VISIBLE_DEVICES=6`), native SGLang backend, `--attention-backend fa`, model `Wan-AI/Wan2.2-T2V-A14B-Diffusers`, `832x480`, 81 frames at 16 FPS (~5.06s), 50 inference steps, `guidance_scale=5.0`, seed 0, no torch compile, and no CPU/layerwise offload.

Prompt: `A cat and a dog baking a cake together in a cozy kitchen. The cat carefully measures flour while the dog stirs batter in a glass bowl, sunlight through the window, smooth cinematic camera motion.`

<table>
  <thead>
    <tr>
      <th>Variant</th>
      <th>Checkpoint Args</th>
      <th>Generate Time</th>
      <th>Avg Denoise Step</th>
      <th>Peak Memory</th>
      <th>Preview</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BF16 FA4 baseline</td>
      <td><code>PYTHONPATH=/tmp/sglang_local_validate/python</code></td>
      <td>161.99s</td>
      <td>3.1375s</td>
      <td>89572 MB</td>
      <td><img src="https://github.com/BBuf/sglang/releases/download/wan22-nvfp4-fa4-validation-20260517-134707/bf16_fa4.gif" width="260" /></td>
    </tr>
    <tr>
      <td>NVFP4 FA4</td>
      <td><code>SGLANG_DIFFUSION_NVFP4_FA4=1</code>, <code>PYTHONPATH=/tmp/flash-attention-fp4-inspect:/tmp/sglang_local_validate/python</code></td>
      <td>134.23s (1.21x)</td>
      <td>2.5969s (1.21x)</td>
      <td>89732 MB</td>
      <td><img src="https://github.com/BBuf/sglang/releases/download/wan22-nvfp4-fa4-validation-20260517-134707/nvfp4_fa4.gif" width="260" /></td>
    </tr>
  </tbody>
</table>

The previews use release-hosted GIFs because GitHub does not render video tags in PR descriptions.

## Tests

- `python3 -m ruff format python/sglang/jit_kernel/flash_attention.py python/sglang/jit_kernel/flash_attention_v4.py python/sglang/multimodal_gen/envs.py python/sglang/multimodal_gen/runtime/layers/attention/backends/flash_attn.py python/sglang/multimodal_gen/test/layers/test_nvfp4_fa4.py`
- `python3 -m ruff check python/sglang/jit_kernel/flash_attention.py python/sglang/jit_kernel/flash_attention_v4.py python/sglang/multimodal_gen/envs.py python/sglang/multimodal_gen/runtime/layers/attention/backends/flash_attn.py python/sglang/multimodal_gen/test/layers/test_nvfp4_fa4.py`
- `python3 -m compileall -q python/sglang/jit_kernel/flash_attention.py python/sglang/jit_kernel/flash_attention_v4.py python/sglang/multimodal_gen/envs.py python/sglang/multimodal_gen/runtime/layers/attention/backends/flash_attn.py python/sglang/multimodal_gen/test/layers/test_nvfp4_fa4.py`
- `CUDA_VISIBLE_DEVICES=6 CUTE_DSL_ENABLE_TVM_FFI=1 FLASHINFER_DISABLE_VERSION_CHECK=1 PYTHONPATH=/tmp/flash-attention-fp4-inspect:/tmp/sglang_local_validate/python pytest -q python/sglang/multimodal_gen/test/layers/test_nvfp4_fa4.py -s`
- Wan2.2 BF16 FA4 baseline: `161.99s` generate time, `3.1375s/step`, `89572 MB` peak memory
- Wan2.2 NVFP4 FA4: `134.23s` generate time, `2.5969s/step`, `89732 MB` peak memory
- Wan2.2 BF16 check with the FP4 fork shadowing `flash_attn` and `SGLANG_DIFFUSION_NVFP4_FA4` disabled















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28272219745](https://github.com/sgl-project/sglang/actions/runs/28272219745)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28272219667](https://github.com/sgl-project/sglang/actions/runs/28272219667)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
