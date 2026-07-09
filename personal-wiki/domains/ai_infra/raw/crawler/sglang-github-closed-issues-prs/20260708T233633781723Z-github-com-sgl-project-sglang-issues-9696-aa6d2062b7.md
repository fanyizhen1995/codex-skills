---
source_id: sglang-github-closed-issues-prs
title: '[Bug] parallel_tool_calls=False is not strictly enforced'
canonical_url: https://github.com/sgl-project/sglang/issues/9696
captured_at: '2026-07-08T23:36:33.781723+00:00'
content_hash: aa6d2062b7eb586e873188c998134277e5615b74d47d5c3e99bca4c4ee7663ac
---
# [Bug] parallel_tool_calls=False is not strictly enforced

URL: https://github.com/sgl-project/sglang/issues/9696
State: closed
Labels: bug, inactive
Closed at: 2026-01-05T00:23:16Z
Merged at: 

### Checklist

- [x] 1. I have searched related issues but cannot get the expected help.
- [x] 2. The bug has not been fixed in the latest version.
- [x] 3. Please note that if the bug-related issue you submitted lacks corresponding environment info and a minimal reproducible demo, it will be challenging for us to reproduce and resolve the issue, reducing the likelihood of receiving feedback.
- [x] 4. If the issue you raised is not a bug but a question, please raise a discussion at https://github.com/sgl-project/sglang/discussions/new/choose Otherwise, it will be closed.
- [x] 5. Please use English, otherwise it will be closed.

### Describe the bug

server: use sglang run LLM models like qwen3-30b-a3b
client: use openai client.chat.completions.create to call model
No matter parallel_tool_calls is False or True in the client, the model output still use multi tool calls in one turn.
Server command
`python3 -m sglang.launch_server --model-path /data00/models/Qwen3-30B-A3B/ --tensor-parallel-size 2 --reasoning-parser qwen3 --attention-backend flashinfer --host 0.0.0.0 --tool-call-parser qwen25`

Client script
```
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import AsyncOpenAI

import logging

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

LLM_BASE_URL = "http://0.0.0.0:30000/v1"
MODEL_NAME = "/data00/models/Qwen3-30B-A3B"
API_KEY = "sk-123456"

tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First integer"},
                    "b": {"type": "integer", "description": "Second integer"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two integers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First integer"},
                    "b": {"type": "integer", "description": "Second integer"},
                },
                "required": ["a", "b"],
            },
        },
    },
]

async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=LLM_BASE_URL)

    print("\nMCP Tool Chat. Type 'q' to exit.")
    while True:
        query = input("\nQuery: ").strip()
        if not query:
            continue
        if query.lower() == "q":
            break

        messages = [{"role": "user", "content": query}]

        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=8000,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            parallel_tool_calls=False,
            extra_body={"enable_thinking": False},
        )
        print("model message++++++++++++:", completion)


if __name__ == "__main__":
    asyncio.run(main())
```

Output:
```model message++++++++++++: ChatCompletion(id='6cff77f805084d29806fe91bf6c8143b', choices=[Choice(finish_reason='tool_calls', index=0, logprobs=None, message=ChatCompletionMessage(content=None, refusal=None, role='assistant', annotations=None, audio=None, function_call=None, tool_calls=**[ChatCompletionMessageToolCall(id='call_d29a2f2e26114606ad5f7a74', function=Function(arguments='{"a": 3, "b": 12}', name='multiply'), type='function', index=None), ChatCompletionMessageToolCall(id='call_805ae7c550ba44e5b31aa3b4', function=Function(arguments='{"a": 11, "b": 49}', name='add'), type='function', index=None)], reasoning_content="Okay, let's see. The user is asking two questions here. First, what is 3 multiplied by 12, and second, what is 11 plus 49. I need to figure out which functions to use for each.\n\nLooking at the tools provided, there's an 'add' function and a 'multiply' function. Both take two integers. So for the first question, 3 * 12, I should use the multiply function with a=3 and b=12. Then, for the second question, 11 + 49, the add function with a=11 and b=49. \n\nWait, do I need to check if the parameters are correct? The functions require integers, and the user provided numbers, so that's fine. The user might want the answers to both operations. I should make sure to call both functions and then present the results. \n\nI think that's all. Each question is straightforward, so I'll generate the tool calls for both.\n"), matched_stop=None)], created=1756306337, model='/data00/models/Qwen3-30B-A3B', object='chat.completion', service_tier=None, system_fingerprint=None, usage=CompletionUsage(completion_tokens=267, prompt_tokens=259, total_tokens=526, completion_tokens_details=None, prompt_tokens_details=None, reasoning_tokens=0), metadata={'weight_version': 'default'})```


<img width="1750" height="1612" alt="Image" src="https://github.com/user-attachments/assets/f5d16fa4-dbe0-454a-b059-efda6717a3ed" />

### Reproduction

server command 
`python3 -m sglang.launch_server --model-path /data00/models/Qwen3-30B-A3B/ --tensor-parallel-size 2 --reasoning-parser qwen3 --attention-backend flashinfer --host 0.0.0.0 --tool-call-parser qwen25`

client
just use python3 to run the script, and ask two questions(use different tools) in one sentence

<img width="3434" height="408" alt="Image" src="https://github.com/user-attachments/assets/e9b651e1-9631-4e50-9051-877c71097e14" />

### Environment

```
Python: 3.12.11 (main, Jun  4 2025, 08:56:18) [GCC 11.4.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.6, V12.6.68
CUDA Driver Version: 535.161.08
PyTorch: 2.8.0+cu126
sglang: 0.5.1.post1+byted.202508262055
sgl_kernel: 0.3.6.post2+byted.202508262052
flashinfer_python: 0.2.11.post3
triton: Module Not Found
transformers: 4.55.2
torchao: 0.9.0+cu126
numpy: 2.3.2
aiohttp: 3.12.15
fastapi: 0.116.1
hf_transfer: 0.1.9
huggingface_hub: 0.34.4
interegular: 0.3.3
modelscope: 1.29.1
orjson: 3.11.2
outlines: 0.1.11
packaging: 25.0
psutil: 7.0.0
pydantic: 2.11.7
python-multipart: 0.0.20
pyzmq: 27.0.2
uvicorn: 0.35.0
uvloop: 0.21.0
vllm: Module Not Found
xgrammar: 0.1.23
openai: 1.99.1
tiktoken: 0.11.0
anthropic: 0.64.0
litellm: Module Not Found
decord: 0.6.0
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE    SYS     SYS     SYS     SYS
NIC1    NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE    SYS     SYS     SYS     SYS
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE    SYS     SYS     SYS     SYS
NIC3    NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X      SYS     SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      NODE    NODE    NODE
NIC5    SYS     SYS     SYS     SYS     NODE    PIX     NODE    NODE    SYS     SYS     SYS     SYS     NODE     X      NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      NODE
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    NODE    PIX     SYS     SYS     SYS     SYS     NODE    NODE    NODE     X 

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  NIC0: mlx5_1
  NIC1: mlx5_2
  NIC2: mlx5_3
  NIC3: mlx5_4
  NIC4: mlx5_5
  NIC5: mlx5_6
  NIC6: mlx5_7
  NIC7: mlx5_8


ulimit soft: 1048576
```
