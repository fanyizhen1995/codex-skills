---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Fix Z-Image accuracy'
canonical_url: https://github.com/sgl-project/sglang/pull/29742
captured_at: '2026-07-08T23:36:33.803929+00:00'
content_hash: 0501f2cbf0c301907f68702dbc3a6d9bc80f5c01857dd6cb5470eb810e34792f
---
# [diffusion] Fix Z-Image accuracy

URL: https://github.com/sgl-project/sglang/pull/29742
State: closed
Labels: run-ci, diffusion, jit-kernel
Closed at: 2026-07-08T01:08:33Z
Merged at: 2026-07-08T01:08:33Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix #28502 , and general accuracy issues with Z-image-Turbo

## Modifications

With `--batching-mode dynamic`, `Tongyi-MAI/Z-Image-Turbo` could produce severely degraded images when requests were batched. 

Initially, i found part of this issue was that qwen3 text encoder default `position_ids` were shaped `[1, seq]` even when `hidden_states` were `[batch, seq, dim]`, causing RoPE to be applied with the wrong flattened token layout for batched prompts,

But following this, I realize that our current z-image turbo implementation is severely degraded, even for singleton generations, compared to the [native pytorch implementation](https://github.com/Tongyi-MAI/Z-Image):

Firstly, z-image sampling and normalization differed from the native implementation above; we use the scheduler default sigma path, outer autocast, and shared fp32-accumulating RMSNorm,  changing the denoising trajectory and bf16 activations for this model

Secondly, we padded batched images/captions to shared batch len but did not preserve RoPE offsets for each request or mask extra batch-only padding in attention, which causes mixed-prompt dynamic batches to attend to invalid tokens and use wrong image positions

## Accuracy Tests

Tested on 1xh100

```
python3 -m sglang.multimodal_gen.runtime.entrypoints.cli.main serve \
  --model-path Tongyi-MAI/Z-Image-Turbo \
  --host 0.0.0.0 \
  --port 30000 \
  --batching-mode dynamic \
  --batching-max-size 5 \
  --batching-delay-ms 1000 \
  --enable-batching-metrics
```
```
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "prompt": "Please produce a black-and-white line art drawing.\n\nSpecifications: Render the artwork exclusively with black lines, with distinct, well-defined outlines. The piece shall consist solely of black linework on a white background, with no fills, no gradients, and no shading. Emphasize clarity of outlines and structural forms. All lines must be sharp, continuous, and with clean edges; the overall image shall be neat and uncluttered.\n\nThe subject to be depicted is: <PROMPT>",
  "n": 1,
  "size": "640x480",
  "response_format": "b64_json",
  "seed": 42,
  "num_inference_steps": 8,
  "guidance_scale": 0.0
}
```
Prompts tested:

- `Draw Donald Duck and Mickey Mouse fishing by the river.`
- `Crayon Shin chan walks with a puppy on the street.`
- `Naruto and Luffy sit side by side on a large boulder. On the left, Naruto has a smile on his face and raises one hand to make a victory gesture. On the right, Luffy wears a wide-brimmed straw hat, an unbuttoned short-sleeved jacket, shorts and flip-flops, with a long sword strapped to his back. He is also grinning happily. Behind them lie a wide expanse of water and the sky dotted with a few clouds, and patches of grass grow beside the boulder.`
- `SpongeBob SquarePants and Patrick sat at the table having dinner together, and there was a TV in the middle of the house with an old phone next to it.`
- `Mario is driving a go kart on the highway, surrounded by many low trees.`

<img width="1600" height="1394" alt="all_prompts_native_main_branch_singleton_batch5_no_prompt_column" src="https://github.com/user-attachments/assets/ec81fe7c-1374-4b7e-90b6-c9904cb7d7ca" />

## Speed Tests and Profiling

1xh100, 1024x1024, 9 steps single generation
| | Loop Time |
|---|---:|
| main | `863.27 ms` |
| current branch | `851.57 ms` |

batch generation size 5:
|  | Batch Wall | Mean Client | Denoising | Avg Step | 
|---|---:|---:|---:|---:|
| main | `4907.5 ms` | `4893.5 ms` | `3749.0 ms` | `416.3 ms` | 
| current branch | `4781.3 ms` | `4765.0 ms` | `3691.5 ms` | `409.9 ms` | 

about 2% faster across single and batch generation

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).























































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28860860153](https://github.com/sgl-project/sglang/actions/runs/28860860153)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28860859883](https://github.com/sgl-project/sglang/actions/runs/28860859883)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
