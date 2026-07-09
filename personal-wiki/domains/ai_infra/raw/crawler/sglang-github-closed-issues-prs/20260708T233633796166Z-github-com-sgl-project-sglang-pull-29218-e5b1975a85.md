---
source_id: sglang-github-closed-issues-prs
title: '[Spec] DFlash: support pure-MLA targets with an fp8 KV cache (Kimi-K2.x-NVFP4)'
canonical_url: https://github.com/sgl-project/sglang/pull/29218
captured_at: '2026-07-08T23:36:33.796166+00:00'
content_hash: e5b1975a85513b1af41f99c4b4862d5d0b7dab554dcf5781669dc579bd8f8f61
---
# [Spec] DFlash: support pure-MLA targets with an fp8 KV cache (Kimi-K2.x-NVFP4)

URL: https://github.com/sgl-project/sglang/pull/29218
State: closed
Labels: blackwell, run-ci
Closed at: 2026-07-08T02:52:14Z
Merged at: 2026-07-08T02:52:14Z

## Summary

Two fixes that let **DFlash** run on a **pure-MLA target with an fp8 KV cache** (`nvidia/Kimi-K2.5-NVFP4` / `Kimi-K2.6-NVFP4`, B200). Without them DFlash verify crashes at target-verify and the server never reaches ready.

The MLA spec-verify routing already exists (`HybridAttnBackend._select_backend`) — this PR only fixes the two crashes. `trtllm_mla` verify works today. **The cuteDSL fold verify kernel additionally requires `flashinfer >= 0.6.13`** (which ships the fold kernel); that is a separate flashinfer bump, not part of this PR.

### Changes
1. **Mamba verify-commit guard** — skip for pure-MLA (`mambaish_config is None`). `HybridAttnBackend` delegates the commit into an inner MLA backend that lacks it, so a bare `hasattr()` passes → `AttributeError` at verify. (`dflash_worker_v2.py`)
2. **bf16 draft-KV decouple** — on an fp8 target, give the `fa4` draft its own bf16 KV in `configure_kv_cache_dtype` (`fa4` needs `K.dtype == Q.dtype`). Scoped to `fa4` + the draft runner, so the target keeps fp8. (`model_runner.py`)

## Validation

`Kimi-K2.6-NVFP4` + draft `Kimi-K2.6-DFlash`, 8×B200 tp=8 — boots clean (target KV fp8, `fa4` draft KV bf16; separate pools). **GSM8K 5-shot, full 1319-set: 0.936** (Invalid 0.001).

Verify-kernel comparison (same config, only the verify backend differs; cuteDSL needs **flashinfer >= 0.6.13**) — 50K-prefix aiperf, `tok/s/user`:

| cc | `trtllm_mla` | cuteDSL | edge |
|---:|---:|---:|---:|
| 1  | 238.3 | 266.8 | +12% |
| 4  | 150.9 | 196.0 | +30% |
| 8  |  95.5 | 145.5 | +52% |
| 16 |  60.0 | 101.0 | **+68%** |

Accept-length is identical (cuteDSL 2.66 vs `trtllm_mla` 2.65, n≈870), so the delta is the verify kernel, not acceptance.

**Nightly:** `test/registered/quant/test_kimi_k26_nvfp4_dflash.py` (`nightly-8-gpu-b200`, tp=8, `trtllm_mla` arm) — gsm8k + perf/accept gate.

## Reproduce (8×B200, tp=8)

```bash
python3 -m sglang.launch_server \
  --model-path nvidia/Kimi-K2.6-NVFP4 --served-model-name nvidia/Kimi-K2.6-NVFP4 \
  --trust-remote-code --tp 8 --quantization modelopt_fp4 \
  --moe-runner-backend flashinfer_trtllm --fp4-gemm-backend flashinfer_cutlass \
  --attention-backend trtllm_mla --kv-cache-dtype fp8_e4m3 --mem-fraction-static 0.85 \
  --speculative-algorithm DFLASH --speculative-draft-model-path nvidia/Kimi-K2.6-DFlash \
  --speculative-draft-model-quantization unquant --speculative-num-draft-tokens 8 \
  --speculative-draft-attention-backend fa4 --speculative-draft-window-size 4096
```

cuteDSL fold verify (**flashinfer >= 0.6.13**): replace `--attention-backend trtllm_mla` with `--prefill-attention-backend trtllm_mla --decode-attention-backend cutedsl_mla --speculative-attention-mode decode`.

- Accuracy: `python3 -m sglang.test.few_shot_gsm8k --num-shots 5 --num-questions 1319 --port 30000`
- Throughput (50K-prefix, cc-sweep): `aiperf profile --model nvidia/Kimi-K2.6-NVFP4 --endpoint-type chat --endpoint /v1/chat/completions --url localhost:30000 --seq-dist "3000,1000:100" --prompt-prefix-length 50000 --prompt-prefix-pool-size $CC --concurrency $CC --request-count $((CC*5)) --num-dataset-entries $((CC*5)) --warmup-request-count $((CC*5)) --extra-inputs ignore_eos:true --streaming --use-legacy-max-tokens --tokenizer nvidia/Kimi-K2.6-NVFP4 --tokenizer-trust-remote-code`











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28836679509](https://github.com/sgl-project/sglang/actions/runs/28836679509)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28836679395](https://github.com/sgl-project/sglang/actions/runs/28836679395)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
