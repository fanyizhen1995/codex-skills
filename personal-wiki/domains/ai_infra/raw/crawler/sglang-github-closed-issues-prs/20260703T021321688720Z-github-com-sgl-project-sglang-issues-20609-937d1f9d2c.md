---
source_id: sglang-github-closed-issues-prs
title: '[Tracking][Diffusion] Inference Batching Support'
canonical_url: https://github.com/sgl-project/sglang/issues/20609
captured_at: '2026-07-03T02:13:21.688720+00:00'
content_hash: 937d1f9d2cbb5dd9528c022b4fd37cbdaa23f57b00f894640d7f4ba014fbbcf2
---
# [Tracking][Diffusion] Inference Batching Support

URL: https://github.com/sgl-project/sglang/issues/20609
State: closed
Labels: inactive
Closed at: 2026-07-03T00:39:36Z
Merged at: 

An initial implementation of dynamic batching for T2I/T2V models can be found
at #18764. Current compatibility grids based off this PR can be found below.
This will be updated as more coverage is added.

`✅` means supported, `❌` means not currently supported, `?` means untested, and
`-` means not applicable.

**image batching support:**

| Model | T2I | I2I |
| --- | --- | --- |
| FLUX.1-dev | ✅ | - |
| FLUX.2-dev | ✅ | ❌ |
| FLUX.2-dev-NVFP4 | ? | ? |
| FLUX.2-Klein-4B | ✅ | ❌ |
| FLUX.2-Klein-9B | ? | ? |
| Z-Image | ? | - |
| Z-Image-Turbo | ✅ | - |
| GLM-Image | ❌ | - |
| Qwen Image | ✅ | - |
| Qwen Image 2512 | ✅ | - |
| Qwen Image Edit | - | ❌ |
| Qwen Image Edit 2509 | - | ? |
| Qwen Image Edit 2511 | - | ? |
| Qwen Image Layered | ? | ? |
| SD3 Medium | ? | - |
| SD3.5 Medium | ? | - |
| SD3.5 Large | ? | - |
| Hunyuan3D-2 | ? | - |
| SANA 1.5 1.6B | ✅ | - |
| SANA 1.5 4.8B | ✅ | - |
| SANA 1600M 1024px | ? | - |
| SANA 600M 1024px | ? | - |
| SANA 1600M 512px | ? | - |
| SANA 600M 512px | ? | - |
| FireRed-Image-Edit 1.0 | - | ? |
| FireRed-Image-Edit 1.1 | - | ? |
| ERNIE-Image | ? | - |
| ERNIE-Image-Turbo | ? | - |

**video batching support:**

| Model | Support |
| --- | --- |
| FastWan2.1 T2V 1.3B | ✅ |
| FastWan2.2 TI2V 5B Full Attn | ❌ |
| Wan2.2 TI2V 5B | ❌ |
| Wan2.2 T2V A14B | ✅ |
| Wan2.2 I2V A14B | ❌ |
| HunyuanVideo | ❌ |
| FastHunyuan | ❌ |
| Wan2.1 T2V 1.3B | ✅ |
| Wan2.1 T2V 14B | ✅ |
| Wan2.1 I2V 480P | ? |
| Wan2.1 I2V 720P | ? |
| TurboWan2.1 T2V 1.3B | ✅ |
| TurboWan2.1 T2V 14B | ✅ |
| TurboWan2.1 T2V 14B 720P | ✅ |
| TurboWan2.2 I2V A14B | ? |
| Wan2.1 Fun 1.3B InP | ? |
| Helios Base | ? |
| Helios Mid | ? |
| Helios Distilled | ? |
| LTX-2 | ? |
| LTX-2.3 | ? |

### TODO, following #18764

- [ ] Support I2I @qimcis
- [ ] Support I2V @yyy1000
- [ ] Support continuous batching for SGLang-Diffusion.
- [ ] Explore stage-wise batching so compatible requests can share specific
      pipeline stages even when the full generation request cannot be merged.
- [ ] Add better memory prediction/admission so batching can use available VRAM
      more aggressively without relying only on fixed caps.
- [ ] Let models declare their text-conditioning layout, e.g. masked,
      fixed-length, or packed varlen/ragged. The current mask path can add overhead for models that can use a more efficient layout.
- [ ] Continue polishing code style and separation of scheduler/admission/model
      responsibilities in follow-up PRs.
- [ ] Support setting benchmark timeout
- [ ] Add CI coverage for batching
- [ ] Confirm supported models
