---
source_id: sglang-github-closed-issues-prs
title: Support per-regex diff-threshold predicates in the tensor comparator
canonical_url: https://github.com/sgl-project/sglang/pull/30654
captured_at: '2026-07-09T23:36:35.329423+00:00'
content_hash: 8b754fdbba24e5787b0fe2bffa678ed92aa25c18616be0713dc6c47edf5cbd74
---
# Support per-regex diff-threshold predicates in the tensor comparator

URL: https://github.com/sgl-project/sglang/pull/30654
State: closed
Labels: 
Closed at: 2026-07-09T12:15:36Z
Merged at: 2026-07-09T12:15:36Z

Replace the comparator's single global float --diff-threshold with per-tensor
pass criteria: a list of (regex, predicate) rules where a tensor is judged by
the first rule whose regex fullmatches its name.

Motivation: RL training dumps contain near-zero tensors (e.g. grads of starved
MoE experts) whose relative diff is meaningless while their absolute diff is
negligible; a single global rel threshold cannot express an 'rel OR max_abs'
rescue for those tensors without loosening the check everywhere else.

The DSL (new module sglang.srt.debug_utils.comparator.threshold_dsl):

- DiffThresholdRule: a frozen (regex pattern, predicate) value object.
- parse_diff_threshold_rules: parses CLI tokens - either a single float
  shorthand (0.0085 expands to a catch-all 'rel <= 0.0085') or flat
  (regex, predicate) pairs; odd token counts and malformed predicates fail
  fast at parse time.
- resolve_predicate: first-fullmatch-wins (specific-before-general ordering);
  a tensor matching no pattern is an error (fail-closed) rather than silently
  passing.
- parse_predicate / evaluate_predicate: compile and evaluate a boolean
  expression over rel / max_abs / mean_abs with comparison operators and
  and/or, e.g. 'rel <= 0.0085 or max_abs <= 1e-3'. Evaluation runs with empty
  __builtins__ and only the three metric names in scope; predicates are
  validated once against a dummy environment so unknown names, attribute
  access, and syntax errors raise ValueError up front. Compiled predicates
  are lru_cached.
- The DSL module itself is policy-free: the default criterion
  (DEFAULT_PREDICATE = 'rel <= 0.001', matching the old CLI default) lives in
  the comparator, and parse_diff_threshold_rules / resolve_predicate take it
  as a required argument.

Wiring, end to end:

- CLI: --diff-threshold changes from one float to nargs='*', accepting the
  old float shorthand or (regex, predicate) pairs, e.g.
  --diff-threshold '.*expert.*' 'rel <= 0.0085 or max_abs <= 1e-3' '.*' 'rel <= 0.0085'.
  With the flag absent, every tensor keeps the previous default ('rel <= 1e-3').
- Plumbing: compare_bundle_pair and friends thread
  diff_threshold_rules: Optional[list[DiffThresholdRule]] instead of
  diff_threshold: float; compare_tensor_pair resolves the predicate by name.
- Verdict: compute_diff evaluates the resolved predicate over
  rel / max_abs / mean_abs instead of the fixed rel_diff <= diff_threshold.
- Types: DiffInfo.diff_threshold: float becomes DiffInfo.predicate: str, so
  reports record the exact criterion each tensor was judged against.
- Formatter: the per-tensor pass/fail marker follows diff.passed (the
  predicate verdict) instead of re-deriving it from rel_diff vs a threshold.
- The replicated-weight check in the unsharder keeps its existing semantics
  by passing an explicit 'max_abs <= atol' predicate.

Behavior is unchanged for float-shorthand and default users.

Also make test_formatter.py and test_output_types.py importable under direct
script execution ('cd test/ && python3 <file>', as used by the CI suite runner
and /rerun-test): their module-level
'from registered.debug_utils.comparator.testing_helpers import ...' previously
resolved only via comparator/conftest.py's sys.path insertion during pytest
collection, so direct execution crashed with ModuleNotFoundError before
pytest.main() ran. Mirror the conftest sys.path insertion at the top of the two
files. (Pre-existing on main; never surfaced per-commit because both files are
registered nightly-only.)

Tests cover the DSL (parsing, resolution order, fullmatch semantics,
fail-closed behavior, predicate evaluation) plus CLI parsing, predicate
resolution inside compare_tensor_pair, downcast-diff predicate propagation,
formatter marker behavior, JSON roundtrip of DiffInfo.predicate, and
end-to-end exit codes for rescued / non-rescued / unmatched tensors.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29017375825](https://github.com/sgl-project/sglang/actions/runs/29017375825)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29017375627](https://github.com/sgl-project/sglang/actions/runs/29017375627)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
