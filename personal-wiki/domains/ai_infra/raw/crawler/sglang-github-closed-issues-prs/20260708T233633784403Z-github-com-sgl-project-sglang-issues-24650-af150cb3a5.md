---
source_id: sglang-github-closed-issues-prs
title: DeepSeek-V4-Flash-FP8 with EAGLE crashes under benchmark load with RoPE tensor
  shape mismatch (expected 128 but got 126)
canonical_url: https://github.com/sgl-project/sglang/issues/24650
captured_at: '2026-07-08T23:36:33.784403+00:00'
content_hash: af150cb3a5c4830a03566d02b7405f47d706f78d55d86229d4e30da9f44ebd52
---
# DeepSeek-V4-Flash-FP8 with EAGLE crashes under benchmark load with RoPE tensor shape mismatch (expected 128 but got 126)

URL: https://github.com/sgl-project/sglang/issues/24650
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:29Z
Merged at: 

**Bug Description**

I hit a reproducible server crash when benchmarking DeepSeek-V4-Flash-FP8 on SGLang with EAGLE speculative decoding enabled.

The server starts successfully and serves initial requests, but under benchmark load it crashes inside the DeepSeek-V4 fused RoPE / compressed attention path with:

        tvm.error.InternalError
        Tensor match failed
        Size mismatch for shape#0('batch_size'): expected 128 but got 126

After that, SGLang receives SIGQUIT, the server exits, and the client side starts seeing incomplete payload / connection refused errors.

**Environment**
     
        Image: lmsysorg/sglang:deepseek-v4-hopper
        Image ID: b88ae28e279f
        GPU: 4 x NVIDIA H200 (using GPUs 4,5,6,7)
        Driver Version: 550.144.03
        CUDA Version: 12.4
        Model: sgl-project/DeepSeek-V4-Flash-FP8
        Host OS / server name: vkg-prod-675-au


**Server Launch Command**

```
docker run --gpus all \
  --shm-size 32g \
  -p 30000:30000 \
  --env HF_TOKEN=<redacted> \
  --env SGLANG_DSV4_FP4_EXPERTS=0 \
  --env SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=256 \
  --env SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 \
  --env CUDA_VISIBLE_DEVICES=4,5,6,7 \
  --env PYTORCH_ALLOC_CONF=expandable_segments:True \
  --ipc=host \
  lmsysorg/sglang:deepseek-v4-hopper \
  sglang serve \
    --trust-remote-code \
    --model-path sgl-project/DeepSeek-V4-Flash-FP8 \
    --tp 4 \
    --dp 1 \
    --enable-dp-attention \
    --moe-a2a-backend deepep \
    --cuda-graph-max-bs 32 \
    --max-running-requests 128 \
    --mem-fraction-static 0.7 \
    --deepep-config '{"normal_dispatch":{"num_sms":96},"normal_combine":{"num_sms":96}}' \
    --speculative-algo EAGLE \
    --speculative-num-steps 1 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 2 \
    --tool-call-parser deepseekv4 \
    --reasoning-parser deepseek-v4 \
    --host 0.0.0.0 \
    --port 30000
```


**Server Startup Log**

```
[2026-05-08 01:11:18 TP0 EP0] max_total_num_tokens=1066240, chunked_prefill_size=8192, max_prefill_tokens=16384, max_running_requests=128, context_len=1048576, available_gpu_mem=28.11 GB
[2026-05-08 01:11:18] INFO:     Started server process [1]
[2026-05-08 01:11:18] INFO:     Waiting for application startup.
[2026-05-08 01:11:18] INFO:     Application startup complete.
[2026-05-08 01:11:18] INFO:     Uvicorn running on http://0.0.0.0:30000
[2026-05-08 01:12:20] The server is fired up and ready to roll!
```


**Benchmark Client Script**

```
import os
import subprocess

MODEL = "sgl-project/DeepSeek-V4-Flash-FP8"
TOKENIZER = "/root/.cache/huggingface/hub/models--sgl-project--DeepSeek-V4-Flash-FP8/snapshots/ae01d80c06cdfe30581edfd0e1c5449dc7ed7f17/"

def benchmark(num_prompt, ISL, OSL, max_concurrency, output_file):
    cmd = [
        "python3", "-m", "sglang.bench_serving",
        "--backend", "sglang",
        "--dataset-name", "random",
        "--model", MODEL,
        "--tokenizer", TOKENIZER,
        "--num-prompts", str(num_prompt),
        "--random-input-len", str(ISL),
        "--random-output-len", str(OSL),
        "--max-concurrency", str(max_concurrency),
        "--host", "127.0.0.1",
        "--port", "30000",
        "--output-file", output_file,
    ]
    subprocess.run(cmd, check=True)

tp = 4
input_output = [
    [1000, 1000],
    [8000, 1000],
    [25000, 1000],
]
concurrencies = [2, 4, 8, 16, 32, 64, 128, 256, 512]

n = 0
skip = 0

for ISL, OSL in input_output:
    for concurrency in concurrencies:
        num_requests = concurrency
        if n >= skip:
            print("concurrency*4,ISL,OSL,concurrency")
            print(concurrency * 4, ISL, OSL, concurrency)
            with open("tmp.out", "a") as fw:
                fw.write(f"ISL:{ISL}, OSL:{OSL}, concurrency:{concurrency}\n")
            benchmark(num_requests, ISL, OSL, concurrency, "tmp.out")
            print("finish 1 benchmark")
        else:
            print("skip")
        n += 1
```


**Reproduction**

```
Start SGLang serve with the Server Launch Command above.
Run the benchmark script above in the same container in a new terminal.
The failure reproduces at:
ISL=1000
OSL=1000
concurrency=64
num_prompts=64

Client side shows:
concurrency*4,ISL,OSL,concurrency
256 1000 1000 64
```


**Expected Behavior**

`The server should continue serving requests under this benchmark load, or at minimum fail gracefully with a clear recoverable error instead of crashing the whole server process.`

**Actual Behavior**

```
The server crashes during speculative decode / verify in the DeepSeek-V4 path. After the crash:
        server logs show RoPE tensor shape mismatch
        SGLang receives SIGQUIT
        client receives incomplete HTTP payload errors
        subsequent client requests fail with ConnectionRefusedError
```

**Server Error Log**

```
[2026-05-08 01:57:04 TP0 EP0] Scheduler hit an exception: Traceback (most recent call last):
  File "/workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3027, in run_scheduler_process
    scheduler.event_loop_overlap()
  File "/workspace/sglang/python/sglang/srt/speculative/eagle_worker_v2.py", line 681, in forward_batch_generation
    batch_output = self.verify(model_worker_batch)
  File "/workspace/sglang/python/sglang/srt/speculative/eagle_worker_v2.py", line 741, in verify
    forward_batch_output = self.target_worker.forward_batch_generation(
  File "/workspace/sglang/python/sglang/srt/models/deepseek_v4.py", line 806, in _forward_prepare
    self.indexer(x=x, q_lora=q_lora, forward_batch=forward_batch)
  File "/workspace/sglang/python/sglang/srt/layers/attention/compressed/indexer.py", line 294, in _forward_prepare_normal
    q = c4_indexer.compute_q(q_lora, positions=positions)
  File "/workspace/sglang/python/sglang/srt/models/deepseek_v4.py", line 359, in compute_q
    fused_rope(
  File "/workspace/sglang/python/sglang/jit_kernel/deepseek_v4.py", line 674, in fused_rope
    module.forward(q, k, freqs_real, positions, inverse)
  File "python/tvm_ffi/cython/function.pxi", line 929, in tvm_ffi.core.Function.__call__
tvm.error.InternalError: Tensor match failed for Tensor<126>[strides=<1>, dtype=int32, device=cuda:0] at /workspace/sglang/python/sglang/jit_kernel/csrc/deepseek_v4/rope.cuh:130
- Root cause: Size mismatch for shape#0('batch_size'): expected 128 but got 126

[2026-05-08 01:57:04] SIGQUIT received. signum=None, frame=None. It usually means one child failed.

I observed the same error on multiple TP ranks, e.g. cuda:0 and cuda:2.
```

**Client Error Log**

```
#Input tokens: 32529
#Output tokens: 31588
Starting warmup with 1 sequences...
Warmup completed with 1 sequences. Starting main benchmark run...
  2%|██▎ | 1/64 [00:49<51:35, 49.14s/it]
output.error='... aiohttp.client_exceptions.ClientPayloadError: Response payload is not completed: <TransferEncodingError: 400, message="Not enough data to satisfy transfer length header.">'

...

requests.exceptions.ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=30000): Max retries exceeded with url: /get_server_info (Caused by NewConnectionError("HTTPConnection(host='127.0.0.1', port=30000): Failed to establish a new connection: [Errno 111] Connection refused"))

subprocess.CalledProcessError: Command '['python3', '-m', 'sglang.bench_serving', '--backend', 'sglang', '--dataset-name', 'random', '--model', 'sgl-project/DeepSeek-V4-Flash-FP8', '--tokenizer', '/root/.cache/huggingface/hub/models--sgl-project--DeepSeek-V4-Flash-FP8/snapshots/ae01d80c06cdfe30581edfd0e1c5449dc7ed7f17/', '--num-prompts', '64', '--random-input-len', '1000', '--random-output-len', '1000', '--max-concurrency', '64', '--host', '127.0.0.1', '--port', '30000', '--output-file', 'tmp.out']' returned non-zero exit status 1.

```

**Additional Notes**
```
This does not look like a simple OOM in this run.
The failure appears related to EAGLE speculative decode + DeepSeek-V4 compressed attention / fused RoPE path.
The specific mismatch is:
        expected batch size: 128
        actual tensor shape: 126
The failure happens after the server has already accepted requests and started processing queued/running batches.
```

**Questions**
      
  ```
        1.Is this a known issue with DeepSeek-V4 + EAGLE on deepseek-v4-hopper?
        2.Is there a recommended workaround (e.g. disable EAGLE, disable compressed attention, adjust cuda-graph-max-bs, max-running-requests, or specific DeepSeek-V4 flags)?
        3.Should fused_rope / compressed indexer be handling non-128-aligned batch shapes differently in this path?
```
