---
source_id: sglang-github-closed-issues-prs
title: Fix GLM-DSA raw config restoration
canonical_url: https://github.com/sgl-project/sglang/pull/29837
captured_at: '2026-07-03T02:13:21.692424+00:00'
content_hash: 4f563a1e01e81ce57b517a3aee9a3793e6f588fde990ac1625bc79c475c5cddc
---
# Fix GLM-DSA raw config restoration

URL: https://github.com/sgl-project/sglang/pull/29837
State: closed
Labels: 
Closed at: 2026-07-03T01:21:43Z
Merged at: 

## Motivation

GLM-5.2-FP8 can fail to load on current SGLang because Hugging Face config parsing clobbers raw GLM-DSA shape fields. In the failing run, `qk_rope_head_dim` was parsed as `192` instead of the raw `64`, so SGLang constructed `model.layers.13.self_attn.fused_qkv_a_proj_with_mqa.weight` as `(2752, 6144)` while the checkpoint contains `(2624, 6144)`.

This affects the normal `AutoConfig.from_pretrained` path. Existing deployment code only restored raw GLM-DSA fields in a legacy fallback path, and upstream main did not have the restore helper in this parser.

## Reproduction

Hardware / model:

- B200 x8
- `zai-org/GLM-5.2-FP8`
- tensor parallel: `--tp 8`
- SGLang current deployment baseline: `75445db7dddeb583b695c459053cdc82896c6cf6`
- Known-good control: `sglang==0.5.13.post1`

Failing command shape:

```bash
python -m sglang.launch_server \
  --model-path zai-org/GLM-5.2-FP8 \
  --tp 8 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 5 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 6 \
  --mem-fraction-static 0.8 \
  --cuda-graph-max-bs 32 \
  --reasoning-parser glm45 \
  --tool-call-parser glm47 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-size 100 \
  --hicache-write-policy write_through \
  --enable-metrics \
  --enable-mfu-metrics \
  --host 0.0.0.0 \
  --port 10100
```

Observed failure before this fix:

```text
AssertionError: param.shape=torch.Size([2752, 6144]) loaded_weight.shape=torch.Size([2624, 6144])
```

The raw checkpoint config has:

```text
q_lora_rank=2048
kv_lora_rank=512
qk_nope_head_dim=192
qk_rope_head_dim=64
v_head_dim=256
```

The checkpoint tensor shape is therefore `2048 + 512 + 64 = 2624` rows. Current parsing produced `qk_rope_head_dim=192`, incorrectly constructing `2048 + 512 + 192 = 2752` rows.

## Fix

Restore raw GLM-DSA config fields immediately after initial HF config parsing and again after SGLang reloads the config from `_CONFIG_REGISTRY`, since the registry reload can overwrite the first restoration.

This keeps the correction in config normalization rather than adding a weight-loader shape special case.

## Validation

- Added unit coverage for the GLM-DSA parser path where both initial `AutoConfig` and registry reload return clobbered fields.
- `py_compile` passed for the edited files.
- `ruff check` passed for the edited files.
- `ruff format --check` passed for the edited files.
- On B200-03 with the full reproduction command above, patched current SGLang:
  - parsed `qk_rope_head_dim=64`, `v_head_dim=256`, `kv_lora_rank=512`, `q_lora_rank=2048`;
  - completed weight load for all TP ranks;
  - entered DeepGEMM warmup with the corrected `N=2624, K=6144` fused shape;
  - reached `/health` 200;
  - returned a successful `/v1/chat/completions` response.

Note: local pytest collection was not run in this Deployment workspace because its system Python has an incompatible Transformers install for this checkout. The targeted runtime smoke was run in the SGLang deployment venv instead.












<sub>✨ Presented to you with <a href=" ">Mind Lab</a > — A Lab for Experiential Intelligence.</sub>










<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28511596736](https://github.com/sgl-project/sglang/actions/runs/28511596736)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28511596516](https://github.com/sgl-project/sglang/actions/runs/28511596516)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
