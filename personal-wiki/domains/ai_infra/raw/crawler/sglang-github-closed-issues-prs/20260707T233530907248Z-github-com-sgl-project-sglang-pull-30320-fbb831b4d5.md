---
source_id: sglang-github-closed-issues-prs
title: '[Doc] Add LongCat 2.0 FP8 cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/30320
captured_at: '2026-07-07T23:35:30.907248+00:00'
content_hash: fbb831b4d5c66875299a8e5413aaddecd5720b927a6ab9c7ab2de636cfdffff8
---
# [Doc] Add LongCat 2.0 FP8 cookbook

URL: https://github.com/sgl-project/sglang/pull/30320
State: closed
Labels: documentation, run-ci, run-ci-extra
Closed at: 2026-07-07T18:48:14Z
Merged at: 2026-07-07T18:48:14Z

## Summary
- Regenerate the LongCat-2.0 FP8 cookbook with the config-driven `Deployment` / `Playground` template.
- Add LongCat config and benchmark data under `docs_new/src/snippets/configs/meituan-longcat/`.
- Register the Meituan cookbook page in `docs_new/docs.json` and add a Meituan card to the autoregressive cookbook overview.

## Validation
- `git diff --check origin/main...HEAD`
- `node -e "JSON.parse(require('fs').readFileSync('docs_new/docs.json','utf8')); console.log('docs.json ok')"`
- JS syntax parse for `docs_new/src/snippets/configs/meituan-longcat/longcat-2.0.jsx` and `longcat-2.0-benchmarks.jsx`
- Config-cell check: 4 cells, all with the required `{hw, variant, quant, strategy, nodes}` dimensions and no hardcoded `--nnodes`, `--node-rank`, or `--dist-init-addr` flags
- Benchmark mapping check: the B300 GSM8K benchmark entry maps to an existing deployment cell
- `rg` check for old-template leftovers: no `LongCat2Deployment`, `longcat2-deployment`, `python3 -m sglang.launch_server`, `temperature`, `top_p`, markdown table rows, or `metatags:` remain in the LongCat cookbook/config files

Note: `mint` is not installed in my local environment, so I could not run `mint broken-links` locally.

## Accuracy / Serving
- Model: `meituan-longcat/LongCat-2.0-FP8`
- Hardware: 8x B300 single node
- Full GSM8K: `95.8904109589041%` on 1314 examples
- Spot check: `98.0%` on 200 GSM8K examples
- CUDA graph was enabled, and decode CUDA graph capture completed successfully during serving validation































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28886387518](https://github.com/sgl-project/sglang/actions/runs/28886387518)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28886387090](https://github.com/sgl-project/sglang/actions/runs/28886387090)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
