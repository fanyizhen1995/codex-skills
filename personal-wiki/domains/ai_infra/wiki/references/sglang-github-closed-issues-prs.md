---
type: Reference
title: SGLang GitHub Closed Issues And PRs
description: Local raw corpus and curated operational signals from closed sgl-project/sglang GitHub issues, pull requests, comments, and review comments.
domain: ai_infra
status: reviewed
tags:
  - sglang
  - github-issues
  - github-pull-requests
  - inference-serving
  - model-runtime
source_refs:
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz
  - ../../raw/crawler/sglang-github-closed-issues-prs/manifest.json
  - ../../raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json
  - ../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md
  - ../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md
updated: 2026-07-08
aliases:
  - sgl-project/sglang closed issues
  - sgl-project/sglang closed PRs
  - SGLang issue and PR corpus
related:
  - ../projects/sglang.md
---
# Summary

This reference indexes the local raw corpus for closed issues and closed pull requests in `sgl-project/sglang`. The raw layer preserves GitHub API pages, joined issue/PR objects, timeline comments, PR review comments, supplement pages used to work around repository-level issue-comment pagination boundaries, and a small crawler supplement captured after the API corpus cutoff. The curated layer keeps only scope, retrieval guidance, and operational signals.

# Corpus Scope

| Item | Value |
| --- | --- |
| Repository | `sgl-project/sglang` |
| Included source | Closed GitHub issues and closed GitHub pull requests |
| Issue endpoint capture | 252 pages, 25,108 mixed issue/PR items |
| Closed issues included | 5,633 |
| Pull request endpoint capture | 195 pages |
| Closed pull requests included | 19,475 |
| Merged PRs | 14,670 |
| Closed-unmerged PRs | 4,805 |
| Issue/PR timeline comments attached | 76,373 |
| PR review comments attached | 46,819 |
| Issue created range | 2024-01-13 to 2026-06-24 |
| Issue closed range | 2024-01-16 to 2026-06-24 |
| PR created range | 2024-01-08 to 2026-06-24 |
| PR closed range | 2024-01-08 to 2026-06-24 |
| Crawler supplement capture | 51 Markdown page snapshots captured 2026-06-29 |
| Crawler supplement overlap | 10 items overlap the API corpus; 41 are later selected page captures |
| Scheduled crawler supplement capture | 318 Markdown page snapshots captured 2026-07-01 through 2026-07-04 |
| Scheduled crawler supplement composition | 41 issues, 277 pull requests, including 198 merged pull requests |
| Scheduled crawler refresh capture | 192 Markdown page snapshots captured 2026-07-05 through 2026-07-07 |
| Scheduled crawler refresh composition | 19 issues, 173 pull requests, including 122 merged pull requests |

Raw files:

- [Joined closed issue/PR corpus](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json)
- [Derived summary](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json)
- [Raw index](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)
- [Closed issues endpoint pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz)
- [Closed pulls endpoint pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz)
- [Issue comments created-order pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz)
- [Issue comments updated-segment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz)
- [Issue comments per-item supplement pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz)
- [PR review comment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz)
- [Crawler supplement manifest](../../raw/crawler/sglang-github-closed-issues-prs/manifest.json)
- [Scheduled crawler supplement manifest, 2026-07-01 to 2026-07-04](../../raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json)
- [Scheduled crawler refresh manifest, 2026-07-05 to 2026-07-07](../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json)

# Capture Notes

The repository-level issue-comment API hit the page-300 boundary in created order. The raw corpus therefore supplements it with updated-order segment pages and per-item comment pages. After this supplementation, 17 closed items still have a mismatch between GitHub's `comments` count field and the visible comments returned by the item's comments API. These 17 items were re-fetched individually and are recorded as residual GitHub API visibility/count differences, not as an untried capture gap.

Unattached comment counts are expected in repository-level comment streams because some comments belong to open items, deleted/inaccessible items, or items outside this closed corpus filter. The joined corpus attaches only comments whose item number is included in the closed issue or closed PR set.

The crawler supplement under `raw/crawler/sglang-github-closed-issues-prs/` is selective browser/page evidence, not a replacement for the API corpus. Its manifest records 51 Markdown captures: 7 issue pages and 44 pull request pages. Ten captured item numbers already exist in the API corpus; 41 are later selected page captures, mostly closed between 2026-06-25 and 2026-06-29. Do not combine those 41 items into the API corpus counts unless a full API refresh with comments and review comments is performed.

The scheduled crawler supplement manifest for 2026-07-01 through 2026-07-04 records 318 additional Markdown page snapshots: 41 issues and 277 pull requests, including 198 merged pull requests. This supplement is useful for near-term operational discovery after the API corpus cutoff, but it remains page-level evidence without joined comments or PR review comments. Its highest-count labels are `run-ci`, `documentation`, `run-ci-extra`, `deepseek`, `diffusion`, `amd`, `jit-kernel`, `inactive`, `bypass-fastfail`, `npu`, `quant`, `dependencies`, `high priority`, `sgl-kernel`, `intel`, `release-highlight`, `blackwell`, and `xpu`.

The 2026-07-05 through 2026-07-07 scheduled crawler refresh records 192 additional page snapshots: 19 issues and 173 pull requests, including 122 merged pull requests. It is still page-level evidence only. Use it to find recent SGLang operational leads, but do not merge it into the API corpus counts or treat it as joined comment/review-comment evidence. Its highest-count labels are `run-ci`, `deepseek`, `documentation`, `diffusion`, `jit-kernel`, `run-ci-extra`, `npu`, `quant`, `bypass-fastfail`, `inactive`, `blackwell`, `amd`, and `hicache`. [raw](../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json)

# Operational Signals

The issue workflow state is mostly completed: 5,585 closed issues are `completed`, 35 are `not_planned`, and 13 are `duplicate`. Treat issue `state_reason` as workflow metadata, not as a direct quality or severity signal.

The highest-count issue labels are `inactive`, `high priority`, `bug`, `good first issue`, `help wanted`, `deepseek`, `enhancement`, `npu`, `collaboration`, `amd`, `router`, and `Multi-modal`. The highest-count PR labels include `run-ci`, `documentation`, `high priority`, `diffusion`, `deepseek`, `npu`, `amd`, `quant`, `model-gateway`, `dependencies`, `sgl-kernel`, and `Multi-modal`.

Keyword-derived themes are retrieval aids rather than mutually exclusive taxonomy. In the captured corpus, frequent surfaces include distributed parallelism and cluster behavior, serving runtime/API work, model support, kernel/attention backend work, memory and KV cache behavior, installation/build/packaging, performance, and reliability/correctness.

In the 2026-07 scheduled crawler supplement, the strongest new operational surfaces are CI and merge workflow (`run-ci`, `run-ci-extra`, `bypass-fastfail`), accelerator-specific backend work (`amd`, `npu`, `intel`, `xpu`, `blackwell`), DeepSeek and GLM-family serving work, diffusion serving, JIT/kernel work, quantization, and documentation. Representative page snapshots include AMD/ROCm disaggregation and MI300X/MI355X issues, Ascend NPU DeepSeek work, Intel XPU graph and kernel support, Blackwell FP8/prefill work, and memory/KV-cache regressions. Treat these as discovery leads until a full API refresh joins comments and review comments.

The 2026-07-05 through 2026-07-07 refresh adds more disaggregated-serving and accelerator-backend leads. Examples include a NIXL UCX worker segfault during disaggregated KV transfer with DeepSeek-R1 FP8, a HiCache prefetch cleanup fix for disaggregated prefill bootstrap aborts, Mooncake Store buffer-registration failure on Ascend 910B3, KV-cache transfer metric window errors, ROCm/Triton FP8 and online-quantization startup failures, routed-experts return stalls that make DeepEP collectives look long when one DP rank enters late, and DeepSeek/NPU/DSA/JIT-kernel implementation work. These are discovery and troubleshooting leads until a full API refresh verifies linked comments, review discussion, and final resolution state. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md)

Selected 2026-07 page-level leads now promoted into [Inference Runtime Infrastructure](inference-runtime-infrastructure.md):

| Item | Surface | Operational signal | Caveat |
| --- | --- | --- | --- |
| #24220 | Router tracing | Request ids are independent across router, prefill worker, and decode worker, making single-request troubleshooting difficult. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md) | Closed issue snapshot only; not proof of implementation. |
| #29915 | Router abort observability | Adds per-abort WARN logs, `router_reason`, and `sgl_router_engine_aborts_total{reason}` after a production incident where premature abort volume lacked cause attribution. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md) | Page-level PR evidence after API cutoff; merged state is from the snapshot. |
| #29017 | PD router failure handling | Cancels paired decode when prefill fails, with live 1P1D Mooncake validation showing decode freed in roughly 4-8 seconds instead of the 300 second default wait. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md) | Covers HTTP PD router behavior, not every engine-side transfer failure. |
| #23272 and #23342 | PD/Mooncake incidents | Record sustained-load KV transfer failures on L40S and an MI300X Mooncake/TCP router hang with worker registration and environment details. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md) | Incident-shaped issue reports, not full postmortems. |
| #29812 and #29954 | Warmup/startup regressions | Show decode warmup readiness stuck in HiCache restore state and a Blackwell GLM-5.2 FP8 startup crash after a DeepGEMM dependency bump. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md) | Startup failure leads need linked fixes or API refresh for final lifecycle accounting. |
| #24456 | Routed-experts return hot path | Diagnoses apparent long DeepEP dispatch/combine collectives under Kimi K2 TP=DP=EP=32 as late-entering DP ranks: a finishing rank gathers routed-experts output and serializes it on the scheduler main thread while peers wait at the next collective. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md) | Closed issue snapshot with issue-author diagnosis; not a merged fix, joined-comment record, or benchmark guarantee. |
| #27704, #29211, #25377 | Benchmark, profiling, and KV-event operations | Add offline throughput profiling, fix pure-DP KV-event publisher port collisions, and add HiCache UMBP DRAM/SSD L3 validation with cache-hit and TTFT measurements. [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md) [raw](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md) | Useful for local operational coverage; not a production SLO or alerting source. |

# Retrieval Notes

Use the joined raw corpus for exact lookup by issue or PR number. Use the summary JSON for aggregate counts, theme examples, label counts, top-discussed items, and capture caveats.

High-discussion examples in the captured corpus include:

| Item | Kind | Comments | Topic |
| --- | --- | ---: | --- |
| #6017 | Issue | 564 | DeepSeek large-scale P/D and expert-parallel instructions |
| #25144 | PR | 281 | Ascend NPU support for DeepSeek-V4 |
| #19746 | PR | 210 | P/D disaggregation decode-side radix cache |
| #21569 | PR | 177 | Transformers upgrade and Hugging Face utility refactor |
| #12263 | PR | 129 | EPD disaggregation support |
| #4848 | PR | 128 | Server-based rollout in Verlengine |
| #18306 | PR | 114 | SGLang-D diffusion weight update support |
| #22217 | PR | 113 | Eagle beta test failure debugging |
| #19225 | PR | 111 | Stable Diffusion 3 backend support |
| #27196 | PR | 107 | Pickle to msgpack migration |

# Relationships

- [SGLang](../projects/sglang.md) is the curated project page for this runtime and serving project.

# Citations

- [SGLang closed issues and PRs with comments](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json)
- [SGLang closed issues and PRs summary](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-summary.json)
- [SGLang closed issue API pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-api-pages.json.gz)
- [SGLang closed pull request API pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-pulls-api-pages.json.gz)
- [SGLang issue comment created-order pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-api-pages.json.gz)
- [SGLang issue comment updated-segment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-updated-segment-api-pages.json.gz)
- [SGLang issue comment per-item supplement pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-issue-comments-by-item-api-pages.json.gz)
- [SGLang PR review comment pages](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-pr-review-comments-api-pages.json.gz)
- [SGLang crawler supplement manifest](../../raw/crawler/sglang-github-closed-issues-prs/manifest.json)
- [SGLang scheduled crawler supplement manifest, 2026-07-01 to 2026-07-04](../../raw/crawler/sglang-github-closed-issues-prs/manifest-20260701-20260704.json)
- [SGLang issue #24220 request-id tracing](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208949433Z-github-com-sgl-project-sglang-issues-24220-d10eb2dd3d.md)
- [SGLang PR #29915 router abort observability](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349139142Z-github-com-sgl-project-sglang-pull-29915-e345899286.md)
- [SGLang PR #29017 PD router paired-decode cancellation](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321693976Z-github-com-sgl-project-sglang-pull-29017-e3dfacd27b.md)
- [SGLang issue #23272 Mooncake KV transfer failure](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208950785Z-github-com-sgl-project-sglang-issues-23272-cd18614391.md)
- [SGLang issue #23342 Mooncake TCP router hang](../../raw/crawler/sglang-github-closed-issues-prs/20260701T021208948083Z-github-com-sgl-project-sglang-issues-23342-a8af43b120.md)
- [SGLang issue #29812 decode warmup hang](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227249888Z-github-com-sgl-project-sglang-issues-29812-e36ce78cbc.md)
- [SGLang issue #29954 DeepGEMM startup regression](../../raw/crawler/sglang-github-closed-issues-prs/20260703T021321689913Z-github-com-sgl-project-sglang-issues-29954-58751d3526.md)
- [SGLang PR #27704 benchmark profiling support](../../raw/crawler/sglang-github-closed-issues-prs/20260704T021349137340Z-github-com-sgl-project-sglang-pull-27704-01338a2479.md)
- [SGLang PR #29211 KV-event publisher port collision fix](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227256930Z-github-com-sgl-project-sglang-pull-29211-98750e7397.md)
- [SGLang PR #25377 HiCache UMBP storage backend](../../raw/crawler/sglang-github-closed-issues-prs/20260702T021227258637Z-github-com-sgl-project-sglang-pull-25377-0207a52512.md)
- [AI infra scheduled crawler refresh manifest, 2026-07-05 to 2026-07-07](../../raw/crawler/manifest-20260705-20260707-scheduled-refresh.json)
- [SGLang issue #23499 NIXL UCX worker segfault](../../raw/crawler/sglang-github-closed-issues-prs/20260707T233530899576Z-github-com-sgl-project-sglang-issues-23499-22090e3cb2.md)
- [SGLang PR #30053 HiCache prefetch cleanup](../../raw/crawler/sglang-github-closed-issues-prs/20260706T021453060525Z-github-com-sgl-project-sglang-pull-30053-c86bbf35fb.md)
- [SGLang issue #24456 routed-experts return hot-path stall](../../raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md)
