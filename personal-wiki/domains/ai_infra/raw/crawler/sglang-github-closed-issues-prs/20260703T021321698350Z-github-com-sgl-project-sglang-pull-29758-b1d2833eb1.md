---
source_id: sglang-github-closed-issues-prs
title: Remove transformers 5.12.1 dead-code workarounds
canonical_url: https://github.com/sgl-project/sglang/pull/29758
captured_at: '2026-07-03T02:13:21.698350+00:00'
content_hash: b1d2833eb18e463b2f0ed6fbcdf55a5c7dfa921188963082e41457199094095a
---
# Remove transformers 5.12.1 dead-code workarounds

URL: https://github.com/sgl-project/sglang/pull/29758
State: closed
Labels: run-ci
Closed at: 2026-07-02T16:03:06Z
Merged at: 2026-07-02T16:03:06Z

## Summary

Now that `transformers` is pinned to `5.12.1` (#29393), several version-guarded shims are unreachable dead code. This PR removes them.

### `ModelConfig._verify_transformers_version` (removed)
Both `raise` branches are never triggered under the pin:
- `is_hrm_text and tf < 5.9.0` — hrm_text needs native config added in 5.9.0; pin is 5.12.1.
- `tf < 5.0.0dev0` (glm-4.6v) — pin is 5.12.1.

The whole method and its call site are dead. `import transformers` / `from packaging import version` were function-local, so removal is clean.

### `HrmTextForCausalLM` `num_attention_layers` branch (removed, added in #27887)
Native `HrmTextConfig.__post_init__` already inflates `num_hidden_layers`:

```python
if self.num_layers_per_stack is None:
    self.num_layers_per_stack = self.num_hidden_layers
    self.num_hidden_layers = self.num_layers_per_stack * self.H_cycles * (self.L_cycles + 1)
```

So `num_attention_layers = num_hidden_layers` (the default) equals the explicit `num_layers_per_stack * H_cycles * (L_cycles + 1)` the branch computed. Verified on `sapientinc/HRM-Text-1B`: after `AutoConfig.from_pretrained`, `num_hidden_layers=128`, `num_layers_per_stack=16`, `H=2`, `L=3` → `16*2*4=128`.

### `kimi_k25.py` `PytorchGELUTanh` try/except (removed)
`PytorchGELUTanh` is an alias of `GELUTanh` in transformers 5.x, so the import always succeeds; the `except` branch also referenced an unimported `activations` module (latent `NameError`).

## Verification

e2e on H200 (`hrm-tf-cleanup` devbox, transformers 5.12.1, sglang editable from main + this change):

- `sapientinc/HRM-Text-1B` served (triton backend, cuda-graph/radix/chunked-prefill disabled per `model_specific_adjustment`).
- `AutoConfig.from_pretrained("sapientinc/HRM-Text-1B")` → `num_hidden_layers=128` (= `num_layers_per_stack * H_cycles * (L_cycles+1)`), confirming the deleted branch's value matches the default.
- 4/4 prompts `finish_reason=stop` with coherent, factually correct output (Tokyo / Rayleigh scattering / 25×4=100 / photosynthesis), matching the 2026-06-23 forward-correctness baseline. No no-EOS runaway.

`pre-commit` (isort / ruff / black / clang-format) passes.

## Note

The remaining transformers workarounds in `hf_transformers_patches.py` and `tokenizer.py` were checked against 5.12.1 upstream and are **not** touched — they patch bugs still present in 5.12.1 (e.g. `PilBackend.process_image` still calls `.numpy()` on CUDA tensors, `standardize_rope_params` still accesses `max_position_embeddings` unguarded) or handle remote-code / v5-API compat.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28445959705](https://github.com/sgl-project/sglang/actions/runs/28445959705)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28445959562](https://github.com/sgl-project/sglang/actions/runs/28445959562)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
