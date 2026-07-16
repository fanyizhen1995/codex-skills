---
source_id: sglang-github-closed-issues-prs
title: '[codex] Default Gemma4 attention backend to trtllm_mha on SM100'
canonical_url: https://github.com/sgl-project/sglang/pull/25005
captured_at: '2026-07-15T23:40:28.356121+00:00'
content_hash: 64b4aa8017eaff7d7eb6eaf64672afb3d3ed91162fe3879d626fc80e943ca825
---
# [codex] Default Gemma4 attention backend to trtllm_mha on SM100

URL: https://github.com/sgl-project/sglang/pull/25005
State: closed
Labels: 
Closed at: 2026-07-15T18:24:23Z
Merged at: 

## Summary

Enable `trtllm_mha` as the default attention backend for Gemma4 on SM100.

When `--attention-backend` is not specified for `Gemma4ForConditionalGeneration`, SGLang now selects:
- `trtllm_mha` on SM100
- `triton` otherwise

This keeps the existing non-SM100 behavior unchanged while enabling the Blackwell-optimized MHA backend for Gemma4 by default.

## Benchmark

Same server flags otherwise, comparing `triton` vs `trtllm_mha`.

Note: the throughput-image benchmark had 999/1000 successful requests with `trtllm_mha`; one request was silently dropped with no client-side error logged, possibly due to a request abort.

### Latency

concurrency=1, 10 prompts

| Metric | triton | trtllm_mha | Delta |
|---|---:|---:|---:|
| Text Duration (s) | 37.29 | 32.75 | -12.2% |
| Text Output tok/s | 113.2 | 128.9 | +13.9% |
| Text Mean TTFT (ms) | 72.05 | 67.04 | -7.0% |
| Text Mean TPOT (ms) | 8.55 | 7.60 | -11.1% |
| Text Median ITL (ms) | 8.84 | 7.63 | -13.7% |
| Image Duration (s) | 38.45 | 33.76 | -12.2% |
| Image Output tok/s | 109.8 | 125.0 | +13.9% |
| Image Mean TTFT (ms) | 182.55 | 179.90 | -1.5% |
| Image Mean TPOT (ms) | 8.62 | 7.57 | -12.2% |

### Throughput

concurrency=100, 1000 prompts

| Metric | triton | trtllm_mha | Delta |
|---|---:|---:|---:|
| Text Duration (s) | 144.45 | 117.92 | -18.4% |
| Text Req/s | 6.92 | 8.48 | +22.5% |
| Text Output tok/s | 3536.6 | 4332.3 | +22.5% |
| Text Total tok/s | 7086.9 | 8681.5 | +22.5% |
| Text Mean E2E (ms) | 13794 | 11221 | -18.7% |
| Text Mean TPOT (ms) | 27.02 | 21.88 | -19.0% |
| Text P99 TPOT (ms) | 37.47 | 29.89 | -20.2% |
| Image Successful | 1000 | 999 | -1 req |
| Image Duration (s) | 249.45 | 228.88 | -8.2% |
| Image Req/s | 4.01 | 4.36 | +8.7% |
| Image Output tok/s | 2048.0 | 2231.6 | +9.0% |
| Image Mean E2E (ms) | 24286 | 22351 | -8.0% |
| Image Mean TPOT (ms) | 46.02 | 42.10 | -8.5% |
| Image Mean TTFT (ms) | 1270.5 | 1317.7 | +3.7% |

## Test

```bash
python3 -c "compile(open('python/sglang/srt/server_args.py').read(), 'python/sglang/srt/server_args.py', 'exec')"
```
