---
source_id: sglang-github-closed-issues-prs
title: Support grad injection and step override in the dumper's model dump
canonical_url: https://github.com/sgl-project/sglang/pull/30657
captured_at: '2026-07-09T23:36:35.328502+00:00'
content_hash: a5108f70d0f209da2b3764b6f99feb11787255b8e7b099214949725647fa5f62
---
# Support grad injection and step override in the dumper's model dump

URL: https://github.com/sgl-project/sglang/pull/30657
State: closed
Labels: run-ci
Closed at: 2026-07-09T12:26:05Z
Merged at: 2026-07-09T12:26:05Z

Two additions for dumping training-side (Megatron) model params so they can be
compared against a baseline:

- dump_model / _dump_inner accept an optional get_grad callable.
  Distributed-optimizer setups do not populate param.grad; the caller knows
  where the real grad lives (e.g. main_grad buckets) and injects the accessor,
  e.g. get_grad=lambda p: p.grad if p.grad is not None else getattr(p, 'main_grad', None).
  Without get_grad the dumper keeps reading param.grad as before.
- Both methods also accept an explicit step override so param dumps can be
  recorded under the training step they belong to instead of the dumper's
  ambient step counter.

Tests cover get_grad injection (override, custom grad storage, None-suppression,
and param.grad-only default) and the step override (explicit step wins over the
ambient counter; absent step keeps it).





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29017806821](https://github.com/sgl-project/sglang/actions/runs/29017806821)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29017806599](https://github.com/sgl-project/sglang/actions/runs/29017806599)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
