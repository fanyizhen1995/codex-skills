---
source_id: sglang-github-closed-issues-prs
title: '[VLM] Qwen3-VL / Moss-VL ViT preprocessing optimizations'
canonical_url: https://github.com/sgl-project/sglang/pull/28940
captured_at: '2026-07-07T23:35:30.911005+00:00'
content_hash: 399f374cd8bbf34ec3a56b3d44b5b7032fca95935d270ff4113e877006271047
---
# [VLM] Qwen3-VL / Moss-VL ViT preprocessing optimizations

URL: https://github.com/sgl-project/sglang/pull/28940
State: closed
Labels: Multi-modal, deepseek, run-ci, run-ci-extra, release-highlight
Closed at: 2026-06-24T06:36:30Z
Merged at: 2026-06-24T06:36:30Z

### Motivation

The ViT position-embedding bilinear interpolation (`fast_pos_embed_interpolate*`) loops in
Python over images, and on the ViT cuda-graph path (`SGLANG_VIT_ENABLE_CUDA_GRAPH=1`) it
additionally does a `grid_thw.cpu().numpy()` round-trip plus a numpy per-image loop. The cost
scales with the number of images — invisible for one image, a real bottleneck for many-image /
video / long multimodal prefills.

Two behavior-preserving optimizations that target the **same bottleneck class: multimodal
preprocessing cost that scales with the number of images per request**. Each is negligible for a
single image but becomes a real cost for many-image / video / long multimodal prefills — exactly
the regime that is growing. Both remove a *per-image serial* cost on the critical path:

1. **Vectorize ViT position-embedding interpolation** — replaces the per-image Python loop (and a
   numpy `grid_thw.cpu()` round-trip on the cuda-graph path) with a single batched op whose cost
   is independent of the number of images. (`qwen3_vl.py`, `moss_vl.py`, `environ.py`)
2. **Decode images in the io worker thread instead of lazily on the event loop** — moves the PIL
   decode of each image off the single main event-loop thread (where it ran serially for all
   images) into the io thread pool, so the per-image decode parallelizes across workers.
   (`base_processor.py`)

Both are gated/safe and verified bit-identical to the existing behavior. The two commits are
self-contained independently.

### Modifications
- `fast_pos_embed_interpolate_vectorized` on `Qwen3VLMoeVisionModel` and `MossVLVisionModel`:
  builds per-token `(image, row, col)` coordinates with `arange` + `repeat_interleave`, computes
  interpolation coordinates via a per-unique-size `linspace` lookup, does the 4-corner bilinear
  weighted sum in one batched op, and does the temporal-repeat + spatial-merge reorder with a
  single gather/scatter. Cost is independent of the number of images.
- New env flag `SGLANG_VIT_ENABLE_VECTORIZED_POS_EMBED` (`EnvBool`, default `True`).
- Both call sites wired: the default `forward` path and the cuda-graph `_prepare_graph_inputs` path.
- Image-count threshold `_VECTORIZED_POS_EMBED_MIN_IMAGES = 6`: below it the per-image loop is
  faster, so it falls back. Both paths are bit-exact, so the switch only trades speed for speed.

### Precision — bit-exact
The vectorized path reproduces the legacy arithmetic exactly (same `linspace` coords, same
bilinear-weight arithmetic, same 4-corner reduction, gather/scatter is a pure permutation):
`rtol=0, atol=0` across single / large-upsample / multi-mixed / video / video+image / many-image
grids, in bf16 and fp32, on CPU and CUDA.

### Performance
`fast_pos_embed_interpolate` micro-benchmark on H20-3e (Qwen3-VL config, bf16), vectorized vs loop:

| images | 1 | 8 | 64 | 256 | 552 |
|---|---|---|---|---|---|
| speedup | 0.27x | 1.34x | 4.68x | 7.82x | 5.85x |

Crossover ~6 images (hence the threshold); single-image (common case) keeps the faster loop.

---

## 2. Decode images in the io worker thread instead of lazily on the event loop

### Motivation
`BaseMultimodalProcessor._load_single_item` runs in the multimodal `io_executor` thread pool and
is meant to do per-item decode off the main thread. But for **PNG / non-JPEG** inputs
`load_image` returns a `PIL.Image` from `Image.open(...)`, which **decodes lazily** — the pixel
data is materialized only on first access. That first access happens later, inside the HF fast
image processor's `pil_to_tensor` → `PIL.Image.tobytes()`, which runs on the **tokenizer
manager's main event-loop thread** (the processor call is `await`ed but executes synchronously in
the loop). So the decode is serialized on a single thread and blocks the event loop.

py-spy of the tokenizer-manager process under multi-image load shows this `tobytes()` decode as
the dominant main-thread cost (~69% of main-thread samples for 16×448px PNG).

### What changed
In `_load_single_item`, force the PIL decode in the io worker thread:

```python
if modality == Modality.IMAGE:
    img, _ = load_image(data, cls.gpu_image_decode)
    if not isinstance(img, torch.Tensor):
        if discard_alpha_channel and img.mode != "RGB":
            img = img.convert("RGB")   # convert() also forces the decode
        else:
            img.load()                 # force the otherwise-lazy decode here
    return img
```

The decode now runs in the `io_executor` worker (parallelized across workers, off the main
thread); the later `tobytes()` becomes a cheap memcpy. JPEG is unaffected — it already returns a
CUDA tensor via nvJPEG (`decode_jpeg(device="cuda")`) and skips this branch.

### Precision — behavior unchanged
Output is bit-identical: same mode (RGBA/P/L → RGB via the existing `convert("RGB")` when
`discard_alpha_channel`; RGB unchanged) and same pixels. Only *when/which thread* the decode runs
changes. `img.load()` is idempotent and safe.

### Performance
Qwen3-VL-4B, 16 images @448px, H20-3e, isolated requests, with `--keep-mm-feature-on-device`:

| metric | before | after |
|---|---|---|
| `processor.__call__` (image processing) | ~95 ms | **~11 ms** |
| preprocess `total_time` | ~124 ms | **~38 ms** |
| py-spy main-thread `tobytes` share | ~69% | **~3%** |

This is a **preprocessing-latency / event-loop-occupancy** win, not a throughput win for
GPU-bound serving: for heavy multi-image requests the vision encoder on the base GPU is the
bottleneck (cold concurrent throughput is GPU-bound and unchanged by this patch). The benefit
shows up in single-request / TTFT latency, in workloads where the vision encoder is not the wall,
and in keeping the tokenizer manager's event loop responsive under load. PNG / non-JPEG only.

---

## Tests

- **Pos-embed**: `test/registered/models/test_vit_pos_embed_interpolate.py` — `torch.equal` between
  the vectorized and loop paths for Qwen3-VL and Moss-VL across single / large / multi-mixed /
  video / video+image / many-image grids, bf16 + fp32, CPU + CUDA.
- **Image decode**: `test/registered/unit/multimodal/test_base_processor_image_decode.py`
  (`base-a-test-cpu`, no server/model) — asserts `_load_single_item` returns an already-decoded
  image (vs a bare lazy `Image.open`), preserves RGBA→RGB alpha-discard, and returns pixels
  bit-identical to the reference path. Verified as a genuine regression test: it **fails on the
  pre-fix code** (`test_load_single_item_forces_decode`) and passes with the fix.

```bash
python -m pytest test/registered/models/test_vit_pos_embed_interpolate.py -v
python -m pytest test/registered/unit/multimodal/test_base_processor_image_decode.py -v
```

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28021555312](https://github.com/sgl-project/sglang/actions/runs/28021555312)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28859032964](https://github.com/sgl-project/sglang/actions/runs/28859032964)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
