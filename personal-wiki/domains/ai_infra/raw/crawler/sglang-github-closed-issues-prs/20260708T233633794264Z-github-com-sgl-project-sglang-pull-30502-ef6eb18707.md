---
source_id: sglang-github-closed-issues-prs
title: Sync amd/aiter-ci with main
canonical_url: https://github.com/sgl-project/sglang/pull/30502
captured_at: '2026-07-08T23:36:33.794264+00:00'
content_hash: ef6eb18707718f86c6ccf41774eac6e7faf12f9e4e6f9c055ce02c9653984b5c
---
# Sync amd/aiter-ci with main

URL: https://github.com/sgl-project/sglang/pull/30502
State: closed
Labels: documentation, quant, amd, dependencies, lora, Multi-modal, deepseek, speculative-decoding, hicache, sgl-kernel, blackwell, npu, piecewise-cuda-graph, diffusion, model-gateway, mthreads, apple-silicon, jit-kernel
Closed at: 2026-07-08T08:25:29Z
Merged at: 

## Motivation

Keep the `amd/aiter-ci` branch updated with the latest SGLang `main` changes.

## Modifications

Merged `origin/main` into `bingxche/aiter-ci-branch-sync-f279` for delivery back to `amd/aiter-ci`.

## Accuracy Tests

Not applicable; this is a branch sync merge.

## Speed Tests and Profiling

Not applicable; this is a branch sync merge.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

Verification:

- Merge completed cleanly with no manual conflict resolution.
- `rg '^(<<<<<<<|>>>>>>>)' /workspace` found no conflict markers.
- `git diff --check origin/amd/aiter-ci...HEAD` reports trailing whitespace in `.github/workflows/pr-test-npu.yml`; the same warning is present when checking `origin/amd/aiter-ci...origin/main`, so it appears to come from the synced upstream `main` diff.

<div><a href="https://cursor.com/agents/bc-ee61c9ee-edc5-4b77-bab3-422317081604"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cursor.com/assets/images/open-in-web-dark.png"><source media="(prefers-color-scheme: light)" srcset="https://cursor.com/assets/images/open-in-web-light.png"><img alt="Open in Web" width="114" height="28" src="https://cursor.com/assets/images/open-in-web-dark.png"></picture></a>&nbsp;<a href="https://cursor.com/automations/1e67c8ce-e4ed-4a76-9918-1ce7f33abe9a"><picture><source media="(prefers-color-scheme: dark)" srcset="https://cursor.com/assets/images/view-automation-dark.png"><source media="(prefers-color-scheme: light)" srcset="https://cursor.com/assets/images/view-automation-light.png"><img alt="View Automation" width="141" height="28" src="https://cursor.com/assets/images/view-automation-dark.png"></picture></a>&nbsp;</div>












<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28927868753](https://github.com/sgl-project/sglang/actions/runs/28927868753)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28927868548](https://github.com/sgl-project/sglang/actions/runs/28927868548)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
