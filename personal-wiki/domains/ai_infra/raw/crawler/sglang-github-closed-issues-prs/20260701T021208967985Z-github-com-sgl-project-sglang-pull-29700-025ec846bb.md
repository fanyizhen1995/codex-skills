---
source_id: sglang-github-closed-issues-prs
title: Add new Intel SGLang members into CI_permission list
canonical_url: https://github.com/sgl-project/sglang/pull/29700
captured_at: '2026-07-01T02:12:08.967985+00:00'
content_hash: 025ec846bbaf4bfe76274a550c2918b0cb2e27cd9d65bfef56fb41ed44c1b5a7
---
# Add new Intel SGLang members into CI_permission list

URL: https://github.com/sgl-project/sglang/pull/29700
State: closed
Labels: intel, run-ci
Closed at: 2026-06-30T03:06:29Z
Merged at: 2026-06-30T03:06:29Z

## Motivation

As title. After their IDs appearing in the list, they can trigger CI by commenting /tag-and-rerun-ci, /tag-run-ci-label, /rerun-failed-ci.

## Modifications

Add the following members into CI_PERMISSIONS.json:

@YangKai0616 : XPU integration of GPTQ/AWQ int4 dense linear and int4 quantized MoE inference.

@Yuxingwang-intel : Enabling and optimizing diffusion models on Intel CPU/XPU.

@cyxlily : SYCL ops development (flash_mla_with_kvcache, hadamard_transform, topk_transform...).

@htzo : Speculative decoding on CPU/XPU.

@liangan1 : Dedicated optimizations for key models on XPU.

@liuyucheng1 : New model enabling & optimizations.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28416611578](https://github.com/sgl-project/sglang/actions/runs/28416611578)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28417493907](https://github.com/sgl-project/sglang/actions/runs/28417493907)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
