---
source_id: sglang-github-closed-issues-prs
title: Add fused EH norm for DeepSeek NextN
canonical_url: https://github.com/sgl-project/sglang/pull/29667
captured_at: '2026-07-02T02:12:27.261610+00:00'
content_hash: ad7b2a359abef09ebc99f48661d84f16d4f56e49c1ec82fd593f4bd825ba11b6
---
# Add fused EH norm for DeepSeek NextN

URL: https://github.com/sgl-project/sglang/pull/29667
State: closed
Labels: deepseek, run-ci, jit-kernel
Closed at: 2026-07-01T09:46:22Z
Merged at: 2026-07-01T09:46:22Z

## Summary

### Before

<img width="1632" height="422" alt="image (1)" src="https://github.com/user-attachments/assets/20510752-c6b3-4380-a6fa-27ded587bf43" />

### After

<img width="1635" height="487" alt="image (2)" src="https://github.com/user-attachments/assets/f368dcd4-d217-46c0-885d-f30c285eda38" />

## Tests

```bash
python test/registered/jit/benchmark/bench_fused_eh_norm.py

=============================================================================================================
             dtype  hidden_size  num_tokens |         jit(us)      torch(us) |       jit(GB/s)    torch(GB/s)
-------------------------------------------------------------------------------------------------------------
0   torch.bfloat16         6144           1 |          3.2973        43.4586 |           20.82           1.58
1   torch.bfloat16         6144           4 |          3.4000        50.3811 |           60.59           4.09
2   torch.bfloat16         6144           6 |          3.3795        50.8522 |           88.04           5.85
3   torch.bfloat16         6144           8 |          3.4205        56.5965 |          113.76           6.87
4   torch.bfloat16         6144          16 |          3.4614        69.7859 |          218.21          10.82
5   torch.bfloat16         6144          32 |          3.6048        70.1133 |          412.71          21.22
6   torch.bfloat16         6144         128 |          3.7683        76.4621 |         1560.98          76.93
7   torch.bfloat16         6144         512 |          7.0732       115.3896 |         3316.81         203.31
8   torch.bfloat16         7168           1 |          3.4205        43.7046 |           23.42           1.83
9   torch.bfloat16         7168           4 |          3.4819        51.2208 |           69.02           4.69
10  torch.bfloat16         7168           6 |          3.5024        52.3267 |           99.11           6.63
11  torch.bfloat16         7168           8 |          3.5434        59.4947 |          128.11           7.63
12  torch.bfloat16         7168          16 |          3.5843        75.0902 |          245.85          11.74
13  torch.bfloat16         7168          32 |          3.7270        75.6326 |          465.70          22.95
14  torch.bfloat16         7168         128 |          3.8707        83.7632 |         1772.96          81.93
15  torch.bfloat16         7168         512 |          7.5093       130.0698 |         3644.86         210.43
16   torch.float16         6144           1 |          3.3181        43.1107 |           20.69           1.59
17   torch.float16         6144           4 |          3.4000        49.8893 |           60.59           4.13
18   torch.float16         6144           6 |          3.4202        50.5654 |           87.00           5.88
19   torch.float16         6144           8 |          3.4410        56.2074 |          113.08           6.92
20   torch.float16         6144          16 |          3.4819        69.5507 |          216.92          10.86
21   torch.float16         6144          32 |          3.6045        69.7648 |          412.75          21.32
22   torch.float16         6144         128 |          3.7888        76.2163 |         1552.54          77.18
23   torch.float16         6144         512 |          7.0921       115.2569 |         3307.94         203.55
24   torch.float16         7168           1 |          3.4410        43.4384 |           23.28           1.84
25   torch.float16         7168           4 |          3.5021        50.9238 |           68.62           4.72
26   torch.float16         7168           6 |          3.5434        52.0291 |           97.97           6.67
27   torch.float16         7168           8 |          3.5638        59.1670 |          127.38           7.67
28   torch.float16         7168          16 |          3.6253        74.7830 |          243.07          11.78
29   torch.float16         7168          32 |          3.7683        75.2947 |          460.60          23.05
30   torch.float16         7168         128 |          3.9120        83.5379 |         1754.25          82.15
31   torch.float16         7168         512 |          7.5384       129.6045 |         3630.81         211.18
=============================================================================================================
```

```bash
pytest -q test/registered/jit/test_fused_eh_norm.py

16 passed, 5 warnings in 5.54s
```

## Accuracy Test

- Benchmark: AIME 2025
- Model: `nvidia/GLM-5.2-NVFP4`
- Settings: 16 repeats, max tokens 64000, temperature 1.0, top-p 0.95

Result:

```text
pass@1[avg-of-16]: 90.00% +/- 3.22% (SEM 0.81%)
```



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28414934410](https://github.com/sgl-project/sglang/actions/runs/28414934410)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28414934306](https://github.com/sgl-project/sglang/actions/runs/28414934306)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
