---
source_id: sglang-github-closed-issues-prs
title: Make KvVmmArena JIT stub unique per process
canonical_url: https://github.com/sgl-project/sglang/pull/30702
captured_at: '2026-07-09T23:36:35.320508+00:00'
content_hash: d0de33df5ce342ee847c309d25e49b974ff99a5bb1c14a7fe474562156896703
---
# Make KvVmmArena JIT stub unique per process

URL: https://github.com/sgl-project/sglang/pull/30702
State: closed
Labels: run-ci
Closed at: 2026-07-09T22:56:27Z
Merged at: 2026-07-09T22:56:27Z

Problem

The KvVmmArena JIT stub .so is built in a host-shared tempdir. With only a per-instance suffix, co-located engine processes build the same-named .so and race on the shared build dir/main.cpp — one process can compile another's source and load a .so missing its own symbols (undefined-symbol crash).

Fix

Suffix the stub per (process, arena instance) and give each stub its own build directory, so neither co-located processes nor multiple arenas in one process share ninja scratch or the .so.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29054578941](https://github.com/sgl-project/sglang/actions/runs/29054578941)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29054727712](https://github.com/sgl-project/sglang/actions/runs/29054727712)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
