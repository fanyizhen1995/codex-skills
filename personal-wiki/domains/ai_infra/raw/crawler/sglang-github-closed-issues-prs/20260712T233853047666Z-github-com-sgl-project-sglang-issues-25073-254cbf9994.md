---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Gemma4 tool-call parser sets streaming `tool_calls[*].index` to the
  tool''s position in the request, not the call index'
canonical_url: https://github.com/sgl-project/sglang/issues/25073
captured_at: '2026-07-12T23:38:53.047666+00:00'
content_hash: 254cbf999409a219aa287ba4246f9ccda377f6a3c8c13eb413e58134dd8376e9
---
# [Bug] Gemma4 tool-call parser sets streaming `tool_calls[*].index` to the tool's position in the request, not the call index

URL: https://github.com/sgl-project/sglang/issues/25073
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:47Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

The Gemma4 tool-call detector (`python/sglang/srt/function_call/gemma4_detector.py`) sets `ToolCallItem.tool_index` to the position of the function in the request's `tools` list, instead of the position of the call inside the assistant's `tool_calls` array.

As a result, when the same function is called more than once in one response, every call shares the same `index` in the OpenAI streaming protocol. OpenAI-compatible clients then merge all argument deltas of repeated calls into one call (so only the first set of arguments survives), even though each call gets a unique `id`. The same bug is present in the non-streaming path (`detect_and_parse`) — `tool_index` is taken from `_get_tool_indices(tools).get(func_name, -1)` rather than from the call enumeration.

**Concrete example.** Request with `tools = [get_menu, add_to_cart, …]`. The model emits one `get_menu` followed by three `add_to_cart` calls; streaming chunks come out like this:

```
ChoiceDeltaToolCall(index=0, id='call_9f50…', function=…(name='get_menu',    arguments=''))
ChoiceDeltaToolCall(index=0, id=None,         function=…(name=None,           arguments='{}'))
ChoiceDeltaToolCall(index=1, id='call_80fa…', function=…(name='add_to_cart', arguments=''))
ChoiceDeltaToolCall(index=1, id=None,         function=…(name=None,           arguments='{"item_id":"p_pep","qty":1}'))
ChoiceDeltaToolCall(index=1, id='call_1d77…', function=…(name='add_to_cart', arguments=''))   # should be index=2
ChoiceDeltaToolCall(index=1, id=None,         function=…(name=None,           arguments='{"item_id":"p_pep","modifiers":["no_onion"],"qty":1}'))
ChoiceDeltaToolCall(index=1, id='call_a6c6…', function=…(name='add_to_cart', arguments=''))   # should be index=3
ChoiceDeltaToolCall(index=1, id=None,         function=…(name=None,           arguments='{"item_id":"cola_15","qty":1}'))
```

Expected indices: `0, 1, 2, 3` (one per call). Actual: all three `add_to_cart` deltas share `index=1` because `add_to_cart` is the second entry in the `tools` list.

### Root cause

In `gemma4_detector.py` both streaming chunks (name and arguments) and the non-streaming path use `self._tool_indices.get(func_name, -1)` / `tool_indices.get(func_name, -1)` as `tool_index`. The detector already increments `self.current_tool_id` on every `call:name{` chunk but never reads it back when constructing `ToolCallItem`.

Other detectors (`deepseekv3/v31/v32`, `glm4_moe`, `glm47_moe`, `kimik2` streaming, `minimax_m2`, `step3`, `qwen3_coder`, `hunyuan` streaming, …) correctly use `self.current_tool_id`. `lfm2_detector.py:153` and `pythonic_detector.py:102` even spell it out in a comment: *"Use the call index in the response, not tool position"*.

### Suggested fix

In `gemma4_detector.py`:
- `parse_streaming_increment`: use `self.current_tool_id` for both the name chunk and the arguments chunk.
- `detect_and_parse`: use `enumerate(matches)` for `tool_index`.
- `self._tool_indices` becomes unused and can be removed.

I have a patch ready and can open a PR.

The same anti-pattern of using `tool_indices.get(name, -1)` for `tool_index` also lives in `hunyuan_detector.py:247` (non-stream path), `internlm_detector.py:131`, `poolside_v1_detector.py:247` (non-stream path), and `base_format_detector.py:92` (`parse_base_json`). Likely the same bug there, but it's out of scope for this issue.

Speculative decoding / MTP is **not** required to reproduce — the bug is purely in the parser.

### Reproduction

Launch a Gemma 4 model with the `gemma4` tool-call parser:

```bash
python -m sglang.launch_server \
    --model-path google/gemma-4-31b-it \
    --tool-call-parser gemma4 \
    --host 0.0.0.0 --port 30000
```

Send a request with multiple tools where the model is likely to call one of them more than once:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

tools = [
    {"type": "function", "function": {
        "name": "get_menu",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "add_to_cart",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id":   {"type": "string"},
                "qty":       {"type": "integer"},
                "modifiers": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["item_id", "qty"],
        },
    }},
]

stream = client.chat.completions.create(
    model="gemma-4",
    stream=True,
    tools=tools,
    messages=[
        {"role": "system", "content":
            "First call get_menu(), then add three items to the cart with "
            "separate add_to_cart calls (one with modifiers)."},
        {"role": "user", "content":
            "I want a pepperoni pizza, another one without onion, and a coke."},
    ],
)

for chunk in stream:
    for tc in (chunk.choices[0].delta.tool_calls or []):
        print(tc)
```

The three `add_to_cart` deltas all come with `index=1` instead of `1, 2, 3`. Equivalently, the non-streaming counterpart returns four `tool_calls` whose `index` field is `0, 1, 1, 1`.

### Environment

```
Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1: NVIDIA H100 80GB HBM3
GPU 0,1 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 535.161.08
PyTorch: 2.11.0+cu130
sglang: 0.5.12.dev93+g9f64d51c7
sglang-kernel: 0.4.2
flashinfer_python: 0.6.8.post1
flashinfer_cubin: 0.6.8.post1
flashinfer_jit_cache: 0.6.8.post1+cu130
triton: 3.6.0
transformers: 5.8.0.dev0
torchao: 0.17.0+cu130
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.13.0
interegular: 0.3.3
modelscope: 1.36.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.3
python-multipart: 0.0.27
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.0
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.98.1
litellm: Module Not Found
torchcodec: 0.11.1+cu130

NVIDIA Topology:
        GPU0    GPU1    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    0-89    0               N/A
GPU1    NV18     X      0-89    0               N/A

Legend:
  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

Hypervisor vendor:: KVM
ulimit soft: 65536
```
