---
source_id: sglang-github-closed-issues-prs
title: '[Bug] `HF_HUB_OFFLINE` not longer supported in version 0.4.5'
canonical_url: https://github.com/sgl-project/sglang/issues/5386
captured_at: '2026-07-10T23:37:20.313903+00:00'
content_hash: e61390754ea67930169fc729ecf64c35ae4014cc9ba02136e947afe819475c8b
---
# [Bug] `HF_HUB_OFFLINE` not longer supported in version 0.4.5

URL: https://github.com/sgl-project/sglang/issues/5386
State: closed
Labels: inactive
Closed at: 2025-08-15T00:20:50Z
Merged at: 

### Checklist

- [x] 1. I have searched related issues but cannot get the expected help.
- [x] 2. The bug has not been fixed in the latest version.
- [x] 3. Please note that if the bug-related issue you submitted lacks corresponding environment info and a minimal reproducible demo, it will be challenging for us to reproduce and resolve the issue, reducing the likelihood of receiving feedback.
- [x] 4. If the issue you raised is not a bug but a question, please raise a discussion at https://github.com/sgl-project/sglang/discussions/new/choose Otherwise, it will be closed.
- [x] 5. Please use English, otherwise it will be closed.

### Describe the bug

Since the latest version, one can no longer set the env variable "HF_HUB_OFFLINE". Setting this variable will lead to the following failure during the model config.
```shell
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/sgl-workspace/sglang/python/sglang/launch_server.py", line 14, in <module>
    launch_server(server_args)
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/http_server.py", line 679, in launch_server
    tokenizer_manager, scheduler_info = _launch_subprocesses(server_args=server_args)
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/entrypoints/engine.py", line 568, in _launch_subprocesses
    tokenizer_manager = TokenizerManager(server_args, port_args)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tokenizer_manager.py", line 159, in __init__
    self.model_config = ModelConfig(
                        ^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/configs/model_config.py", line 168, in __init__
    self._verify_quantization()
  File "/sgl-workspace/sglang/python/sglang/srt/configs/model_config.py", line 289, in _verify_quantization
    quant_cfg = self._parse_quant_hf_config()
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/configs/model_config.py", line 248, in _parse_quant_hf_config
    if hf_api.file_exists(self.model_path, "hf_quant_config.json"):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_validators.py", line 114, in _inner_fn
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/hf_api.py", line 2958, in file_exists
    get_hf_file_metadata(url, token=token)
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_validators.py", line 114, in _inner_fn
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 1401, in get_hf_file_metadata
    r = _request_wrapper(
        ^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 285, in _request_wrapper
    response = _request_wrapper(
               ^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/file_download.py", line 308, in _request_wrapper
    response = get_session().request(method=method, url=url, **params)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/requests/sessions.py", line 589, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/requests/sessions.py", line 703, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/huggingface_hub/utils/_http.py", line 107, in send
    raise OfflineModeIsEnabled(
huggingface_hub.errors.OfflineModeIsEnabled: Cannot reach https://huggingface.co/upstage/SOLAR-10.7B-Instruct-v1.0/resolve/main/hf_quant_config.json: offline mode is enabled. To disable it, please unset the `HF_HUB_OFFLINE` environment variable.
```

I work on a research cluster where the nodes do not have internet access.

I would be more than happy to provide a PR if you are interested.

### Reproduction

Taking the example from the documentation
```shell
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct
docker run --gpus all \
    --shm-size 32g \
    -p 30000:30000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    --env "HF_HUB_OFFLINE=1" \
    --ipc=host \
    lmsysorg/sglang:latest \
    python3 -m sglang.launch_server --model-path meta-llama/Llama-3.1-8B-Instruct --host 0.0.0.0 --port 30000
```

### Environment

```shell
Apptainer> python3 -m sglang.check_env
Python: 3.12.8 (main, Dec  4 2024, 08:54:12) [GCC 11.4.0]
ROCM available: True
GPU 0,1: AMD Instinct MI300A
GPU 0,1 Compute Capability: 9.4
ROCM_HOME: /opt/rocm
HIPCC: HIP version: 6.3.42131-fa1d09cbd
ROCM Driver Version: 6.10.5
PyTorch: 2.6.0a0+git8d4926e
sglang: 0.4.5
sgl_kernel: 0.0.8
flashinfer: Module Not Found
triton: 3.2.0+gitcddf0fc3
transformers: 4.51.0
torchao: 0.10.0
numpy: 1.26.4
aiohttp: 3.11.11
fastapi: 0.115.6
hf_transfer: 0.1.9
huggingface_hub: 0.30.2
interegular: 0.3.3
modelscope: 1.24.1
orjson: 3.10.16
outlines: 0.1.11
packaging: 24.2
psutil: 6.1.1
pydantic: 2.10.5
multipart: Module Not Found
zmq: Module Not Found
uvicorn: 0.34.0
uvloop: 0.21.0
vllm: 0.6.7.dev2+g113274a0.rocm630
xgrammar: 0.1.17
openai: 1.72.0
tiktoken: 0.7.0
anthropic: 0.49.0
litellm: 1.65.4.post1
decord: 0.6.0
AMD Topology: 


============================ ROCm System Management Interface ============================
=============================== Link Type between two GPUs ===============================
       GPU0         GPU1         
GPU0   0            XGMI         
GPU1   XGMI         0            
================================== End of ROCm SMI Log ===================================

ulimit soft: 8192
```
