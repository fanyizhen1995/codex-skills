---
source_id: sglang-github-closed-issues-prs
title: Move LoRA cuda-graph buffers and logging into LoRAManager
canonical_url: https://github.com/sgl-project/sglang/pull/31151
captured_at: '2026-07-14T23:40:21.680001+00:00'
content_hash: 6168f00f4e639f08e46baecc99488aa43cd23920410fec7892c2738620f31f89
---
# Move LoRA cuda-graph buffers and logging into LoRAManager

URL: https://github.com/sgl-project/sglang/pull/31151
State: closed
Labels: lora
Closed at: 2026-07-14T07:56:19Z
Merged at: 2026-07-14T07:56:19Z

### mrc-lora-extraction(extract-lora-moe-buffers-prep,non_mechanical_provable): Prep _init_lora_cuda_graph_moe_buffers for extraction

### mrc-lora-extraction(extract-lora-moe-buffers-move,mechanical_provable): Move _init_lora_cuda_graph_moe_buffers to lora.lora_manager (cut+paste)

### mrc-lora-extraction(absorb-init-lora-cuda-graph-moe-buffers-into-ini,non_mechanical_provable): Absorb _init_lora_cuda_graph_moe_buffers into init_lora_manager

The MoE buffer pre-allocation was a separate call right after init_lora_manager() in initialize(); fold it into init_lora_manager so the manager owns its own setup. Drops the stale '# Phase 1 of ...' comment in the process; the ordering constraint (run before init_memory_pool) is preserved since init_lora_manager is still called from initialize() ahead of pool init.

### mrc-lora-extraction(move-lora-load-unload-logging-from-modelrunner-i,non_mechanical_provable): Move LoRA load/unload logging from ModelRunner into LoRAManager

The start/complete (and avail-mem) log lines wrapped the lora_manager calls inside
ModelRunner. Push them down into LoRAManager.{load,unload}_lora_adapter[_from_tensors]
so ModelRunner just delegates; the manager logs around its own private impl. The
init-time lora_paths batch-load keeps calling the unlogged private path, preserving
its no-log behavior.

### mrc-lora-extraction(make-init-lora-cuda-graph-moe-buffers-public,non_mechanical_provable): Make init_lora_cuda_graph_moe_buffers public

It is imported and called across modules, so drop the leading underscore.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316237765](https://github.com/sgl-project/sglang/actions/runs/29316237765)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316237537](https://github.com/sgl-project/sglang/actions/runs/29316237537)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
