---
source_id: sglang-github-closed-issues-prs
title: more fixes for Nemotron 3 parser for tool call and force nonempty content
canonical_url: https://github.com/sgl-project/sglang/pull/30533
captured_at: '2026-07-13T23:40:05.160685+00:00'
content_hash: 43d9238bc8bce0b3cbed921f0c7ab62dd1d1d0c452f544761a87d9a8415b05f4
---
# more fixes for Nemotron 3 parser for tool call and force nonempty content

URL: https://github.com/sgl-project/sglang/pull/30533
State: closed
Labels: run-ci
Closed at: 2026-07-13T22:50:28Z
Merged at: 2026-07-13T22:50:28Z

1. <tool_call> should be an end of reasoning parser (just like in TensorRT-LLM)
2. When in streaming mode, "force_nonempty_content": true is not respected.

Fix these two issues













































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29256920374](https://github.com/sgl-project/sglang/actions/runs/29256920374)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29256920204](https://github.com/sgl-project/sglang/actions/runs/29256920204)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
