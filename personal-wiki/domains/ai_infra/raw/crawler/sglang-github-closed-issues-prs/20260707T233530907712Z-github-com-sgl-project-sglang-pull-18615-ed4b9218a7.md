---
source_id: sglang-github-closed-issues-prs
title: Remove FA from SM100 sgl-kernel build
canonical_url: https://github.com/sgl-project/sglang/pull/18615
captured_at: '2026-07-07T23:35:30.907712+00:00'
content_hash: ed4b9218a7815e970f1a073b55a04227045e1caf2b5faebd44d43c28cdc851b7
---
# Remove FA from SM100 sgl-kernel build

URL: https://github.com/sgl-project/sglang/pull/18615
State: closed
Labels: sgl-kernel
Closed at: 2026-07-07T17:44:34Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Since FA4 on SM100 is entirely JIT based of CuteDSL, I don't think we need to compile these redundant kernels of FA on SM100.

## Modifications

The removal of:

```
target_compile_definitions(common_ops_sm100_build PRIVATE
    FLASHATTENTION_DISABLE_BACKWARD
    FLASHATTENTION_DISABLE_DROPOUT
    FLASHATTENTION_DISABLE_UNEVEN_K
)
```

Should reduce confusion, it doesn't seem to be doing anything right now.
