---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] fix quickreduce acc error in cudagraph mode'
canonical_url: https://github.com/sgl-project/sglang/pull/29508
captured_at: '2026-07-15T23:40:28.379133+00:00'
content_hash: 9a1f9ae94f2206b0daa8936e1d08b70a04749cc8de99f9a3258a2a8bb5ba55f2
---
# [Bugfix] fix quickreduce acc error in cudagraph mode

URL: https://github.com/sgl-project/sglang/pull/29508
State: closed
Labels: amd, sgl-kernel, run-ci, bypass-fastfail
Closed at: 2026-07-15T05:16:03Z
Merged at: 2026-07-15T05:16:03Z

**1. cause:**
Once `flag_color` is fixed by `graph`, it remains unchanged for each round 
→ The written flag value repeats in each round and cannot be distinguished from the residual value of the previous round
 → The waiting party is prematurely satisfied by the old value and is immediately granted access
 → At this point, since the data for the current round has not yet been fully transmitted, the system reads the old data next, resulting in an error

**2. repro code**
```
import argparse
import multiprocessing
import os

# quick-reduce reads these envs when QuickAllReduce is constructed; set them
# before importing sglang so the (cached) env values are correct.
# FP = lossless regime so the all-reduce is bit-exact for small fp16 integers.
os.environ.setdefault("ROCM_QUICK_REDUCE_QUANTIZATION", "FP")
os.environ.setdefault("ROCM_QUICK_REDUCE_CAST_BF16_TO_FP16", "0")

import torch
import torch.distributed as dist

from sglang.srt.distributed.device_communicators.quick_all_reduce import (
    QuickAllReduce,
)


def worker(rank, world_size):
    device = torch.device(f"cuda:{rank}")
    torch.cuda.set_device(device)

    # gloo (CPU) group: QuickAllReduce must be attached to a non-NCCL group; it
    # is used only for the one-time IPC-handle exchange.
    dist.init_process_group(
        backend="gloo",
        init_method="tcp://127.0.0.1:29500",
        rank=rank,
        world_size=world_size,
    )

    qr = QuickAllReduce(group=dist.group.WORLD, device=device)
    assert not qr.disabled, (
        "quick-reduce unavailable on this arch/env "
        "(needs ROCm MI300 gfx94/gfx95, even GPU count, same node, "
        "and a non-NONE ROCM_QUICK_REDUCE_QUANTIZATION)."
    )

    regime = os.environ["ROCM_QUICK_REDUCE_QUANTIZATION"]
    N = 1 << 21  # 2M fp16 = 4 MB, above qr thresholds for the direct call path
    inp = torch.empty(N, dtype=torch.float16, device=device)
    out = torch.empty(N, dtype=torch.float16, device=device)

    # Every rank contributes the SAME value v in a round, so the true cross-rank
    # all-reduce sum is simply world * v.
    def expected(v):
        return float(world_size * v)

    if rank == 0:
        print(
            f"[repro] world_size={world_size} elems={N} regime={regime} fp16",
            flush=True,
        )

    # Warmup, then capture a graph with EXACTLY ONE quick-reduce (isolated qr,
    # so it is the sole writer of its flag slot -- the condition that triggers
    # the stale-flag bug).
    inp.fill_(1.0)
    qr.quick_all_reduce(inp, out=out)
    torch.cuda.synchronize()
    dist.barrier()

    g = torch.cuda.CUDAGraph()
    with torch.cuda.graph(g):
        qr.quick_all_reduce(inp, out=out)
    torch.cuda.synchronize()
    dist.barrier()

    for v in range(10):
        inp.fill_(float(v))  # in-place: same value on every rank
        dist.barrier()
        g.replay()
        torch.cuda.synchronize()
        dist.barrier()
        got = out.float()
        expect = expected(v)
        if rank == 0:
            print(f"round {v}: got={got[:10]}, expected={expect}", flush=True)

    dist.destroy_process_group()


def run_multiprocessing(world_size):
    processes = []
    for rank in range(world_size):
        p = multiprocessing.Process(target=worker, args=(rank, world_size))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world_size",
        type=int,
        default=4,
        help="number of processes / GPUs to use",
    )
    args = parser.parse_args()

    multiprocessing.set_start_method("spawn")
    run_multiprocessing(world_size=args.world_size)


```

**3.solution**
Refer to `customallreduce` and use a pointer to maintain the `flag_color` for each block, passing it as a pointer to the device side for execution.



**4.This change will not affect performance.**


**5.Validation result**
original:
round 0: got=tensor([0., 0., 0., 0., 0., 0., 0., 0., 0., 0.], device='cuda:0'), expected=0.0
round 1: got=tensor([1., 1., 1., 1., 1., 1., 1., 1., 1., 1.], device='cuda:0'), expected=4.0
round 2: got=tensor([5., 5., 5., 5., 5., 5., 5., 5., 5., 5.], device='cuda:0'), expected=8.0
round 3: got=tensor([10., 10., 10., 10., 10., 10., 10., 10., 10., 10.], device='cuda:0'), expected=12.0
round 4: got=tensor([14., 14., 14., 14., 14., 14., 14., 14., 14., 14.], device='cuda:0'), expected=16.0
round 5: got=tensor([19., 19., 19., 19., 19., 19., 19., 19., 19., 19.], device='cuda:0'), expected=20.0
round 6: got=tensor([23., 23., 23., 23., 23., 23., 23., 23., 23., 23.], device='cuda:0'), expected=24.0
round 7: got=tensor([28., 28., 28., 28., 28., 28., 28., 28., 28., 28.], device='cuda:0'), expected=28.0
round 8: got=tensor([32., 32., 32., 32., 32., 32., 32., 32., 32., 32.], device='cuda:0'), expected=32.0
round 9: got=tensor([36., 36., 36., 36., 36., 36., 36., 36., 36., 36.], device='cuda:0'), expected=36.0

after modification
round 0: got=tensor([0., 0., 0., 0., 0., 0., 0., 0., 0., 0.], device='cuda:0'), expected=0.0
round 1: got=tensor([4., 4., 4., 4., 4., 4., 4., 4., 4., 4.], device='cuda:0'), expected=4.0
round 2: got=tensor([8., 8., 8., 8., 8., 8., 8., 8., 8., 8.], device='cuda:0'), expected=8.0
round 3: got=tensor([12., 12., 12., 12., 12., 12., 12., 12., 12., 12.], device='cuda:0'), expected=12.0
round 4: got=tensor([16., 16., 16., 16., 16., 16., 16., 16., 16., 16.], device='cuda:0'), expected=16.0
round 5: got=tensor([20., 20., 20., 20., 20., 20., 20., 20., 20., 20.], device='cuda:0'), expected=20.0
round 6: got=tensor([24., 24., 24., 24., 24., 24., 24., 24., 24., 24.], device='cuda:0'), expected=24.0
round 7: got=tensor([28., 28., 28., 28., 28., 28., 28., 28., 28., 28.], device='cuda:0'), expected=28.0
round 8: got=tensor([32., 32., 32., 32., 32., 32., 32., 32., 32., 32.], device='cuda:0'), expected=32.0
round 9: got=tensor([36., 36., 36., 36., 36., 36., 36., 36., 36., 36.], device='cuda:0'), expected=36.0












































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28848133402](https://github.com/sgl-project/sglang/actions/runs/28848133402)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28848133182](https://github.com/sgl-project/sglang/actions/runs/28848133182)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
