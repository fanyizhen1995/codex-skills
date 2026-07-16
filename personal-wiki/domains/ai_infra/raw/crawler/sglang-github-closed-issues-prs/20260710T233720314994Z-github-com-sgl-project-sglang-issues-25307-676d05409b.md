---
source_id: sglang-github-closed-issues-prs
title: '[Bug] PiecewiseCudaGraphRunner drops dummy lora_ids before prepare_lora_batch
  during forced PCG capture'
canonical_url: https://github.com/sgl-project/sglang/issues/25307
captured_at: '2026-07-10T23:37:20.314994+00:00'
content_hash: 676d05409b888da5f81929bd3ed0b4701f1255f3864dc4662110f95cece106ce
---
# [Bug] PiecewiseCudaGraphRunner drops dummy lora_ids before prepare_lora_batch during forced PCG capture

URL: https://github.com/sgl-project/sglang/issues/25307
State: closed
Labels: 
Closed at: 2026-07-10T01:24:45Z
Merged at: 

## Describe the bug

When launching SGLang with LoRA and forced Piecewise CUDA Graph, `PiecewiseCudaGraphRunner.capture_one_batch_size()` creates dummy LoRA IDs for graph capture:

```python
if self.model_runner.server_args.enable_lora:
    lora_ids = [None] * bs
else:
    lora_ids = None
```

but the constructed `ForwardBatch` still receives:

```python
lora_ids=None
```

The same function then calls:

```python
self.model_runner.lora_manager.prepare_lora_batch(forward_batch)
```

because the local `lora_ids` variable is not `None`.

As a result, `prepare_lora_batch()` receives `forward_batch.lora_ids is None`, even though the capture path intended to use a dummy list. This causes a startup-time failure during forced PCG capture.

## Why this looks like a code bug

`LoRAManager.prepare_lora_batch()` expects `forward_batch.lora_ids` to be list-like and uses `len(forward_batch.lora_ids)` / iteration over it. In the failing path, the caller computed a valid dummy list but discarded it when constructing `ForwardBatch`.

Current main still has this pattern at commit `88d3ed7df19eeb67d718e8b4eabdb32a14c63029`.

## Reproduction

Environment:

- Commit: `88d3ed7df19eeb67d718e8b4eabdb32a14c63029`
- GPU: `NVIDIA A100-SXM4-40GB`
- Driver: `580.126.20`
- `nvidia-smi` CUDA version: `13.0`
- NVCC: `Cuda compilation tools, release 12.9, V12.9.41`
- PyTorch: `2.11.0+cu130`
- Python: `3.10.12`
- SGLang: `0.0.0.dev1+g88d3ed7df`
- `sglang-kernel`: `0.4.2.post1`
- `flashinfer_python`: `0.6.11.post1`
- `triton`: `3.6.0`
- `transformers`: `5.6.0`

The preferred Llama reproduction pair was not accessible in this environment because the base model is gated, so I used this public base/adapter pair:

- Base model: `Qwen/Qwen3-0.6B`
- LoRA adapter: `AIPlans/Qwen3-0.6B-DPO`

Control launch without forced PCG starts successfully and logs that piecewise CUDA graph is disabled:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --enable-lora \
  --lora-paths lora0=AIPlans/Qwen3-0.6B-DPO \
  --max-loras-per-batch 2 \
  --mem-fraction-static 0.70 \
  --log-level debug \
  --host 127.0.0.1 \
  --port 30000
```

Relevant control log:

```text
[2026-05-14 20:44:47] Disable piecewise CUDA graph because --disable-piecewise-cuda-graph is set
[2026-05-14 20:44:50] Uvicorn running on http://127.0.0.1:30000
[2026-05-14 20:45:35] The server is fired up and ready to roll!
```

Forced-PCG launch used `--lora-backend torch_native` because the default `csgmv` backend currently hits an earlier, separate Dynamo graph-break in LoRA tuning config before `capture_one_batch_size()` is reached. The `torch_native` backend gets to the target PCG capture path and reproduces this issue:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --enable-lora \
  --lora-paths lora0=AIPlans/Qwen3-0.6B-DPO \
  --max-loras-per-batch 2 \
  --lora-backend torch_native \
  --enforce-piecewise-cuda-graph \
  --piecewise-cuda-graph-tokens 4 \
  --mem-fraction-static 0.70 \
  --log-level debug \
  --host 127.0.0.1 \
  --port 30000
```

Temporary local debug instrumentation was added immediately before the `prepare_lora_batch()` call:

```python
print(
    "DEBUG_PCG_LORA:",
    "local_lora_ids=",
    lora_ids,
    "forward_batch.lora_ids=",
    forward_batch.lora_ids,
    flush=True,
)
```

Failing output:

```text
DEBUG_PCG_LORA: local_lora_ids= [None] forward_batch.lora_ids= None
[2026-05-14 20:48:43] Piecewise CUDA Graph failed with error: object of type 'NoneType' has no len()
```

Traceback:

```text
Traceback (most recent call last):
  File "<sglang checkout>/python/sglang/srt/managers/scheduler.py", line 4025, in run_scheduler_process
    scheduler = Scheduler(
  File "<sglang checkout>/python/sglang/srt/managers/scheduler.py", line 437, in __init__
    self.init_model_worker()
  File "<sglang checkout>/python/sglang/srt/managers/scheduler.py", line 718, in init_model_worker
    self.init_tp_model_worker()
  File "<sglang checkout>/python/sglang/srt/managers/scheduler.py", line 673, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "<sglang checkout>/python/sglang/srt/managers/tp_worker.py", line 262, in __init__
    self._init_model_runner()
  File "<sglang checkout>/python/sglang/srt/managers/tp_worker.py", line 347, in _init_model_runner
    self._model_runner = ModelRunner(
  File "<sglang checkout>/python/sglang/srt/model_executor/model_runner.py", line 535, in __init__
    self.initialize(pre_model_load_memory)
  File "<sglang checkout>/python/sglang/srt/model_executor/model_runner.py", line 825, in initialize
    self.init_piecewise_cuda_graphs()
  File "<sglang checkout>/python/sglang/srt/model_executor/model_runner.py", line 3084, in init_piecewise_cuda_graphs
    self.piecewise_cuda_graph_runner = PiecewiseCudaGraphRunner(self)
  File "<sglang checkout>/python/sglang/srt/model_executor/piecewise_cuda_graph_runner.py", line 357, in __init__
    self.capture()
  File "<sglang checkout>/python/sglang/srt/model_executor/piecewise_cuda_graph_runner.py", line 519, in capture
    self.capture_one_batch_size(num_tokens)
  File "<sglang checkout>/python/sglang/srt/model_executor/piecewise_cuda_graph_runner.py", line 619, in capture_one_batch_size
    self.model_runner.lora_manager.prepare_lora_batch(forward_batch)
  File "<sglang checkout>/python/sglang/srt/lora/lora_manager.py", line 315, in prepare_lora_batch
    weight_indices = [0] * len(forward_batch.lora_ids)
TypeError: object of type 'NoneType' has no len()
```

## Expected behavior

Either:

1. `ForwardBatch` should receive the dummy IDs:

```python
lora_ids=lora_ids
```

or

2. if LoRA + forced PCG is intentionally unsupported, the server should fail early with a clear error instead of entering the capture path and failing inside `prepare_lora_batch`.

## Local patch result

This local one-line patch gets past the `prepare_lora_batch()` failure:

```diff
-                lora_ids=None,
+                lora_ids=lora_ids,
```

With the same debug print, the patched run shows:

```text
DEBUG_PCG_LORA: local_lora_ids= [None] forward_batch.lora_ids= [None]
```

After that, it fails later with a different LoRA/PCG Dynamo graph break in the torch-native LoRA op:

```text
Piecewise CUDA Graph failed with error: Data-dependent branching
...
File ".../sglang/srt/lora/torch_ops/lora_ops.py", line 68, in sgemm_lora_a_fwd
    if seq_len == 0:
```

So the one-line patch confirms this issue is the immediate cause of the original `prepare_lora_batch()` crash, even though there may still be separate LoRA/PCG compatibility problems after it.

## Duplicate check

I searched open and closed issues/PRs for:

- `piecewise_cuda_graph_runner lora_ids`
- `lora_ids=None prepare_lora_batch`
- `PiecewiseCudaGraphRunner prepare_lora_batch`
- `DEBUG_PCG_LORA`
- `forced piecewise cuda graph LoRA`

I found adjacent LoRA/CUDA graph work, including merged PR #21974 about padded `None` LoRA IDs causing a different `KeyError` in `prepare_lora_batch`, but I did not find an issue or PR for this exact `PiecewiseCudaGraphRunner.capture_one_batch_size()` dummy-`lora_ids` drop before `prepare_lora_batch()`.
