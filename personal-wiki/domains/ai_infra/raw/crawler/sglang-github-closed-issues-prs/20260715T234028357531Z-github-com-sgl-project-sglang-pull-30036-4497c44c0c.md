---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Support RL rollout for the Wan pipeline via a per-request scheduler
  switch'
canonical_url: https://github.com/sgl-project/sglang/pull/30036
captured_at: '2026-07-15T23:40:28.357531+00:00'
content_hash: 4497c44c0cb141ba7b284bfe009cbb8ceb082e62913884a92e4df1dcb86a60a0
---
# [diffusion] Support RL rollout for the Wan pipeline via a per-request scheduler switch

URL: https://github.com/sgl-project/sglang/pull/30036
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-15T14:30:52Z
Merged at: 2026-07-15T14:30:51Z

## Motivation

Wan serves with UniPC, but the RL rollout path (`SchedulerRLMixin`: SDE sampling with per-step log-probs) runs on first-order flow-match Euler. One engine serves both rollout (`rollout=True`) and eval (`rollout=False`) requests within a training run, so the scheduler choice must be per request.

Diffusion disaggregation reconstructs the request-local scheduler on the denoiser because mutable scheduler objects are not transferred between roles. That reconstruction must apply the same per-request mapping; otherwise a Wan rollout prepared with Euler on the encoder is rebuilt from the denoiser's serving UniPC template.

## Modifications

- `post_training/rollout_scheduler.py` (new): `rollout_scheduler_for(serving)` maps the serving scheduler to the one rollout requests denoise with — UniPC → flow-match Euler at the serving shift. One `isinstance` branch per validated scheduler family; anything else passes through unchanged.
- `get_or_create_rollout_request_scheduler` centralizes rollout mapping and request ownership. A newly mapped scheduler is bound directly; an identity-passthrough serving scheduler is cloned only when request isolation is required.
- `TimestepPreparationStage.forward` uses the helper for `rollout=True` requests and keeps the existing serving path for `rollout=False` requests.
- Disaggregated denoisers select an isolated request scheduler before initializing its timesteps. Wan rollout constructs one request-local Euler without an extra deepcopy; non-rollout requests still clone the serving scheduler.
- `RolloutDenoisingMixin` reads `batch.scheduler` instead of the stage module (`DenoisingStage` already asserts it is bound).

A serving-only engine never initializes any RL object. Pipelines already serving an RL-capable scheduler keep their scheduler type; unmapped schedulers keep failing with `does not support rollout`.

## Validation

- Local untracked focused unit tests: 3 passed, covering disaggregated Wan rollout (one Euler construction, no clone), disaggregated eval (one UniPC clone), and isolated identity-passthrough rollout schedulers.
- `python -m unittest python/sglang/multimodal_gen/test/unit/test_disagg_roles.py`: 47 passed.
- `python -m unittest python/sglang/multimodal_gen/test/unit/test_scheduler_rollout_unit.py`: 6 passed.
- `pre-commit run --files` on all three modified production files: passed.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29395422721](https://github.com/sgl-project/sglang/actions/runs/29395422721)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29395422590](https://github.com/sgl-project/sglang/actions/runs/29395422590)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
