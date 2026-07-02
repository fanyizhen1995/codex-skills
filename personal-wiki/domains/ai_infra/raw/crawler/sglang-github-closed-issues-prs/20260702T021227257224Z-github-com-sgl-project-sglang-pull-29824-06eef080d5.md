---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] CI: tighten multimodal-gen consistency thresholds'
canonical_url: https://github.com/sgl-project/sglang/pull/29824
captured_at: '2026-07-02T02:12:27.257224+00:00'
content_hash: 06eef080d5d1a41d2653569a7336315b161d4d974cdf63e5ad7d9b2f0b95427a
---
# [diffusion] CI: tighten multimodal-gen consistency thresholds

URL: https://github.com/sgl-project/sglang/pull/29824
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-01T17:32:51Z
Merged at: 2026-07-01T17:32:51Z

## Summary

- Tighten existing per-case multimodal-gen consistency thresholds in `consistency_threshold.json`.
- Base the updates on the latest main scheduled multimodal-gen run I found: `Scheduled Full Run` [27242606028](https://github.com/sgl-project/sglang/actions/runs/27242606028), head `98fe7e326ed4ec7ea872f15e351c10611d23a5fe`, completed successfully on 2026-06-10.
- Use the worst observed metric for repeated checks, keep conservative margins/caps, and only tighten existing overrides: no global default changes and no new case overrides.

Threshold rule used:
- `clip_threshold`: latest worst clip minus 0.02, capped at 0.98
- `ssim_threshold`: latest worst SSIM minus 0.04, capped at 0.95
- `psnr_threshold`: latest worst PSNR minus 3 dB, capped at 30 dB
- `mean_abs_diff_threshold`: latest worst mean abs diff plus 3, floored at 4

## Testing

- `python3 -m json.tool python/sglang/multimodal_gen/test/server/consistency_threshold.json`
- `git diff --check`
- `PYTHONPATH=python pytest python/sglang/multimodal_gen/test/unit/test_consistency_metrics.py -q` did not run to collection locally because this machine's Python environment is missing `pybase64` while importing repo test conftest.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28526682813](https://github.com/sgl-project/sglang/actions/runs/28526682813)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28526682511](https://github.com/sgl-project/sglang/actions/runs/28526682511)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
