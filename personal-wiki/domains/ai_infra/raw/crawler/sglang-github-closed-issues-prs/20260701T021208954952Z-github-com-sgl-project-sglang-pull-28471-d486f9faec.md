---
source_id: sglang-github-closed-issues-prs
title: 'docs(cookbook): add AMD MI300X/MI325X/MI355X support for GLM-5.2'
canonical_url: https://github.com/sgl-project/sglang/pull/28471
captured_at: '2026-07-01T02:12:08.954952+00:00'
content_hash: d486f9faec82c83fd5e2b8d74de45637c0774cc80d2477787fe2981e251a9a6e
---
# docs(cookbook): add AMD MI300X/MI325X/MI355X support for GLM-5.2

URL: https://github.com/sgl-project/sglang/pull/28471
State: closed
Labels: documentation
Closed at: 2026-06-30T21:08:52Z
Merged at: 2026-06-30T21:08:52Z

## Summary
Adds AMD **MI300X / MI325X / MI355X** support to the GLM-5.2 cookbook. GLM-5.2 shares the GLM-5.1 / DeepSeek-V3.2 (`glm_moe_dsa`) architecture, so the validated GLM-5.1 ROCm recipe carries over with only the model path swapped.

## Changes
- **Deploy panel** (`docs_new/src/snippets/configs/zai-org/glm-5.2.jsx`):
  - `mi300x`, `mi325x`, `mi355x` added to `supportedHardware` + ROCm `dockerImages`.
  - Single-node **TP8 FP8/BF16** cells using the DSA **tilelang** backend (`--dsa-prefill-backend tilelang --dsa-decode-backend tilelang --chunked-prefill-size 131072 --mem-fraction-static 0.80 --watchdog-timeout 1200`).
  - DSA-prefill Context Parallel disabled on AMD (verified on Hopper only).
- **Page** (`docs_new/cookbook/autoregressive/GLM/GLM-5.2.mdx`): description + an AMD bullet in Configuration Tips.

## Notes
- **No MTP on AMD (yet).** EAGLE/MTP speculative decoding currently does not build for gfx950 (the spec-decode kernel fails to compile), so the AMD cells omit `--speculative-*` and serve without MTP. This is documented in Config Tips. Once the gfx950 spec-decode kernel lands, MTP cells can be added.
- **Validation:** GLM-5.2-FP8 served end-to-end on MI355X-class (gfx950) hardware at TP8 via the DSA tilelang path. MI300X/MI325X (gfx942) and BF16 cells mirror the GLM-5.1 recipe and are marked `verified: false` pending a run.

## Test plan
- [ ] Render the GLM-5.2 cookbook page; confirm AMD appears in the Deploy panel and generates the expected ROCm `sglang serve` command.
- [ ] Serve `zai-org/GLM-5.2-FP8` on MI300X/MI325X to flip those cells to `verified: true`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28475719904](https://github.com/sgl-project/sglang/actions/runs/28475719904)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28475719698](https://github.com/sgl-project/sglang/actions/runs/28475719698)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
