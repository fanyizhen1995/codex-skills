---
source_id: sglang-github-closed-issues-prs
title: '[docs] Note the default dsa-topk-backend on all DSA-model cookbook pages'
canonical_url: https://github.com/sgl-project/sglang/pull/31124
captured_at: '2026-07-14T23:40:21.682286+00:00'
content_hash: 8d4e86ac25f316927dc6c4b63650e61eb343ebaebe80849d7fd46f5aa29a9fa8
---
# [docs] Note the default dsa-topk-backend on all DSA-model cookbook pages

URL: https://github.com/sgl-project/sglang/pull/31124
State: closed
Labels: documentation
Closed at: 2026-07-14T07:04:47Z
Merged at: 2026-07-14T07:04:47Z

## Motivation

The cookbook deployment panels for DSA models generate launch commands that are all validated with the default DSA indexer top-k backend (`--dsa-topk-backend sgl-kernel`), while the other top-k backend choices have not been fully validated on these models — but nothing on those pages says so.

## Modifications

Add a `<Warning>` right below the deployment panel of every cookbook model that runs the DSA indexer top-k path (attention backend `dsa`, `--dsa-topk-backend`, default `sgl-kernel`), stating that all recipes run on the default and that other top-k backend choices have not been fully validated on the model:

- `GLM/GLM-5.2.mdx`, `GLM/GLM-5.1.mdx`, `GLM/GLM-5.mdx` (`GlmMoeDsaForCausalLM`)
- `DeepSeek/DeepSeek-V3_2.mdx`, `DeepSeek/DeepSeek-Math-V2.mdx` (`DeepseekV32ForCausalLM`; Math-V2 is V3.2-based, `index_topk=2048`)
- `Meituan/LongCat-2.0.mdx` (LongCat sparse attention runs through the same `dsa` backend, `index_topk=2048`)

Backend name and default verified against `python/sglang/srt/server_args.py` (`dsa_topk_backend`, default `sgl-kernel`) and `python/sglang/srt/layers/attention/dsa_backend.py`; model architectures verified against the HF configs. `mint validate` passes.

## Checklist

- [x] Format your code with `pre-commit run --all-files`
- [ ] Add unit tests (docs-only change)
- [x] Update documentation as needed

🤖 Generated with [Claude Code](https://claude.com/claude-code)





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29312260546](https://github.com/sgl-project/sglang/actions/runs/29312260546)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29312260229](https://github.com/sgl-project/sglang/actions/runs/29312260229)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
