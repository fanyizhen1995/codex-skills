---
source_id: sglang-github-closed-issues-prs
title: '[Bug] DeepSeek V4 Pro probabilistically outputs reasoning only (no content)
  when enabling MTP'
canonical_url: https://github.com/sgl-project/sglang/issues/26039
captured_at: '2026-07-07T23:35:30.898686+00:00'
content_hash: eb44e3a126c5982674f3a823cba9d62d328bce928b92d0b0e044b7338af93395
---
# [Bug] DeepSeek V4 Pro probabilistically outputs reasoning only (no content) when enabling MTP

URL: https://github.com/sgl-project/sglang/issues/26039
State: closed
Labels: 
Closed at: 2026-07-07T12:36:41Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When enabling MTP on DeepSeek V4 Pro, in the GPQA test set, the model probabilistically produces only thoughts without content, This issue occurs with a probability of approximately 0.1%. Disabling MTP resolves the problem.

I debugged and found that the draft model predicted EOS, and the target model verified/passed that EOS.

### Reproduction

docker image: nightly-dev-cu13-20260520-425dffbd

```
# prefill
python -m sglang.launch_server --model-path /data/models/deepseek-v4-pro_v1 --disaggregation-ib-device mlx5_10,mlx5_11,mlx5_12,mlx5_13,mlx5_14,mlx5_15,mlx5_16,mlx5_17 --host 0.0.0.0 --port 30050 --trust-remote-code --tp 8 --dp 8 --enable-dp-attention --moe-runner-backend flashinfer_mxfp4 --chunked-prefill-size 32768 --disaggregation-mode prefill --load-balance-method total_requests --disable-flashinfer-autotune --mem-fraction-static 0.82 --max-running-requests 64 --disable-cuda-graph --moe-a2a-backend deepep --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 --enable-cache-report --enable-metrics --log-level-http info --log-level info

# decode
python -m sglang.launch_server --model-path /data/models/deepseek-v4-pro_v1 --disaggregation-ib-device mlx5_10,mlx5_11,mlx5_12,mlx5_13,mlx5_14,mlx5_15,mlx5_16,mlx5_17 --host 0.0.0.0 --port 30050 --disaggregation-mode decode --trust-remote-code --tp 8 --dp 8 --enable-dp-attention --speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 --load-balance-method total_requests --disable-flashinfer-autotune --mem-fraction-static 0.85 --max-running-requests 512 --cuda-graph-bs 1 4 6 8 10 12 14 16 18 20 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56 58 60 62 64 --moe-a2a-backend deepep --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 --enable-cache-report --enable-metrics --log-level-http info --log-level info
```


A curl script to quick reproduction:


```

# send request
# python curl-batch.py -u http://127.0.0.1:30050/v1/chat/completions -m deepseek-v4-pro -o deepseek-v4-pro-output -c 256 -n 1000 
# check empty content
# python curl-batch.py --check -o deepseek-v4-pro-output

import argparse
import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests


API_URL = "http://127.0.0.1:30050"
HEADERS = {
    "Content-Type": "application/json"
}
PROMPT = (
    "Answer the following multiple choice question. The last line of your response "
    "should be of the following format: 'ANSWER: [LETTER]' (without quotes) where "
    "[LETTER] is one of A,B,C,D. Think step by step before answering.\n\n"
    "Enamine reactions include nucleophilic substitutions, electrophilic additions, "
    "and the condensation of secondary amines with carbonyl compounds to generate "
    "enamines. Enamine reactions are useful techniques for creating complex compounds "
    "with specified functional groups and stereochemistry.\n"
    "Mention the product of the following reaction (B) and select the correct sequence "
    "of the reagents according to the reaction steps (A).\n"
    "(E)-N-methyl-N-(pentan-2-ylidene)ethanaminium + A ---> B\n\n"
    "A) (i) LDA, DME (ii) CH3CH2I (iii) H3O+ B = pentan-2-one + N,N-dimethylethanamine\n"
    "B) A = (i) LDA, DME (ii) CH3CH2I (iii) H3O+ B = heptan-4-one\n"
    "C) (i) LDA (ii) DME, CH3CH2I, H3O+, B = heptan-4-one\n"
    "D) (i) LDA (ii) DME, CH3CH2I, H3O+, B = pentan-2-one + N,N-dimethylethanamine"
)


def send_one(url: str, model: str, idx: int, output_dir: str):
    out_path = os.path.join(output_dir, f"{idx}.json")
    if os.path.exists(out_path):
        return
    body = {
        "model": model,
        "thinking": {"type": "enabled"},
        "chat_template_kwargs": {
            "thinking": True,
            "enable_thinking": True
        },
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 131072,
    }
    t0 = time.time()
    try:
        resp = requests.post(url, headers=HEADERS, json=body, timeout=3000)
        elapsed = time.time() - t0
        result = {
            "idx": idx,
            "status_code": resp.status_code,
            "elapsed": elapsed,
            "response": resp.json() if resp.status_code == 200 else resp.text,
        }
    except Exception as e:
        elapsed = time.time() - t0
        result = {"idx": idx, "status_code": -1, "elapsed": elapsed, "error": str(e)}

    out_path = os.path.join(output_dir, f"{idx}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def check_empty_content(output_dir: str):
    empty_ids = []
    for fname in sorted(os.listdir(output_dir)):
        if not fname.endswith(".json") or fname.endswith(".meta.json"):
            continue
        fpath = os.path.join(output_dir, fname)
        with open(fpath) as f:
            data = json.load(f)
        if data.get("status_code") != 200:
            continue
        resp = data.get("response", {})
        choices = resp.get("choices", [])
        for choice in choices:
            msg = choice.get("message", {})
            content = msg.get("content")
            if content is None or content == "":
                empty_ids.append(data["idx"])
                break
    if empty_ids:
        print(f"Empty content IDs ({len(empty_ids)}): {empty_ids}")
    else:
        print("All responses have content.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", default=API_URL)
    parser.add_argument("-m", "--model", default="deepseek-v4-pro")
    parser.add_argument("-o", "--output-dir", required=True)
    parser.add_argument("-n", "--total", type=int, default=1000)
    parser.add_argument("-c", "--concurrency", type=int, default=128)
    parser.add_argument("--check", action="store_true", help="Only check empty content in output dir")
    args = parser.parse_args()

    if args.check:
        check_empty_content(args.output_dir)
        return

    os.makedirs(args.output_dir, exist_ok=True)

    executor = ThreadPoolExecutor(max_workers=args.concurrency)
    sem = asyncio.Semaphore(args.concurrency)

    async def bounded(i):
        async with sem:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, send_one, args.url, args.model, i, args.output_dir)

    tasks = [bounded(i) for i in range(args.total)]
    await asyncio.gather(*tasks)
    executor.shutdown(wait=False)

    print("Done. Checking empty content...")
    check_empty_content(args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())

```

### Environment

```
Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA B300 SXM6 AC
GPU 0,1,2,3,4,5,6,7 Compute Capability: 10.3
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 590.44.01
PyTorch: 2.11.0+cu130
sglang: 0.0.0.dev1+g0c8049d9b
sglang-kernel: 0.4.2.post2
flashinfer_python: 0.6.11.post1
flashinfer_cubin: 0.6.11.post1
flashinfer_jit_cache: 0.6.11.post1+cu130
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0+cu130
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.15.0
interegular: 0.3.3
modelscope: 1.37.0
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.29
pyzmq: 27.1.0
uvicorn: 0.47.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.0
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.103.1
litellm: Module Not Found
torchcodec: 0.11.1+cu130
NVIDIA Topology: 
	[4mGPU0	GPU1	GPU2	GPU3	GPU4	GPU5	GPU6	GPU7	NIC0	NIC1	NIC2	NIC3	NIC4	NIC5	NIC6	NIC7	NIC8	CPU Affinity	NUMA Affinity	GPU NUMA ID[0m
GPU0	 X 	NV18	NV18	NV18	NV18	NV18	NV18	NV18	PXB	NODE	NODE	NODE	SYS	SYS	SYS	SYS	SYS	0-63,128-191	0		N/A
GPU1	NV18	 X 	NV18	NV18	NV18	NV18	NV18	NV18	NODE	PXB	NODE	NODE	SYS	SYS	SYS	SYS	SYS	0-63,128-191	0		N/A
GPU2	NV18	NV18	 X 	NV18	NV18	NV18	NV18	NV18	NODE	NODE	PXB	NODE	SYS	SYS	SYS	SYS	SYS	0-63,128-191	0		N/A
GPU3	NV18	NV18	NV18	 X 	NV18	NV18	NV18	NV18	NODE	NODE	NODE	PXB	SYS	SYS	SYS	SYS	SYS	0-63,128-191	0		N/A
GPU4	NV18	NV18	NV18	NV18	 X 	NV18	NV18	NV18	SYS	SYS	SYS	SYS	PXB	NODE	NODE	NODE	NODE	64-127,192-255	1		N/A
GPU5	NV18	NV18	NV18	NV18	NV18	 X 	NV18	NV18	SYS	SYS	SYS	SYS	NODE	PXB	NODE	NODE	NODE	64-127,192-255	1		N/A
GPU6	NV18	NV18	NV18	NV18	NV18	NV18	 X 	NV18	SYS	SYS	SYS	SYS	NODE	NODE	PXB	NODE	NODE	64-127,192-255	1		N/A
GPU7	NV18	NV18	NV18	NV18	NV18	NV18	NV18	 X 	SYS	SYS	SYS	SYS	NODE	NODE	NODE	PXB	NODE	64-127,192-255	1		N/A
NIC0	PXB	NODE	NODE	NODE	SYS	SYS	SYS	SYS	 X 	NODE	NODE	NODE	SYS	SYS	SYS	SYS	SYS				
NIC1	NODE	PXB	NODE	NODE	SYS	SYS	SYS	SYS	NODE	 X 	NODE	NODE	SYS	SYS	SYS	SYS	SYS				
NIC2	NODE	NODE	PXB	NODE	SYS	SYS	SYS	SYS	NODE	NODE	 X 	NODE	SYS	SYS	SYS	SYS	SYS				
NIC3	NODE	NODE	NODE	PXB	SYS	SYS	SYS	SYS	NODE	NODE	NODE	 X 	SYS	SYS	SYS	SYS	SYS				
NIC4	SYS	SYS	SYS	SYS	PXB	NODE	NODE	NODE	SYS	SYS	SYS	SYS	 X 	NODE	NODE	NODE	NODE				
NIC5	SYS	SYS	SYS	SYS	NODE	PXB	NODE	NODE	SYS	SYS	SYS	SYS	NODE	 X 	NODE	NODE	NODE				
NIC6	SYS	SYS	SYS	SYS	NODE	NODE	PXB	NODE	SYS	SYS	SYS	SYS	NODE	NODE	 X 	NODE	NODE				
NIC7	SYS	SYS	SYS	SYS	NODE	NODE	NODE	PXB	SYS	SYS	SYS	SYS	NODE	NODE	NODE	 X 	NODE				
NIC8	SYS	SYS	SYS	SYS	NODE	NODE	NODE	NODE	SYS	SYS	SYS	SYS	NODE	NODE	NODE	NODE	 X 				

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  NIC0: mlx5_10
  NIC1: mlx5_11
  NIC2: mlx5_12
  NIC3: mlx5_13
  NIC4: mlx5_14
  NIC5: mlx5_15
  NIC6: mlx5_16
  NIC7: mlx5_17
  NIC8: mlx5_bond_0


ulimit soft: 1048576

```
