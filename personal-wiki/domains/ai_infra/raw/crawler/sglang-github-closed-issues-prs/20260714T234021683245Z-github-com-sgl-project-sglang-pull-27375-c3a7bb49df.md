---
source_id: sglang-github-closed-issues-prs
title: '[Model] Add support for JetBrains'' Mellum v2 code generation model'
canonical_url: https://github.com/sgl-project/sglang/pull/27375
captured_at: '2026-07-14T23:40:21.683245+00:00'
content_hash: c3a7bb49df176432b7a73fbf0e282ce326fbc78000b53976eaf8e36a4f66b3b1
---
# [Model] Add support for JetBrains' Mellum v2 code generation model

URL: https://github.com/sgl-project/sglang/pull/27375
State: closed
Labels: documentation, run-ci
Closed at: 2026-07-14T05:54:38Z
Merged at: 2026-07-14T05:54:38Z

## Motivation

Add support for [JetBrains/Mellum2-12B-A2.5B-Thinking](https://huggingface.co/JetBrains/Mellum2-12B-A2.5B-Thinking) and related variants, a hybrid sliding-window-attention MoE code-generation model from JetBrains.


## Modifications

- New `MellumForCausalLM` model file inheriting from Qwen with the following additions/changes: interleaved sliding-window/full attention via `layer_types`, per-layer-type RoPE and per-layer dense/sparse MLP routing via `mlp_layer_types`.
- HF config compatibility shim in `_CONFIG_REGISTRY`: prefers native `MellumConfig` when available (`transformers>=5.10.2`), falls back to a `Qwen3MoeConfig`-based alias otherwise.
- Hybrid-SWA registration in `model_config.py`.
- `MellumForCausalLM` added to `common_utils.py` MoE tuning architecture dispatch.
- Documentation row added to `docs_new/docs/supported-models/generative_models.mdx`.

## Usage

### Launch Server

```bash
python -m sglang.launch_server --model-path JetBrains/Mellum2-12B-A2.5B-Thinking \
  --host 0.0.0.0 --port 30000 --attention-backend flashinfer \
  --reasoning-parser qwen3
```

### Basic Chat

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

resp = client.chat.completions.create(
    model="JetBrains/Mellum2-12B-A2.5B-Thinking",
    messages=[{"role": "user", "content": "Write a Python function to compute Fibonacci numbers."}],
    max_tokens=1024,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(resp.choices[0].message.content)

# Thinking/Reasoning
resp = client.chat.completions.create(
    model="JetBrains/Mellum2-12B-A2.5B-Thinking",
    messages=[{"role": "user", "content": "If a train travels at 60 km/h for 2.5 hours, how far?"}],
    max_tokens=2048,
    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
)
print(resp.choices[0].message.reasoning_content)
print(resp.choices[0].message.content)
```

## Accuracy Tests

BF16, served via `sglang.launch_server` with `flashinfer` attention backend. SGLang TP=1 on 1×H200; SGLang TP=2 on 2×H200.

| Eval                                | SGLang TP=1 | SGLang TP=2 |
| ----------------------------------- | ----------: | ----------: |
| GSM8K (200, 5-shot, completion API) |       0.830 |       0.840 |
| MMLU (500, thinking off)            |       0.620 |       0.624 |
| HumanEval pass@1 (50, thinking off) |       0.852 |       0.844 |
| HumanEval pass@5                    |       0.860 |       0.860 |

Sampling: `temperature=0`, `max_tokens=512` (GSM8K) / `1024` (MMLU, HumanEval). GSM8K uses `/v1/completions` to bypass the chat template's `<think>` prefix; MMLU and HumanEval use `/v1/chat/completions` with `enable_thinking=false`.

## Speed Tests and Profiling

BF16, `sglang.bench_serving --backend sglang --dataset-name random`.
### Latency (10 prompts, cc=1)

```bash
python3 -m sglang.bench_serving --backend sglang \
  --host 127.0.0.1 --port 30000 \
  --dataset-name random --num-prompts 10 --max-concurrency 1
```

| Metric                          |   TP=1 |   TP=2 |
| ------------------------------- | -----: | -----: |
| Successful requests             |     10 |     10 |
| Output token throughput (tok/s) | 305.37 | 338.53 |
| Total token throughput (tok/s)  | 610.73 | 677.07 |
| Mean TTFT (ms)                  |  42.77 |  36.61 |
| Mean TPOT (ms)                  |   3.23 |   2.92 |
| Median ITL (ms)                 |   3.23 |   2.87 |

### Throughput (1000 prompts, cc=100)

```bash
python3 -m sglang.bench_serving --backend sglang \
  --host 127.0.0.1 --port 30000 \
  --dataset-name random --num-prompts 1000 --max-concurrency 100
```

| Metric                          |    TP=1 |    TP=2 |
| ------------------------------- | ------: | ------: |
| Successful requests             |    1000 |    1000 |
| Request throughput (req/s)      |    7.51 |   10.24 |
| Output token throughput (tok/s) | 7687.10 | 10486.3 |
| Total token throughput (tok/s)  |   15374 |   20973 |
| Mean TTFT (ms)                  | 1494.67 | 1175.03 |
| Mean TPOT (ms)                  |   11.54 |    8.34 |
| Median ITL (ms)                 |   10.22 |    7.17 |




## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.





























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29285622880](https://github.com/sgl-project/sglang/actions/runs/29285622880)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29285622794](https://github.com/sgl-project/sglang/actions/runs/29285622794)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
