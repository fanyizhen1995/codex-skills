---
source_id: sglang-github-closed-issues-prs
title: Fix OpenAI serving benchmark input token accounting
canonical_url: https://github.com/sgl-project/sglang/pull/29840
captured_at: '2026-07-02T02:12:27.259976+00:00'
content_hash: 67fd8e7eda546f429487dd9f303ad00653892d7835f9ab109dab1beefb97fdb7
---
# Fix OpenAI serving benchmark input token accounting

URL: https://github.com/sgl-project/sglang/pull/29840
State: closed
Labels: 
Closed at: 2026-07-01T11:47:21Z
Merged at: 

## Motivation

  The OpenAI-format serving benchmark currently relies on client-side prompt token estimates for input-token metrics. For
  OpenAI-compatible chat workloads, this can diverge from the server-reported `usage.prompt_tokens` because the server may
  apply its own chat template, tokenizer behavior, tool serialization, or request preprocessing.

  This caused benchmark reports to show only a single `Total input tokens` value based on the dataset-side estimate, making it
  difficult to distinguish:

  - client-side estimated prompt tokens from dataset preprocessing
  - server-side actual prompt tokens returned by the serving endpoint

  There were also two dataset handling gaps for OpenAI-format JSONL inputs:

  - `max_completion_tokens` was not treated the same as `max_tokens` when deriving per-request output length.
  - `sharegpt_context_len` was not propagated to the OpenAI dataset loader, so over-context OpenAI-format requests were not
  filtered consistently.

  ## Modifications

  `serving.py`

  - Capture `usage.prompt_tokens` from OpenAI completions streaming responses.
  - Capture `usage.prompt_tokens` from OpenAI chat completions streaming responses.
  - Capture `usage.prompt_tokens` from OpenAI chat completions non-streaming responses.
  - Store the server-reported prompt length in `RequestFuncOutput.prompt_len`.
  - Add `total_input_client` to `BenchmarkMetrics`.
  - Report input tokens separately as:
    - `Total input tokens (client)`
    - `Total input tokens (server)`

  `openai_dataset.py`

  - Add `context_len` to `OpenAIDataset`.
  - Propagate `args.sharegpt_context_len` into OpenAI-format dataset loading.
  - Treat `max_completion_tokens` as an output-length source, matching OpenAI chat completion request format.
  - Skip OpenAI-format requests whose estimated prompt length plus output length exceeds `context_len`.

  ## Accuracy Tests

  No model forward path or serving behavior changed.

  This change only affects serving benchmark accounting and dataset filtering. The server-side input token metric now uses
  `usage.prompt_tokens` when available, which better reflects the actual request seen by the serving backend.

  ## Speed Tests and Profiling

  No inference throughput impact.

  The additional work is limited to reading `usage.prompt_tokens` from response chunks and carrying one extra aggregate counter
  in benchmark metrics.

  ## Validation

  - Ran Python compile checks for modified files:
    - `python3 -m py_compile python/sglang/benchmark/serving.py python/sglang/benchmark/datasets/openai_dataset.py`
  - Ran pre-commit hooks during commit:
    - AST check
    - trailing whitespace check
    - ruff
    - isort
    - black-jupyter
    - codespell
    - repository policy hooks



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:warning: [Run #28510082551](https://github.com/sgl-project/sglang/actions/runs/28510082551)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: [Run #28510082254](https://github.com/sgl-project/sglang/actions/runs/28510082254)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
