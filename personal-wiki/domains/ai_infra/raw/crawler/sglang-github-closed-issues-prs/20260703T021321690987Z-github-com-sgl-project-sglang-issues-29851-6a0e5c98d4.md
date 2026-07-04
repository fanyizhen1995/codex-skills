---
source_id: sglang-github-closed-issues-prs
title: '[Bug] AssertionError:, model load glm5.2 startup error'
canonical_url: https://github.com/sgl-project/sglang/issues/29851
captured_at: '2026-07-03T02:13:21.690987+00:00'
content_hash: 6a0e5c98d461aced07d217397ffb1fd06fbe76e55d85613c697b4b10cc6853ee
---
# [Bug] AssertionError:, model load glm5.2 startup error

URL: https://github.com/sgl-project/sglang/issues/29851
State: closed
Labels: 
Closed at: 2026-07-02T08:06:25Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

<img width="1541" height="756" alt="Image" src="https://github.com/user-attachments/assets/890c5da0-7e53-42ba-a2ef-5c88640acc06" />

### Reproduction

```
python -m sglang.launch_server --model-path /work/models/ --port 30000 --trust-remote --host 0.0.0.0 --served-model-name xdeepseekv3testbo --watchdog-timeout 300 --enable-cache-report --max-running-requests 512 --collect-tokens-histogram --chunked-prefill-size 16384 --tp 8 --pp-size 4 --context-length 1048576 --disable-radix-cache --mem-fraction-static 0.85 --max-total-tokens 1200000 --page-size 64 --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3 --enable-nsa-prefill-context-parallel --dp-size 1 --moe-dense-tp-size 1 --nsa-prefill-cp-mode round-robin-split --tool-call-parser glm47 --allow-auto-truncate --reasoning-parser glm45 --kv-cache-dtype fp8_e4m3 --disable-cuda-graph --enable-metrics --tokenizer-worker-num 8 --disaggregation-mode prefill --disaggregation-bootstrap-port 8998 --nnodes 4 --dist-init-addr glm52-test-pp4-prefill-0.glm52-test-pp4-prefill.aiservice:20102 --node-rank 0```

### Environment

H20
