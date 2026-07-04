---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [DO NOT MERGE] ci: test AMD PR workflow on MI300 shadow runners (Cirrascale
  Austin)'
canonical_url: https://github.com/sgl-project/sglang/pull/28605
captured_at: '2026-07-04T02:13:49.136823+00:00'
content_hash: ba4733a265ec1eb71761849d379dd92c9e30bb2f1fb1dd2c7613b42539c4f076
---
# [AMD] [DO NOT MERGE] ci: test AMD PR workflow on MI300 shadow runners (Cirrascale Austin)

URL: https://github.com/sgl-project/sglang/pull/28605
State: closed
Labels: amd
Closed at: 2026-07-03T07:15:47Z
Merged at: 

## Summary
Based on #28584. Re-routes the AMD PR test workflow GPU jobs to the new Cirrascale Austin (`ccs-aus-csp-bm-pvt-prd`) MI300 shadow runner labels, and folds in the per-runner perf-snapshot diagnostic from #26434 to characterize them under real CI load:
- 1-GPU jobs -> `linux-sglang-mi300-1gpu.test`
- 2-GPU jobs -> `linux-sglang-mi300-2gpu.test`
- 4-GPU and 8-GPU jobs -> `linux-sglang-mi300-8gpu.test`

This PR is for shadow-runner validation only (**do not merge**).

---

## MI300 shadow-runner validation (Cirrascale Austin · `ccs-aus-csp-bm-pvt-prd`)

Validation of the new MI300 shadow runner labels using the per-runner perf-snapshot method from #26434 (`scripts/ci/amd/diagnose_runner_perf.sh`, emitted host-side from `ensure_vram_clear.sh` and in-container from `amd_ci_start_container.sh`). This branch = #28584's runner-label rewiring + #26434's diagnostic, dispatched across all three tiers.

**Result: full green.** Run [27735530050](https://github.com/sgl-project/sglang/actions/runs/27735530050) — every targeted job passed on the new runners. `stage-c-test-4-gpu` (which timed out on the earlier #28584 run) passed here, confirming that earlier failure was test duration/content, not the runner.

### Per-run step timings

| Tier | Runner label | Job | Start CI container | Install deps | Run test | Result |
| ---- | ------------ | --- | ------------------ | ------------ | -------- | ------ |
| 1-GPU | `linux-sglang-mi300-1gpu.test` | sgl-kernel-unit-test-amd | **5.9m** | **2.4m** | **3.7m** | ✅ |
| 1-GPU | `linux-sglang-mi300-1gpu.test` | stage-a-test-1-gpu-small-amd | **5.9m** | **2.7m** | **10.5m** | ✅ |
| 2-GPU | `linux-sglang-mi300-2gpu.test` | sgl-kernel-unit-test-2-gpu-amd | **5.8m** | **2.4m** | **0.7m** | ✅ |
| 8-GPU | `linux-sglang-mi300-8gpu.test` | stage-c-test-4-gpu-amd | **5.7m** | **2.4m** | **20.1m** | ✅ |

`Start CI container` is a consistent **~5.8m** Docker-Hub pull (no LAN-registry cache hit, no warm image), versus **17–32m** on the old MI300 pool documented in #26434 — i.e. this cluster does not exhibit the cliff that motivated #26434.

### Per-host `[runner-perf-diag]` snapshot (one host per tier)

| Metric | `1gpu.test` | `2gpu.test` | `8gpu.test` |
| ------ | ----------- | ----------- | ----------- |
| host | `…1gpu.test-gbfkh-runner-b4mhx` | `…2gpu.test-ncf5g-runner-22bqg` | `…8gpu.test-l6948-runner-nt9kv` |
| CPU | AMD EPYC 9454 (192 thr) | AMD EPYC 9454 (192 thr) | AMD EPYC 9454 (192 thr) |
| RAM | ~2.32 TiB | ~2.32 TiB | ~2.32 TiB |
| loadavg (1m) | 2.34 | 4.02 | 0.33 |
| GPUs visible (`rocm-smi`) | 1 | 2 | 8 |
| disk `dd` 256 MiB fsync (`/tmp`) | 579 MB/s | 573 MB/s | 587 MB/s |
| `tcp_congestion_control` | **cubic** | **cubic** | **cubic** |
| `tcp_rmem` / `tcp_wmem` max | **16 MiB / 16 MiB** | **16 MiB / 16 MiB** | **16 MiB / 16 MiB** |
| `http_sample` throughput (host) | 12.4 MB/s | 14.9 MB/s | 15.8 MB/s |
| `http_sample` throughput (in-container) | 14.3 MB/s | — | — |
| LAN registry `10.245.143.50:5000` | unreachable (conn reset) | unreachable | unreachable |
| `sgl-data` bind-mount (in-container) | **MISSING** | **MISSING** | **MISSING** |

GPU state via `rocm-smi` is healthy on every tier (junction ~48–50 °C, perf level `auto`, ~140 W idle); RCCL multi-GPU collectives passed on the 8-GPU node.

### Comparison vs #26434 baselines

| Metric | New MI300 (Austin `.test`) | Old MI300 (#26434) | MI325 (#26434) |
| ------ | -------------------------- | ------------------ | -------------- |
| CPU | AMD EPYC 9454 | Intel Xeon Platinum 8570 | AMD EPYC 9534/9575F |
| `tcp_congestion_control` | **cubic** | cubic | **bbr** |
| `tcp_rmem` max | **16 MiB** | 6 MiB | 16 MiB |
| `tcp_wmem` max | **16 MiB** | 4 MiB | 16 MiB |
| `http_sample` (5 MiB, diag) | 12–16 MB/s | 9.0 MB/s | 17.9 MB/s |
| `Start CI container` | **~5.8 min** | 17–32 min | ~7.7 min |
| loadavg (1m) | 0.3 – 4 | 8.8 – 2974 | ~20 |
| LAN docker registry | unreachable | reachable (≈2 ms) | unreachable |

### Findings

1. **Runners are healthy and production-shaped.** All three tiers pick up jobs, start containers, install deps, expose the right GPU count, and pass real suites (sgl-kernel 1-/2-GPU, stage-a, stage-c-4-GPU). Host hardware (EPYC 9454, ~2.3 TiB RAM, low loadavg, ~580 MB/s fsync disk) is a clear step up from the old MI300 pool.
2. **TCP congestion control is `cubic`, not `bbr`.** Socket buffers are already healthy (16 MiB rmem/wmem max — matching MI325 and unlike the old MI300's 6/4 MiB), so throughput (~12–16 MB/s) sits between old MI300 (~9) and MI325 (~18). Switching to `bbr` should recover most of the remaining gap on high-BDP CDN paths (HF / PyPI / Docker Hub / S3).
3. **No persistent cache bind-mount.** `/home/runner/sglang-data` is missing on the host and `sgl_data_mount=MISSING` in-container, so HF / pip / MIOPEN caches land in the container layer and every job re-downloads at ~12–16 MB/s. A persistent `sglang-data` (hf-cache + pip-cache) bind-mount would cut per-job setup time.
4. **SGLang LAN registry `10.245.143.50:5000` is unreachable from Austin** (expected — different DC), so image pulls go to Docker Hub. TLS/TTFB to Docker Hub is fast (~80–230 ms) so the ~5.8m pull is fine today; if pull time becomes a concern, mirror the ROCm CI images to a registry reachable from this cluster.

### Recommendations (runner-pool infra)

1. Set `net.ipv4.tcp_congestion_control=bbr` on the MI300 host kernels (buffers are already at 16 MiB).
2. Bind-mount a persistent `/home/runner/sglang-data` (hf-cache + pip-cache) on every MI300 host.
3. (Optional) Mirror AMD CI docker images to a registry reachable from the Austin cluster.

## Test plan
- Dispatch `pr-test-amd.yml` on this branch across all three runner tiers and confirm jobs are picked up, containers start, and tests execute. ✅ (run 27735530050, all green)
- Classify any failures as runner/infra vs. test content. ✅ (no infra failures)





















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28210886414](https://github.com/sgl-project/sglang/actions/runs/28210886414)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28210886304](https://github.com/sgl-project/sglang/actions/runs/28210886304)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
