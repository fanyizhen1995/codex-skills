---
source_id: sglang-github-closed-issues-prs
title: '[misc] Add init-static value extraction to the general code style rule'
canonical_url: https://github.com/sgl-project/sglang/pull/30701
captured_at: '2026-07-09T23:36:35.321617+00:00'
content_hash: 20ddc1e9006340d5246b790d1c7cc18315ca0c7bf24f641cc50d225fed5776a4
---
# [misc] Add init-static value extraction to the general code style rule

URL: https://github.com/sgl-project/sglang/pull/30701
State: closed
Labels: documentation
Closed at: 2026-07-09T22:25:53Z
Merged at: 2026-07-09T22:25:53Z

Add a bullet to .claude/rules/general-code-style.md: values whose inputs are frozen for the object's lifetime are computed once in __init__ and stored as well-named attributes, with input immutability as the hard precondition (shipped examples: needs_cpu_seq_lens in the attention backends).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29054492291](https://github.com/sgl-project/sglang/actions/runs/29054492291)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29054492124](https://github.com/sgl-project/sglang/actions/runs/29054492124)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
