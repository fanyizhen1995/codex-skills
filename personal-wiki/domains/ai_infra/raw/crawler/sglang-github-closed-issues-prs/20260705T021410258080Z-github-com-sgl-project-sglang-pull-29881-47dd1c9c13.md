---
source_id: sglang-github-closed-issues-prs
title: Avoid logits multimem all-gather on cross-node TP groups
canonical_url: https://github.com/sgl-project/sglang/pull/29881
captured_at: '2026-07-05T02:14:10.258080+00:00'
content_hash: 47dd1c9c1390548ecdd99f82ecc981cc35d9e0aa68494322adbe4cec16e3750e
---
# Avoid logits multimem all-gather on cross-node TP groups

URL: https://github.com/sgl-project/sglang/pull/29881
State: closed
Labels: run-ci
Closed at: 2026-07-04T07:24:58Z
Merged at: 2026-07-04T07:24:58Z

## Summary

- disable the logits `MultimemAllGatherer` fast path when the TP process group spans multiple nodes
- fall back to the existing normal tensor-parallel all-gather path before calling `torch.distributed._symmetric_memory.rendezvous`
- add unit coverage for cross-node vs single-node TP group behavior

## Why

We hit a startup hang on a multi-node H20 deployment where logits multimem all-gather attempted to create symmetric memory over a cross-node TP group during target-verify CUDA graph capture. This path failed while establishing the symmetric-memory handle and left the server unable to become ready. SGLang already disables other custom all-reduce fast paths for process groups spanning nodes; this applies the same guard to logits multimem all-gather.

## Reproduction environment

Hardware/topology:

- 4 H20 hosts, each 8 x NVIDIA H20-3e
- TP16: 2 hosts x 8 GPUs
- TP32: 4 hosts x 8 GPUs
- tensor-parallel groups span multiple hosts

Software:

- PyTorch `2.11.0+cu130`
- CUDA `13.0`
- SGLang source based on a recent `main`/deployment branch containing GLM-5.2 support

Models:

- GLM-5.2 FP8
- GLM-5.2 BF16

FP8 TP16 launch shape:

```bash
python3 -m sglang.launch_server \
  --model-path <GLM-5.2-FP8-path> \
  --served-model-name <served-model-name> \
  --host 0.0.0.0 --port 30000 \
  --tp-size 16 --nnodes 2 --node-rank <0|1> \
  --dist-init-addr <rank0-host>:<port> \
  --context-length 1048576 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --mem-fraction-static 0.80 \
  --max-running-requests 16 \
  --cuda-graph-max-bs-decode 16 \
  --enable-metrics --enable-mfu-metrics \
  --disable-custom-all-reduce \
  --disable-overlap-schedule
```

BF16 TP32 launch shape:

```bash
python3 -m sglang.launch_server \
  --model-path <GLM-5.2-BF16-path> \
  --served-model-name <served-model-name> \
  --host 0.0.0.0 --port 30000 \
  --tp-size 32 --nnodes 4 --node-rank <0|1|2|3> \
  --dist-init-addr <rank0-host>:<port> \
  --context-length 1048576 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --mem-fraction-static 0.75 \
  --max-running-requests 16 \
  --cuda-graph-max-bs-decode 32 \
  --enable-metrics --enable-mfu-metrics \
  --disable-custom-all-reduce \
  --disable-overlap-schedule
```

Observed logs:

```text
Capture target verify CUDA graph begin. backend=full, num_tokens_per_bs=4, ...
multimem all-gather disabled (Failed to send fd: No such file or directory)
```

A `py-spy` snapshot showed the blocked path under:

```text
logits_processor.py:_get_logits
triton_symm_mem_ag.MultimemAllGatherer
torch.distributed._symmetric_memory.rendezvous
```



Temporary workaround used during deployment:

```bash
export SGLANG_DISABLE_LOGITS_MULTIMEM_AG=1
```

This avoids constructing the logits multimem all-gather path and lets SGLang use the existing normal tensor-parallel all-gather fallback. It was used as a deployment workaround before this PR, together with CUDA graph and MTP still enabled.

With a local patch that disabled only logits multimem all-gather, the same deployment became ready with CUDA graph and MTP still enabled. A validated 1M FP8 TP16 service used:

```bash
--max-total-tokens 1048576 --kv-cache-dtype fp8_e4m3
```

and reported:

```text
context_length=1048576
max_total_tokens=1048576
max_total_num_tokens=1048576
kv_cache_dtype=fp8_e4m3
speculative_algorithm=EAGLE
disable_cuda_graph=False
disable_decode_cuda_graph=False
```

## Tests

```bash
PYTHONPATH=python python3 -m pytest test/srt/test_triton_symm_mem_ag.py -q
python3 -m py_compile python/sglang/srt/distributed/device_communicators/triton_symm_mem_ag.py test/srt/test_triton_symm_mem_ag.py
git diff --check
```

<sub>✨ Presented to you with <a href=" ">Mind Lab</a > — A Lab for Experiential Intelligence.</sub>









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28634147034](https://github.com/sgl-project/sglang/actions/runs/28634147034)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28689676978](https://github.com/sgl-project/sglang/actions/runs/28689676978)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
