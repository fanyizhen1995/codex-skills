---
source_id: sglang-github-closed-issues-prs
title: Use Marlin for SM120 MXFP4 MoE
canonical_url: https://github.com/sgl-project/sglang/pull/28231
captured_at: '2026-07-14T23:40:21.671927+00:00'
content_hash: 2e0d2bbf5554f4e0e0425f089a876d3b442a57e494a053d8914e41fa52752769
---
# Use Marlin for SM120 MXFP4 MoE

URL: https://github.com/sgl-project/sglang/pull/28231
State: closed
Labels: run-ci
Closed at: 2026-06-19T02:19:42Z
Merged at: 2026-06-19T02:19:42Z

## Summary

Implement MXFP4 Marlin MoE for GPT-OSS and make `marlin` the default GPT-OSS MXFP4 MoE backend on SM120.

With GPT-OSS MXFP4 now covered by `marlin` on SM120, there is no longer a reason to keep the SM120-specific GPT-OSS `triton_kernel` path, especially since `triton_kernels` is mainly developed for data center GPU targets and is not expected to be the right long-term path for this SM120 use case, as mentioned [here](https://github.com/sgl-project/sglang/issues/19637#issuecomment-4700599414). Remove that path and delete the DSV4 SM120 MXFP4 Triton fallback file.

## Per-Request Throughput

<img width="1800" height="1040" alt="gpt_oss_sm120_marlin_benchmark" src="https://github.com/user-attachments/assets/10a6ecaa-d67d-4fa2-9012-ff31cf5596a6" />


## GPQA

```text
python -m gpt_oss.evals \
  --model openai/gpt-oss-20b \
  --eval gpqa \
  --n-threads 256 \
  --reasoning-effort low \
  --base-url http://127.0.0.1:30000/v1

[{'eval_name': 'gpqa', 'model_name': 'openai__gpt-oss-20b-low_temp1.0_20260614_065126', 'metric': 0.5871212121212122}]
```

## Raw Serving Data

```bash
for CONC in 1 2 4 8 16 32 64 128 256; do
  python -m sglang.bench_serving \
    --model openai/gpt-oss-20b \
    --dataset-name random \
    --random-input-len 512 \
    --random-output-len 512 \
    --max-concurrency "$CONC" \
    --num-prompts "$((CONC * 8))" \
    --random-range-ratio 1.0
done
```

### `marlin`

| Concurrency | Output tok/s | Total tok/s | Mean E2E ms | Mean TTFT ms | Mean TPOT ms | Mean ITL ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 214.52 | 429.04 | 2384.34 | 29.97 | 4.61 | 4.61 |
| 2 | 367.80 | 735.60 | 2781.27 | 34.83 | 5.37 | 5.37 |
| 4 | 587.77 | 1175.54 | 3481.23 | 46.18 | 6.72 | 6.72 |
| 8 | 952.56 | 1905.12 | 4296.10 | 89.24 | 8.23 | 8.23 |
| 16 | 1591.42 | 3182.85 | 5142.81 | 119.28 | 9.83 | 9.83 |
| 32 | 2626.09 | 5252.17 | 6229.54 | 205.76 | 11.79 | 11.79 |
| 64 | 4585.39 | 9170.78 | 7133.93 | 337.83 | 13.30 | 13.30 |
| 128 | 7416.35 | 14832.69 | 8820.49 | 626.45 | 16.04 | 16.04 |
| 256 | 11660.38 | 23320.77 | 11126.64 | 564.45 | 20.67 | 20.67 |

### `triton_kernel` baseline

| Concurrency | Output tok/s | Total tok/s | Mean E2E ms | Mean TTFT ms | Mean TPOT ms | Mean ITL ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 149.81 | 299.62 | 3415.36 | 54.40 | 6.58 | 6.58 |
| 2 | 282.69 | 565.38 | 3619.09 | 59.92 | 6.97 | 6.97 |
| 4 | 476.85 | 953.71 | 4290.86 | 82.70 | 8.24 | 8.24 |
| 8 | 737.00 | 1474.01 | 5553.42 | 136.71 | 10.60 | 10.60 |
| 16 | 1313.57 | 2627.14 | 6231.66 | 196.67 | 11.81 | 11.81 |
| 32 | 2317.11 | 4634.22 | 7061.52 | 335.01 | 13.16 | 13.16 |
| 64 | 3703.31 | 7406.62 | 8834.33 | 541.86 | 16.23 | 16.23 |
| 128 | 2326.95 | 4653.89 | 28138.97 | 1024.50 | 53.06 | 53.06 |
| 256 | 4263.94 | 8527.89 | 30677.79 | 858.16 | 58.36 | 58.36 |

## DSV4 Flash

Also checked it on SM120 after these changes.

- GSM8K 200 examples: `0.97`
- Concurrency 1 output throughput: `11.22 tok/s` (I was surprised it was this low, but this seems to be the actual speed because main is around the same.)













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #27521933633](https://github.com/sgl-project/sglang/actions/runs/27521933633)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27521933575](https://github.com/sgl-project/sglang/actions/runs/27521933575)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
