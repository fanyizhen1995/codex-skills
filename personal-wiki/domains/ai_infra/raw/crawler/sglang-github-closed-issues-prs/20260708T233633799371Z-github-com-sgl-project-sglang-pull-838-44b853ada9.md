---
source_id: sglang-github-closed-issues-prs
title: Fix List input bug
canonical_url: https://github.com/sgl-project/sglang/pull/838
captured_at: '2026-07-08T23:36:33.799371+00:00'
content_hash: 44b853ada94a35e01ad278fdaf7d0596ff9dc2b32d7893e311e806effea27e98
---
# Fix List input bug

URL: https://github.com/sgl-project/sglang/pull/838
State: closed
Labels: 
Closed at: 2024-07-30T20:40:52Z
Merged at: 2024-07-30T20:40:52Z

Thank you for your contribution, we really appreciate it. The following instructions will help improve your pull request and make it easier to receive feedback. If there are any items you don't understand, don't worry. Just submit the pull request and ask the maintainers for help.

## Motivation

Please explain the motivation behind this PR and the goal you aim to achieve with it.

## Modification

Fix one small bug in openai/adapter

change line 364: if isinstance(prompt, str) or isinstance(prompt[0], str):

while the code in main will cause error when serving list input

## Checklist

1. Ensure pre-commit `pre-commit run --all-files` or other linting tools are used to fix potential lint issues.
2. Confirm that modifications are covered by complete unit tests. If not, please add more unit tests for correctness.
3. Modify documentation as needed, such as docstrings or example tutorials.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
