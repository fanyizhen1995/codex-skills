---
source_id: sglang-github-closed-issues-prs
title: '[Refactor] Share chat encoding dispatch between serving and offline tools'
canonical_url: https://github.com/sgl-project/sglang/pull/30623
captured_at: '2026-07-09T23:36:35.331318+00:00'
content_hash: 67eadc2da03db1dc0808adbd6a5d5b6a2157ac897d65862ceef87fd22d723732
---
# [Refactor] Share chat encoding dispatch between serving and offline tools

URL: https://github.com/sgl-project/sglang/pull/30623
State: closed
Labels: run-ci
Closed at: 2026-07-09T09:45:43Z
Merged at: 2026-07-09T09:45:43Z

Extract the chat-encoding dispatch (DeepSeek-V4/V3.2 custom encoders vs HF chat template) from serving_chat into a shared `chat_encoding` module with a minimal `encode_simple_chat` helper, and drop the benchmark-side mirror of it. Stacks on #30615.

### Mechanical equivalence verification

```
verify-refactor-equivalence: 5/5 OK
  OK    predicate AST equivalence (serving -> shared)        [AST static]
  OK    dsv4 prompt with/without empty system identical      [real encoder execution]
  OK    HF-template branch: same apply_chat_template args    [mock behavioral]
  OK    no-template model raises ValueError                  [mock behavioral]
  OK    dsv4 branch: tokenizer.encode(encode_messages(...))  [mock + real encoder]
```

- **Predicate move**: `_resolve_chat_encoding_spec` (pre-refactor) vs shared `resolve_chat_encoding_spec` compared as normalized ASTs under the three declared substitutions (`self.tool_call_parser` -> `tool_call_parser`, `self.tokenizer_manager.model_config.hf_config` -> `hf_config`, `self.tokenizer_manager.tokenizer` -> `tokenizer`) — identical, pure mechanical move.
- **Empty-system contract**: `encoding_dsv4.encode_messages` executed for a user-only conversation with and without the prepended empty system message — byte-identical prompts, so the benchmark token stream is unchanged while the serving-side insertion semantics are now explicit.
- **HF-template branch**: mocked tokenizer confirms `apply_chat_template` is called with the same arguments as the previous benchmark code, with no system insertion on the default path, and a missing chat template still raises `ValueError`.

Verification script (reproducible): https://gist.github.com/hnyls2002/4cd80b5baea21c2076539655ddc5d871

Intentional behavior deltas (not covered by equivalence): the benchmark's DeepSeek-V4 detection now follows the serving rule instead of its own arch list, and the benchmark gains DeepSeek-V3.2 custom-encoding support.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29008550738](https://github.com/sgl-project/sglang/actions/runs/29008550738)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29008550537](https://github.com/sgl-project/sglang/actions/runs/29008550537)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
