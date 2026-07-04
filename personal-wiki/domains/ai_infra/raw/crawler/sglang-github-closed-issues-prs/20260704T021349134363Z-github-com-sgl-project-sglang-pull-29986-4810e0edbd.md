---
source_id: sglang-github-closed-issues-prs
title: '[AMD]: hot-patch transformers dynamic_module_utils symlink bug'
canonical_url: https://github.com/sgl-project/sglang/pull/29986
captured_at: '2026-07-04T02:13:49.134363+00:00'
content_hash: 4810e0edbd0ae86af413c84335caa3e3ec0d65152ed335e56f38246da2e7bacb
---
# [AMD]: hot-patch transformers dynamic_module_utils symlink bug

URL: https://github.com/sgl-project/sglang/pull/29986
State: closed
Labels: amd
Closed at: 2026-07-03T10:20:37Z
Merged at: 2026-07-03T10:20:37Z

## Motivation

`transformers==5.12.1` introduced `dynamic_module_utils._compute_local_source_files_hash`, which calls `Path(...).resolve()` on custom-code module files. In a normal HuggingFace cache the snapshot files (`models--org--name/snapshots/<hash>/x.py`) are **relative symlinks** into `../../blobs/<blob>`. Resolving them jumps into `blobs/`, so `get_relative_import_files` then looks for sibling modules next to the blob target and cannot find them.

Any `trust_remote_code` model whose remote code uses relative imports hits this. Concretely, Kimi-K2.6 fails at processor init:

```
FileNotFoundError: .../blobs/media_utils.py
```

(from `kimi_k25_vision_processing.py: from .media_utils import ...`). This blocks the Kimi K2.6 disaggregation runs on the ROCm/MI35x images.

## Modifications

Add a hot-patch step to `docker/rocm.Dockerfile` that mirrors upstream transformers PR [#46618](https://github.com/huggingface/transformers/pull/46618) (merged, not yet released): stop `.resolve()`-ing the module file and its relative-import sources so the snapshot `.py` paths are used, giving a stable hash identical to the non-symlinked case.

- AMD ROCm image build only; the common sglang code path is untouched (NV/CUDA unaffected).
- Self-skips once transformers ships the fix.
- Fails the build loudly if the target strings are present but no substitution happens (guards against a silent no-op on a future transformers layout change).

## Checklist

- [x] Verified end-to-end against transformers 5.12.1 in the current MI35x ROCm image: the unpatched image reproduces `FileNotFoundError: .../blobs/<name>.py` on a symlinked HF-cache layout with a relative-import remote-code module; the patched image loads it successfully and produces a hash identical to the plain-directory case.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28628792856](https://github.com/sgl-project/sglang/actions/runs/28628792856)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28628792817](https://github.com/sgl-project/sglang/actions/runs/28628792817)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
