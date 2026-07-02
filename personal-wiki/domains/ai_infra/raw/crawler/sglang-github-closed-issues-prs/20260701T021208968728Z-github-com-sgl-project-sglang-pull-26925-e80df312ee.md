---
source_id: sglang-github-closed-issues-prs
title: '[multimodal_gen] Allow --dit-cpu-offload with --dit-layerwise-offload'
canonical_url: https://github.com/sgl-project/sglang/pull/26925
captured_at: '2026-07-01T02:12:08.968728+00:00'
content_hash: e80df312ee91c109e9c25595c504b7e2888b24f80e48bdeacf8fe0a7441e1b74
---
# [multimodal_gen] Allow --dit-cpu-offload with --dit-layerwise-offload

URL: https://github.com/sgl-project/sglang/pull/26925
State: closed
Labels: run-ci, diffusion
Closed at: 2026-06-01T15:17:54Z
Merged at: 2026-06-01T15:17:54Z

# [multimodal_gen] Allow --dit-cpu-offload with --dit-layerwise-offload

## Motivation

When `--dit-layerwise-offload` is enabled (or `_adjust_offload` auto-sets `dit_cpu_offload=True` on low-VRAM cards), `ServerArgs` silently force-disables `dit_cpu_offload`. This breaks server startup on cards that cannot fit the full DiT on-device, because the loader materializes the entire transformer state dict to GPU **before** layerwise offload takes over at runtime — the model OOMs at load time.

Reproduced on RTX 5090 (32 GiB, 31.36 GiB usable) with `Qwen-Image-Edit-2509` (38.1 GiB DiT, bf16), both with and without a LoRA adapter:

| Configuration | LoRA | Result | Peak VRAM | OOMs |
| --- | --- | --- | --- | --- |
| `--dit-cpu-offload false --dit-layerwise-offload true` | yes | Fails (OOM during DiT load and again during native fallback) | 32073 MiB (ceiling) | 3 |
| `--dit-cpu-offload true  --dit-layerwise-offload true` | yes | Startup OK | 25499 MiB | 0 |
| `--dit-cpu-offload false --dit-layerwise-offload true` | no  | Fails (same path) | 32073 MiB | 3 |
| `--dit-cpu-offload true  --dit-layerwise-offload true` | no  | Startup OK | 29367 MiB peak / 24633 MiB steady | 0 |

The two flags are complementary, not mutually exclusive:

- `dit_cpu_offload` controls **initial residency** — DiT weights stay on host memory so the loader never tries to push the full model to GPU.
- `dit_layerwise_offload` controls **runtime H2D/D2H** — only the prefetched layers are brought on-device per denoising step.

The auto-disable was removing the only working combination on low-VRAM cards.

## Modifications

`python/sglang/multimodal_gen/runtime/server_args.py`:

1. **`_disable_cpu_offload_for_layerwise_components`** — drop the branch that flipped `dit_cpu_offload` to `False`. The function still disables `text_encoder_cpu_offload` / `image_encoder_cpu_offload` / `vae_cpu_offload` for components selected for layerwise offload (no behavior change there).
2. **`_validate_offload`** — drop the `"layerwise offload is selected for DiT components, automatically disabling dit_cpu_offload."` warning + auto-disable. The `SGLANG_CACHE_DIT_ENABLED` `ValueError` and the `use_fsdp_inference` auto-disable just above are preserved.
3. **`--dit-layerwise-offload` help text** — remove the inaccurate "Cannot be used together with … dit_cpu_offload …" clause; add a one-liner noting that the combination yields the lowest peak GPU memory.

`python/sglang/multimodal_gen/test/unit/test_server_args.py`:

4. **Update 6 existing tests** whose assertions encoded the old force-disable behavior (`test_layerwise_components_disable_matching_cpu_offloads`, `test_auto_wan2_2_a14b_layerwise_offload_adds_dit`, `test_memory_wan_layerwise_offload_is_enabled_without_fsdp`, `test_explicit_fastwan_dit_layerwise_still_selects_dit_group`, `test_explicit_multi_gpu_dit_layerwise_only_selects_dit_group`, `test_memory_mode_wan_uses_layerwise_offload`) — flip `assertFalse(args.dit_cpu_offload)` to `assertTrue` with a short comment.
5. **Add `test_dit_layerwise_offload_preserves_dit_cpu_offload`** — focused regression test asserting that `dit_cpu_offload=True` + `dit_layerwise_offload=True` both stay on after `ServerArgs` construction.

## Accuracy Tests

This PR only changes config validation and a static help string; runtime code paths for both flags are unchanged. End-to-end model outputs are unaffected.

## Speed Tests and Profiling

Server startup, RTX 5090 × 1, `Qwen-Image-Edit-2509`, `--dit-offload-prefetch-size 4`, no other offloads. GPU memory sampled every 8–10 s by `nvidia-smi --query-gpu=memory.used`.

### With LoRA (`merged_lora_03.safetensors`, `lora_scale=0.4`)

`--dit-cpu-offload false --dit-layerwise-offload true` (force-disable path = current `main`):

```
5441 -> 32073 (OOM) -> 2 -> 5441 -> 22785 -> 30325 MiB (OOM) -> ...
torch.OutOfMemoryError: GPU 0 has a total capacity of 31.36 GiB of which 38.19 MiB is free.
Error while loading customized transformer, falling back to native version
```

3 OOMs, no startup.

`--dit-cpu-offload true --dit-layerwise-offload true` (this PR):

```
5441 -> 5837 (DiT kept on host) -> 21883 -> 22839 -> 25499 MiB
LayerwiseOffloadManager initialized with num prefetched layer: 4, total num layers: 60
Application startup complete. Uvicorn running on http://0.0.0.0:30000
```

0 OOMs, peak 25499 MiB.

### Without LoRA

Identical command minus `--lora-path` / `--lora-scale`. Same pattern: `dit_cpu_offload=false` hits 32073 MiB and OOMs (3 OOMs, no startup); `dit_cpu_offload=true` peaks at 29367 MiB transient / 24633 MiB steady, `Application startup complete`. Confirms the OOM is in the loader path itself, not a LoRA artifact.

### Repro

```bash
CUDA_VISIBLE_DEVICES=0 sglang serve \
  --model-path /path/to/Qwen-Image-Edit-2509 \
  --num-gpus 1 --port 30000 \
  --dit-cpu-offload true \
  --dit-layerwise-offload true \
  --dit-offload-prefetch-size 4 \
  --text-encoder-cpu-offload false \
  --enable-cfg-parallel false \
  --host 0.0.0.0
```

## Checklist

- [x] Format your code according to [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit). `black --check`, `isort --check`, and `ruff --select=F401,F821` all clean against `server_args.py` and `test_server_args.py` (`black 26.1.0`, `isort 7.0.0`, `ruff 0.15.1`, matching `.pre-commit-config.yaml`).
- [x] Add unit tests according to [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). Added `test_dit_layerwise_offload_preserves_dit_cpu_offload` plus updated six existing tests; full `python -m unittest python.sglang.multimodal_gen.test.unit.test_server_args` passes 74 / 74.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). Updated the CLI help for `--dit-layerwise-offload` so it no longer claims incompatibility with `--dit-cpu-offload` and notes the lowest-peak-memory combination.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). See *Accuracy Tests* (no runtime change, accuracy unaffected) and *Speed Tests and Profiling* (real-server startup memory profiles with and without LoRA on RTX 5090).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance). Code style preserved; passes the repo's pre-commit-config-pinned `black` / `isort` / `ruff` versions.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #26754122363](https://github.com/sgl-project/sglang/actions/runs/26754122363)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26754121990](https://github.com/sgl-project/sglang/actions/runs/26754121990)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
