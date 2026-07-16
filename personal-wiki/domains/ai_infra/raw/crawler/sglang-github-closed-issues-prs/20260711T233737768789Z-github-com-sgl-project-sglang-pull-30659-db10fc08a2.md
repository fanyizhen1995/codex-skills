---
source_id: sglang-github-closed-issues-prs
title: 'Fix GLM tool-call parser: preserve string arguments with underscores'
canonical_url: https://github.com/sgl-project/sglang/pull/30659
captured_at: '2026-07-11T23:37:37.768789+00:00'
content_hash: db10fc08a2600a68aa42558deb1aa7b0a64bfddf904ffbeca348c1d7c28a31ab
---
# Fix GLM tool-call parser: preserve string arguments with underscores

URL: https://github.com/sgl-project/sglang/pull/30659
State: closed
Labels: run-ci
Closed at: 2026-07-11T11:26:45Z
Merged at: 

Fixes #30644

ast.literal_eval (PEP 515) strips underscores from numeric literals, converting "123_456" to integer 123456. When a tool schema declares an argument as type 'string', this silently corrupts the value.

Skip the ast.literal_eval result when the schema expects a string but the parsed value is numeric, letting it fall through to string-based parsing strategies.



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29150327291](https://github.com/sgl-project/sglang/actions/runs/29150327291)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29150328220](https://github.com/sgl-project/sglang/actions/runs/29150328220)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
