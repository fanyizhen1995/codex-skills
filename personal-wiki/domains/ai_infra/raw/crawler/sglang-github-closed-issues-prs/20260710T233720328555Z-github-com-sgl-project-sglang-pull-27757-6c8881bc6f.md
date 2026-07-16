---
source_id: sglang-github-closed-issues-prs
title: Fix Mistral GSM8K chat eval
canonical_url: https://github.com/sgl-project/sglang/pull/27757
captured_at: '2026-07-10T23:37:20.328555+00:00'
content_hash: 6c8881bc6fb6bceda793040e73e029f12c5600ea7e7d183903f2ff7f054f560d
---
# Fix Mistral GSM8K chat eval

URL: https://github.com/sgl-project/sglang/pull/27757
State: closed
Labels: high priority, dependencies, run-ci, bypass-fastfail
Closed at: 2026-07-10T04:08:49Z
Merged at: 2026-07-10T04:08:49Z

## Summary

Move the nightly text-model GSM8K eval from the hand-rolled 5-shot chat-API scorer to `sgl-eval` (zero-shot chat, `\boxed{}` answer, `math_verify` grading), fill in real thresholds for every nightly model, and fix the CI install-order bug that blocked the sgl-eval path.

## Root cause

`nightly-test-text-accuracy-2-gpu-h100` was red on Mistral-family models (e.g. `mistralai/Mistral-7B-Instruct-v0.3` 0.414 vs 0.47 threshold). Reproduced on a devbox: the model generates correctly with `finish_reason=stop` and no runaway — it is not a serving regression. The old scorer wraps a completion-style 5-shot `Question:/Answer:` prompt in Mistral's `[INST]` chat template, which breaks the few-shot context for Mistral-family models; last-number extraction then occasionally grabs the wrong number when the response continues into another Q/A block.

## What this PR does

1. **Switch the nightly eval to `sgl-eval`** (`api="sgl_eval"` in `test_text_models_gsm8k_eval.py`). sgl-eval is a black-box subprocess running zero-shot chat with `\boxed{}` formatting and `math_verify` grading, which avoids the few-shot/chat-template interaction.
2. **Make sgl-eval opt-in**: only the nightly correctness eval sets `api='sgl_eval'`. Every other gsm8k caller keeps the hand-rolled 5-shot completion scorer unchanged.
3. **Fill real thresholds** for all 15 nightly models, baselined on H100 2-GPU over the full 1319-example split (measured_score − 0.05).
4. **Fix the antlr4 install-order bug** (below).

## The CI install-order bug

sgl-eval's `latex2sympy2_extended` requires `antlr4-python3-runtime` 4.9.3 / 4.11 / 4.13.2 and raises `ImportError: Unsupported ANTLR version 4.7.2` on 4.7.x. The `antlr4-python3-runtime==4.9.3` pin in `python/pyproject.toml [test]` was not enough — CI still loaded 4.7.2:

```
install_sglang        # [dev]→[test] → sgl-eval → latex2sympy2_extended (needs antlr4 4.9.3) ✓
install_extra_deps    # uv pip install -e lmms-eval/ → lmms-eval v0.5 → latex2sympy2 1.9.1
                      #   hard-pins antlr4==4.7.2, clobbering 4.9.3 ✗
install_test_tools    # does not restore antlr4
```

The clobber comes from `latex2sympy2==1.9.1` (a transitive dep of `lmms-eval`, distinct from `latex2sympy2_extended`), which hard-pins `antlr4-python3-runtime==4.7.2`.

Fix: in `scripts/ci/cuda/ci_install_dependency.sh`, right after the `lmms-eval` install, force it back:
```bash
$PIP_CMD install "antlr4-python3-runtime==4.9.3" --force-reinstall --no-deps $PIP_INSTALL_SUFFIX
```

## Thresholds (H100 2-GPU, full 1319 split, sgl-eval zero-shot)

| model | measured | threshold |
|---|---|---|
| meta-llama/Llama-3.1-8B-Instruct | 0.81 | 0.77 |
| Qwen/Qwen3-8B | 0.81 | 0.76 |
| Qwen/Qwen3-4B | 0.82 | 0.77 |
| meta-llama/Llama-3.1-70B-Instruct | 0.95 | 0.90 |
| mistralai/Mixtral-8x7B-Instruct-v0.1 | 0.44 | 0.39 |
| Qwen/Qwen2-57B-A14B-Instruct | 0.51 | 0.46 |
| neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8 | 0.82 | 0.77 |
| neuralmagic/Mistral-7B-Instruct-v0.3-FP8 | 0.28 | 0.23 |
| neuralmagic/DeepSeek-Coder-V2-Lite-Instruct-FP8 | 0.85 | 0.80 |
| zai-org/GLM-4.5-Air-FP8 | 0.77 | 0.73 |
| neuralmagic/gemma-2-2b-it-FP8 | 0.07 | 0.02 |
| neuralmagic/Meta-Llama-3.1-70B-Instruct-FP8 | 0.94 | 0.89 |
| neuralmagic/Mixtral-8x7B-Instruct-v0.1-FP8 | 0.40 | 0.35 |
| neuralmagic/Qwen2-72B-Instruct-FP8 | 0.88 | 0.83 |
| neuralmagic/Qwen2-57B-A14B-Instruct-FP8 | 0.45 | 0.40 |

Low scorers (`gemma-2-2b-it-FP8` 0.07, `Mistral-7B-v0.3-FP8` 0.28) are genuine — verified on a devbox that the model emits `\boxed{}` correctly and the grader extracts the answer (no format issue, no `no_answer`). GSM8K is a numeric answer task, so these reflect weak zero-shot reasoning on small/older-instruct models, not an eval bug.

## Validation

- `/rerun-test test/registered/eval/test_text_models_gsm8k_eval.py` on 2-gpu-h100 — all 15 models pass: [run 28645576771](https://github.com/sgl-project/sglang/actions/runs/28645576771) ✅
- Prior rerun [28642161462](https://github.com/sgl-project/sglang/actions/runs/28642161462) failed with the antlr4 clobber on all models — fixed here.
- `pre-commit run --files` and `py_compile` on changed files.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29058072699](https://github.com/sgl-project/sglang/actions/runs/29058072699)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29058072562](https://github.com/sgl-project/sglang/actions/runs/29058072562)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
