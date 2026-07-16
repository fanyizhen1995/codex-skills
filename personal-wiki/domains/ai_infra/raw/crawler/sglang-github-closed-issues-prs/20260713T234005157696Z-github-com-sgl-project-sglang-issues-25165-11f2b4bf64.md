---
source_id: sglang-github-closed-issues-prs
title: '[Bug] main branch seems broke with deepseek v4 flash deployment'
canonical_url: https://github.com/sgl-project/sglang/issues/25165
captured_at: '2026-07-13T23:40:05.157696+00:00'
content_hash: 11f2b4bf6444d65ed38081e26e854af9e0ac5f43d98ae33d645b7d98fdc85832
---
# [Bug] main branch seems broke with deepseek v4 flash deployment

URL: https://github.com/sgl-project/sglang/issues/25165
State: closed
Labels: inactive
Closed at: 2026-07-13T00:36:17Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

I'm using H20-141G * 4 to deploy deepseek-v4-flash fp8 version. But found this error:

`  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3995, in run_scheduler_process
    scheduler = Scheduler(
                ^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 434, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 705, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 660, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 262, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 347, in _init_model_runner
    self._model_runner = ModelRunner(
                         ^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 532, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 618, in initialize
    compute_initial_expert_location_metadata(
  File "/sgl-workspace/sglang/python/sglang/srt/eplb/expert_location.py", line 590, in compute_initial_expert_location_metadata
    return ExpertLocationMetadata.init_trivial(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/eplb/expert_location.py", line 89, in init_trivial
    common = ExpertLocationMetadata._init_common(server_args, model_config)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/eplb/expert_location.py", line 192, in _init_common
    ModelConfigForExpertLocation.from_model_config(model_config)
  File "/sgl-workspace/sglang/python/sglang/srt/eplb/expert_location.py", line 574, in from_model_config
    model_class, _ = get_model_architecture(model_config)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_loader/utils.py", line 220, in get_model_architecture
    architectures = resolve_transformers_arch(model_config, architectures)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_loader/utils.py", line 150, in resolve_transformers_arch
    raise ValueError(
ValueError: Cannot find model module. 'DeepseekV4ForCausalLM' is not a registered model in the Transformers library (only relevant if the model is meant to be in Transformers) and 'AutoModel' is not present in the model config's 'auto_map' (relevant if the model is custom).`

### Reproduction

SGLANG_DSV4_FP4_EXPERTS=0 SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 sglang serve   --trust-remote-code   --model-path /path/deepseekv4flash   --tp 4   --speculative-algo EAGLE   --speculative-num-steps 3   --speculative-eagle-topk 1   --speculative-num-draft-tokens 4   --tool-call-parser deepseekv4   --reasoning-parser deepseek-v4   --host 0.0.0.0   --port 30000

### Environment

node: H40 * 4
