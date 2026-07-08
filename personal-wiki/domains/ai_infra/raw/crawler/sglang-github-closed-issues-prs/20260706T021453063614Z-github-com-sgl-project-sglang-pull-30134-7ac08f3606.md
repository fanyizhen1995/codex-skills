---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Freeze the static flag groups at the end of scheduler init (stack
  8/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30134
captured_at: '2026-07-06T02:14:53.063614+00:00'
content_hash: 7ac08f360602255cde4af73650a88d20860daa5c3a23b3475abedbde01405d2b
---
# [refactor] Freeze the static flag groups at the end of scheduler init (stack 8/10)

URL: https://github.com/sgl-project/sglang/pull/30134
State: closed
Labels: 
Closed at: 2026-07-05T07:01:50Z
Merged at: 

Unit 8 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077). Based on #30133.

The config-resolution lifecycle of a scheduler process now has an end point:
after every load-time stage has run (target and draft model init, the
weight-resolved kv-cache dtype), Scheduler.__init__ locks the static flag
groups via freeze_flags(). flags.capture stays writable; recording a runtime
override or re-publishing after the freeze raises. Placed at scheduler-init
end rather than alloc_memory_pool because draft (NextN) model init — a
load-time resolution stage — runs after the target runner's memory pool is
allocated.

Also removes the dead instance write of use_mla_backend on the published
ServerArgs (ModelRunner.__init__): its readers migrated to the runner's own
attribute, and the write shadowed the ServerArgs.use_mla_backend() method
with a bool on the published instance. Ratchet baseline 346 -> 341.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721913859](https://github.com/sgl-project/sglang/actions/runs/28721913859)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721913810](https://github.com/sgl-project/sglang/actions/runs/28721913810)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
