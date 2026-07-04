---
source_id: sglang-github-closed-issues-prs
title: '[Bug] : ImportError: cannot import name ''dynamic_per_tensor_quant'' from
  ''aiter'' (unknown location)'
canonical_url: https://github.com/sgl-project/sglang/issues/23083
captured_at: '2026-07-04T02:13:49.126707+00:00'
content_hash: b8c57460ca0c6f093300f2011d424e19493d689a3031d60da5b2f7ac4c69ffa0
---
# [Bug] : ImportError: cannot import name 'dynamic_per_tensor_quant' from 'aiter' (unknown location)

URL: https://github.com/sgl-project/sglang/issues/23083
State: closed
Labels: inactive
Closed at: 2026-07-04T00:38:25Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

ImportError: cannot import name 'dynamic_per_tensor_quant' from 'aiter' (unknown location) with latest SGlang docker image on MI355x.
SGlang Version: v0.5.10.post1-rocm720-mi35x

Error:
```
Attaching to sglang_serving_0
sglang_serving_0  | /sgl-workspace/sglang/python/sglang/launch_server.py:51: UserWarning: 'python -m sglang.launch_server' is still supported, but 'sglang serve' is the recommended entrypoint.
sglang_serving_0  |   Example: sglang serve --model-path <model> [options]
sglang_serving_0  |   warnings.warn(
sglang_serving_0  | Traceback (most recent call last):
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/layers/quantization/fp8_kernel.py", line 79, in <module>
sglang_serving_0  |     from aiter import (  # v0.1.3
sglang_serving_0  | ImportError: cannot import name 'dynamic_per_tensor_quant' from 'aiter' (unknown location)
sglang_serving_0  | 
sglang_serving_0  | During handling of the above exception, another exception occurred:
sglang_serving_0  | 
sglang_serving_0  | Traceback (most recent call last):
sglang_serving_0  |   File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
sglang_serving_0  |     return _run_code(code, main_globals, None,
sglang_serving_0  |   File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
sglang_serving_0  |     exec(code, run_globals)
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/launch_server.py", line 59, in <module>
sglang_serving_0  |     server_args = prepare_server_args(sys.argv[1:])
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/server_args.py", line 6539, in prepare_server_args
sglang_serving_0  |     return ServerArgs.from_cli_args(raw_args)
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/server_args.py", line 5975, in from_cli_args
sglang_serving_0  |     return cls(**{attr: getattr(args, attr) for attr in attrs})
sglang_serving_0  |   File "<string>", line 352, in __init__
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/server_args.py", line 778, in __post_init__
sglang_serving_0  |     self._handle_piecewise_cuda_graph()
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/server_args.py", line 1086, in _handle_piecewise_cuda_graph
sglang_serving_0  |     if self.get_model_config().is_piecewise_cuda_graph_disabled_model:
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/server_args.py", line 6021, in get_model_config
sglang_serving_0  |     from sglang.srt.configs.model_config import ModelConfig
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/configs/model_config.py", line 27, in <module>
sglang_serving_0  |     from sglang.srt.layers.quantization import QUANTIZATION_METHODS
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/layers/quantization/__init__.py", line 19, in <module>
sglang_serving_0  |     from sglang.srt.layers.quantization.auto_round import AutoRoundConfig
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/layers/quantization/auto_round.py", line 12, in <module>
sglang_serving_0  |     from sglang.srt.layers.quantization.utils import get_scalar_types
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/layers/quantization/utils.py", line 13, in <module>
sglang_serving_0  |     from sglang.srt.layers.quantization.fp8_kernel import scaled_fp8_quant
sglang_serving_0  |   File "/sgl-workspace/sglang/python/sglang/srt/layers/quantization/fp8_kernel.py", line 85, in <module>
sglang_serving_0  |     raise ImportError("aiter is required when SGLANG_USE_AITER is set to True")
sglang_serving_0  | ImportError: aiter is required when SGLANG_USE_AITER is set to True
```

### Reproduction

Docker compose file:
```
services:
  sglang_serving_0:
    command: --model-path=Qwen/Qwen3.5-2B --host 0.0.0.0 --port=8000 --trust-remote-code
      --enable-metrics --dtype=auto  --kv-cache-dtype=auto --reasoning-parser=qwen3
      --context-length=2048 --tp-size=1
    container_name: sglang_serving_0
    devices:
    - /dev/kfd:/dev/kfd
    - /dev/dri:/dev/dri
    entrypoint:
    - python3
    - -m
    - sglang.launch_server
    environment:
      CUDA_VISIBLE_DEVICES: '0'
      HF_TOKEN: <HF TOKEN>
      HSA_NO_SCRATCH_RECLAIM: 1
    image: lmsysorg/sglang:v0.5.10.post1-rocm720-mi35x
    ipc: host
    privileged: true
    restart: always
    shm_size: 32G
    volumes:
    - /mnt/models:/root/.cache/huggingface:rw
```

### Environment

Docker container in MI355x AMD GPU
