---
source_id: nccl-github-releases
title: 'nccl4py-v0.1.1: fix compatibility issue with cuda.core 0.5.0'
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.1.1
captured_at: '2026-06-26T02:01:31.915456+00:00'
content_hash: f4d9e1ea8d7e2590b9a442b855f80e6de55f4ac4ec34306874d0696fbd012baa
---
# nccl4py-v0.1.1: fix compatibility issue with cuda.core 0.5.0

URL: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.1.1

RSS Summary:
<p>cuda.core 0.5.0 removed "experimental" in the module path, and added expermental/init.py for compatibility, but cuda.core.experimental._stream.IsStreamT and cuda.core.experimental._memory.DevicePointerT are not included, leading to compatibility issue.</p>

Article Body:
