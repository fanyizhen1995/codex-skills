---
source_id: sglang-github-closed-issues-prs
title: '[cookbook] GLM-5.2 NVFP4 B300: TP8 recipe + 3 strategies'
canonical_url: https://github.com/sgl-project/sglang/pull/29557
captured_at: '2026-07-01T02:12:08.974399+00:00'
content_hash: 19a8e6e3be4380c6252e79c6d202cfc526309649d93ffd751d4b9856ed93ae4a
---
# [cookbook] GLM-5.2 NVFP4 B300: TP8 recipe + 3 strategies

URL: https://github.com/sgl-project/sglang/pull/29557
State: closed
Labels: documentation
Closed at: 2026-06-29T21:42:20Z
Merged at: 2026-06-29T21:42:20Z

## Motivation

Update the GLM-5.2 **NVFP4 B300** cookbook entries. They previously shipped the TP4 layout with only `low-latency` + `balanced`. Replace them with the verified single-node **8×B300 TP8** recipe and add the missing `high-throughput` strategy, all measured on the `lmsysorg/sglang:dev-glm52-nvfp4` preview image.

## Changes

`docs_new/src/snippets/configs/zai-org/glm-5.2.jsx` — B300 NVFP4 cells:

- **low-latency** — `tp4 → tp8`, `mem-fraction-static 0.8 → 0.85`, keep full MTP 5-1-6
- **balanced** — `tp8 + dp8 + --enable-dp-attention`, shorter MTP 2-1-3, plus the two flags this path requires: `--speculative-attention-mode decode` (avoids a CUDA-graph capture deadlock) and `--max-running-requests 256` (lifts the default ~48-request throttle so DP-Attention can fill all 8 ranks)
- **high-throughput** (new) — `tp8 + dp8 + --enable-dp-attention`, no MTP, `--max-running-requests 1024`

`docs_new/src/snippets/configs/zai-org/glm-5.2-benchmarks.jsx` — fill the matching speed numbers for all three strategies. `tokens_per_sec_per_gpu = total output tok/s ÷ 8 GPUs`. `aime25` overrides to 89.58 on the NVFP4 build (same checkpoint as the GB300 NVFP4 entries); gsm8k inherits the variant default.

| strategy | conc | tok/s/gpu | TTFT | TPOT |
|---|---|---|---|---|
| low-latency | 1 / 16 | 51 / 224 | 196 / 274 ms | 1.86 / 6.95 ms |
| balanced | 64 / 256 | 153 / 205 | 680 / 3010 ms | 48.9 / 149 ms |
| high-throughput | 1024 | 430 | 6370 ms | 280 ms |

## Checklist

- Docs/cookbook-only change; both JSX configs validated via `node --check` + module import.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28402970621](https://github.com/sgl-project/sglang/actions/runs/28402970621)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28402970448](https://github.com/sgl-project/sglang/actions/runs/28402970448)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
