---
source_id: sglang-github-closed-issues-prs
title: '[AMD][DI][CI] 3/N Add Kimi K2.6 FP8 MI355X 1P1D nightly recipes'
canonical_url: https://github.com/sgl-project/sglang/pull/29855
captured_at: '2026-07-06T02:14:53.066050+00:00'
content_hash: 758beadbe8ed6ddc7d93f0ec56cb8e1f66e522319f4c06d27073eb3038840996
---
# [AMD][DI][CI] 3/N Add Kimi K2.6 FP8 MI355X 1P1D nightly recipes

URL: https://github.com/sgl-project/sglang/pull/29855
State: closed
Labels: 
Closed at: 2026-07-05T04:05:13Z
Merged at: 2026-07-05T04:05:12Z

## Summary
Add **Kimi K2.6 (FP8)** 2-node 1P1D disaggregation coverage to the MI355X nightly, with base + EAGLE3 MTP legs (validated end-to-end on real hardware, g09/g29).

This is intentionally **minimal and additive** — it does **not** change the common/NV path:
- **`scripts/ci/slurm/process_result.py` is untouched.** It stays on `yaml.safe_load`; the flat Kimi recipes expose `resources` / `backend.sglang_config` directly, so the summary table reads them with zero common-path change. No `recipe_utils.py`, no `extends:` inheritance.
- **`scripts/ci/slurm/launch_mi355x.sh`** gains a small, gated model path. A recipe may carry an optional `model:` block (docker `-e` env + sglang server args); the launcher writes it to `WORKDIR/model_flags.sh` as `MODEL_ENV_ARGS` / `MODEL_SERVER_ARGS` bash arrays (via `shlex.quote`) and sources it in prefill/decode. It also supports split prefill/decode attention backends, an optional `--swa-full-tokens-ratio`, and an external speculative draft checkpoint (EAGLE3). Recipes **without** a `model:` block (all DSV4) keep the existing hardcoded path — their generated `docker run` argv is **byte-identical** to before.
- **Kimi K2.6** recipes added under `recipes/mi355x-fp8/kimik26/1k1k/` (base + `-mtp`, both flat/self-contained), plus two `nightly-configs.yaml` blocks. Kimi uses split attention (prefill aiter / decode triton), `kimi_k2` parsers, `enable_multithread_load`, and an external EAGLE3 draft for the MTP leg — all expressed purely in the recipe YAML.

## Validation (MI355X g09/g29)
- Kimi base (TP8): GSM8K **0.941**, full sweep conc 1→256 clean.
- Kimi -mtp (EAGLE3 external draft): GSM8K **0.948**, incl. conc256.
- DSV4 `docker run` argv confirmed byte-identical old vs new launcher (base / -mtp / -dp8ep8).

## Notes
- Kimi `-dp8ep8` is intentionally excluded: it hits a GPU memory access fault at PD warmup under DP-attention dp8+EP8 (aiter MLA / int4-MoE path) — a model/kernel bug, not a launcher issue. Base + MTP cover Kimi functionally.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28534403432](https://github.com/sgl-project/sglang/actions/runs/28534403432)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28534403321](https://github.com/sgl-project/sglang/actions/runs/28534403321)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
