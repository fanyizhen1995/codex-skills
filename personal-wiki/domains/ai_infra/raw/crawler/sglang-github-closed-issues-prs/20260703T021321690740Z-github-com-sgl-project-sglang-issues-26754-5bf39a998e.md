---
source_id: sglang-github-closed-issues-prs
title: '[Bug] ValueError: deepseek_v4_c4_state state_pools must not contain None'
canonical_url: https://github.com/sgl-project/sglang/issues/26754
captured_at: '2026-07-03T02:13:21.690740+00:00'
content_hash: 5bf39a998ead2012110cb731e2821f105e5b107966e1fded2b94a3ab52b2c58d
---
# [Bug] ValueError: deepseek_v4_c4_state state_pools must not contain None

URL: https://github.com/sgl-project/sglang/issues/26754
State: closed
Labels: 
Closed at: 2026-07-02T08:07:43Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

<img width="1532" height="1003" alt="Image" src="https://github.com/user-attachments/assets/8318fd7d-3993-424f-9e4e-010c3d8deb82" />

### Reproduction

```
python -m sglang.launch_server --model-path /work/models/ --port 30000 --trust-remote --host 0.0.0.0 --served-model-name xdeepseekv3testbo --disable-cuda-graph --enable-cache-report --max-running-requests 512 --collect-tokens-histogram --chunked-prefill-size 8192 --pp-size 4 --tp-size 2 --context-length 1000000 --mem-fraction-static 0.88 --page-size 256 --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3 --tool-call-parser deepseekv4 --allow-auto-truncate --reasoning-parser deepseek-v4 --enable-nsa-prefill-context-parallel --nsa-prefill-cp-mode round-robin-split --enable-hierarchical-cache --hicache-ratio 4 --hicache-size 0 --hicache-write-policy write_through --hicache-io-backend direct --hicache-mem-layout page_first_direct --enable-metrics --disaggregation-mode prefill --disaggregation-bootstrap-port 8998 --nnodes 1 --dist-init-addr xopdsv4flashhw-testbo-prefill-0.xopdsv4flashhw-testbo-prefill.aiservice:20102 --node-rank 0
```

### Environment

H20 PP8
CC @hzh0425
