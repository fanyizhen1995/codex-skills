---
source_id: sglang-github-closed-issues-prs
title: '[Perf] MoE load_weights is quadratic: per-tensor linear scan of expert_params_mapping
  dominates RL weight-sync time (~60 s per full pass on Qwen3-30B-A3B)'
canonical_url: https://github.com/sgl-project/sglang/issues/30848
captured_at: '2026-07-11T23:37:37.762169+00:00'
content_hash: 7459dc466c707d3b228c078e77ff82310cce58f9a879d164e66057d2e1eb21bb
---
# [Perf] MoE load_weights is quadratic: per-tensor linear scan of expert_params_mapping dominates RL weight-sync time (~60 s per full pass on Qwen3-30B-A3B)

URL: https://github.com/sgl-project/sglang/issues/30848
State: closed
Labels: 
Closed at: 2026-07-11T08:36:57Z
Merged at: 

### Problem

The `load_weights` implementation shared by the MoE models (e.g. `sglang/srt/models/qwen3_moe.py::Qwen3MoeForCausalLM.load_weights`, same pattern in qwen2_moe / deepseek variants) does, for **every** incoming tensor:

```python
for mapping in expert_params_mapping:   # num_experts x 3 entries (384 for 128 experts)
    param_name, weight_name, expert_id, shard_id = mapping
    if weight_name not in name:         # substring test per entry
        continue
```

plus `params_dict = dict(self.named_parameters())` rebuilt at the top of **every call**.

For a one-shot disk load this is negligible. But in RL weight-sync flows (`update_weights_from_tensor`, called every training step with the full set of HF-named tensors, often in many chunked calls), the cost is quadratic in practice: a Qwen3-30B-A3B checkpoint has 48 layers × 128 experts × 3 projections ≈ **18k expert tensors**, each scanning ~half of the 384-entry mapping → ~3.5M substring comparisons per full pass, plus dozens of `params_dict` rebuilds (one per chunked call).

### Measured impact

Disaggregated RL (verl + SGLang rollout, H100s): per-step weight sync into a Qwen3-30B-A3B server measured **55–63 s**, for both a sparse-delta path and the stock full-broadcast path — profiling attributes the bulk to the name-resolution loop, not to the actual copies (18k small `copy_` calls are ~sub-second). Dense models (Qwen2.5-7B/32B/72B, ~340 tensors) apply in <1 s per bucket through the same flow.

### Suggested fix

Index the mapping once instead of scanning per tensor — expert names are fully determined (`experts.{E}.{proj}.`):

```python
# at mapping construction time (once):
self._expert_mapping_by_key = {w: (p, e, s) for p, w, e, s in self.expert_params_mapping}

# in load_weights, per tensor:
m = _EXPERT_KEY_RE.search(name)          # r"experts\.\d+\.\w+\."
hit = self._expert_mapping_by_key.get(m.group(0)) if m else None
```

and cache `params_dict` on the module instead of rebuilding per call. We ship this as a workaround inside verl's custom weight loader (resolving the name and calling `param.weight_loader` directly) and it removes the bottleneck entirely, but the fix seems generally useful for every `update_weights_from_tensor` / RL user of MoE models.

Happy to send a PR if the approach sounds right.
