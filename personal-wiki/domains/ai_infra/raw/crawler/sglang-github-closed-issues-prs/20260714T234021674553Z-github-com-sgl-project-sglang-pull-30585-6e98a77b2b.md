---
source_id: sglang-github-closed-issues-prs
title: Enhance mechanical-refactor-verify skill with a whole-chain verifier, new relocation
  primitives, and generator inference
canonical_url: https://github.com/sgl-project/sglang/pull/30585
captured_at: '2026-07-14T23:40:21.674553+00:00'
content_hash: 6e98a77b2ba06c7dec3d1b5ffbfe571acb9f9e075f4f755996fe6a60f7ea3633
---
# Enhance mechanical-refactor-verify skill with a whole-chain verifier, new relocation primitives, and generator inference

URL: https://github.com/sgl-project/sglang/pull/30585
State: closed
Labels: documentation
Closed at: 2026-07-14T08:45:48Z
Merged at: 2026-07-14T08:45:48Z

## Motivation

The `mechanical-refactor-verify` skill lets us prove that a "mechanical" refactor commit — a file split, a function move, a module extraction, a rename — is a **pure relocation** and nothing else, so a reviewer can trust it without re-reading every moved line. Until now the skill could only prove **one commit at a time**: there was no way to take a whole refactor branch/PR and get a single machine verdict that *every* commit is either a proven relocation or an explicitly-declared human-review commit.

This PR completes the skill into a full **`split` → `construct` → `verify`** workflow: authoring a compliant chain, generating its proof folder, and verifying an entire chain against that folder in one command. It also broadens the set of relocations the engine can reproduce faithfully, and pins down both properties in normative spec files.

## Modifications

### 1. Whole-chain verifier (new capability)

- New `scripts/mechanical_refactor_reproduction_cli.py` — the **chain verifier**. Given `--base <commit> --branch <branch> --proof <folder>` it walks every commit in `base..branch` and emits one full markdown report (to stdout and to `<proof>/chain_report.md`).
- Verifies the **"verified chain" property**: every commit is *classified*, and every provable commit has exactly one proof that runs to a PASS.
  - **Classification (the word rule):** each commit message must contain exactly one standalone word — `mechanical_provable` (claims a machine-provable relocation) or `non_mechanical_provable` (declares the minimal unprovable residue, left to human review). Neither → `UNCLASSIFIED`; both → `AMBIGUOUS_KIND`. The word is matched standalone and lowercase, so `non_mechanical_provable` never also counts as the bare word.
  - **Proof obligation:** each `mechanical_provable` commit resolves to exactly one `<sha-prefix>.py` proof (searched in both `<proof>/repro_scripts/` and flat `<proof>/`); `MISSING_PROOF` / `AMBIGUOUS_PROOF` otherwise. A proof PASSes iff **both** exit code 0 **and** the arbiter's `PASS:` verdict line is on stdout.
  - `non_mechanical_provable` commits get `HUMAN_REVIEW` — flagged for eyes, never certified.
  - Chain verdict is PASS iff every commit is `PASS` or `HUMAN_REVIEW`.
- **Concurrency:** proofs run up to `--jobs N` at a time (default 3); safe because each proof runs in its own throwaway worktree with a unique branch and never touches the checked-out tree. Classification/resolution stay sequential and the report keeps chain order regardless of completion order.
- **`--skip-passed` incremental cache:** every PASS is recorded (a FAIL never is) keyed by the triple `(commit full sha, sha256 of proof script, sha256 of the `reproduction_utils.py` next to it)`. With `--skip-passed`, a pending proof is skipped only on an exact triple match — a rebase, an edited script, or an edited engine all invalidate it. The cache lives in the repo's **git common dir** (machine-local, never travels with the proof/gist/PR), so it can only ever reuse *this machine's own* verdicts and does not weaken the do-not-trust-the-PR rule.
- **Setup guards:** the chain must be linear (a merge commit anywhere is a setup error), the range must be non-empty, refs must resolve, and `base` must be an ancestor of `branch`.
- **Exit codes:** `0` verifies, `1` walked-but-a-commit-fails, `2` setup error (unresolvable ref, non-ancestor base, empty range, merge in chain, missing proof folder).
- Verdict vocabulary: `PASS`, `HUMAN_REVIEW`, `FAIL`, `MISSING_PROOF`, `AMBIGUOUS_PROOF`, `UNCLASSIFIED`, `AMBIGUOUS_KIND` (only the first two are ok). The report includes per-kind counts, the proof PASS count, one table row per commit, and a **Failure details** section per non-ok commit.

### 2. New / expanded relocation primitives (`reproduction_utils.py`)

The proof engine reproduces a commit by replaying AST-located, byte-faithful primitives, running the real pre-commit formatter, and byte-diffing against the target (empty diff = proof). This PR adds/extends primitives so more real refactors reproduce exactly:

- `move_symbol(...)` — now supports `after=<top-level symbol>` (land a def immediately below a symbol, e.g. just above a following `if TYPE_CHECKING:` guard that has no nameable anchor), `leave_delegate` / `delegate_name` (author a forwarding stub in the source), `from_class` disambiguation for same-named defs, and `drop_self_annotation`.
- `move_assign(name, ...)` — relocate a module-level constant verbatim together with the code that reads it (paste above a named sibling, else after the trailing import).
- `extract_function(...)` — inferred by the generator for intra-file function extraction; cuts an inline body verbatim, re-indents under an authored signature, replaces the block with an authored call. Faithful **only** when the body moves unchanged.
- `extract_symbols_to_new_module(...)` — gather scattered defs/classes into a new module under an **audited header** (imports, docstring, TYPE_CHECKING block, `logging.getLogger(__name__)`, or a `drop_assigns`'d / surviving-verbatim constant — anything else raises).
- `route_call_sites_through_field(...)` — `recv.m(args)` → `recv.field.m(args)`, the call-side dual of `leave_delegate`; converges (already-routed calls skipped).
- `add_imported_name` / `remove_imported_name` — fold/drop a single name in a `from m import a, b`, preserving exploded (magic-comma) form when 2+ names survive or comments are present, collapsing a lone survivor by default (`keep_exploded=True` to keep it exploded).
- `add_import(after=<substr>)`, `add_typechecking_import` (creates the block and drops a lone `pass` placeholder), `lower_call_sites`, `requalify_call_sites`, `remove_import`, `repath_import`, `delete_file` — all with byte-faithful splicing (literal spelling, comments, and magic trailing commas survive; CRLF round-trips; column arithmetic is UTF-8-byte-accurate).

### 3. Generator inference (`mechanical_refactor_proof_generator.py`)

- Infers `extract_function` for intra-file extraction, robust to formatter reflow; the extracted signature is the `def` header only.
- Infers whole-class moves between existing modules, and moves that leave a forwarding delegate.
- Infers an in-file method reorder as a `move_symbol` with `src == dst`.
- Disambiguates same-named defs in move inference by diff indentation.
- Emitted repro scripts exit non-zero unless they print `PASS`.

### 4. Normative specs (source of truth)

- New `spec-reproduction-cli.md` — the verified-chain property, CLI contract, report, and exit codes.
- Expanded `spec-reproduction-utils.md` — the clean-move property, the full allowed/not-allowed lists, and each primitive's contract. On any disagreement these spec files win over code, tests, and guides.

### 5. Guides

- New `guide-modify-skill.md` — the rules for changing the engine/generator/spec (spec-leads, the byte-faithfulness invariant, the testing bar).
- Reworked `guide-split.md` (the chain contract + prepare/move/postpare recipes and anti-patterns), `guide-construct-proof.md` (whole-chain proof folder + single-commit proof), and `guide-verify-proof.md` (whole-chain verifier + audit checklist + do-not-trust-the-PR rule). `SKILL.md` now routes the three commands.

### 6. Tests

New pytest suites mirror every module:

- `scripts/tests/reproduction_cli/` — classification, proof discovery, chain verification, the report, and `--skip-passed`.
- `scripts/tests/proof_generator/` — `extract_function` inference and move inference.
- `scripts/tests/reproduction_utils/` — `move_assign`, `move_symbol` (+ delegate), `extract_symbols_to_new_module`, call-site rewrites, imports, and `delete_file`.

## Notes

- The skill is developer tooling under `.claude/skills/` — no SGLang runtime or model code is touched, so there is no accuracy or speed impact.
- Explicit trust boundary: whatever the pre-commit hooks auto-fix is absorbed on both the reproduced and target sides, so the hook set is part of the trusted base.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29318552118](https://github.com/sgl-project/sglang/actions/runs/29318552118)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29318551777](https://github.com/sgl-project/sglang/actions/runs/29318551777)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
