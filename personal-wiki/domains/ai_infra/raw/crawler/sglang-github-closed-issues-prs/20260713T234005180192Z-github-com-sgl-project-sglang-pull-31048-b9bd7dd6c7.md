---
source_id: sglang-github-closed-issues-prs
title: 'fix(tokenizer): configure Rust server special tokens at load time'
canonical_url: https://github.com/sgl-project/sglang/pull/31048
captured_at: '2026-07-13T23:40:05.180192+00:00'
content_hash: b9bd7dd6c74c4326596d56b9a3c1896ba44797e6229d1e6bfca0940782c18c2f
---
# fix(tokenizer): configure Rust server special tokens at load time

URL: https://github.com/sgl-project/sglang/pull/31048
State: closed
Labels: dependencies
Closed at: 2026-07-13T16:37:26Z
Merged at: 

## Summary

- upgrade the Rust server to dynamo-tokenizers 1.5.1
- construct the encode-pool tokenizer once with add_special_tokens=true, which selects the plain HuggingFace backend without a CachedTokenizer wrapper
- keep the detokenizer on default tokenizer options and leave CachedTokenizer unchanged
- add offline SGLang coverage for HF backend selection, repeated scalar parity, batch parity, and exactly-once BOS/EOS around multiple chat-boundary tokens

## Test Plan

- cargo test tokenizer::tests::add_special_tokens_encoder_matches_direct_hf --lib
- cargo test --lib
- cargo test --doc
- cargo fmt --all -- --check
- cargo clippy --all-targets --all-features -- -D warnings







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29266332621](https://github.com/sgl-project/sglang/actions/runs/29266332621)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29266333260](https://github.com/sgl-project/sglang/actions/runs/29266333260)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
