---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] feat: performance_mode=speed enables torch.compile by default'
canonical_url: https://github.com/sgl-project/sglang/pull/30016
captured_at: '2026-07-04T02:13:49.133860+00:00'
content_hash: d5171fb70cb563e36c2c69f8cead2496e11a3c1f57854ed8562a151b61cc0eb0
---
# [diffusion] feat: performance_mode=speed enables torch.compile by default

URL: https://github.com/sgl-project/sglang/pull/30016
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-03T11:12:18Z
Merged at: 2026-07-03T11:12:18Z

## Motivation

`--performance-mode speed` configures GPU-resident execution (offloads off, FSDP/CFG-parallel policy) but leaves `torch.compile` off unless the user *also* passes `--enable-torch-compile`. In practice that split is easy to miss: auditing our cross-framework benchmark found several speed-intent deployments silently running eager DiTs. "speed" should mean fastest-by-default.

## Change

In the auto-tuner's speed branch, enable `torch.compile` when the user has not explicitly set it. An explicit `--enable-torch-compile false` still wins — that override matters in practice: on short-step models the compile overhead can measure *slower* end-to-end (e.g. Z-Image turbo 9-step on H100: 0.79 s eager vs 0.99 s compiled, ABAB ×2), so the opt-out stays first-class and is mentioned in the log line.

```
performance_mode=speed enables torch.compile (pass --enable-torch-compile false to opt out)
```

## Tests

- `test_speed_mode_enables_torch_compile_by_default`
- `test_speed_mode_preserves_explicit_torch_compile_off`
- `test_auto_mode_leaves_torch_compile_off`

(existing speed-mode residency tests unchanged and passing)

🤖 Generated with [Claude Code](https://claude.com/claude-code)











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28644396170](https://github.com/sgl-project/sglang/actions/runs/28644396170)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28644395994](https://github.com/sgl-project/sglang/actions/runs/28644395994)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
