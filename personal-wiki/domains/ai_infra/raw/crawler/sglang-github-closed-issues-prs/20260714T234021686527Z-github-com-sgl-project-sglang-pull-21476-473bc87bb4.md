---
source_id: sglang-github-closed-issues-prs
title: '[Perf] Enable fused gated RMS norm kernel for n_groups > 1 on Mamba layers
  for Nemotron models'
canonical_url: https://github.com/sgl-project/sglang/pull/21476
captured_at: '2026-07-14T23:40:21.686527+00:00'
content_hash: 473bc87bb4e70695505e31a21692b14f5560153b4325bd8a6be0818bb366f95e
---
# [Perf] Enable fused gated RMS norm kernel for n_groups > 1 on Mamba layers for Nemotron models

URL: https://github.com/sgl-project/sglang/pull/21476
State: closed
Labels: 
Closed at: 2026-07-14T01:49:08Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation


`Mixer2RMSNormGate` currently only enable the fused `rms_norm_gated` kernel when n_groups is 1 - this is likely because support for higher n_groups wasn't supported until #16397. This affect the all of the NemotronH family of models that uses Mamba layers.


## Modifications

**`python/sglang/srt/layers/attention/mamba/mixer2_rms_norm_gated.py`**:
Remove `self.n_groups != 1` from the condition to fall back to native Pytorch implementation.
Added `group_size=self.group_size` to the input argument of the fused kernel.
 
## Accuracy Tests

NemotronH-Nano-9B-v2-FP8, GSM8K 5-shot, 200 questions:

  | | Accuracy | Threshold |
  |---|---|---|
  | Baseline (unfused) | 90.5% | 85% |
  | Fused | 89.0% | 85% |

## Benchmarking and Profiling

NemotronH-Nano-9B-v2-FP8 on RTX 4090, GSM8K 200 questions, `--max-running-requests 16`:

  ### End-to-end

  | Metric | Baseline | Fused | Change |
  |---|---|---|---|
  | Latency | 87.2s | 75.7s | **-13.2%** |
  | Throughput | 276.6 tok/s | 314.2 tok/s | **+13.6%** |

  ### Nsys kernel breakdown

  | Category | Baseline | Fused | Delta |
  |---|---|---|---|
  | GEMM | 59.45s | 57.57s | -1.88s (-3%) |
  | CPU (non-GPU idle) | 13.90s | 8.00s | **-5.90s (-42%)** |
  | elementwise | 3.18s | 0.88s | **-2.30s (-72%)** |
  | reduce | 0.48s | 0.04s | **-0.44s (-92%)** |
  | norm | 0.80s | 1.07s | +0.27s |
  | **Total** | **86.99s** | **76.04s** | **-10.94s (-13%)** |

Note that at the moment of tests NemotronH models cannot enable PCG by default, but as I understand the whole Mamba layer would be split op in PCG so in principle PCG shouldn't affect this.

## Checklist

  - [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/develope
  r_guide/contribution_guide.html#format-code-with-pre-commit).
  - [ ] Add unit tests according to the [Run and add unit
  tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
  - [ ] Update documentation according to [Write
  documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
  - [x] Provide accuracy and speed benchmark results according to [Test the
  accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and
  [Benchmark the
  speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
  - [x] Follow the SGLang code style
  [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).
