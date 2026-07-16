---
source_id: sglang-github-closed-issues-prs
title: '[DO NOT MERGE] Reproduction scripts'
canonical_url: https://github.com/sgl-project/sglang/pull/30851
captured_at: '2026-07-11T23:37:37.769996+00:00'
content_hash: e8a57573f5029424173962f226f52dd35263fe455dd5fbbdea4cb0f040f6aac2
---
# [DO NOT MERGE] Reproduction scripts

URL: https://github.com/sgl-project/sglang/pull/30851
State: closed
Labels: documentation
Closed at: 2026-07-11T09:18:44Z
Merged at: 

**Do not merge** — this is a companion branch for the GLM NVFP4 GB300/B300 blog post so readers can reproduce its two figures. Everything lives under `benchmark/glm_nvfp4_blog/`; no SGLang source is touched. The only dependencies are SGLang (this branch, based on `release/v0.5.15`) and [evalscope](https://github.com/modelscope/evalscope) pinned by commit as the benchmark client.

### The two figures

| Main figure | ISL ablation |
|---|---|
| ![main](https://raw.githubusercontent.com/Jiminator/sglang/glm-nvfp4-blog-repro/benchmark/glm_nvfp4_blog/expected_main_figure.png) | ![isl](https://raw.githubusercontent.com/Jiminator/sglang/glm-nvfp4-blog-repro/benchmark/glm_nvfp4_blog/isl_ablation/expected_isl_ablation.png) |

**Workload**: OpenHands multi-turn agentic replay — ~80k mean input tokens/request, 220 output tokens/turn, 13 turns/conversation, ~92% aggregate prefix-cache hit, real EAGLE (5/1/6) speculative acceptance. Datasets are built deterministically from public HF datasets (`nebius/SWE-rebench-openhands-trajectories` padded with `nvidia/OpenScienceReasoning-2`).

**Hardware**: one 4×GB300 node (top row / ISL ablation) and/or one 8×B300 node (bottom row) — the rows are independent.

### Setup (once)

```bash
git clone -b glm-nvfp4-blog-repro https://github.com/Jiminator/sglang.git && cd sglang
# install SGLang from this branch as usual, then:
cd benchmark/glm_nvfp4_blog
evalscope-deps/scripts/install_evalscope_deps.sh   # evalscope deps without downgrading any pin
PIP_NO_DEPS=1 pip install "evalscope[all] @ git+https://github.com/modelscope/evalscope.git@acd09b44384d53174768bb1063f675420f76fae9"

# day-0 curves only: the GLM-5.2 launch-day tree (public glm-opt branch)
git -C ../.. fetch origin glm-opt
git -C ../.. worktree add ../sglang-day0 22dce572045c277ce46f1a287c4be1112b214368
export DAY0_SGLANG=$(cd ../../../sglang-day0 && pwd)
```

### Main figure (one curve = one server script + one client call)

Start a server script, run the shared client, stop the server, repeat — ~15–30 min each:

```bash
# example: GB300, GLM-5.2 on v0.5.15, both parallelism panels
gb300/server_glm52_v0515_tp4.sh &        # terminal 1 (fused top-k v2 + deferred MoE finalize ON)
./run_client.sh nvidia/GLM-5.2-NVFP4 results/gb300/glm52_v0515 tp4    # terminal 2
# ... stop server, then the TEP panel:
gb300/server_glm52_v0515_tep4.sh &
./run_client.sh nvidia/GLM-5.2-NVFP4 results/gb300/glm52_v0515 tep4
```

The full 12-run matrix (script ↔ output path) is in `benchmark/glm_nvfp4_blog/README.md`. The client builds the dataset on first use (cached), waits for `/health`, and runs concurrency 1→8 in one evalscope invocation (offset rotation keeps every step on fresh conversations). Then:

```bash
python3 plot_main_figure.py     # -> main_figure.png (plots whichever curves exist)
```

### ISL ablation (GB300)

```bash
cd isl_ablation
./run_isl_client.sh v0515       # 80K -> 1M context ladder, c=1, ~2-3 h (first run builds datasets)
./run_isl_client.sh day0        # needs DAY0_SGLANG
python3 plot_isl_figure.py      # -> isl_ablation.png
```

The driver boots its own server per rung — only the dataset first-turn budget and `--context-length` change between rungs.

### Notes

- Expect ~±2–4% run-to-run variance per point (widest at c=1): match the expected figures in shape and ordering, not to the pixel. The ~92% cache-hit and ~5.0 acceptance-length invariants in `benchmark_summary.json` confirm a faithful replay.
- Day-0 servers intentionally use launch-day flags (no `--bf16-gemm-backend`, no fused top-k / deferred-finalize env vars, `--cuda-graph-max-bs` spelling) — that's the point of the curve.
- On a fresh machine, run any one pair once as a throwaway JIT warm-up (compiled-kernel caches persist on disk).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29146575778](https://github.com/sgl-project/sglang/actions/runs/29146575778)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29146575653](https://github.com/sgl-project/sglang/actions/runs/29146575653)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
