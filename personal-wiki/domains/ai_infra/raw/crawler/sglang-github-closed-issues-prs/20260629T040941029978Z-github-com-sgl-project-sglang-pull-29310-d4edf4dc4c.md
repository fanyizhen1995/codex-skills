---
source_id: sglang-github-closed-issues-prs
title: '[HiCache] Detect for double-free in HostKVCache'
canonical_url: https://github.com/sgl-project/sglang/pull/29310
captured_at: '2026-06-29T04:09:41.029978+00:00'
content_hash: d4edf4dc4c641b9cf50c94b65eda60e477e8660a7bc32a700055bb473192d884
---
# [HiCache] Detect for double-free in HostKVCache

URL: https://github.com/sgl-project/sglang/pull/29310
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-06-29T01:02:22Z
Merged at: 2026-06-29T01:02:22Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

The uses of `host_indices` in `HiRadixCache` and `HiCacheController` are tricky, because of the flexible life-time.  This patch adds detection for double-free in `HostKVCache`.  When double-free happens, an assertion failure will occur.

## Modifications

Modified `HostKVCache`, using a booelan tensor to track allocated indices.  Added assertion in `alloc` and `free`.

Also added a unit test case.

## Accuracy Tests

N/A.

## Speed Tests and Profiling

I tested GLM5.2 PP=4 TP=4.  The checking code seems not affect performance.

<img width="1488" height="782" alt="ACE5635E-0D4A-4ADC-B7C5-12A4353103A2" src="https://github.com/user-attachments/assets/53b2c614-5ecc-41b9-8938-83df665b3876" />


Server startup command:
(`num-total-tokens` and `hicache-ratio` are set so that L1 + L2 are large enough to hold all tokens).
```sh
python3 -m sglang.launch_server \
--model-path zai-org/GLM-5.2-FP8 \
--host 0.0.0.0 --port 30000 \
--tp 4 --pp-size 4 --dist-init-addr <node0>:20102 --nnodes 2 --node-rank 0 \
--context-length 202752 --mem-fraction-static 0.8 --kv-cache-dtype fp8_e4m3 \
--page-size 64 --chunked-prefill-size 8192 \
--enable-hierarchical-cache --hicache-ratio 2 \
--enable-metrics \
--max-total-tokens=1000000 \
--hicache-ratio=4 \
--trust-remote-code
```

Testing script:
```sh
set -e
for i in $(seq 1 5); do
    python benchmark/hicache/bench_multiturn.py  \
        --num-clients=512 \
        --num-rounds=10 \
        --disable-auto-run  \
        --model=deepseek-ai/DeepSeek-V4-Flash  \
        --request-rate 16
done
```

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28291858821](https://github.com/sgl-project/sglang/actions/runs/28291858821)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28291858745](https://github.com/sgl-project/sglang/actions/runs/28291858745)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
