---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM-5.2-NVFP4 + flashinfer_trtllm: long-context outputs collapse to
  ''!!!!'' (NaN logits) — fp32 correction_bias regression from #29783'
canonical_url: https://github.com/sgl-project/sglang/issues/30989
captured_at: '2026-07-13T23:40:05.151119+00:00'
content_hash: dbda629d1741241a2f4802ee49c068d8f8955cc8d93672015c6d8ffedd137571
---
# [Bug] GLM-5.2-NVFP4 + flashinfer_trtllm: long-context outputs collapse to '!!!!' (NaN logits) — fp32 correction_bias regression from #29783

URL: https://github.com/sgl-project/sglang/issues/30989
State: closed
Labels: 
Closed at: 2026-07-13T19:54:40Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version (the triggering commit `d8462f49619` is on current `main`).
- [x] Environment info and a minimal reproducible demo are included below.
- [x] This is a bug report, not a general question.
- [x] Written in English.

### Describe the bug

**Symptom.** Serving `nvidia/GLM-5.2-NVFP4` with `--quantization modelopt_fp4 --moe-runner-backend flashinfer_trtllm`, long-context requests (roughly >6.5k tokens, content-dependent) return nothing but `!!!!!!...`. With `"logprobs": true`, every output token's logprob is `null` (NaN serialized to JSON) — the logits are all-NaN, greedy argmax degenerates to the first index, and GLM's vocab id 0 happens to be `!`. Short requests are fine. FP8 checkpoints of the same model are unaffected.

**Regression commit.** Bisected (overlay bisection over the 194 commits between a healthy 2026-07-02 build and v0.5.15, with single-variable half-reverts) to `d8462f49619` (#29783). The sole trigger is the removal of this branch in `MoEGate.__init__` (`python/sglang/srt/models/deepseek_v2.py`):

```python
if (quant_config.get_name() == "modelopt_fp4"
        and get_moe_runner_backend().is_flashinfer_trtllm()):
    correction_bias_dtype = torch.bfloat16
```

so `e_score_correction_bias` is now created as **fp32** and passed unconverted as `routing_bias` to flashinfer's `trtllm_fp4_block_scale_moe` (`moe_runner/flashinfer_trtllm.py`, bypassed-topk branch). Factorial verification: bias bf16 → healthy regardless of router-logits dtype; bias fp32 → collapse regardless of router-logits dtype. Note flashinfer's documented contract is `routing_bias: ... Must be bfloat16 if provided` (`flashinfer/fused_moe/core.py` docstring); the kernel does not validate the dtype. The FP8 path is unaffected because it explicitly casts (`correction_bias.to(torch.bfloat16)` in `moe_runner/flashinfer_trtllm.py`), while the FP4 path passes the tensor raw.

**Underlying mechanism (verified by capturing the failing kernel call and replaying it standalone on 1 GPU).** The NaN is born inside the flashinfer trtllm routing kernel (`routingCustom`, DeepSeekV3 routing with `n_group=1`): when several experts' selection keys `sigmoid(logit) + bias` are **bitwise-equal and the tie group straddles the top-8 boundary**, the kernel emits NaN expert weights (`do_finalize=False` shows `expert_weights = [nan, nan, nan, nan, ...]`; same inputs with bf16 bias give a normal `[0.254, 0.254, 0.212, 0.170, ...]`).

GLM-5.2 makes such exact ties inevitable with an fp32 bias:

- its `e_score_correction_bias` has only **196/256 unique values** (all ≈ 11.13–11.32, duplicates are a training artifact);
- for some long-context tokens all 256 router logits are very negative (max ≈ −5), so most `sigmoid(logit)` contributions (≤4e−3, many <1e−6) fall below the fp32 ulp of the bias (~1e−6 at 11.3) and **vanish in the addition** — the key becomes exactly the (duplicated) bias value → bitwise tie groups at the top-8 boundary → NaN → propagates to all logits → `!` spam for the rest of the generation.

With a bf16 bias the coarse quantization (ulp 0.0625 at 11.3) merges bias values into a few groups spaced far wider than any sigmoid contribution, and the surviving sigmoids strictly order each group — no exact tie ever forms, which is why the pre-#29783 cast was (accidentally) load-bearing.

Ablations on the captured failing call (each run is seconds, single GPU):
| variant | result |
|---|---|
| as captured (fp32 bias) | NaN (whole token row) |
| same values, bias cast to bf16 | clean |
| logits + 10 (sigmoid ~1, ties broken) | clean |
| bias de-duplicated (+k·1e−5) | clean |
| synthetic: logits ≡ −20, 32-way tied bias, **bf16** bias | **NaN** — the kernel defect itself is tie-handling, not dtype |

Also reproducible with the real logits row + real bias + **random** FP4 expert weights, so the trigger payload is just 2×256 floats.

**Suggested fix.** Short-term in sglang: restore the bf16 cast for `modelopt_fp4` + `flashinfer_trtllm` (mirror the FP8 path's explicit `.to(torch.bfloat16)`). Root fix belongs in flashinfer: make `routingCustom` tie-handling NaN-free and validate `routing_bias` dtype per its documented contract — I can file a companion issue there with the standalone kernel repro if useful.

Additional notes:
- `--load-format dummy` does NOT reproduce (needs real weight value distributions).
- Onset is content-dependent and not monotonic in prompt length (a token with all-very-negative router logits must occur), hence multiple probe lengths below.
- Unrelated but found while ruling out alternatives: `marlin`/`cutlass` FP4 MoE loaders crash on GLM's layout (w13 shape 3072 vs 6144 in `fused_moe_triton/layer.py:_load_w13`); can file separately.

### Reproduction

Server (observed on 4×B300 / SM103, TP=4; any build containing `d8462f49619`, e.g. v0.5.15):

```bash
python3 -m sglang.launch_server \
    --model-path nvidia/GLM-5.2-NVFP4 --trust-remote-code \
    --quantization modelopt_fp4 --moe-runner-backend flashinfer_trtllm \
    --tp-size 4 --kv-cache-dtype fp8_e4m3 --mem-fraction-static 0.85 \
    --context-length 500000 --chunked-prefill-size 8192 --port 30005
```

Client (needs `pip install datasets`; the trigger prompt is a pinned row of the public `openai/graphwalks` dataset — a verified trigger, since the failure is content-dependent):

```python
#!/usr/bin/env python3
"""Probe a GLM-5.2-NVFP4 server for the '!' collapse (NaN logits)."""
import argparse, json, sys, urllib.request

DATASET = "openai/graphwalks"
REVISION = "f338bb265735a56a79f4b0f5def722c9c3268ead"  # pin for byte-identical prompt
PROMPT_CHARS_RANGE = (437_000, 438_000)  # deterministically selects one row

def load_trigger_prompt():
    from datasets import load_dataset
    ds = load_dataset(DATASET, revision=REVISION, split="train", streaming=True)
    lo, hi = PROMPT_CHARS_RANGE
    return next(r for r in ds if lo <= r["prompt_chars"] < hi)["prompt"]

def probe(url, model, prompt, chars, want_logprobs):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content":
                      prompt[:chars] + "\n\nFinal question: reply with the single word OK."}],
        "temperature": 0, "max_tokens": 40,
    }
    if want_logprobs:
        payload["logprobs"] = True
    req = urllib.request.Request(f"{url.rstrip('/')}/v1/chat/completions",
                                 json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=600))
    choice = resp["choices"][0]
    msg = choice["message"]
    text = " ".join(filter(None, [msg.get("content"), msg.get("reasoning_content")])).strip()
    collapsed = text.count("!") > max(10, len(text) // 2)
    line = f"chars={chars:7d}  {'COLLAPSED' if collapsed else 'ok       '}  out={text[:40]!r}"
    if want_logprobs:
        lps = ((choice.get("logprobs") or {}).get("content")) or []
        nulls = sum(1 for t in lps if t.get("logprob") is None)
        line += f"  null_logprobs={nulls}/{len(lps)}"
    print(line, flush=True)
    return collapsed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:30005")
    ap.add_argument("--model", default="nvidia/GLM-5.2-NVFP4")
    ap.add_argument("--chars", default="10000,20000,40000,80000")
    ap.add_argument("--logprobs", action="store_true")
    args = ap.parse_args()
    prompt = load_trigger_prompt()
    print(f"prompt loaded ({len(prompt)} chars); probing {args.url}")
    any_collapse = False
    for chars in (int(c) for c in args.chars.split(",")):
        any_collapse |= probe(args.url, args.model, prompt, chars, args.logprobs)
    print("\nRESULT:", "reproduced" if any_collapse else "not reproduced")
    return 1 if any_collapse else 0

if __name__ == "__main__":
    sys.exit(main())
```

Observed on a fresh `lmsysorg/sglang:v0.5.15` container, stock image, NVIDIA-published checkpoint:

```
prompt loaded (437559 chars); probing http://127.0.0.1:30005
chars=  10000  COLLAPSED  out='!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'  null_logprobs=40/40
chars=  20000  COLLAPSED  out='!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'  null_logprobs=40/40
chars=  40000  COLLAPSED  out='!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'  null_logprobs=40/40
chars=  80000  COLLAPSED  out='!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'  null_logprobs=40/40

RESULT: reproduced
```

On a 2026-07-02 build (pre-#29783) the same probe prints `ok` on all four points, and both LongBench and a 256k-tier graphwalks eval recover fully (e.g. graphwalks answerable F1 0.000 → 0.67).

### Environment

```
Python: 3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3: NVIDIA B300 SXM6 AC
GPU 0,1,2,3 Compute Capability: 10.3
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 580.126.20
PyTorch: 2.11.0+cu130
sglang: 0.5.15
sglang-kernel: 0.4.4
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: 0.6.12+cu130
triton: 3.6.0
transformers: 5.12.1
torchao: 0.17.0+cu130
numpy: 2.3.5
aiohttp: 3.14.1
fastapi: 0.139.0
huggingface_hub: 1.23.0
interegular: 0.3.3
modelscope: 1.38.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.51.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
NVIDIA Topology: 4x B300, NV18 all-to-all (matrix omitted)
```
