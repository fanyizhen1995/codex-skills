# Harness Wiki Crawler E2E Evaluator Design

## Objective

Install the harness foundation in this repository and add Step4 evaluator gates so an independent evaluator can validate the Personal Wiki Crawler Workbench as a user. The target validation mode is end-to-end: fetch a source, move it through queue approval and ingest, rebuild wiki indexes, run validation, and record evaluator evidence.

## Scope

This work covers:

- Harness step 1: root `AGENTS.md` and durable `docs/` knowledge files.
- Harness step 2: project-specific content for architecture, conventions, technology decisions, and quality standards.
- Harness step 3: `init.sh`, `tasks.json`, `progress.md`, and task management rules.
- Harness Step4: repo-side evaluator scripts, evaluator docs/templates, local Codex Stop/SubagentStop hook wiring, and the generic Step4 demo task.
- A wiki crawler end-to-end evaluator task and scenario that treats the crawler as a user-facing workflow.

This work does not redesign the crawler workbench or broaden crawler behavior beyond what is needed to make the evaluator scenario executable and reproducible.

## Architecture

The repository remains the owner of runtime harness behavior. The local `harness-step4-evaluator-gates` skill installs generic evaluator assets into the repo, including:

- `scripts/harness_evaluator_*.py` runtime scripts.
- `docs/harness/` evaluator docs and scenario contracts.
- `.codex/evaluations/templates/` bundle templates.
- A demo task used to prove Stop hook auto-trigger wiring.

The wiki crawler scenario is added as repo data, not skill data. It lives under `docs/harness/evaluator-scenarios/` and is referenced by a `tasks.json` task with `requires_eval=true`. The evaluator receives an `input.json` bundle and independently runs scenario steps against the crawler workbench workflow.

## Wiki Crawler E2E Flow

The wiki crawler evaluator scenario should verify the workflow from the perspective of a user:

1. Use an isolated crawler state directory so existing workbench state is not reused.
2. Load or create a deterministic source profile for the `ai_infra` domain.
3. Run the source through the crawler capture path.
4. Confirm raw evidence is written under `personal-wiki/domains/ai_infra/raw/`.
5. Approve and run the generated ingest task.
6. Rebuild index and backlinks.
7. Run wiki validation for `ai_infra` and the full wiki.
8. Check that the evaluator bundle contains `input.json`, `summary.md`, and `result.json` with scenario evidence.

Because this is the end-to-end option, the scenario may depend on local Codex and network access. If those dependencies are unavailable, the evaluator should return `blocked` with concrete evidence instead of reporting a pass.

## State And Side Effects

The implementation should keep side effects explicit:

- Harness state is versioned in repository files.
- Evaluator runtime output is written under `.codex/evaluations/`.
- Temporary crawler state should use a dedicated state directory, not the default developer state.
- Any real wiki content changes caused by the E2E scenario must be visible in git status and documented in `progress.md`.

The worktree already contains unrelated edits. Implementation must not revert or commit unrelated files.

## Error Handling

Evaluator failures use Step4 result semantics:

- `pass`: all required user scenarios passed with evidence.
- `fail`: the crawler workflow ran but violated an expected outcome.
- `blocked`: the evaluator could not reach a trustworthy verdict because of missing dependencies, unavailable network, local Codex issues, or incomplete evidence.

The evaluator must prefer actionable failure details over generic errors.

## Verification

Minimum verification after installation:

- `bash init.sh`
- `python3 -m json.tool tasks.json`
- Harness Step4 unit tests or installer checks that can run locally.
- Step4 live smoke for `harness-evaluator-demo-01`.
- Existing crawler backend/frontend tests that are practical in the local environment.
- A wiki crawler E2E evaluator run for the dedicated task.
- `git diff --check`

Any verification that cannot be run must be reported with the exact blocker.

