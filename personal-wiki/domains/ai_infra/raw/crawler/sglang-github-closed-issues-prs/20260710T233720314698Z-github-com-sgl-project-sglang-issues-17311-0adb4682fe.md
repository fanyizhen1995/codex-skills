---
source_id: sglang-github-closed-issues-prs
title: '[Feature]: Enable RDMA weight transfer for RL use cases'
canonical_url: https://github.com/sgl-project/sglang/issues/17311
captured_at: '2026-07-10T23:37:20.314698+00:00'
content_hash: 0adb4682fe4543b0332dfe1ad05fe794e2847142ad0f4410ca88db9ba628a16a
---
# [Feature]: Enable RDMA weight transfer for RL use cases

URL: https://github.com/sgl-project/sglang/issues/17311
State: closed
Labels: inactive
Closed at: 2026-06-20T00:50:04Z
Merged at: 

As part of [roadmap](https://github.com/sgl-project/sglang/issues/12780), several features are in the works for enabling zero-copy weight update cross hosts between training and inference instances during distributed RL training. 

<img width="1696" height="1141" alt="Image" src="https://github.com/user-attachments/assets/7591047f-ff65-41eb-9a3e-fdc805efaf77" />
Illustration of current design. A CPU-offloadable engine replica is created on each trainer rank, which receives local bucketed weight update and sends to sgl instance via TransferEngine. 

- [x] [extend nnode info](https://github.com/sgl-project/sglang/pull/17389) Extending remote_weight_info and parallelism_info http query to cross node via nccl communication. 
- [x] [Expose parallelism info](https://github.com/sgl-project/sglang/pull/20907) to enable engine replica creation. 
- [ ] _Review Pending_ [Unified Weight Mapping Interface](https://github.com/sgl-project/sglang/pull/17326) : To allow weight mapping between incoming parameter -> model weight shard. will be part of a larger refactor
@zhaochenyang20
