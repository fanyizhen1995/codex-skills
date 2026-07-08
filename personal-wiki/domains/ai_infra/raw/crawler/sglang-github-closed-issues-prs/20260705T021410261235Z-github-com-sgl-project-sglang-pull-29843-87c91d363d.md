---
source_id: sglang-github-closed-issues-prs
title: '[trtllm_mha] Fuse cuda-graph metadata rebuild into one triton kernel'
canonical_url: https://github.com/sgl-project/sglang/pull/29843
captured_at: '2026-07-05T02:14:10.261235+00:00'
content_hash: 87c91d363d12d20d72cae8224957913ee1250ca3b134f058de13221e71bf61a7
---
# [trtllm_mha] Fuse cuda-graph metadata rebuild into one triton kernel

URL: https://github.com/sgl-project/sglang/pull/29843
State: closed
Labels: blackwell, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-04T05:24:28Z
Merged at: 2026-07-04T05:24:28Z

## Motivation

The TRTLLM MHA backend's CUDA-graph metadata path rebuilds the page table(s)
and seqlen buffers with ~25 small aten ops per graph replay (index gathers,
`floor_divide`, `cumsum`, dtype casts, copies). On some host CPUs this is
~0.7-1.0 ms of pure dispatch, and it repeats several times per decode step
(draft-decode steps + target-verify + draft-extend) on every TP rank. The
resulting per-rank CPU jitter skews `cudaGraphLaunch` across ranks and is paid
as spin time inside the first custom all-reduce of every replayed graph.

## Modifications

- Add `trtllm_mha_graph_metadata.py`: a single fused Triton kernel
  (`update_trtllm_mha_graph_metadata`) that rebuilds the whole metadata set in
  ONE launch — `cache_seqlens`, `cu_seqlens_k`, optional `cu_seqlens_q` (three
  q-modes: preset / cumsum / strided), the full `page_table`, the optional
  SWA-translated `swa_page_table`, and the optional `swa_out_cache_loc` (with
  the `-1` sentinel guard preserved). It builds on the existing on-device
  page-table work (`trtllm_mha_page_table`): reads are bounded by the on-device
  `cache_seqlens`, and the table is written to the static `max_num_pages` width,
  so there is still no host max / `seq_lens_cpu` D2H sync.

- Wire the fused kernel into `trtllm_mha_backend.py`'s cuda-graph path using the
  existing base-class split: `init_forward_metadata_out_graph` binds the
  per-batch buffer slices (host prep) and the new `init_forward_metadata_in_graph`
  launches the fused kernel as the graph-recorded GPU op. This replaces the
  previous separate `_fill_page_table_device` / cumsum / copy calls. The
  draft-extend path now reads the static per-request query width captured into
  the graph shape (`metadata.max_seq_len_q`) instead of inspecting replay-time
  accept-token tensors, so the recorded body contains no `.item()` — satisfying
  the in-graph lint contract.

- Add the in-graph metadata call to the three EAGLE / MTP draft cuda-graph
  runners (`eagle_draft_extend`, `frozen_kv_mtp`,
  `multi_layer_eagle_draft_extend`) so the fused kernel is recorded inside their
  captured graphs (the normal decode path already calls the in-graph hook via
  the decode cuda-graph runner).

- Add `test/registered/attention/test_trtllm_mha_graph_metadata.py`: correctness
  tests validating the fused kernel against a pure-aten reference across batch
  sizes, seqlen offsets, all three q-modes, and SWA on/off (including the `-1`
  sentinel and zero-padded tail), plus hook-dispatch tests and a
  record-inside-a-CUDA-graph replay test.

### Notes on upstream divergence

This was originally developed on top of the on-device page-table build. It ports
cleanly onto current `main`: the base attention backend already defines the
`init_forward_metadata_out_graph` / `init_forward_metadata_in_graph` split and
the decode cuda-graph runner already invokes the in-graph hook, so the fused
kernel slots directly into that contract. `trtllm_mha_page_table` is retained
(the eager `init_forward_metadata` path still uses `_fill_page_table_device`).

Runtime kernel/e2e validation is pending CI (developed without local GPU
access); the change compiles and is wired to the existing graph-capture
contract.

## Original commits

- `1994a9f0`





















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28692090030](https://github.com/sgl-project/sglang/actions/runs/28692090030)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28692089937](https://github.com/sgl-project/sglang/actions/runs/28692089937)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
