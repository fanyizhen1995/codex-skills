---
source_id: sglang-github-closed-issues-prs
title: '[bench] Add agentic-trace multi-turn dataset to bench_serving'
canonical_url: https://github.com/sgl-project/sglang/pull/29215
captured_at: '2026-07-07T23:35:30.920478+00:00'
content_hash: 4ca6f4b4d30972f7a89ad5594bc52a0d595a36494cfd0ec9409d88bea1b65427
---
# [bench] Add agentic-trace multi-turn dataset to bench_serving

URL: https://github.com/sgl-project/sglang/pull/29215
State: closed
Labels: documentation
Closed at: 2026-07-07T02:45:44Z
Merged at: 2026-07-07T02:45:44Z

## Motivation

`bench_serving` already supports multi-turn replay (a `DatasetRow` whose `prompt` is a list of per-round payloads is replayed round by round, feeding the server's real assistant reply back into the next round's history), but there was no dataset loader for pre-built agentic traces. This PR adds an `agentic-trace` dataset so we can benchmark realistic multi-turn agentic workloads (OpenHands / SWE-smith style traces) end to end.

## Modifications

- Add `python/sglang/benchmark/datasets/agentic_trace.py` with `AgenticTraceDataset`:
  - Reads a trace JSON of the shape `{"metadata": {...}, "conversations": [[{"messages": [...], "prompt_tokens": N}, ...], ...]}`.
  - Each conversation becomes one `DatasetRow` whose `prompt` is the list of per-turn message deltas, which the existing multi-turn machinery detects and replays.
  - Defaults per-turn output length to 220 (matches the OpenHands/`swe_smith` recipe) when `--sharegpt-output-len` is not given.
- Register `agentic-trace` in `python/sglang/benchmark/datasets/__init__.py` and add it to the `--dataset-name` choices in `benchmark/serving.py`.
- Add two CLI flags:
  - `--dataset-offset`: rotate the conversation list before sampling so successive sweep steps start on fresh conversations (mirrors evalscope `--dataset-offset`).
  - `--agentic-max-turns`: cap each conversation to N turns for small, fast profiling runs.
- Document the dataset and its flags in `docs_new/docs/developer_guide/bench_serving.mdx`.

Requires a chat backend, e.g.:

```bash
python -m sglang.benchmark.serving \
  --backend sglang-oai-chat \
  --dataset-name agentic-trace \
  --dataset-path /path/to/trace.json \
  --num-prompts 64
```

## Accuracy Tests

N/A — benchmarking tooling only; no model output paths changed.

## Speed Tests and Profiling

N/A — this adds a benchmark dataset loader; it does not change inference code paths.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).




























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28837472794](https://github.com/sgl-project/sglang/actions/runs/28837472794)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28837472704](https://github.com/sgl-project/sglang/actions/runs/28837472704)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
