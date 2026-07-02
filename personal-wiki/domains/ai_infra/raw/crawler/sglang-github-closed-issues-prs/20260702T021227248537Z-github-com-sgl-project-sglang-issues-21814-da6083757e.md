---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Prefill disaggregation warmup fails with "''SamplingParams'' object
  is not subscriptable"'
canonical_url: https://github.com/sgl-project/sglang/issues/21814
captured_at: '2026-07-02T02:12:27.248537+00:00'
content_hash: da6083757e63189b105405220a4d085341b8b2fc493479ecf4e14fbda1da6db5
---
# [Bug] Prefill disaggregation warmup fails with "'SamplingParams' object is not subscriptable"

URL: https://github.com/sgl-project/sglang/issues/21814
State: closed
Labels: 
Closed at: 2026-04-09T05:52:55Z
Merged at: 

### Checklist

- [x] I searched related issues but found no obvious duplicate.
- [x] The bug was observed in a real run before the fix in #21261.
- [x] I am providing the actual runtime command and logs.
- [x] This is a bug report, not a usage question.
- [x] Please use English.

### Describe the bug

In a PD-disaggregated `dynamo.sglang` run, the prefill worker logged:

```text
[2026-03-31 02:32:49] Start of prefill disaggregation warmup ...
[2026-03-31 02:32:49] Prefill warmup failed: 'SamplingParams' object is not subscriptable
```

The worker did not crash immediately. It continued initializing and registered successfully afterward, so the full job eventually became healthy and completed its benchmark. However, the warmup path itself failed and emitted the error above.

This appears to be the same underlying issue fixed in PR #21261, where internal code paths could receive `sampling_params` as a `SamplingParams` object rather than a `dict` / `list[dict]`.

### Reproduction

This was reproduced in an actual SLURM run using SRT-SLURM with 1 prefill node and 1 decode node on B200s.

If you use `srt-slurm`, you can directly reproduce with:

```bash
srtctl apply -f recipes/b200-fp8/8k1k.yaml:zip_override_stp_maxtpt[1]
```

Prefill launch command extracted from the orchestrator log:

```bash
python3 -m dynamo.sglang \
  --model-path /model \
  --served-model-name deepseek-ai/DeepSeek-R1 \
  --host 0.0.0.0 \
  --port 30000 \
  --disaggregation-mode prefill \
  --dump-config-to /data/home/weiliangl/srt-slurm/outputs/0331-0228-b200-fp8-stp-max-tpt-dep8-1p-1d-bootstrap-refactor-safe/2739/logs/b300-002_config.json \
  --attention-backend trtllm_mla \
  --chunked-prefill-size 65536 \
  --context-length 9600 \
  --data-parallel-size 8 \
  --disable-radix-cache \
  --disaggregation-transfer-backend nixl \
  --enable-dp-attention \
  --enable-dp-lm-head \
  --enable-flashinfer-allreduce-fusion \
  --expert-parallel-size 1 \
  --kv-cache-dtype fp8_e4m3 \
  --load-balance-method total_requests \
  --max-prefill-tokens 8192 \
  --max-running-requests 32 \
  --mem-fraction-static 0.55 \
  --moe-dense-tp-size 1 \
  --moe-runner-backend flashinfer_trtllm \
  --quantization fp8 \
  --stream-interval 30 \
  --tensor-parallel-size 8 \
  --trust-remote-code \
  --watchdog-timeout 1000000
```

Relevant environment from the same run:

```text
CUDA_SCALE_LAUNCH_QUEUES=4x
DYN_REQUEST_PLANE=nats
SGLANG_LOG_FORWARD_ITERS=1
SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=100000
SGLANG_DISAGGREGATION_HEARTBEAT_MAX_FAILURE=100000
SGLANG_DISAGGREGATION_WAITING_TIMEOUT=100000
SGLANG_MOONCAKE_CUSTOM_MEM_POOL=True
SGLANG_USE_MESSAGE_QUEUE_BROADCASTER=0
SGLANG_DISABLE_TP_MEMORY_INBALANCE_CHECK=1
MC_FORCE_MNNVL=1
NCCL_MNNVL_ENABLE=1
NCCL_CUMEM_ENABLE=1
SGLANG_PER_TOKEN_GROUP_QUANT_8BIT_V2=1
```

### Observed behavior

Prefill worker log:

```text
[2026-03-31 02:32:49] Start of prefill disaggregation warmup ...
[2026-03-31 02:32:49] Prefill warmup failed: 'SamplingParams' object is not subscriptable
[2026-03-31 02:32:49] Prefill worker handler initialized - bootstrap host: 192.168.95.12, bootstrap port: 57563
```

Orchestrator behavior after that:

```text
2026-03-31 02:32:58 [INFO] Model is not ready, waiting for 0 prefills and 1 decodes. Have 1 prefills and 0 decodes.
2026-03-31 02:33:58 [INFO] Model is ready. Have 1 prefills and 1 decodes.
2026-03-31 02:38:05 [INFO] Benchmark completed successfully
```

So the warmup failure was non-fatal for the whole run, but it is still a real bug in the warmup path.

### Expected behavior

Prefill disaggregation warmup should accept internal `SamplingParams` objects and should not log:

```text
Prefill warmup failed: 'SamplingParams' object is not subscriptable
```

### Environment

- SGLang mounted from a local checkout inside the container
- Dynamo: 1.0.1
- Model: `deepseek-ai/DeepSeek-R1` (`dsr1-fp8`)
- Precision: FP8
- Attention backend: `trtllm_mla`
- Transfer backend: `nixl`
- Topology: 1 prefill node + 1 decode node, 8 GPUs per node (B200)
- Benchmark config in this run: GPQA

### Additional context

This issue appears to be fixed by PR #21261: "Fix 'SamplingParams' object is not subscriptable".
I am filing this issue mainly to capture the real production log, runtime command, and observed behavior that triggered the fix.
