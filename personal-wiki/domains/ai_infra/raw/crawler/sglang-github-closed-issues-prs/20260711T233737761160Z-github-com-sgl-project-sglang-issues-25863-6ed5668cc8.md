---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Qwen3.5-397B-A17B-FP8 on B300 with v0.5.12-cu130 TP4 conc=256 produces
  ~0% GSM8K accuracy (tp=4, trtllm_mha + flashinfer_trtllm MoE)'
canonical_url: https://github.com/sgl-project/sglang/issues/25863
captured_at: '2026-07-11T23:37:37.761160+00:00'
content_hash: 6ed5668cc872dd02e0a253e97891cad66c2e7dc75e0c64d271940b1c405eea17
---
# [Bug] Qwen3.5-397B-A17B-FP8 on B300 with v0.5.12-cu130 TP4 conc=256 produces ~0% GSM8K accuracy (tp=4, trtllm_mha + flashinfer_trtllm MoE)

URL: https://github.com/sgl-project/sglang/issues/25863
State: closed
Labels: 
Closed at: 2026-07-11T18:59:56Z
Merged at: 

## human
`Qwen/Qwen3.5-397B-A17B-FP8` TP=4 conc=256 on inferencex eval harness produce low eval score

https://github.com/SemiAnalysisAI/InferenceX/actions/runs/26144042784/job/76895376231



### ai generated Summary

`Qwen/Qwen3.5-397B-A17B-FP8` produces near-zero accuracy on GSM8K (5-shot) when served with `lmsysorg/sglang:v0.5.12-cu130` on B300 (`tp=4`, `--attention-backend trtllm_mha`, `--moe-runner-backend flashinfer_trtllm`). Same prompts on a known-good config get ~0.85+; here we measured **`exact_match=0.0000` (strict-match)** / **`0.0015` (flexible-extract)** — i.e. the model is generating answers that don't match GSM8K's expected format at all, which strongly suggests an output-quality / detokenization regression rather than a flat throughput bug.

The server starts cleanly (cuda-graph capture completes, requests succeed), so this is **not** a crash — it's a silent quality failure.

### Environment

- Image: `lmsysorg/sglang:v0.5.12-cu130`
- GPU: NVIDIA B300 (single node, `tp=4`)
- Model: `Qwen/Qwen3.5-397B-A17B-FP8`
- Driver/CUDA: cu130 stack as bundled in the image

### Reproduction

Launch command (full args from the failing run's `server_args=` line):

```
python3 -m sglang.launch_server \
  --model-path /data/models/Qwen3.5-397B-A17B-FP8 \
  --host 0.0.0.0 --port 8888 \
  --trust-remote-code \
  --tensor-parallel-size 4 --data-parallel-size 1 --expert-parallel-size 1 \
  --enable-symm-mem \
  --disable-radix-cache \
  --quantization fp8 \
  --kv-cache-dtype fp8_e4m3 \
  --mamba-ssm-dtype bfloat16 \
  --attention-backend trtllm_mha \
  --mm-attention-backend triton_attn \
  --moe-runner-backend flashinfer_trtllm \
  --cuda-graph-max-bs 256 --max-running-requests 256 \
  --max-prefill-tokens 16384 --chunked-prefill-size 16384 \
  --mem-fraction-static 0.8 \
  --stream-interval 50 --scheduler-recv-interval 10 \
  --tokenizer-worker-num 6 \
  --context-length 9472
```

(`--mm-attention-backend triton_attn` is a workaround for the unrelated cute `sm_103` assertion we filed in #25564; without it the server crashes during warmup.)

Eval command:

```
python3 -m lm_eval --model local-chat-completions \
  --apply_chat_template \
  --tasks gsm8k \
  --output_path /tmp/eval_out \
  --log_samples \
  --model_args 'model=/data/models/Qwen3.5-397B-A17B-FP8,base_url=http://0.0.0.0:8888/v1/chat/completions,api_key=EMPTY,eos_string=</s>,max_retries=5,num_concurrent=64,timeout=1800,tokenized_requests=False,max_length=9472' \
  --gen_kwargs max_tokens=5376,temperature=0,top_p=1
```

### Result

```
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.0015|±  |0.0011|
|     |       |strict-match    |     5|exact_match|↑  |0.0000|±  |0.0000|
```

vs. expected ~0.85 threshold (the same recipe on prior images cleared this).

### Failing run (logs + per-sample dump)

https://github.com/SemiAnalysisAI/InferenceX/actions/runs/26144042784/job/76895376231

Per-sample lm-eval output is archived in the run artifacts if you want to inspect the model's actual generations vs the gold answers.

### Suspected causes (initial hunches — could use eyes from someone familiar with the v0.5.12 changes)

Combination of any of:
- `--moe-runner-backend flashinfer_trtllm` on Qwen3.5 MoE with fp8 — possible numerics regression for this kernel path?
- `--attention-backend trtllm_mha` with this model
- `--quantization fp8` + `--kv-cache-dtype fp8_e4m3` interaction with the v0.5.12 changes
- Chat-template handling change (we're using `--apply_chat_template` via `local-chat-completions`, so any change to how the served chat template emits assistant turns could nuke GSM8K's expected `#### [number]` format)

Happy to try any toggle / pin / debug print you want.
