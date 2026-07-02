---
source_id: sglang-github-closed-issues-prs
title: '[Bug] sglang.launch_server crashes on Apple OSX / MLX with AttributeError:
  ''MlxModelRunnerStub'' object has no attribute ''prefill_aware_swa'''
canonical_url: https://github.com/sgl-project/sglang/issues/29679
captured_at: '2026-07-02T02:12:27.248903+00:00'
content_hash: 5fd6ba61cedd3c0133c7bf6233f611c33251a708d33ca7628af158ac2a2213af
---
# [Bug] sglang.launch_server crashes on Apple OSX / MLX with AttributeError: 'MlxModelRunnerStub' object has no attribute 'prefill_aware_swa'

URL: https://github.com/sgl-project/sglang/issues/29679
State: closed
Labels: 
Closed at: 2026-07-01T05:55:45Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Hi SGLang Team: 
I am following the step in [Apple Silicon with Metal](https://docs.sglang.io/docs/hardware-platforms/apple_metal) to run SGLang on Mac. But it crashes regardless of which model I use (`Tried mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` and `mlx-community/Meta-Llama-3-8B-Instruct-4bit`). This happens on the latest main branch of sglang.

<img width="1280" height="1011" alt="Image" src="https://github.com/user-attachments/assets/5065b78a-2d44-4b98-be55-914e0d2e844f" />

### Reproduction

### Steps to reproduce
```
SGLANG_USE_MLX=1 python -m sglang.launch_server \
  --model mlx-community/Meta-Llama-3-8B-Instruct-4bit
  --disable-cuda-graph \
  --host 0.0.0.0
```

### Observed behavior
sglang.launch_server crashed with the following output:
```
[2026-06-29 14:45:55] Init Unified RadixTree with components (<ComponentType.FULL: 0>,)
[2026-06-29 14:45:55] Tree cache initialized: source=default impl=UnifiedRadixCache hybrid_swa=False hybrid_ssm=False hierarchical=False streaming_wrapped=False
[2026-06-29 14:45:56] INFO:     Started server process [71581]
[2026-06-29 14:45:56] INFO:     Waiting for application startup.
[2026-06-29 14:45:56] INFO:     Application startup complete.
[2026-06-29 14:45:56] INFO:     Uvicorn running on http://0.0.0.0:30000 (Press CTRL+C to quit)
[2026-06-29 14:45:57] INFO:     127.0.0.1:51847 - "GET /model_info HTTP/1.1" 200 OK
[2026-06-29 14:45:57] Scheduler hit an exception: Traceback (most recent call last):
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 4277, in run_scheduler_process
    scheduler.run_event_loop()
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 1493, in run_event_loop
    dispatch_event_loop(self)
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 4140, in dispatch_event_loop
    scheduler.event_loop_overlap_mlx()
  File "/Users/shhuang/Work/sglang/sglang-metal/lib/python3.12/site-packages/torch/utils/_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/shhuang/Work/sglang/python/sglang/srt/hardware_backend/mlx/scheduler_mixin.py", line 239, in event_loop_overlap_mlx
    next_batch = self.get_next_batch_to_run()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/shhuang/Work/sglang/python/sglang/srt/utils/nvtx_utils.py", line 109, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 2666, in get_next_batch_to_run
    new_batch = self.get_new_batch_prefill()
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 2726, in get_new_batch_prefill
    ret = self._get_new_batch_prefill_raw(
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/shhuang/Work/sglang/python/sglang/srt/managers/scheduler.py", line 2952, in _get_new_batch_prefill_raw
    if self.tp_worker.model_runner.prefill_aware_swa:
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MlxModelRunnerStub' object has no attribute 'prefill_aware_swa'

[2026-06-29 14:45:57] SIGQUIT received. signum=None, frame=None. It usually means one child failed.
[2026-06-29 14:45:57] Sleeping 5 seconds before crash diagnostics to let GPU activity settle.
[2026-06-29 14:46:02] No live scheduler processes found; skipping py-spy and CUDA coredump.
[2026-06-29 14:46:02] kill_process_tree called: parent_pid=71581, include_parent=True, pid=71581
zsh: killed     SGLANG_USE_MLX=1 python -m sglang.launch_server --model  --disable-cuda-graph
```




### Environment

```
% python3 -m sglang.check_env
Python: 3.12.13 (main, Jun 23 2026, 15:44:24) [Clang 22.1.3 ]
MPS available: True
macOS Version: 26.5.1
macOS Build: 25F80
Apple Silicon: Apple M3 Pro
Unified Memory: 36.0 GB
CPU Cores (Total): 12
CPU Cores (Performance): 6
CPU Cores (Efficiency): 6
Metal Support: Metal 4
GPU Cores: 18
PyTorch: 2.11.0
sglang: 0.5.15.dev244+gc7b9b92d9
sglang-kernel: Module Not Found
flashinfer_python: Module Not Found
flashinfer_cubin: Module Not Found
flashinfer_jit_cache: Module Not Found
triton: Module Not Found
transformers: 5.8.1
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.14.1
fastapi: 0.138.1
huggingface_hub: 1.21.0
interegular: 0.3.3
modelscope: 1.37.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.49.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.112.0
litellm: Module Not Found
torchcodec: Module Not Found
mlx: 0.31.2
mlx-lm: 0.31.3
mlx-metal: 0.31.2
ulimit soft: 256
```
