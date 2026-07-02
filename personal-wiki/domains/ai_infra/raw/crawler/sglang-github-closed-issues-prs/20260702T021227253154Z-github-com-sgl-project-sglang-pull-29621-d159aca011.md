---
source_id: sglang-github-closed-issues-prs
title: Extract reusable VMM shareable-handle helpers from register_graph_inputs
canonical_url: https://github.com/sgl-project/sglang/pull/29621
captured_at: '2026-07-02T02:12:27.253154+00:00'
content_hash: d159aca011359dbf814cfcccf0e3d8a7212966269e7b6bc9bc32c613097747ad
---
# Extract reusable VMM shareable-handle helpers from register_graph_inputs

URL: https://github.com/sgl-project/sglang/pull/29621
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-01T21:02:01Z
Merged at: 2026-07-01T21:02:01Z

## Why

`CustomAllReduceV2`'s `register_graph_inputs` shares a VMM
(`expandable_segments`) allocation across ranks the usual way: export each
allocation's handle (FABRIC, or a POSIX fd when FABRIC is unavailable),
all-gather it, then import + `cuMemMap` the peer allocation.

It inlines all of this in one long function, even though the export / exchange /
import-and-map steps are generic and reusable by other VMM peer-pointer code.
Extracting them enables that reuse and makes `register_graph_inputs` easier to
read.

## What

Lift that machinery into reusable module-level functions in `vmm_utils.py`
(renamed from `custom_all_reduce_vmm_utils.py`, since it is no longer
all-reduce-specific):

- `export_shareable_handles` — FABRIC export with a POSIX-fd fallback (all-rank vote)
- `exchange_posix_fds` — SCM_RIGHTS fd exchange over a UNIX socket
- `import_and_map_alloc` / `map_chunk_into_span` / `import_peer_handle`
- helpers: `check_drv`, `make_rw_access_desc`, `all_ranks_ok`, `release_mappings`

`register_graph_inputs` now orchestrates these. No behavior change — the
`cuMem*` call sequence and CUDA flags are identical; only one shared error
string was generalized.

## Test

Adds `test/registered/unit/distributed/test_vmm_utils.py` — round-trips the
helpers across ranks for both transports (POSIX via `cuMemCreate(POSIX_FD)`,
FABRIC where an NVLink fabric is present) and both single-base and multi-chunk
span mapping. `test_custom_all_reduce` continues to cover the FABRIC
`register_graph_inputs` path under `expandable_segments`.



































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28499080854](https://github.com/sgl-project/sglang/actions/runs/28499080854)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28499196626](https://github.com/sgl-project/sglang/actions/runs/28499196626)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
