---
source_id: sglang-github-closed-issues-prs
title: '[Bug] NGRAM speculative decoding crashes when return_hidden_states=True due
  to Tensor truth-value check'
canonical_url: https://github.com/sgl-project/sglang/issues/26131
captured_at: '2026-07-10T23:37:20.315606+00:00'
content_hash: 490aa699fb3e59c3df5d3bd59a6d1aef2fe53c1096f68248986b817db25a9fb8
---
# [Bug] NGRAM speculative decoding crashes when return_hidden_states=True due to Tensor truth-value check

URL: https://github.com/sgl-project/sglang/issues/26131
State: closed
Labels: 
Closed at: 2026-07-10T01:24:29Z
Merged at: 

Environment:

- SGLang commit: `cadfa2d025d3e251352a115291621c8214c733e5`
- GPU: single `NVIDIA A100-SXM4-40GB` (`40960 MiB`)
- CUDA / driver: CUDA `13.0` from `nvidia-smi`; NVIDIA driver `580.126.20`; PyTorch CUDA `13.0`
- Python: `3.10.12`
- PyTorch: `2.11.0+cu130`
- Model: `Qwen/Qwen2.5-7B-Instruct`, HF snapshot `a09a35458c702b33eeacc393d103063234e8bc28`
- Install method: clean upstream clone of `https://github.com/sgl-project/sglang`, editable source install using upstream docs' source install command `pip install -e "python"` in a fresh virtualenv. No SGLang source edits were made. I installed build prerequisites/Rust toolchain only because Ubuntu's packaged Cargo 1.75 could not build the upstream Rust crate.

Summary:

Enabling NGRAM speculative decoding together with hidden-state return crashes during target verification.

Reproduction:

Clean clone and install:

```bash
git clone https://github.com/sgl-project/sglang.git
cd sglang
git rev-parse HEAD
# cadfa2d025d3e251352a115291621c8214c733e5

python3 -m venv ~/sglang-repro-venv
source ~/sglang-repro-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "python"
```

Engine reproduction script:

```python
import sglang as sgl

model = "Qwen/Qwen2.5-7B-Instruct"
prompts = [
    "Repeat the phrase 'the quick brown fox jumps over the lazy dog' five times, then summarize it.",
    "Write a short paragraph that repeatedly uses the words data, model, token, and cache.",
    "Complete this repetitive template: A B C A B C A B C ...",
]

llm = sgl.Engine(
    model_path=model,
    trust_remote_code=True,
    mem_fraction_static=0.7,
    cuda_graph_max_bs=8,
    log_level="info",
    enable_return_hidden_states=True,
    speculative_algorithm="NGRAM",
    speculative_num_draft_tokens=16,
    speculative_ngram_max_bfs_breadth=10,
    attention_backend="flashinfer",
)

outputs = llm.generate(
    prompts,
    sampling_params={"temperature": 0.0, "max_new_tokens": 64},
    return_hidden_states=True,
)
print(outputs)
llm.shutdown()
```

Equivalent command used in the repro harness:

```bash
python ~/sglang_ngram_hidden_repro.py \
  --case ngram_hidden \
  --model Qwen/Qwen2.5-7B-Instruct \
  --batch-size 3 \
  --max-new-tokens 64
```

Expected behavior:

Hidden states should be returned, or at minimum the request should complete without crashing.

Actual behavior:

The scheduler process crashes during NGRAM verification:

```text
Scheduler hit an exception: Traceback (most recent call last):
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/managers/scheduler.py", line 3809, in run_scheduler_process
    scheduler.run_event_loop()
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/managers/scheduler.py", line 1508, in run_event_loop
    dispatch_event_loop(self)
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/managers/scheduler.py", line 3680, in dispatch_event_loop
    scheduler.event_loop_normal()
  File "/home/gabe/sglang-repro-venv/lib/python3.10/site-packages/torch/utils/_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/managers/scheduler.py", line 1526, in event_loop_normal
    result = self.run_batch(batch)
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/managers/scheduler.py", line 2909, in run_batch
    batch_result = self.model_worker.forward_batch_generation(
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/speculative/ngram_worker.py", line 314, in forward_batch_generation
    logits_output, next_token_ids, num_correct_drafts = verify_input.verify(
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/speculative/ngram_info.py", line 454, in verify
    self._fill_requests(batch, logits_output)
  File "/home/gabe/sglang-upstream-clean-20260522-220923/python/sglang/srt/speculative/ngram_info.py", line 206, in _fill_requests
    if logits_output.hidden_states:
RuntimeError: Boolean value of Tensor with more than one value is ambiguous
```

Controls:

- No NGRAM + `return_hidden_states=True`: completed successfully, no crash.
- NGRAM + `return_hidden_states=False`: completed successfully, no crash. NGRAM verification was exercised; response metadata included `spec_accept_length`, `spec_accept_rate`, `spec_verify_ct`, etc.

Independent runs:

- Run 1: crashed at `python/sglang/srt/speculative/ngram_info.py::_fill_requests`, line 206, `if logits_output.hidden_states:`, with `RuntimeError: Boolean value of Tensor with more than one value is ambiguous`.
- Run 2: crashed at the same frame and error.
- Run 3: crashed at the same frame and error.

Failure rate: 3/3.

Suspected cause:

`logits_output.hidden_states` is an optional `torch.Tensor`, but `_fill_requests()` checks it with Python truthiness:

```python
if logits_output.hidden_states:
    logits_output.hidden_states = logits_output.hidden_states[
        self.accept_indices
    ]
```

A multi-element tensor cannot be evaluated as a boolean. The guard likely should check `is not None` before indexing.

Notes:

- This reproduction used only a clean upstream `sgl-project/sglang` checkout.
- No forks, local patches, monkeypatches, workaround branches, or source edits were used.
- Final duplicate search immediately before filing found no matching upstream issue or PR for:
  - `"logits_output.hidden_states" "NgramVerifyInput"`
  - `"Boolean value of Tensor with more than one value is ambiguous" "ngram"`
  - `"return_hidden_states" "NGRAM"`
  - `"ngram_info.py" "hidden_states"`
