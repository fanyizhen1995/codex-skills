---
source_id: sglang-github-closed-issues-prs
title: '[Refactor] Split DeepSeek-V4 MQALayer into a reusable attention base'
canonical_url: https://github.com/sgl-project/sglang/pull/30711
captured_at: '2026-07-10T23:37:20.325867+00:00'
content_hash: e756b4ad802e6e5251cc8d452b1613d4eb72620e1ae6178122525abc77a13bb0
---
# [Refactor] Split DeepSeek-V4 MQALayer into a reusable attention base

URL: https://github.com/sgl-project/sglang/pull/30711
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-10T08:14:04Z
Merged at: 2026-07-10T08:14:04Z

Split the monolithic MQALayer into MqaAttentionBase (attention core with construction-time overridable knobs) plus MQALayer (rope/compressor/indexer/multi-stream wiring), and extract the mHC parameter/head helpers as free functions. Pure restructuring: every new constructor knob defaults to the previous behavior.

Mechanical verification (per-method AST equivalence + verbatim-extraction checks): 37/40 methods byte-identical; the 3 call-site deltas are the declared extract-method/extract-constant hunks, and the constructor split passes a knob-by-knob None-default review with zero lost attributes. Full report: https://gist.github.com/hnyls2002/b4bfa20e6b42b5161eb5f6838ff3521d







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29058976827](https://github.com/sgl-project/sglang/actions/runs/29058976827)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29058976657](https://github.com/sgl-project/sglang/actions/runs/29058976657)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
