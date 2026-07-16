---
source_id: sglang-github-closed-issues-prs
title: 'bench: support random image resolutions'
canonical_url: https://github.com/sgl-project/sglang/pull/30879
captured_at: '2026-07-12T23:38:53.058673+00:00'
content_hash: 0e68090e5f052f4c8cd3c00b3cbb1042da8b3c620eaf7a73a946348efc02bb32
---
# bench: support random image resolutions

URL: https://github.com/sgl-project/sglang/pull/30879
State: closed
Labels: run-ci
Closed at: 2026-07-12T00:28:57Z
Merged at: 2026-07-12T00:28:57Z

## Summary

- add `random:<min_h>x<min_w>-<max_h>x<max_w>` to the image benchmark dataset
- sample one independent resolution per image from inclusive bounds, while preserving the benchmark seed for reproducibility
- support `vllm-chat` image requests, so the same OpenAI Chat multimodal trace can be sent to SGLang and vLLM
- account for vLLM Kimi's streamed `delta.reasoning` field as well as the standard `delta.reasoning_content`, preventing zero TTFT/ITL metrics for Kimi reasoning output
- print sampled min/max/mean dimensions and add parser/sampler/streaming coverage

## Validation

- `python3 -m pytest test/registered/bench_fn/test_bench_serving_reasoning_stream.py test/registered/bench_fn/test_benchmark_datasets_api.py -k "reasoning or image_sampler" -q` on NVIDIA H200: **13 passed**.

## Performance

This PR changes benchmark generation and metric collection only; it does not alter an SGLang serving path, so it has no meaningful before/after serving-performance claim. It enables reproducible, seeded K2.7/Qwen random-image matrices and makes the SGLang/vLLM chat results comparable, including TTFT/ITL for Kimi reasoning streams.



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29159068010](https://github.com/sgl-project/sglang/actions/runs/29159068010)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29159067885](https://github.com/sgl-project/sglang/actions/runs/29159067885)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
