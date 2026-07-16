---
source_id: sglang-github-closed-issues-prs
title: Extract init_torch_distributed and refactor into functions
canonical_url: https://github.com/sgl-project/sglang/pull/31152
captured_at: '2026-07-14T23:40:21.680228+00:00'
content_hash: 0b37a5fc5f6e90c5cbef0588fc35812a2612062ef8b74f412fe9a4d668529bf8
---
# Extract init_torch_distributed and refactor into functions

URL: https://github.com/sgl-project/sglang/pull/31152
State: closed
Labels: 
Closed at: 2026-07-14T07:56:58Z
Merged at: 2026-07-14T07:56:58Z

### mrc-init-torch-distributed(init-dist-prep,non_mechanical_provable): Prep init_torch_distributed for extraction: @staticmethod + 15 kwargs + TorchDistributedResult

De-self in place: the method becomes a kwargs @staticmethod returning a
frozen TorchDistributedResult; the call site unpacks the result onto the
runner fields. The body stays at its original position in the class. Stage
the destination bootstrap module with its header + the result struct.

### mrc-init-torch-distributed(init-dist-move,mechanical_provable): Move init_torch_distributed to distributed.bootstrap (cut+paste)

### mrc-init-torch-distributed(init-dist-wrapper-postpare,non_mechanical_provable): Reintroduce the init_torch_distributed orchestration wrapper and requalify through the distributed.bootstrap module import

Wrap the moved function back into the init_torch_distributed method
(result unpacking onto the runner fields) and route the call through the
bootstrap module import instead of the bare function import.

### mrc-init-torch-distributed(init-dist-extract-backend,non_mechanical_provable): Extract _resolve_backend from init_torch_distributed

Move backend resolution (default + mooncake override + IB device filter)
to a private free function below init_torch_distributed.

### mrc-init-torch-distributed(init-dist-extract-init-method,non_mechanical_provable): Extract _resolve_dist_init_method from init_torch_distributed

Move the 3-branch dist init URL resolution (env override / dist_init_addr /
host fallback) into a private free function.

### mrc-init-torch-distributed(init-dist-extract-all-reduce-flags,non_mechanical_provable): Extract _set_all_reduce_flags from init_torch_distributed

Move the three custom/mscclpp/torch_symm_mem all-reduce setters into a
private free function.

### mrc-init-torch-distributed(init-dist-extract-cpu-threads,non_mechanical_provable): Extract _init_cpu_threads_env from init_torch_distributed

Move the CPU branch (amx/arm64 init + shm_allgather fake + warning) into
a private free function. The cpu/non-cpu dispatch stays at the caller.

### mrc-init-torch-distributed(init-dist-extract-parallel-groups,non_mechanical_provable): Extract _init_parallel_groups from init_torch_distributed

Move the four parallel-init calls (init_distributed_environment +
initialize_model_parallel + initialize_dp_attention + npu
register_sgl_tp_rank) into a private free function.

### mrc-init-torch-distributed(init-dist-extract-prewarm-nccl,non_mechanical_provable): Extract _prewarm_nccl from init_torch_distributed

Move the NCCL/RCCL warmup all_reduce body into a private free function;
the enable guard stays at the caller to keep the helper signature narrow.

### mrc-init-torch-distributed(init-dist-extract-memory-balance,non_mechanical_provable): Extract _check_tp_memory_balance from init_torch_distributed

Move the 90% memory imbalance check (raise vs warn based on env flag)
into a private free function; the tp_size/draft guard stays at the caller.
Includes black autoformat of the moved f-string.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29316275492](https://github.com/sgl-project/sglang/actions/runs/29316275492)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316275300](https://github.com/sgl-project/sglang/actions/runs/29316275300)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
