---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Move the capture-time torch.compile flag to flags.capture (stack
  9/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30135
captured_at: '2026-07-06T02:14:53.063369+00:00'
content_hash: 50efa8a6b4b239de0cd262586fad0eae014647ab0b51a362c61a56cf97d9700e
---
# [refactor] Move the capture-time torch.compile flag to flags.capture (stack 9/10)

URL: https://github.com/sgl-project/sglang/pull/30135
State: closed
Labels: deepseek, npu
Closed at: 2026-07-05T07:01:53Z
Merged at: 

Unit 9 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077). Based on #30134.

enable_torch_compile becomes a leaf on the non-frozen capture tier: seeded
from the published config at set_server_args (defaults for sentinel/mock
publishes), carried across runtime-stage re-resolves so recording cannot
clobber a capture-time write, and writable after freeze_flags(). The warmup
write (a model whose _can_torch_compile is False disables compile) and all
twelve srt readers — cuda-graph runners, draft runners, the CPU graph
runner, the NPU backend, the DeepSeek dual-stream check — flip to
get_flags().capture.enable_torch_compile; the server_args mutation retires.
server_args.enable_torch_compile is now pristine user input.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721914233](https://github.com/sgl-project/sglang/actions/runs/28721914233)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721914196](https://github.com/sgl-project/sglang/actions/runs/28721914196)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
