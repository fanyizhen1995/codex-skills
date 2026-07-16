---
source_id: sglang-github-closed-issues-prs
title: Extract leaf helpers out of ModelRunner into utility modules
canonical_url: https://github.com/sgl-project/sglang/pull/31146
captured_at: '2026-07-14T23:40:21.680902+00:00'
content_hash: 996cf23d22f235a8db714db254cfdb2a5763bd327c01ac8ac87360c60fcb2c9f
---
# Extract leaf helpers out of ModelRunner into utility modules

URL: https://github.com/sgl-project/sglang/pull/31146
State: closed
Labels: quant
Closed at: 2026-07-14T07:52:04Z
Merged at: 2026-07-14T07:52:04Z

### mrc-leaf-helpers(extract-init-cublas-prep,non_mechanical_provable): Prep init_cublas for extraction: @staticmethod + class-qualified call site

### mrc-leaf-helpers(extract-init-cublas-move,mechanical_provable): Move init_cublas to utils.common (cut+paste)

### mrc-leaf-helpers(extract-apply-torch-tp-prep,non_mechanical_provable): Prep apply_torch_tp for extraction: @staticmethod + kwarg-only + class-qualified call site

### mrc-leaf-helpers(extract-apply-torch-tp-move,mechanical_provable): Move apply_torch_tp to layers.model_parallel (cut+paste)

### mrc-leaf-helpers(apply-torch-tp-wrapper-postpare,non_mechanical_provable): Requalify the apply_torch_tp wrapper call through the model_parallel module import

### mrc-leaf-helpers(extract-init-threads-binding-prep,non_mechanical_provable): Prep init_threads_binding for extraction: @staticmethod + kwargs + return-value

De-self in place: the method becomes a kwargs @staticmethod returning
local_omp_cpuid; the initialize call site assigns the return through the
class-qualified form. The body stays at its original position in the class.

### mrc-leaf-helpers(extract-init-threads-binding-move,mechanical_provable): Move init_threads_binding to utils.numa_utils (cut+paste)

### mrc-leaf-helpers(init-threads-binding-wrapper-postpare,non_mechanical_provable): Reintroduce the init_threads_binding orchestration wrapper and requalify through the numa_utils module import

Wrap the moved function back into the init_* helper (initialize resumes
calling self.init_threads_binding()) and route the call through the
numa_utils module import instead of the bare function import.

### mrc-leaf-helpers(extract-prealloc-symm-pool-prep,non_mechanical_provable): Prep prealloc_symmetric_memory_pool for extraction: @staticmethod + kwargs

### mrc-leaf-helpers(extract-prealloc-symm-pool-move,mechanical_provable): Move prealloc_symmetric_memory_pool to pynccl_allocator (cut+paste)

### mrc-leaf-helpers(move-resolve-language-model,mechanical_provable): Move resolve_language_model from model_runner.py to model_loader/utils.py (cut+paste)

### mrc-leaf-helpers(step-span-name-prep,non_mechanical_provable): Rename _build_step_span_name to its public move-name build_step_span_name in place

### mrc-leaf-helpers(step-span-name-move,mechanical_provable): Move build_step_span_name to utils.profile_utils (cut+paste)

### mrc-leaf-helpers(inline-trivial-build-model-config-into-its-two-c,non_mechanical_provable): Inline trivial _build_model_config into its two call sites

_build_model_config only forwarded to ModelConfig.from_server_args with the same argument shape, so inline it at the two draft-config call sites and drop the method.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29315980863](https://github.com/sgl-project/sglang/actions/runs/29315980863)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29315980659](https://github.com/sgl-project/sglang/actions/runs/29315980659)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
