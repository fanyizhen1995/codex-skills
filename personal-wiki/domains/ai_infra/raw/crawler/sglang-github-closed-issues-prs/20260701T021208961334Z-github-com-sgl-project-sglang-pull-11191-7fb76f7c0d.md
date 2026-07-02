---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Support Sparse Attention and KV cache scheduling between CPU and
  GPU for GQA/DSA.'
canonical_url: https://github.com/sgl-project/sglang/pull/11191
captured_at: '2026-07-01T02:12:08.961334+00:00'
content_hash: 7fb76f7c0d4988583c7b5127d3cead9f13cf153e633815150ef087f5d3b0e95f
---
# [Feature] Support Sparse Attention and KV cache scheduling between CPU and GPU for GQA/DSA.

URL: https://github.com/sgl-project/sglang/pull/11191
State: closed
Labels: 
Closed at: 2026-06-30T07:58:41Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.ai to discuss further. -->

The main implementation is currently in a private repository. I will migrate the code to this branch within a week.

## Motivation
Support sparse attention computation for LLMs using GQA/DSA to accelerate inference under long context. 


## Modifications

- Support the sparse attention computation for FlashAttention and FlashMLA attention backend.
- Decouple the selection of important KV caches from the sparse-attention-based computation to accelerate the overall computation.
- Implement KV-cache scheduling between CPU RAM and GPU global memory, and optimize the associated strategies to improve throughput for inference services in long-context scenarios.


TodoList:

- [x] Support CUDA Graph for Async Implementation.
- [ ] Fix potential issues when starting as server.
- [ ] Support DSA as retriever.
- [ ] Implement KV Cache management scheduling module.

## Accuracy Tests
We tested the model accuracy of the sparse attention scheme using the Qwen3-8B and Llama3.1-8B on LongBench and RULER. (when only 4096 tokens are retained for each request during the computation of the attention module):

<img width="716" height="627" alt="image" src="https://github.com/user-attachments/assets/c31062b5-965a-4e91-8227-f181ed169c30" />

The performance improvement for Llama3.1 8B on H20 with 32k input and 1024 output:
baseline:
<img width="1209" height="1089" alt="image" src="https://github.com/user-attachments/assets/359e5264-40f5-4b6c-ba1b-c19f1f0fe1a9" />
sparse with retrain 4096 kv cache:
<img width="1209" height="1112" alt="image" src="https://github.com/user-attachments/assets/13c9b1ce-b49c-4989-b23a-e00213c83992" />


<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
It will be provided at a later time.



## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.ai/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.ai/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.ai/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.ai/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.ai/developer_guide/contribution_guide.html#benchmark-the-speed).
