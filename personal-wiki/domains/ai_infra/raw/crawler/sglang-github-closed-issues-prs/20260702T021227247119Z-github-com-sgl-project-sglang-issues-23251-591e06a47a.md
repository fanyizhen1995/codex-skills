---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Missing module in tuning_fused_moe_triton'
canonical_url: https://github.com/sgl-project/sglang/issues/23251
captured_at: '2026-07-02T02:12:27.247119+00:00'
content_hash: 591e06a47ab2cd1cd7a22b6cb67eb25c5e4b5b18b44083a311306c3e9444dcb3
---
# [Bug] Missing module in tuning_fused_moe_triton

URL: https://github.com/sgl-project/sglang/issues/23251
State: closed
Labels: inactive
Closed at: 2026-07-02T00:48:14Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

It seems that one of the module required for MoE optimization is missing:[benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py](https://github.com/sgl-project/sglang/tree/main/benchmark/kernels/fused_moe_triton)

```bash
python benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py \
    --model zai-org/GLM-4.7 \
    --tp-size 2 \
    --dtype fp16 \
    —tune
Traceback (most recent call last):
  File "/home/jovyan/ipetrov/code/cluster/sglang/benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py", line 11, in <module>
    from common_utils import (
  File "/home/jovyan/ipetrov/code/cluster/sglang/benchmark/kernels/fused_moe_triton/common_utils.py", line 6, in <module>
    from sglang.srt.layers.moe.moe_runner.triton_utils.fused_moe import get_config_dtype_str
ModuleNotFoundError: No module named 'sglang.srt.layers.moe.moe_runner.triton_utils'
(ipetrov_sglang2) ➜  sglang git:(main) which sglang pip
```


**Background**

I was inferencing GLM-4.7 and during the run the warning appeared:
```
[2026-04-20 10:14:11 TP10] Using default MoE kernel config. Performance might be sub-optimal! Config file not found at /home/jovyan/.mlspace/envs/ipetrov_sglang2/lib/python3.12/site-packages/sglang/srt/layers/moe/fused_moe_triton/configs/triton_3_5_1/E=161,N=96,device_name=NVIDIA_H100_80GB_HBM3.json, you can create them with https://github.com/sgl-project/sglang/tree/main/benchmark/kernels/fused_moe_triton
```

So I am trying to fis this warning by following the guide, but unable to run the script. [benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py](https://github.com/sgl-project/sglang/tree/main/benchmark/kernels/fused_moe_triton).



### Reproduction

Run following snippet:
```bash
python benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py \
    --model zai-org/GLM-4.7 \
    --tp-size 2 \
    --dtype fp16 \
    —tune
```

### Environment

Name: sglang Version: 0.5.10.post1
Name: triton Version: 3.5.1
Name: torch Version: 2.9.1
