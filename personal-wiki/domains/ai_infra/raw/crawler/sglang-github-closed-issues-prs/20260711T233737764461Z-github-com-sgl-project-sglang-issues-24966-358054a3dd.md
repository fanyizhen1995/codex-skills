---
source_id: sglang-github-closed-issues-prs
title: '[Bug]  Step3-VL multi-image requests failed'
canonical_url: https://github.com/sgl-project/sglang/issues/24966
captured_at: '2026-07-11T23:37:37.764461+00:00'
content_hash: 358054a3dd671ca4cb652c27f72170e074204ab1ffc251e758bb5a37808873fa
---
# [Bug]  Step3-VL multi-image requests failed

URL: https://github.com/sgl-project/sglang/issues/24966
State: closed
Labels: inactive
Closed at: 2026-07-11T00:33:02Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Step3-VL currently cannot correctly handle multiple image items in the multimodal embedding path.

Both Step3 model implementations contain a single-image assertion in `get_image_feature()`:

```python
assert len(items) == 1  # We only have images.
```

However, in SGLang, `items` can contain multiple `MultimodalDataItem`s. This can happen for a single request with multiple images, or when the multimodal embedding path batches cache-miss image items together. As a result, valid multi-image Step3-VL requests may fail with an assertion error.

There is also a correctness issue after SGLang splits a bundled multi-image processor output into per-image items. Step3 preprocessing stores:

- `pixel_values`: one global image tensor per image
- `num_patches`: one local-patch count per image
- `patch_pixel_values`: a flat concatenation of all local patch tensors

The generic split path can split `pixel_values` and `num_patches` by image, but `patch_pixel_values` is indexed by cumulative patch count rather than image count. For example, if `num_patches = [2, 0, 3]`, then the correct patch ranges are `[0:2]`, `[2:2]`, and `[2:5]`. Without special handling, per-image items can keep the full flat `patch_pixel_values` tensor, causing later images to use patches from earlier images.

This affects Step3-VL multi-image requests, especially when one or more images produce local crops/patches.

### Reproduction

Serve Step3-VL-10B:

```bash
python -m sglang.launch_server \
  --model-path stepfun-ai/Step3-VL-10B \
  --port 30000 \
  --trust-remote-code
```

Send a request with multiple images:

```python
from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:30000/v1",
    timeout=3600,
)

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": "<image_url_1>"},
            },
            {
                "type": "image_url",
                "image_url": {"url": "<image_url_2>"},
            },
            {
                "type": "text",
                "text": "Compare these two images.",
            },
        ],
    }
]

response = client.chat.completions.create(
    model="stepfun-ai/Step3-VL-10B",
    messages=messages,
    max_tokens=512,
    extra_body={"top_k": -1},
)

print(response.choices[0].message.content)
```

Expected behavior:

- Step3-VL should process multiple images in one request.
- Each image should receive only its own local patch features.

Actual behavior:

- The request can fail in `get_image_feature()` with `assert len(items) == 1`.
- If the assert is removed without fixing split logic, local patch features can be associated with the wrong image after per-image item splitting.


### Environment

Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H20
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 535.161.08
PyTorch: 2.11.0+cu129
sglang: 0.0.0.dev1+ge55646ff8
sglang-kernel: 0.4.2+cu129
flashinfer_python: 0.6.8.post1
flashinfer_cubin: 0.6.8.post1
flashinfer_jit_cache: 0.6.8.post1+cu129
triton: 3.6.0
transformers: 5.6.0
torchao: 0.17.0+cu129
numpy: 2.4.3
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
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.99.0
litellm: Module Not Found
torchcodec: 0.11.1+cu129
NVIDIA Topology:
	GPU0	GPU1	GPU2	GPU3	GPU4	GPU5	GPU6	GPU7	NIC0	NIC1	NIC2	NIC3	NIC4	NIC5	NIC6	NIC7	CPU Affinity	NUMA Affinity	GPU NUMA ID
GPU0	 X 	NV18	NV18	NV18	NV18	NV18	NV18	NV18	PIX	NODE	NODE	NODE	SYS	SYS	SYS	SYS	0-47,96-143	0		N/A
GPU1	NV18	 X 	NV18	NV18	NV18	NV18	NV18	NV18	NODE	PIX	NODE	NODE	SYS	SYS	SYS	SYS	0-47,96-143	0		N/A
GPU2	NV18	NV18	 X 	NV18	NV18	NV18	NV18	NV18	NODE	NODE	PIX	NODE	SYS	SYS	SYS	SYS	0-47,96-143	0		N/A
GPU3	NV18	NV18	NV18	 X 	NV18	NV18	NV18	NV18	NODE	NODE	NODE	PIX	SYS	SYS	SYS	SYS	0-47,96-143	0		N/A
GPU4	NV18	NV18	NV18	NV18	 X 	NV18	NV18	NV18	SYS	SYS	SYS	SYS	PIX	NODE	NODE	NODE	48-95,144-191	1		N/A
GPU5	NV18	NV18	NV18	NV18	NV18	 X 	NV18	NV18	SYS	SYS	SYS	SYS	NODE	PIX	NODE	NODE	48-95,144-191	1		N/A
GPU6	NV18	NV18	NV18	NV18	NV18	NV18	 X 	NV18	SYS	SYS	SYS	SYS	NODE	NODE	PIX	NODE	48-95,144-191	1		N/A
GPU7	NV18	NV18	NV18	NV18	NV18	NV18	NV18	 X 	SYS	SYS	SYS	SYS	NODE	NODE	NODE	PIX	48-95,144-191	1		N/A
NIC0	PIX	NODE	NODE	NODE	SYS	SYS	SYS	SYS	 X 	NODE	NODE	NODE	SYS	SYS	SYS	SYS
NIC1	NODE	PIX	NODE	NODE	SYS	SYS	SYS	SYS	NODE	 X 	NODE	NODE	SYS	SYS	SYS	SYS
NIC2	NODE	NODE	PIX	NODE	SYS	SYS	SYS	SYS	NODE	NODE	 X 	NODE	SYS	SYS	SYS	SYS
NIC3	NODE	NODE	NODE	PIX	SYS	SYS	SYS	SYS	NODE	NODE	NODE	 X 	SYS	SYS	SYS	SYS
NIC4	SYS	SYS	SYS	SYS	PIX	NODE	NODE	NODE	SYS	SYS	SYS	SYS	 X 	NODE	NODE	NODE
NIC5	SYS	SYS	SYS	SYS	NODE	PIX	NODE	NODE	SYS	SYS	SYS	SYS	NODE	 X 	NODE	NODE
NIC6	SYS	SYS	SYS	SYS	NODE	NODE	PIX	NODE	SYS	SYS	SYS	SYS	NODE	NODE	 X 	NODE
NIC7	SYS	SYS	SYS	SYS	NODE	NODE	NODE	PIX	SYS	SYS	SYS	SYS	NODE	NODE	NODE	 X

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
