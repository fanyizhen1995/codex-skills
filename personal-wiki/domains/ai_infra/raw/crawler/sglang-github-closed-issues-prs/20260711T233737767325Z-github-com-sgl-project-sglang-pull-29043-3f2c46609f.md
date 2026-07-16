---
source_id: sglang-github-closed-issues-prs
title: Fix PP grammar preprocessing hang
canonical_url: https://github.com/sgl-project/sglang/pull/29043
captured_at: '2026-07-11T23:37:37.767325+00:00'
content_hash: 3f2c46609fba713c5619b411ec1f19f08a824a12e4284a6aec508f7b2ddce003
---
# Fix PP grammar preprocessing hang

URL: https://github.com/sgl-project/sglang/pull/29043
State: closed
Labels: 
Closed at: 2026-07-11T19:04:10Z
Merged at: 

## Motivation

  Structured output / grammar requests can hang when pipeline parallelism is enabled.

  In the PP path, grammar preprocessing receives a grammar compilation `Future`, but the request was still added to the normal grammar queue. That queue is not the
  right place to make progress for this PP preprocessing path, so the request can remain stuck before scheduling.

  ## Modifications

  - Resolve the grammar compilation `Future` directly in the PP preprocessing path.
  - Cache the compiled grammar in the grammar backend.
  - Apply the request reasoning budget after the grammar is available.
  - If grammar compilation fails, convert the failure to an `InvalidGrammarObject` and abort the request with a clear error message.
  - Keep the existing non-PP behavior unchanged.

  ## Accuracy Tests

  This PR does not change model forward logic, logits, sampling, kernels, or generated token semantics.

  It only changes grammar preprocessing control flow for PP mode, so no model accuracy impact is expected.

  ## Speed Tests and Profiling

  No inference speed regression is expected.

  The change only avoids a PP-only hang by resolving grammar compilation in the preprocessing path. Non-PP behavior is unchanged.

  ## Checklist

  - [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
  - [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
  - [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
  - [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy)
  and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
  - [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28027387878](https://github.com/sgl-project/sglang/actions/runs/28027387878)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28027387349](https://github.com/sgl-project/sglang/actions/runs/28027387349)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
