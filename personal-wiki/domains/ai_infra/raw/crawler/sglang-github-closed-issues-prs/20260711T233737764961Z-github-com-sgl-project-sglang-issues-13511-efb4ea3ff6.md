---
source_id: sglang-github-closed-issues-prs
title: '[Roadmap] roadmap of request tracing (2025 Q4 and 2026 Q1)'
canonical_url: https://github.com/sgl-project/sglang/issues/13511
captured_at: '2026-07-11T23:37:37.764961+00:00'
content_hash: efb4ea3ff6202a909ab64f6796c0a95a4f32d52993028e6a2c6690cd8c578587
---
# [Roadmap] roadmap of request tracing (2025 Q4 and 2026 Q1)

URL: https://github.com/sgl-project/sglang/issues/13511
State: closed
Labels: inactive
Closed at: 2026-07-11T00:32:59Z
Merged at: 

### Tracing for uncovered engine components
- [x] Add trace-level, trace-module, and unify tracing/request-stage-metrics @sufeng-buaa  https://github.com/sgl-project/sglang/pull/13152 https://github.com/sgl-project/sglang/pull/17862
- [ ] Implement tracing for Hierarchical Cache (selected by --trace-module hicache) @stmatengss https://github.com/sgl-project/sglang/pull/23755
- [x] Implement distributed request tracing for PP https://github.com/sgl-project/sglang/pull/23169
- [x] Implement distributed request tracing for Speculative Decode https://github.com/sgl-project/sglang/pull/19545
- [ ] implenment tracing for mooncake backend in PD disaggregation https://github.com/sgl-project/sglang/pull/23755

### Tracing for sgl-model-gateway
- [x] Implement low-overhead Router request tracing with aggregation of trace data from the engine @sufeng-buaa https://github.com/sgl-project/sglang/pull/13897

### Performance and Availability
- [ ] Optimize tracing overhead under large batch_size to ensure TTFT/TPOT is minimally impacted @sufeng-buaa 
- [x] adjust trace level Dynamically (add http API) @sufeng-buaa  https://github.com/sgl-project/sglang/pull/17862
- [x] Implement coverage of exception paths in request handling to prevent unclosed spans and avoid memory leaks. https://github.com/sgl-project/sglang/pull/17862
- [x] Improve span attributes @zhanghaotong https://github.com/sgl-project/sglang/pull/17008
- [ ] Optimize trace level @zhanghaotong 
- [x] Improve necessary events (such as retract) @zhanghaotong  https://github.com/sgl-project/sglang/pull/17862

### Data process
- [ ] Export OTLP data to database, filter and enhance processing. Currently, a simple script is provided to convert text data into Chrome JSON format (which can be parsed by Perfetto). @sufeng-buaa 

### Exploratory work (Draft)
- [ ] Refine output information (e.g., top-k tokens, etc.). May introduce performance issues? @zhanghaotong 
- [ ] Fine-grained tracing for multimodal @zhanghaotong 
- [x] Further unify metrics and tracing; currently, metrics are relatively fragmented.
- [x] Fine-grained tracing for SGLang diffusion https://github.com/sgl-project/sglang/pull/21254
