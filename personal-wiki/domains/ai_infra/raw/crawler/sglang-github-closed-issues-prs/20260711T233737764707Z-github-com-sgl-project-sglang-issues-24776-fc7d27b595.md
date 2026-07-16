---
source_id: sglang-github-closed-issues-prs
title: '[Bug] running DeepSeek-V4-Pro on B300 server crashes with cookbook param'
canonical_url: https://github.com/sgl-project/sglang/issues/24776
captured_at: '2026-07-11T23:37:37.764707+00:00'
content_hash: fc7d27b595f2fdfe5a113e15a1c3cced50362c39d942abee93980cce2ca0b7c1
---
# [Bug] running DeepSeek-V4-Pro on B300 server crashes with cookbook param

URL: https://github.com/sgl-project/sglang/issues/24776
State: closed
Labels: inactive
Closed at: 2026-07-11T00:33:01Z
Merged at: 

From official cookbook here: https://docs.sglang.io/cookbook/autoregressive/DeepSeek/DeepSeek-V4

I started the model with: 
`SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 \
SGLANG_OPT_SWA_SPLIT_LEAF_ON_INSERT=1 \
SGLANG_OPT_USE_JIT_NORM=1 \
SGLANG_OPT_USE_JIT_INDEXER_METADATA=1 \
SGLANG_OPT_USE_TOPK_V2=1 \
SGLANG_OPT_USE_CUSTOM_ALL_REDUCE_V2=1 \
SGLANG_OPT_SWA_EVICT_DROP_PAGE_MARGIN=1 \
SGLANG_OPT_USE_FAST_MASK_EP=1 \
SGLANG_OPT_FIX_MEGA_MOE_MEMORY=1 \
SGLANG_OPT_FIX_NEXTN_MEGA_MOE=1 \
SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=0 \
NVSHMEM_DISABLE_IB=1 \
SGLANG_OPT_SWA_RELEASE_LEAF_LOCK_AFTER_WINDOW=1 \
SGLANG_OPT_USE_DEEPGEMM_MEGA_MOE=1 \
SGLANG_OPT_FIX_HASH_MEGA_MOE=1 \
SGLANG_OPT_DEEPGEMM_MEGA_MOE_NUM_MAX_TOKENS_PER_RANK=8320 \
sglang serve \
  --trust-remote-code \
  --model-path deepseek-ai/DeepSeek-V4-Pro \
  --tp 8 \
  --dp 8 \
  --enable-dp-attention \
  --moe-a2a-backend deepep \
  --mem-fraction-static 0.835 \
  --cuda-graph-max-bs 544 \
  --swa-full-tokens-ratio 0.075 \
  --chunked-prefill-size 65536 \
  --tokenizer-worker-num 8 \
  --enable-prefill-delayer \
  --deepep-config '{"normal_dispatch":{"num_sms":96},"normal_combine":{"num_sms":96}}' \
  --tool-call-parser deepseekv4 \
  --reasoning-parser deepseek-v4 \
  --host 0.0.0.0 \
  --port 30000`
on single 8*B300 machine.

After running for a period of time, the server will hang with some NCCL and OOM issue.
`[2026-05-09 02:29:39] INFO:     172.24.11.197:0 - "GET /metrics HTTP/1.1" 200 OK
[2026-05-09 02:29:39] INFO:     172.24.11.197:0 - "GET /metrics HTTP/1.1" 200 OK
[rank5]:[W509 02:29:39.495163912 TCPStore.cpp:106] [c10d] sendBytes failed on SocketImpl(fd=122, addr=[localhost]:38184, remote=[localhost]:8875): Broken pipe
Exception raised from sendBytes at /pytorch/torch/csrc/distributed/c10d/Utils.hpp:653 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >) + 0x80 (0x72840977cb80 in /usr/local/lib/python3.12/dist-packages/torch/lib/libc10.so)
frame #1: <unknown function> + 0x5ffc5d1 (0x72835ec735d1 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cpu.so)
frame #2: <unknown function> + 0x5ffce62 (0x72835ec73e62 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cpu.so)
frame #3: <unknown function> + 0x5ffe96e (0x72835ec7596e in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cpu.so)
frame #4: c10d::TCPStore::check(std::vector<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::allocator<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > const&) + 0x30e (0x72835ec7028e in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cpu.so)
frame #5: c10d::ProcessGroupNCCL::HeartbeatMonitor::runLoop() + 0x3c8 (0x72833c1b4e18 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #6: <unknown function> + 0xecdb4 (0x7285020e7db4 in /usr/lib/x86_64-linux-gnu/libstdc++.so.6)
frame #7: <unknown function> + 0x9caa4 (0x728504c56aa4 in /usr/lib/x86_64-linux-gnu/libc.so.6)
frame #8: <unknown function> + 0x129c6c (0x728504ce3c6c in /usr/lib/x86_64-linux-gnu/libc.so.6)

[rank5]:[W509 02:29:39.508328002 ProcessGroupNCCL.cpp:1771] [PG ID 0 PG GUID 0 Rank 5] Failed to check the "should dump" flag on TCPStore, (maybe TCPStore server has shut down too early), with error: Broken pip`

So, should I run it with --tp 8 --dp 1 on a single 8*B300 machine? Is this --tp 8 \
  --dp 8 for 8 machines?
