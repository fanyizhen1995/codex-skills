---
source_id: sglang-github-closed-issues-prs
title: 'fix(mimo-vl): pass padded_context_dim to Qwen2_5_VisionPatchMerger'
canonical_url: https://github.com/sgl-project/sglang/pull/29994
captured_at: '2026-07-04T02:13:49.129813+00:00'
content_hash: 522dcb1390cec20ea12b94025e85ddd729efbed25521ce0e7321978eb1bf23b1
---
# fix(mimo-vl): pass padded_context_dim to Qwen2_5_VisionPatchMerger

URL: https://github.com/sgl-project/sglang/pull/29994
State: closed
Labels: 
Closed at: 2026-07-04T00:08:26Z
Merged at: 2026-07-04T00:08:26Z

MiMo-VL crashes at model init on the scheduled 8-GPU H200 run (`base-c-test-8-gpu-h200`):

```
TypeError: Qwen2_5_VisionPatchMerger.__init__() missing 1 required positional argument: 'padded_context_dim'
  File "python/sglang/srt/models/mimo_vl.py", line 301, in __init__
```

#20072 added a required `padded_context_dim` arg to `Qwen2_5_VisionPatchMerger` and updated the `qwen2_5_vl` caller, but `mimo_vl` reuses the same class and was missed, so every MiMo-VL launch fails at init.

Fix: pass `padded_context_dim=num_heads * head_dim` in the `mimo_vl` merger call, matching `qwen2_5_vl`.

### Checklist

- [x] Format with pre-commit
- [ ] Add unit tests
- [x] Update documentation as needed



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28637061857](https://github.com/sgl-project/sglang/actions/runs/28637061857)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28637061797](https://github.com/sgl-project/sglang/actions/runs/28637061797)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
