---
source_id: sglang-github-closed-issues-prs
title: Deterministic seeded sampling can force-select low-probability token when MurmurHash32
  returns UINT32_MAX
canonical_url: https://github.com/sgl-project/sglang/issues/25106
captured_at: '2026-07-12T23:38:53.047086+00:00'
content_hash: b0ebbf918882136c77cf59060c58bea029e8c0dccffb90d2a041f79b3182126c
---
# Deterministic seeded sampling can force-select low-probability token when MurmurHash32 returns UINT32_MAX

URL: https://github.com/sgl-project/sglang/issues/25106
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:50Z
Merged at: 

### Bug

In `python/sglang/srt/layers/sampler.py::multinomial_with_seed`, deterministic seeded sampling converts a 32-bit hash to a uniform float with:

```python
x = hashed.to(torch.float64) / torch.iinfo(torch.uint32).max
```

When the Triton `murmur_hash32` path returns `0xffffffff`, this maps to exactly `1.0`. The subsequent Gumbel transform `-log(-log(x))` becomes `+inf`, so that token wins `argmax` regardless of its logprob.

This creates a rare but deterministic correctness bug: for some `(seed, position, token_id)` triples, seeded sampling can select a token whose logprob is effectively impossible.

### Validated on latest main

Commit: `a4109e87ac0e14cd62cdf25a0da1c4001ee2d400`

Environment:

```text
GPU: NVIDIA A100-SXM4-40GB
Driver: 580.126.20
CUDA shown by nvidia-smi: 13.0
torch: 2.11.0+cu130
triton: 3.6.0
cuda available: True
```

I searched open issues/PRs for the following before filing and did not find this exact boundary bug:

```text
murmur_hash32 gumbel infinity deterministic sampling
uint32 max deterministic sampling seed Gumbel
torch.iinfo(torch.uint32).max
multinomial_with_seed hash UINT32_MAX
UINT32_MAX Gumbel
0xffffffff multinomial_with_seed
```

### Repro output

Using the current `murmur_hash32` kernel, the repro found this deterministic hit:

```text
seed=7847 position=12345 token_id=1208
hash=0xffffffff
```

Full output from an A100 40GB run:

```text
NVIDIA A100-SXM4-40GB
searched 536,870,912 hashes, 0.33 Ghash/s
FOUND hit after 1,073,741,824 hashes in 1.66s
seed=7847 position=12345 token_id=1208
hash=0xffffffff
bad_token=1208
sampled_id=1208
u_at_bad_token=1.0
is u exactly 1.0? True
logprob[token0]=0.0
logprob[bad_token]=-1000000.0
unsafe_sample=1208
safe_sample=0
unsafe finite at bad token? False
safe finite at bad token? True
REPRO COMPLETE
```

`multinomial_with_seed()` selected token `1208` even though token `0` had logprob `0.0` and token `1208` had logprob `-1000000.0`.

### Expected behavior

No hash value should produce infinite Gumbel noise. Deterministic sampling should not force-select an arbitrarily low-probability token because the uniform mapping hit the closed interval endpoint `1.0`.

A typical fix direction is to map the uint32 hash into the open interval `(0, 1)`, for example:

```python
x = (hashed.to(torch.float64) + 0.5) / (2.0 ** 32)
```

In the repro above, that makes the bad token's Gumbel finite and selects token `0` instead.
