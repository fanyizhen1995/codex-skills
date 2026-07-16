---
source_id: sglang-github-closed-issues-prs
title: Fix patch targets in test_tokenizer_batch_encode
canonical_url: https://github.com/sgl-project/sglang/pull/23042
captured_at: '2026-07-15T23:40:28.379653+00:00'
content_hash: 8726c68b5ed842b036252815222806eab13badc099dc2a6354890554a8e53aea
---
# Fix patch targets in test_tokenizer_batch_encode

URL: https://github.com/sgl-project/sglang/pull/23042
State: closed
Labels: intel, xpu, run-ci
Closed at: 2026-07-15T05:03:37Z
Merged at: 

## Fix patch targets in test_tokenizer_batch_encode

### Summary
`test/manual/test_tokenizer_batch_encode.py` was failing in `setUp` with:

```
AttributeError: <module 'sglang.srt.utils'> does not have the attribute 'get_zmq_socket'
```

The test patched `sglang.srt.utils.get_zmq_socket` and
`sglang.srt.utils.hf_transformers_utils.get_tokenizer`, but neither name is
exposed at those locations. `TokenizerManager` imports them as:

```python
from sglang.srt.utils.network import get_zmq_socket
from sglang.srt.utils.hf_transformers_utils import get_tokenizer
```
AttributeError: <module 'sglang.srt.utils'> does not have the attribute 'get_zmq_socket'
```
## Changes

```sglang.srt.utils.get_zmq_socket → sglang.srt.managers.tokenizer_manager.get_zmq_socket
sglang.srt.utils.hf_transformers_utils.get_tokenizer → sglang.srt.managers.tokenizer_manager.get_tokenizer
```

## After (6 PASSED)



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->[Run #26013692327](https://github.com/sgl-project/sglang/actions/runs/26013692327)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: **Not enabled** — add `run-ci-extra` label to opt in.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
