---
source_id: sglang-github-closed-issues-prs
title: '[Bug] multi-tokenizer mode startup error.'
canonical_url: https://github.com/sgl-project/sglang/issues/29878
captured_at: '2026-07-05T02:14:10.232157+00:00'
content_hash: d85beb6475915d2c680a81a68f30be4c86f85f5f936ed6f80b66f23bec5e5a41
---
# [Bug] multi-tokenizer mode startup error.

URL: https://github.com/sgl-project/sglang/issues/29878
State: closed
Labels: high priority, GLM
Closed at: 2026-07-04T19:09:43Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

<img width="1042" height="768" alt="Image" src="https://github.com/user-attachments/assets/1ede2b04-1019-43d5-b922-cfca0e1e346d" />
introduced by #29214
CC @merrymercy 

### Reproduction

```
python -m sglang.launch_server --model-path /work/models/ --port 30000 --trust-remote --host 0.0.0.0 --served-model-name xdeepseekv3testbo --watchdog-timeout 300 --enable-cache-report --max-running-requests 512 --collect-tokens-histogram --chunked-prefill-size 16384 --tp 8 --pp-size 4 --context-length 1048576 --disable-radix-cache --mem-fraction-static 0.85 --max-total-tokens 1200000 --page-size 64 --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3 --enable-nsa-prefill-context-parallel --dp-size 1 --moe-dense-tp-size 1 --nsa-prefill-cp-mode round-robin-split --tool-call-parser glm47 --allow-auto-truncate --reasoning-parser glm45 --kv-cache-dtype fp8_e4m3 --disable-cuda-graph --enable-metrics --tokenizer-worker-num 8 --disaggregation-mode prefill --disaggregation-bootstrap-port 8998 --nnodes 4 --dist-init-addr glm52-test-pp4-prefill-0.glm52-test-pp4-prefill.aiservice:20102 --node-rank 0
```

### Environment

H20 GLM52
