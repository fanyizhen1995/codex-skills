---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Gemma3TextModel crashes with KeyError when rope_parameters.full_attention
  lacks factor'
canonical_url: https://github.com/sgl-project/sglang/issues/26013
captured_at: '2026-07-10T23:37:20.315878+00:00'
content_hash: a0df1ecb1362f8e6b0453fba7f82af518fd664abf400ea0988cccf7fc2c17637
---
# [Bug] Gemma3TextModel crashes with KeyError when rope_parameters.full_attention lacks factor

URL: https://github.com/sgl-project/sglang/issues/26013
State: closed
Labels: 
Closed at: 2026-07-10T01:24:24Z
Merged at: 

## Environment

- SGLang commit: `c5251a98a9d499d600beb557835ac5874e0c3f36` (`main`)
- SGLang package: `0.5.13.dev319+gc5251a98a`
- Install path: clean upstream checkout, fresh venv, `pip install --upgrade pip`, then `pip install -e "python"`. Missing build tools (`rustc`/`cargo` and `protoc`) were installed, but no SGLang source changes or Python dependency pin overrides were used.
- Python: `3.10.12`
- PyTorch: `2.11.0+cu130`
- Transformers: `5.8.1`
- CUDA: `nvidia-smi` reports CUDA `13.0`; `torch.version.cuda` is `13.0`; no system `nvcc` on PATH
- Driver: `580.126.20`
- GPU: one `NVIDIA A100-SXM4-40GB`

## Bug summary

`Gemma3TextModel.__init__` appears to handle nested/default and flat RoPE configs by computing `global_theta` and `local_theta`, but then unconditionally reads `config.rope_parameters["full_attention"]["factor"]` when constructing `global_config.rope_parameters`.

This crashes for Gemma3 configs where `full_attention` uses default/non-scaled RoPE and therefore does not include `factor`.

## Minimal repro

```python
import traceback

import torch
from transformers import Gemma3TextConfig

from sglang.srt.models.gemma3_causal import Gemma3ForCausalLM

cfg = Gemma3TextConfig(
    vocab_size=1024,
    hidden_size=128,
    intermediate_size=256,
    num_hidden_layers=2,
    num_attention_heads=4,
    num_key_value_heads=2,
    head_dim=32,
    hidden_activation="gelu_pytorch_tanh",
    max_position_embeddings=1024,
    sliding_window=64,
    layer_types=["sliding_attention", "full_attention"],
    rope_parameters={
        "sliding_attention": {
            "rope_type": "default",
            "rope_theta": 10000.0,
        },
        "full_attention": {
            "rope_type": "default",
            "rope_theta": 1000000.0,
        },
    },
)

print("Transformers-normalized rope_parameters:")
print(cfg.rope_parameters)

try:
    with torch.device("cuda" if torch.cuda.is_available() else "cpu"):
        model = Gemma3ForCausalLM(cfg, quant_config=None)
    print("SUCCESS: model constructed")
except Exception:
    traceback.print_exc()
    raise
```

Run:

```bash
CUDA_VISIBLE_DEVICES=0 python /tmp/repro_sglang_gemma3_rope_factor.py
```

Transformers accepts and preserves the config shape:

```text
Transformers-normalized rope_parameters:
{'sliding_attention': {'rope_type': 'default', 'rope_theta': 10000.0}, 'full_attention': {'rope_type': 'default', 'rope_theta': 1000000.0}}
```

`Gemma3TextConfig()` defaults also produce the same nested default RoPE config without `factor`.

## Actual behavior

The model constructor crashes in SGLang:

```text
Traceback (most recent call last):
  File "/tmp/repro_sglang_gemma3_rope_factor.py", line 38, in <module>
    model = Gemma3ForCausalLM(cfg, quant_config=None)
  File "/home/gabe/sglang-upstream-rope-factor-20260521-210228/sglang/python/sglang/srt/models/gemma3_causal.py", line 734, in __init__
    self.model = Gemma3TextModel(
  File "/home/gabe/sglang-upstream-rope-factor-20260521-210228/sglang/python/sglang/srt/models/gemma3_causal.py", line 584, in __init__
    "factor": config.rope_parameters["full_attention"]["factor"],
KeyError: 'factor'
```

## Public checkpoint repro

I also reproduced this with a public Hugging Face Gemma3-family checkpoint/config, without editing the checkpoint config:

```python
from transformers import AutoConfig
cfg = AutoConfig.from_pretrained("unsloth/gemma-3-270m")
print(type(cfg))
print(cfg.rope_parameters)
```

Output:

```text
<class 'transformers.models.gemma3.configuration_gemma3.Gemma3TextConfig'>
{'sliding_attention': {'rope_type': 'default', 'rope_theta': 10000.0}, 'full_attention': {'rope_type': 'default', 'rope_theta': 1000000.0}}
```

Then:

```bash
CUDA_VISIBLE_DEVICES=0 python -m sglang.launch_server \
  --model-path unsloth/gemma-3-270m \
  --host 127.0.0.1 \
  --port 30000
```

This reached model load and failed with the same traceback ending at:

```text
File ".../python/sglang/srt/models/gemma3_causal.py", line 584, in __init__
    "factor": config.rope_parameters["full_attention"]["factor"],
KeyError: 'factor'
```

## Expected behavior

Either default/non-scaled Gemma3 RoPE configs should construct successfully, or SGLang should fail early with a clear validation error if `full_attention.factor` is required.

## Duplicate check

I searched both open and closed issues and PRs in `sgl-project/sglang` for:

- `Gemma3TextModel rope_parameters full_attention factor`: no issues, no PRs
- `Gemma3 KeyError factor`: no issues; PR hits `#20133` and `#10866` were unrelated keyword matches
- `gemma3_causal.py full_attention factor`: no issues, no PRs
- `Gemma3 rope_parameters factor`: no issues; PR hits `#17784` and `#20133` were not matching bug reports/fixes for this crash. `#17784` is the merged Transformers upgrade and the crash still reproduces on current `main`.
- `Gemma3TextConfig factor`: no issues, no PRs

## Validation note

This was validated against upstream `sgl-project/sglang` only, on the default `main` branch at commit `c5251a98a9d499d600beb557835ac5874e0c3f36`. I did not use a fork, PR branch, patched checkout, monkeypatch, vendored copy, or local source workaround.
