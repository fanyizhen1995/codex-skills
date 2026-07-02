---
source_id: sglang-github-closed-issues-prs
title: 'docs: add B200 NVFP4 recipes + benchmarks to GLM-5.2 cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/29674
captured_at: '2026-07-01T02:12:08.974901+00:00'
content_hash: cac77fb026a65584b63f3454bec9d348173a8d6b798bb2370a59d7909d38bcc6
---
# docs: add B200 NVFP4 recipes + benchmarks to GLM-5.2 cookbook

URL: https://github.com/sgl-project/sglang/pull/29674
State: closed
Labels: documentation
Closed at: 2026-06-29T21:06:30Z
Merged at: 2026-06-29T21:06:30Z

## What

Adds **B200 + NVFP4 (TP8)** deployment recipes and benchmarks to the GLM-5.2 cookbook page.

- **3 new cells** (`b200|nvfp4`: low-latency / balanced / high-throughput) for `nvidia/GLM-5.2-NVFP4` via `--quantization modelopt_fp4`.
  - low-latency: TP8 + EAGLE MTP 5-1-6, `chunked-prefill 8192`, `mem-fraction 0.85`
  - balanced: TP8 + `--dp 8 --enable-dp-attention` + MTP 2-1-3, `chunked-prefill 32768`, `mem-fraction 0.92`, `max-running 256`
  - high-throughput: TP8 + `--dp 8 --enable-dp-attention`, `chunked-prefill 32768`, `mem-fraction 0.92`, `max-running 512`
- **Docker-image override** `b200|nvfp4 → lmsysorg/sglang:dev-glm52-nvfp4` (NVFP4 needs the `modelopt_fp4` build).
- **Benchmarks** measured on the `dev-glm52-nvfp4` preview image (P50 TTFT/TPOT; `tokens_per_sec_per_gpu` = output tok/s/GPU):

| strategy | concurrency | TTFT (ms) | TPOT (ms) | tok/s/GPU |
|---|---|---|---|---|
| low-latency | 1 / 16 | 295 / 2491 | 1.85 / 5.43 | 58.6 / 254.3 |
| balanced | 64 / 256 | 5837 / 16736 | 12.70 / 30.00 | 418.9 / 593.7 |
| high-throughput | 1024 | 130174 | 67.12 | 589.4 |

## Notes

Docs-only change under `docs_new/` (config-driven cookbook format). `mint validate` passes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28401508750](https://github.com/sgl-project/sglang/actions/runs/28401508750)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28401508479](https://github.com/sgl-project/sglang/actions/runs/28401508479)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
