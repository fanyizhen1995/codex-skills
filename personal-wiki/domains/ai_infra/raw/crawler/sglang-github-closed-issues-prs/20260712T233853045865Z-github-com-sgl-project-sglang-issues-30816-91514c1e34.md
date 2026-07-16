---
source_id: sglang-github-closed-issues-prs
title: '[Bug] HunyuanV3 (hy_v3): shared-expert weights silently skipped (`mlp.shared_experts.*`
  vs model''s `shared_mlp`) → NaN on first forward'
canonical_url: https://github.com/sgl-project/sglang/issues/30816
captured_at: '2026-07-12T23:38:53.045865+00:00'
content_hash: 91514c1e34ccd0056673b313f6d96eb97c710882c22b466f83c42ba09777e658
---
# [Bug] HunyuanV3 (hy_v3): shared-expert weights silently skipped (`mlp.shared_experts.*` vs model's `shared_mlp`) → NaN on first forward

URL: https://github.com/sgl-project/sglang/issues/30816
State: closed
Labels: 
Closed at: 2026-07-12T03:52:48Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution. (Searched `hunyuan shared_experts`, `HYV3 shared_mlp`, `Hy3 NaN`, `hunyuan_v3 shared` — no existing report. The closest is PR #30331, a sibling fix in `hunyuan_v3_nextn.py` — same silent-name-drop class, different module; see Proposed fix.)
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.

### Describe the bug

HunyuanV3 (`hy_v3` / `HYV3ForCausalLM`) checkpoints name the shared expert
`model.layers.N.mlp.shared_experts.{gate,up,down}_proj.*`, but SGLang's `HYV3ForCausalLM`
model module is named **`shared_mlp`**:

```python
# sglang/srt/models/hunyuan_v3.py, HYV3MoEFused.__init__
if getattr(config, "num_shared_experts", 0) > 0:
    self.shared_mlp = HYV3FeedForward(
        hidden_size=config.hidden_size,
        intermediate_size=config.moe_intermediate_size * config.num_shared_experts,
        hidden_act=config.hidden_act,
        quant_config=quant_config,
        prefix=f"{prefix}.shared_mlp",
        reduce_results=False,
    )
```

`HYV3ForCausalLM.load_weights` has a remap for the router (`router.gate` → `gate`), but
**no remap for the shared expert**:

```python
# sglang/srt/models/hunyuan_v3.py, HYV3ForCausalLM.load_weights
for name, loaded_weight in weights:
    ...
    if "router.gate." in name:
        name = name.replace("router.", "")
    if name not in params_dict:
        continue
    param = params_dict[name]
    weight_loader = getattr(param, "weight_loader", default_weight_loader)
    weight_loader(param, loaded_weight)
```

Because the checkpoint's tensor names contain `.shared_experts.` and the model's parameter
dict only has entries under `.shared_mlp.`, **every shared-expert weight fails
`if name not in params_dict: continue` and is silently skipped** — no warning, no error.
`shared_mlp` stays at its randomly-initialized (effectively zero after a fresh
`nn.Parameter` allocation pattern used here) weights, so:

- `shared_mlp.gate_up_proj` outputs all-zero (or garbage) activations
- `down_proj` then FP4-quantizes a degenerate input (e.g. `amax=0` → the global scale
  `448·6/amax` blows up / degenerates)
- the shared-expert branch produces **NaN**, which propagates into the residual stream

The model **loads without any error** (the routed experts, `mlp.experts.N.*`, match
SGLang's expected names and load fine, so nothing looks wrong at load time), then crashes
on the very first forward pass (warmup or first real request) with:

```
/build/pytorch/aten/src/ATen/native/cuda/TensorCompare.cu:109: _assert_async_cuda_kernel:
Assertion `probability tensor contains either inf, nan or element < 0` failed.
...
File ".../sglang/srt/layers/sampler.py", line 656, in sampling_from_probs_torch
    sampled_index = torch.multinomial(probs, num_samples=1)
torch.AcceleratorError: CUDA error: device-side assert triggered
```

This bug is **architecture-independent** — it is a pure weight-name mismatch, not a
kernel/quantization/hardware issue, and should reproduce on any GPU, any quant format,
any TP/PP configuration.

### How we localized it

We used SGLang's own `--debug-tensor-dump-output-folder` per-layer tensor dump to trace
the forward pass op-by-op. The dump showed, in execution order:

```
model.layers.1.mlp.shared_mlp.gate_up_proj   -> output all-zero
model.layers.1.mlp.shared_mlp.act_fn         -> output all-zero
model.layers.1.mlp.shared_mlp.down_proj      -> NaN   (first inf/nan in the whole trace)
model.layers.1.mlp.experts (routed)          -> finite
```

i.e. the routed experts computed correctly; only the shared-expert branch was broken, and
it was broken because it was never fed real weights.

### Reproduction

Serve any HunyuanV3 NVFP4 checkpoint that names the shared expert `shared_experts` (e.g.
`vroomfondel/Hy3-NVFP4-W4A4`, a ModelOpt `modelopt_fp4` export of `tencent/Hy3`):

```bash
python3 -m sglang.launch_server \
  --model-path vroomfondel/Hy3-NVFP4-W4A4 \
  --quantization modelopt_fp4 --trust-remote-code \
  --tool-call-parser hunyuan --reasoning-parser hunyuan \
  --tp-size <N> --nnodes <N> --node-rank <r> --nccl-init-addr <head>:<port> \
  --moe-runner-backend flashinfer_cutlass --fp4-gemm-backend flashinfer_cutlass \
  --attention-backend triton \
  --served-model-name hy3
```

Then send a single request:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"hy3","messages":[{"role":"user","content":"Hello"}],"max_tokens":8}'
```

The server loads cleanly, then crashes on this first forward with the `multinomial`
device-side assert above.

### Proposed fix

Add a name remap at the very top of the weight-loading loop in `load_weights`, mirroring
the existing `router.gate` remap, so it runs *before* the stacked
`gate_proj`/`up_proj` → `gate_up_proj` mapping (which then applies correctly to the
renamed keys):

```python
# sglang/srt/models/hunyuan_v3.py, HYV3ForCausalLM.load_weights
for name, loaded_weight in weights:
    # HunyuanV3 checkpoints name the shared expert `mlp.shared_experts.*`; this
    # model's module is `shared_mlp` — remap so the weights actually load.
    name = name.replace(".shared_experts.", ".shared_mlp.")
    ...
```

This is a pure name remap — no new logic, no shape changes. The shared-expert weights
are otherwise completely normal (same quantization scheme as the routed experts, which
already load and run correctly).

This is the **same failure class** as PR #30331 ("[Fix] Load HunyuanV3 NextN
final_layernorm into the draft head's output norm"), which fixed a silent name-mismatch
drop in `hunyuan_v3_nextn.py` (checkpoint `...final_layernorm.weight` not remapped to the
model's `shared_head.norm.weight`, dropped by the same `if name not in params_dict:
continue` fallthrough). Same file family, same silent-drop mechanism — a targeted remap
plus a small load-time regression test (assert the shared-expert params are non-null /
actually loaded) would prevent both.

**We verified this fix end-to-end:** after applying it (as a runtime patch, no
checkpoint modification), `vroomfondel/Hy3-NVFP4-W4A4` serves *coherently* — correct
multilingual generation, correct step-by-step reasoning/math, valid code generation —
on a 4× DGX Spark (GB10 / sm121) cluster at TP=4, no NaN, no garbled output. Before the
fix, every configuration that reached a forward pass (various attention/MoE/FP4-GEMM
backend combinations, EP=1 vs EP=4, TP=4 vs PP=4) hit the identical NaN — which in
hindsight makes sense, since it's a weight-loading bug, not a backend/kernel one.

### Environment

- SGLang version: 0.5.14 (custom sm121/GB10 build; the model-loading code path here is
  unmodified upstream code, not one of our patches)
- flashinfer: 0.6.14
- CUDA: 13.x
- GPU: NVIDIA GB10 (DGX Spark, sm121) — but as noted above, this is not an
  architecture-specific issue; it should reproduce on any GPU that can serve HunyuanV3.
- Checkpoint: `vroomfondel/Hy3-NVFP4-W4A4` (ModelOpt `modelopt_fp4` export of
  `tencent/Hy3`)
