# 项目进度记录

> 每次 session 完成任务后，在顶部追加记录。不要删除历史。
> 格式：`## YYYY-MM-DD 任务名`

---

## 2026-07-16 Unified Loop Supervisor Completion

- Completed `loop-supervisor-unification-01`: one SQLite-backed Supervisor now owns reconciliation, bounded Planner/Generator/Evaluator scheduling, recovery, project-global Reviewer cadence, user decisions, service keepalive, and Dashboard projections; the Worker remains the independent action executor.
- Preserved the live migration chain: parent-22 recovery (`77b0429`) and four post-cutover semantic parents (`5e7d775`, `e772bb9`, `ebb1d17`, `c7e9d5b`) are all contained by `origin/main`.
- Fixed final live defects in `208ae35` and `366a4e4`: Reviewer leases renew during atomic writes; long-lived run projections stay within 4096 characters/8192 bytes; same-revision summary format upgrades remain fingerprint-bound; compacted autonomous and demand-parent progress retains stable Reviewer cadence.
- Exact task verification passed: 675 Supervisor/harness tests, 189 Dashboard backend tests, 47 frontend/evaluator tests, Dashboard browser evaluator, 8-scenario isolated Supervisor E2E, AI Infra wiki validation, service health, JSON validation, and `git diff --check`.
- Task evaluator attempt 3 passed both required browser/runtime scenarios. The populated final evaluator bundle also passed with no findings and `proceed_to_user_acceptance`.
- Evidence:
  - `docs/harness/reports/2026-07-16-loop-supervisor-unification-final.md`
  - `.codex/loop-dashboard-eval/loop-supervisor-unification-01/result.json`
  - `.codex/loop-supervisor-e2e/loop-supervisor-unification-01/result.json`
  - `.codex/evaluations/finals/loop-supervisor-unification-01/20260716T204417Z-attempt-1/result.json`
- Runtime after restart: crawler backend `8765`, crawler frontend `5173`, Loop Dashboard `8766`, `loop-supervisor`, and `loop-supervisor-worker` are online; Supervisor SQLite integrity and foreign keys are healthy.

## 2026-07-10 Autonomous Loop Continuation Hardening

- Completed `loop-runtime-continuation-hardening-01`: Supervisor now owns idempotent `stopped_budget` continuation creation, while `loop-auto-resume` exclusively executes actionable runs under per-run locks and automatically retries transient autonomous commit inspection failures.
- Proved four semantic AI infra parent tasks advanced without manual phase starts: parent-18 NVIDIA BlueField-4 (`ad78c73`), parent-19 Iluvatar Zhikai 50/100 (`5da2892`), parent-20 Volcano performance issues (`accdace`), and parent-21 Huawei Atlas 800T A3 (`d1c6b21`). Supervisor created continuation-008 after budget exhaustion, and parent-21 completed there automatically.
- Verified the two-parent audit cadence: `audit-001.json` after parent-18 and `audit-002.json` after parent-20 both returned `pass` with `continue`; parent-22 is now being planned automatically and is the next ordinary audit boundary.
- Fixed two runtime blockers: `.codex/supervisor/**` no longer causes false autonomous dirty-path blocks (`cd4b890`), and transient Git commit failures are retried once per task with stderr retained in `commit-result.json` (`3d40fdd`). Parent-19 exercised the retry path after a real Git exit 128.
- Recorded upstream instability without treating it as a harness pass: parent-18 had two SSE timeouts, parent-20 had two 30-minute Generator timeouts, and parent-21 used Planner fallback before Generator attempt 1 hit model capacity; completed artifacts and independent Evaluator passes allowed automatic recovery. The generic Planner timeout fallback remains a known quality risk because it loses a concrete candidate and verification plan.
- Runtime and visibility evidence: Crawler backend `8765`, Crawler frontend `5173`, Loop Dashboard `8766`, `loop-supervisor`, and `loop-auto-resume` were online; target-specific crawler/wiki/search/frontend freshness passed after parent-21; current continuation is visible in the Dashboard.
- Verification evidence:
  - Task `verify` command -> exit 0: 123 focused harness tests, 202 orchestrator tests, 74 Dashboard backend tests, and 21 Dashboard frontend/evaluator tests passed.
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-runtime-continuation-hardening-01 --scenario loop-supervisor-01` -> `status=pass`; browser screenshot: `.codex/loop-dashboard-eval/loop-runtime-continuation-hardening-01/loop-supervisor-success.png`.
  - `python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> `No validation issues`.
  - Crawler backend health, Crawler frontend HTTP, Loop Dashboard health, `loop-auto-resume`, `loop-supervisor`, JSON validation, and `git diff --check` all passed.

## 2026-07-09 Loop Supervisor 01

- Completed `loop-supervisor-01`: added a real project-level Loop Supervisor runtime, global Dashboard APIs/UI, browser evaluator scenario, CLI watch mode, and service runtime metadata refresh support.
- Supervisor now writes `.codex/supervisor/*`, reads `.codex/service-runtime/<service>.json`, classifies loop runs, keeps autonomous continuation planning idempotent, escalates repeated failures to user decisions, and consumes Auditor control inputs without pretending to judge task quality itself.
- Loop Dashboard now shows a global `Loop Supervisor` panel outside the task run list, with service keepalive, version freshness, data freshness, continuation plans, recovery attempts, user decisions, Auditor control input, and honest missing-artifact states.
- Evidence:
  - `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor.py` -> 34 passed
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/backend/tests/test_store.py apps/loop_dashboard/backend/tests/test_redaction.py` -> 74 passed
  - `node --check apps/loop_dashboard/frontend/app.js` -> pass
  - `python3 -m pytest -q apps/loop_dashboard/frontend/test_supervisor_contract.py scripts/tests/test_loop_dashboard_evaluator.py` -> 19 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01` -> pass
  - Task reviews clean through SDD ledger `.superpowers/sdd/progress.md`

## 2026-07-08 Loop Auditor Global Review Backlog

- Recorded `loop-auditor-global-review-01` as a high-priority harness task.
- Scope: redesign Loop Auditor as a global loop process reviewer that inspects recent Planner, Generator, Evaluator, cleanup, auto-resume, service freshness, Dashboard visibility, commit/push, skill inventory, repeated blockers, tunnel vision, and direction-control evidence across multiple rounds.
- Expected output: operator-readable process findings, remediation recommendations, and loop decisions (`must_fix`, `should_fix`, `refocus`, `stop`, or `continue`) that feed back into the loop before more work proceeds.
- Evidence:
  - `tasks.json` updated with a complete task record and verification plan.

## 2026-07-08 AI Infra Expansion Continuation Cadence Gate

- Registered `ai-infra-expansion-continuation-20260708` and implemented the P0 precondition for the continuation plan: autonomous AI infra Auditor cadence is now policy/run-state driven and the expanded policy audits once per 2 completed parent tasks.
- Finished the pre-loop SGLang #24456 ingest cleanup as commit `cc31558` and pushed it to `origin/main`; API search and frontend knowledge search can see `24456`.
- Preserved the operating constraint that Crawler Workbench backend/frontend, Loop Dashboard, and `loop-auto-resume` must remain online for continuation runs.
- Evidence:
  - RED: `test_run_autonomous_parent_task_cadence_audits_every_two_completed_tasks` failed with 2 audit reports before the fix.
  - GREEN focused: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_parent_task_cadence_audits_every_two_completed_tasks scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_create_preflight_run_copies_audit_cadence_from_policy_file -v` -> 2 passed.
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts -v` -> 60 passed.
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor -v` -> 7 passed.
  - `python3 -m unittest scripts.tests.test_harness_loop_auto_resume -v` -> 1 passed.
  - `python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v` -> 184 passed.
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> No validation issues.

## 2026-07-08 Crawler Freshness Requirement Clarified

- Clarified `loop-supervisor-01` scope: Crawler Workbench means both backend and frontend, not just a backend health check.
- Added the requirement that crawler runtime data and running versions must stay current: after code/config/data changes, backend APIs, frontend views, source/wiki/search data, and search indexes must reflect the latest committed or ingested state without stale results.
- Evidence:
  - `curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health` -> crawler backend online
  - `python3 - <<'PY' ... urllib.request.urlopen('http://127.0.0.1:8765/openapi.json') ... PY` -> crawler backend OpenAPI version `0.1.0`
  - `curl --noproxy '*' -fsSI http://127.0.0.1:5173/` -> crawler frontend online

## 2026-07-08 Loop Supervisor Backlog

- Recorded `loop-supervisor-01` as a high-priority TODO after `loop-auditor-auto-resume-runner-01`.
- Documented the interim operating rule: future loop tasks must keep Crawler Workbench backend/frontend, Loop Dashboard, and `loop-auto-resume` online, and must use loop run directories visible to Loop Dashboard.
- Evidence:
  - `curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health` -> crawler backend online
  - `curl --noproxy '*' -fsSI http://127.0.0.1:5173/` -> crawler frontend online
  - `curl --noproxy '*' -fsS http://127.0.0.1:8766/api/health` -> loop dashboard online
  - `tmux has-session -t loop-auto-resume` -> loop auto-resume watcher online

## 2026-07-08 Loop Auditor Auto Resume Runner

- Completed `loop-auditor-auto-resume-runner-01`: `audit_blocked` runs now have a standalone auto-resume watcher instead of relying on a human or dashboard refresh to call the orchestrator again.
- Confirmed the visible stuck run `.worktrees/loop-dashboard-auditor/.codex/loop-runs/loop-auditor-engine-dev` was resumed from `audit_blocked` to `passed_waiting_human_merge`; `audit-002.json` closes the open `must_fix` finding and the Dashboard API reports `open_must_fix=0`.
- Added `scripts/harness_loop_auto_resume.py`, which scans project-local and worktree loop runs and invokes `run-demand-multi` or `run-autonomous` for orchestrator-actionable phases.
- Fixed a dirty-path false block where `.codex/loop-runs/<run>/audit-remediation-result.json` was treated as an unexpected child change after remediation.
- Updated Loop Dashboard state classification so `audit_blocked` is blocked but not completed.
- Evidence:
  - RED: `test_audit_blocked_is_blocked_but_not_completed` failed because `completed=True`; `test_harness_loop_auto_resume` failed because the runner module did not exist.
  - GREEN focused: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py::test_audit_blocked_is_blocked_but_not_completed` -> 1 passed
  - GREEN focused: `python3 -m unittest scripts.tests.test_harness_loop_auto_resume -v` -> 1 passed
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_auto_resume scripts.tests.test_harness_loop_orchestrator -v` -> 262 tests passed
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 63 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-auto-resume-01` -> pass

## 2026-07-08 Loop Auditor Automatic Remediation

- Completed `loop-auditor-remediation-auto-01`: `audit_blocked` no longer remains a manual dead end for loop execution.
- Demand-development parent loops now create an orchestrator-owned audit remediation child task, pass the open `must_fix` finding IDs into the child contract, and write a follow-up passing audit report that closes the remediated findings.
- Autonomous-knowledge loops now schedule an audit remediation implementation task from `audit_blocked`, run the existing generator/evaluator/cleanup path, then re-open the loop through a passing audit report.
- Loop Dashboard now marks remediation children with `审计整改`, includes the remediation flag in backend run detail, and the browser evaluator verifies the remediated run reaches `通过，等待人工合并` with `audit-002.json`.
- Evidence:
  - RED/GREEN focused coverage: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_run_demand_multi_audit_blocked_uses_deterministic_remediation_planner_with_codex_driver scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_run_demand_multi_audit_blocked_runs_remediation_child_and_rechecks scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_autonomous_audit_blocked_runs_remediation_task_and_rechecks -v` -> 3 passed after implementation
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v` -> 261 tests passed
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 62 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-remediation-01` -> pass
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-engine-01` -> pass
  - `python3 -m json.tool docs/harness/evaluator-scenarios/loop-auditor-engine-01.json >/dev/null`
  - `git diff --check`

## 2026-07-08 Loop Auditor Engine Review Fixes

- Completed `loop-auditor-engine-review-fixes-01`: addressed review items 1-4 for the Auditor engine and Dashboard.
- Fixed deterministic git signals so `commits_since_last_audit` counts from the previous audit HEAD, and `git status` failures are explicit errors instead of being treated as clean.
- Renamed the production auditor path to `rule_based_audit_report` / `write_rule_based_audit_report` while keeping compatibility aliases for older tests.
- Grouped repeated evaluator findings by structured `category` + `title` keys before falling back to text, reducing fragile full-stdout comparisons.
- Clarified Dashboard audit/skill wording: active engine notices are per-run, display-only artifacts say they do not hard-block, and skill log matches are shown as "日志线索（非使用证明）" rather than usage facts.
- Evidence:
  - RED: focused auditor/store tests failed before implementation on missing `rule_based_audit_report`, old phase notices, and `used_recently`.
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor -v` -> 7 passed
  - `python3 -m unittest scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v` -> 191 passed
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts -v` -> 67 passed
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 62 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-engine-01` -> pass

## 2026-07-08 Loop Auditor Engine

- Completed `loop-auditor-engine-01`: added a real Loop Auditor runtime module for deterministic signal computation, validated audit reports, fake/codex auditor execution, and open `must_fix` hard blocking.
- Wired parent demand-development and autonomous-knowledge loop boundaries so open `must_fix` findings move runs to `audit_blocked` with `next_action=create_audit_remediation_task`.
- Updated Loop Dashboard to distinguish display-only audit artifacts from active orchestrator-generated audit reports, and added Chinese `audit_blocked`/remediation labels.
- Extended the browser evaluator to create a real `loop-auditor-engine-dev` fixture through `run_auditor(fake)` plus `run_demand_multi`, then verify active engine state, audit report path, deterministic signals, and dashboard visibility.
- Evidence:
  - `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v` -> 255 tests passed
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 62 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-engine-01` -> pass
  - `python3 -m json.tool docs/harness/evaluator-scenarios/loop-auditor-engine-01.json >/dev/null`

## 2026-07-08 Loop Dashboard Auditor And Skill View

- Completed `loop-dashboard-auditor-01`: added real Loop Dashboard support for `audit_summary`, deterministic audit signals, direction control, audit findings, and current project Skill inventory.
- Added the `审计与 Skill` dashboard tab and browser evaluator coverage proving users can see `Auditor`, `open must_fix`, deterministic signals, and project skill usage.
- Kept this implementation loop visible in the root Loop Dashboard through worktree run `.worktrees/loop-dashboard-auditor/.codex/loop-runs/loop-dashboard-auditor-dev`.
- Evidence:
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 57 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-auditor-01` -> pass
  - `python3 -m json.tool tasks.json >/dev/null`
  - `git diff --check`

## 2026-07-06 AI Infra Meta Loop Runtime Hardened Smoke Correction

- Superseded the earlier AI infra meta loop smoke evidence in this file after the hardened placeholder-only gate landed.
- Current expected smoke behavior for `python3 scripts/harness_ai_infra_meta_loop_smoke.py --repo-root . --run-id evaluator-scenario-ai-infra-meta-loop-runtime --isolate-clone` is a blocked placeholder path, not a passing merge-ready result.
- Treat any older mention of `overall_status=pass` or `expanded_code_scope.status=pass` for this smoke as stale evidence.
- Corrected expectations:
  - `overall_status=blocked`
  - `expanded_code_scope.status=blocked`
  - `synthetic_placeholder_block=true`
  - no `commit-result.json` artifact is expected for the placeholder-only freshness path

## 2026-07-06 AI Infra Meta Loop Runtime Review Fix

- Tightened `transition_meta_loop_to_expansion(...)` guardrails after Task 6 review:
  - refuse non-`demand_development` parents even if they are already at `passed_waiting_human_merge`
  - require the exact expanded AI infra autonomous policy file `docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json`
- Marked `ai-infra-meta-loop-runtime-01` done in `tasks.json` to match the completed runtime work.
- Commit created: `fix(harness): enforce ai infra transition guardrails`
- Evidence:
  - RED: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_transition_meta_loop_blocks_non_demand_parent_in_passed_waiting_human_merge scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests.test_transition_meta_loop_blocks_non_expanded_autonomous_policy_file -v` -> 2 failures before the fix
  - GREEN: same focused command -> 2 passed after the fix
  - Full verification rerun recorded with the final task fix commit.

## 2026-07-06 AI Infra Meta Loop Runtime Phase Transition

- Completed `ai-infra-meta-loop-runtime-01`: added the demand-development Phase A to autonomous Phase B transition helper and CLI, documented the transition contract, and marked the planned runtime task done.
- Verified the transition runtime creates a confirmed `ai_infra` autonomous expansion child only from a parent run at `passed_waiting_human_merge`, with a real checkpoint commit and repo-local evidence paths.
- Phase B autonomous knowledge expansion can now start from the recorded expansion child after the checkpoint handoff.
- Commits created:
  - `feat(harness): transition ai infra meta loops to expansion`
- Evidence:
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_ai_infra_evidence -v` -> 211 tests passed
  - `python3 scripts/harness_ai_infra_meta_loop_smoke.py --repo-root . --run-id evaluator-scenario-ai-infra-meta-loop-runtime --isolate-clone` -> `overall_status=pass`, `missing_evidence_gate.status=pass`, `expanded_code_scope.status=pass` [stale before 2026-07-06 hardened placeholder freshness gate; current expected result is blocked]
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/ai-infra-meta-loop-runtime-01.json >/dev/null`
  - `python3 - <<'PY' ... validate_loop_policy_payload(...) ... PY`
  - `curl --noproxy '*' http://127.0.0.1:8765/api/health` -> HTTP 200, `{\"status\":\"ok\"...}`
  - `curl --noproxy '*' -I http://127.0.0.1:5173/ | sed -n '1,5p'` -> `HTTP/1.1 200 OK`
  - `curl --noproxy '*' http://127.0.0.1:8766/api/health` -> HTTP 200, `{\"status\":\"ok\"}`
  - `git diff --check`

## 2026-07-06 AI Infra Meta Loop Runtime Started

- Registered `ai-infra-meta-loop-runtime-01` for Phase A runtime/evaluator implementation before autonomous `ai_infra` expansion.
- Added the implementation plan at `docs/superpowers/plans/2026-07-06-ai-infra-meta-loop-runtime.md`.
- Confirmed the implementation branch is isolated at `.worktrees/ai-infra-meta-loop-runtime` and the main workspace crawler raw/runtime artifacts remain out of scope.
- Confirmed long-running services are reachable before implementation:
  - Crawler Workbench backend `http://127.0.0.1:8765/api/health`
  - Crawler Workbench frontend `http://127.0.0.1:5173/`
  - Loop Dashboard `http://127.0.0.1:8766/api/health`
- Baseline evidence:
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator -v` -> 160 tests passed
  - `python3 -m json.tool tasks.json >/dev/null`
  - `git diff --check`

## 2026-07-06 AI Infra Autonomous Expansion Loop Preflight

- Added the AI infra autonomous expansion design spec for comprehensive `ai_infra` wiki growth across training, inference, orchestration, data/RAG, evaluation/observability, security/cost, hardware, network, storage, and cluster operations.
- Defined deterministic duplicate/gap proof requirements before each candidate task, including canonical URL, GitHub issue/PR, paper, hardware model, source profile, and wiki/index checks.
- Added the expanded AI infra autonomous policy fixture as a run-contract/evaluator artifact, while documenting that current Phase 3 runtime still uses the conservative hardcoded autonomous scope until policy fixture loading is implemented.
- Follow-up tightened the spec for Loop Dashboard freshness, Crawler Workbench backend/frontend refresh, and the new Domain Channels source subscription model.
- Follow-up from grill-me review made the missing runtime work explicit: expanded policy runtime loading, coverage-map state, gap-proof validation, required-evidence gates, AI infra evaluator scenarios, and always-on Crawler Workbench plus Loop Dashboard monitoring.
- User selected the Meta Loop chaining mode: run demand-development fixes first, automatically transition to autonomous knowledge expansion in the same feature branch after evaluator gates and a checkpoint commit, then wait for a final human merge gate.
- Evidence:
  - `python3 -m json.tool docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json >/dev/null`
  - `python3 - <<'PY' ... validate_loop_policy_payload(...) ... PY`
  - `git diff --check`

## 2026-07-04 Wiki Crawler Capture Artifacts

- Organized the current uncommitted wiki/crawler capture artifacts for the `ai_infra` domain into a dedicated commit scope.
- Added a standing `AGENTS.md` rule: every wiki/crawler crawl or ingest must be validated, staged without local runtime artifacts, and committed as an independent change.
- Kept local runtime files out of scope: `.codex/loop-dashboard-8766.log`, `.codex/loop-dashboard-8766.pid`, and `generated/`.
- Evidence:
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> no validation issues
  - Precise credential scan for `ghp_`, `github_pat_`, `Authorization: Bearer/token`, and bearer-like tokens across the new crawler raw paths -> no matches
  - Staged path check limited to `AGENTS.md`, `progress.md`, and `personal-wiki/domains/ai_infra/`

## 2026-07-03 Domain Channel Management Live E2E

- Completed `crawler-domain-channels-live-e2e-01` through the harness loop in `.worktrees/crawler-domain-channels-live-e2e-01`.
- Extended the isolated wiki crawler evaluator to cover Domain Channels API workflow, real Playwright UI clicks, child source creation, source-run continuity, and retained-artifact synthetic secret hygiene.
- Harness run `.codex/loop-runs/crawler-domain-channels-live-e2e-01/run.json` reached `passed_waiting_human_merge` after evaluator, artifact hygiene, and cleanup.
- Evidence:
  - `python3 -m unittest scripts.tests.test_wiki_crawler_e2e_evaluator -v` -> 8 passed
  - `python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01` -> pass, with `domain-channels-live-user-flow: pass`
  - `.codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01/evidence.json` -> `secret_plaintext_scan.passed=true`
  - `.codex/loop-runs/crawler-domain-channels-live-e2e-01/artifact-manifest.json` -> `status=pass`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json >/dev/null`
  - `git diff --check`

## 2026-07-03 Domain Channel Management UI

- Completed `crawler-domain-channels-ui-01`: added the Domain Channels frontend navigation and management page for domain filtering, channel creation, selected-channel notes editing, synthetic secret replacement, access probing, probe history, and child source creation.
- Added channel/source/probe/secret TypeScript API client functions and response types, including channel auth states needed by the UI.
- Updated Playwright UI config to use an isolated frontend port and avoid reusing the long-running dev server during evaluator-style UI tests.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx` -> 25 passed
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm run build` -> pass
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm run test:ui` -> 3 passed
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json >/dev/null`
  - `git diff --check`

## 2026-07-03 Domain Channel Management Secrets And Probes

- Completed `crawler-domain-channels-probe-secrets-01`: added encrypted local channel secrets using the existing cryptography dependency, key-file lifecycle under the isolated workbench state directory, HTTP probe execution/history, channel readiness states, and source-run blocking with persisted failed run reasons.
- Added channel/source CRUD APIs needed by the upcoming Domain Channels frontend workflow, including conservative source/channel delete behavior.
- Secret APIs return only configured metadata and tests verify synthetic plaintext is not returned or stored in the SQLite database.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py` -> 18 passed
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py tests/test_fetch_service_policy.py tests/test_api.py` -> 41 passed

## 2026-07-03 Domain Channel Management Loop Execution Preference

- User confirmed local merge for `crawler-domain-channels-model-01`.
- For the remaining Domain Channel Management loop tasks, continue execution without stopping at each task's human merge gate unless a real blocker is encountered.
- Report the final consolidated outcome after all registered loop tasks complete, or earlier only if the loop becomes blocked.

## 2026-07-03 Domain Channel Management Model

- Completed `crawler-domain-channels-model-01`: added backend channel schema, migration compatibility, generated channel assignment for source profiles, one-time `sources.yaml` seed import, source `fetcher_type` compatibility fields, channel list API, and channel fields on source list responses.
- Updated startup initialization so SQLite remains the runtime source of truth after the first seed import.
- Preserved existing `mirror_profiles()` behavior for direct tests and manual tools while adding channel backfill.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py tests/test_db_profiles.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_scheduler.py` -> 77 passed
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json >/dev/null`
  - `git diff --check`

## 2026-07-03 Domain Channel Management Planner Loop

- Started demand-development loop `crawler-domain-channels-dev-01` for Domain Channel Management.
- Registered four evaluator-gated tasks: model/API compatibility, channel secrets/probes, Domain Channels UI, and isolated live e2e validation.
- Added evaluator scenario contracts and the implementation plan for the loop handoff.
- Local ignored loop artifacts were written under `.codex/loop-runs/crawler-domain-channels-dev-01/` with `planner-output.json`, `generator-prompt.md`, and `run.json` advanced to `generating`.
- Evidence:
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json >/dev/null`
  - `python3 -m json.tool .codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json >/dev/null`
  - `python3 -c "from pathlib import Path; from scripts.harness_loop_contracts import read_json_file, validate_planner_output_payload, validate_run_payload; validate_planner_output_payload(read_json_file(Path('.codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json'))); validate_run_payload(read_json_file(Path('.codex/loop-runs/crawler-domain-channels-dev-01/run.json')))"`
  - `git diff --check`

## 2026-07-03 Loop Dashboard Worktree History

- Completed `loop-dashboard-history-01`: Loop Dashboard now reads runs from both the current checkout `.codex/loop-runs` and project-local `.worktrees/*/.codex/loop-runs`.
- Added source metadata (`source_kind`, `source_path`) to run summaries/details, deduplicates duplicate `run_id` entries by newest `updated_at`, and shows the source path in the frontend `运行信息`.
- Extended the browser-click evaluator to seed and select a completed worktree history run, then verify the source path is visible to the user.
- Evidence:
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests` -> 30 passed
  - `python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v` -> 21 passed
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-history-01` -> pass
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json >/dev/null`
  - `git diff --check`

## 2026-07-03 Loop Dashboard

- Completed `loop-dashboard-dev-01`: added an independent read-only Loop Dashboard for current-project loop runs, agent summaries, visual flow, logs/events, completed states, and blocked diagnostics.
- Added a Chinese frontend and browser-click evaluator that starts the dashboard against temporary fixture loop artifacts and validates run selection, agent cards, flow diagram, log filtering, redaction, and completed states with Playwright.
- Documented the dashboard startup command, `LOOP_DASHBOARD_PROJECT_ROOT` override for other projects, read-only backend boundary, and evaluator command in `docs/harness/planner-generator-evaluator-loop.md`.
- Marked `loop-dashboard-dev-01` done in `tasks.json`; the feature is waiting for human merge confirmation and is ready to use locally.
- Evidence:
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests`
  - `python3 -m unittest scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_evaluator_scenarios -v`
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01`
  - `python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id loop-dashboard-dev` -> `passed_waiting_human_merge`
  - `python3 -m json.tool tasks.json >/dev/null`
  - `git diff --check`

## 2026-07-02 Planner Generator Evaluator Loop Phase 3

- Completed `planner-generator-evaluator-loop-phase-3-01`: added the Phase 3 autonomous smoke helper, evaluator scenario, and loop policy fixtures for demand-development and autonomous-knowledge.
- Documented Phase 3 operator commands, no-action requirements, allowlist/manual-confirm/denylist limits, supply-chain evidence, auto-commit behavior, and smoke output in `docs/harness/planner-generator-evaluator-loop.md`.
- Marked Phase 3 done in `tasks.json` with verification covering scenario tests, the isolated-clone smoke helper, JSON parsing, policy validation, and diff hygiene.
- Evidence:
  - `python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v`
  - `python3 scripts/harness_loop_phase3_smoke.py --repo-root . --run-id evaluator-scenario-phase-3 --domain ai_infra --task-id planner-generator-evaluator-loop-phase-3-01 --isolate-clone`
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json >/dev/null`
  - `python3 -m json.tool docs/harness/loop-policies/autonomous-knowledge.json >/dev/null`
  - `python3 -m json.tool docs/harness/loop-policies/demand-development.json >/dev/null`
  - `git diff --check`

## 2026-07-02 Planner Generator Evaluator Loop Phase 2

- Completed `planner-generator-evaluator-loop-phase-2-01`: CLI now exposes `artifact-hygiene` and `cleanup`, evaluator pass routes generated artifacts through hygiene before cleanup, and `run` continues through those phases to the human merge gate.
- Added the Phase 2 evaluator scenario at `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json`.
- Updated the loop runbook with task-contract evaluator input, scenario command evidence, artifact redaction manifests, cleanup behavior, and the human merge gate rules.
- Marked Phase 2 done in `tasks.json`; Phase 3 is the next active focus.
- Evidence:
  - `python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v` -> 52 passed
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_evaluator_cli scripts.tests.test_harness_evaluator_orchestrator scripts.tests.test_harness_evaluator_hooks scripts.tests.test_harness_evaluator_scenarios -v` -> 174 passed
  - `python3 scripts/harness_loop_phase2_smoke.py --repo-root . --run-id evaluator-scenario-phase-2 --task-id planner-generator-evaluator-loop-phase-2-01` -> `passed_waiting_human_merge`, with scenario command, artifact hygiene, and cleanup evidence
  - `python3 -m json.tool tasks.json >/dev/null` -> pass
  - `python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json >/dev/null` -> pass

## 2026-07-02 Planner Generator Evaluator Loop Phase 2 And Phase 3 Registered

- Registered `planner-generator-evaluator-loop-phase-2-01` for the next harness loop hardening step: task-contract evaluator input, scenario command artifacts, attempt evidence, cleanup/recovery, and artifact hygiene.
- Registered `planner-generator-evaluator-loop-phase-3-01` for the later autonomous knowledge loop: domain `loop-state.json`, no-action gap detection, allowlisted automatic wiki/crawler changes, supply-chain checks, auto-commit, cleanup, and continued planning.
- Phase 2 is the active next implementation target; Phase 3 remains blocked by Phase 2.

## 2026-07-02 Planner Generator Evaluator Loop Phase 1

- Implemented the demand-development Planner -> Generator -> Evaluator loop skeleton with preflight state, JSON contract validators, fake/codex Planner and Generator drivers, evaluator handoff, failure evidence capture, and a human merge gate.
- Registered `planner-generator-evaluator-loop-phase-1-01`, added the evaluator scenario contract, and documented Phase 1 commands in `docs/harness/planner-generator-evaluator-loop.md`.
- Evidence:
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v` -> 45 passed
  - `python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1-final --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2` -> `passed_waiting_human_merge`
  - `python3 scripts/harness_evaluator_orchestrator.py run-task-loop --driver fake --task-id planner-generator-evaluator-loop-phase-1-01 --repo-root . --max-attempts 2` -> pass at `.codex/evaluations/tasks/planner-generator-evaluator-loop-phase-1-01/fake-attempt-2/result.json`

## 2026-07-01 Kubernetes Volcano Kueue Closed Issues Backfill

- Replaced the initial public GitHub seed corpus with authenticated raw evidence for the requested scope:
  - `volcano-sh/volcano`: all-time closed issues, 1,772 issues and 8,369 locally joined comments.
  - `kubernetes-sigs/kueue`: all-time closed issues, 2,488 issues and 6,650 locally joined comments.
  - `kubernetes/kubernetes`: issues closed on or after 2023-07-01, 5,897 issues and 6,386 locally joined comments.
- Added closed-date windows, per-repository closed windows, repository-level issue-comment joins, monthly Search API issue discovery, progress logging, and transient GitHub read retries to the corpus CLI.
- Updated Kubernetes, Volcano, Kueue, and the shared corpus reference wiki pages from partial seed wording to the verified backfill scope.
- Fixed the reviewer finding that repository-level comment joins were being reported as complete: summaries and manifests now record GitHub-reported comment totals, mismatched issue counts, `comment_capture_complete: false`, and a `comments_incomplete_repository_join` partial reason.
- Evidence:
  - `python3 scripts/github_closed_issues_corpus.py verify-manifest --repo-root . --manifest .codex/github-closed-issues/github-closed-issues-volcano-kueue-full-k8s-3y-01/manifest.json --min-repos 3` -> pass
  - `python3 -m pytest -q scripts/tests/test_github_closed_issues_corpus.py` -> 34 passed

## 2026-07-01 Kubernetes Volcano Kueue Closed Issues

- Added `github-closed-issues-k8s-volcano-kueue-01` to the project task list and configured monthly Crawler Workbench GitHub source profiles for `kubernetes/kubernetes`, `volcano-sh/volcano`, and `kubernetes-sigs/kueue`.
- Added a reproducible GitHub closed-issue corpus CLI that filters pull requests, fetches selected issue comments, writes compressed raw evidence plus summary/index files, and verifies the run manifest.
- Ran the initial public-API seed capture with `--max-pages 1 --max-comment-issues 5` because no valid `GITHUB_TOKEN` was available in the shell. The local proxy path failed during TLS handshake, so the successful run explicitly unset proxy environment variables.
- Seed corpus results:
  - `kubernetes/kubernetes`: 25 closed issues and 36 attached comments.
  - `volcano-sh/volcano`: 23 closed issues and 5 attached comments.
  - `kubernetes-sigs/kueue`: 25 closed issues and 19 attached comments.
- Curated draft wiki pages for Kubernetes, Volcano, Kueue, and the shared closed-issue corpus reference. The reference records raw paths, partial reasons, `state_reason` interpretation, retrieval notes, and monthly source IDs.
- Evidence:
  - `pytest -q scripts/tests/test_github_closed_issues_corpus.py` -> 15 passed
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_api.py tests/test_db_profiles.py tests/test_fetchers.py` -> 83 passed
  - `python3 scripts/github_closed_issues_corpus.py verify-manifest --repo-root . --manifest .codex/github-closed-issues/github-closed-issues-k8s-volcano-kueue-01/manifest.json --min-repos 3` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `.codex/evaluations/tasks/github-closed-issues-k8s-volcano-kueue-01/20260630T181618Z-attempt-1/result.json` -> pass

## 2026-06-29 Crawler Manual URL Ingest

- Added an ad hoc URL ingest path in Crawler Workbench: `POST /api/manual-ingests` creates/reuses a manual trusted web source, fetches raw evidence, approves the generated ingest task, runs the existing wiki ingest pipeline, validates, and optionally records an auto commit.
- Added a compact `零散 URL 入库` form to the Sources page with default `ai_infra` domain and auto-commit enabled.
- Registered `crawler-manual-url-ingest-01` in `tasks.json` with required evaluator coverage.
- Evidence:
  - `REPO_ROOT=$(pwd) && cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_manual_ingest.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_ingest_git.py && cd ../frontend && npm test -- src/App.test.tsx && npm run build && cd "$REPO_ROOT" && python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-manual-url-ingest-01` -> backend 57 passed, frontend 23 passed, build passed with Vite chunk-size warning, evaluator pass
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm run test:ui:live` -> 1 passed

## 2026-06-29 Crawler Workbench Sync And Commit Cleanup

- Confirmed there are no untracked compute accelerator raw/wiki files left to ingest; compute accelerator crawl evidence is already curated in `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-crawl-inventory.md` and `personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-parameter-comparison.md`.
- Confirmed the live workbench database contains accelerator records: 178 `raw_items`, 21 `accelerator_skus`, 31 `accelerator_observations`, and 29 `accelerator_resolved_specs`.
- Recovered legacy dirty-baseline failures to approved retry state and confirmed the local DB has no remaining `baseline dirty paths include files outside the ingest task` failed rows.
- Verified the crawler workbench UI hides approved retry tasks from the manual queue; stale frontend screenshots were from an old running frontend/backend state and need service restart after commit.
- Evidence:
  - `pytest personal-wiki/apps/crawler_workbench/backend/tests/test_api.py personal-wiki/apps/crawler_workbench/backend/tests/test_codex_worker.py personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py personal-wiki/apps/crawler_workbench/backend/tests/test_fetchers.py -q` -> 117 passed
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx && npm run build && npm run test:ui:live` -> 22 passed, build passed, live Playwright flow passed
  - `python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators` -> pass

## 2026-06-28 Compute Accelerator Spec Extraction

- Added structured extraction tables and services for compute accelerator SKUs, source-backed observations, and resolved specs.
- Wired `specs_candidate` fetches to extract observations inside the fetch transaction and added API endpoints:
  - `GET /api/accelerator-specs`
  - `POST /api/accelerator-specs/extract`
- Added crawler workbench `参数库` page with resolved fields, expandable observation evidence, per-observation provenance/raw paths, and manual backfill.
- Backfilled the live workbench DB from existing accelerator raw captures:
  - `accelerator_skus`: 19
  - `accelerator_observations`: 29
  - `accelerator_resolved_specs`: 27
- Marked `compute-accelerator-spec-extraction-01` done in `tasks.json`.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_accelerator_specs.py tests/test_fetch_service_policy.py` -> 24 passed
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build` -> 22 passed, build passed with Vite chunk-size warning
  - `REPO_ROOT=$(pwd) && cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_accelerator_specs.py tests/test_fetch_service_policy.py tests/test_api.py tests/test_db_profiles.py tests/test_discovery.py && cd ../frontend && npm test && npm run build && cd "$REPO_ROOT" && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> backend 92 passed, frontend 22 passed, build passed, wiki validation passed
  - `.codex/evaluations/tasks/compute-accelerator-spec-extraction-01/20260628T070902Z-attempt-1/result.json` -> pass

## 2026-06-28 Compute Accelerator Crawl Backfill

- Confirmed the accelerator crawl did write to the workbench database: 75 compute accelerator fetch runs total, 67 succeeded, 8 historical failed, 63 raw_items, and 71 accelerator candidates.
- Fixed verified dead discovery URLs for Biren, Enflame, Kunlunxin, Intel DSA, and Microsoft Maia 200, mirrored runtime `sources.yaml` into SQLite, and reran those sources plus AMD Instinct.
- Backfill results:
  - Succeeded: `compute-accelerator-discovery-amd-instinct`, `compute-accelerator-discovery-biren-products`, `compute-accelerator-discovery-enflame-products`, `compute-accelerator-discovery-kunlunxin-products`, `compute-accelerator-discovery-intel-dsa-docs`, `compute-accelerators-microsoft-maia-200`.
  - `compute-accelerators-microsoft-maia-200` now uses Microsoft TechCommunity and succeeded as a first-run baseline; because the source has `baseline_on_first_run: true`, it did not create a raw item on that first success.
  - Remaining unresolved connectivity failures: `compute-accelerator-discovery-google-cloud-tpu-docs` and `compute-accelerators-google-tpu` (TLS EOF/direct timeout from this environment).
- Added `compute-accelerator-spec-extraction-01` as the next high-priority task for converting raw accelerator evidence into structured SKU, observation, and resolved spec data visible in the crawler workbench.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py::test_accelerator_discovery_profiles_use_reachable_product_indexes tests/test_db_profiles.py::test_accelerator_profiles_use_once_policy_and_discovery_profiles_are_monthly` -> 2 passed
  - `python3 -m unittest scripts.tests.test_harness_evaluator_scenarios.HarnessEvaluatorScenarioTests.test_compute_accelerator_spec_extraction_contract_is_registered` -> pass
  - `python3 -m json.tool tasks.json >/dev/null` -> pass
  - `python3 -m json.tool docs/harness/evaluator-scenarios/compute-accelerator-spec-extraction-01.json >/dev/null` -> pass

## 2026-06-28 Compute Accelerator Monthly Discovery

- Added one-shot run policy for concrete accelerator model/spec sources so completed evidence captures are not scheduled again after a successful raw capture.
- Added monthly discovery profiles for future GPU/NPU/TPU/DPU/IPU/FPGA/DSA/AI ASIC model discovery while retaining the existing NCCL and SGLang subscriptions.
- Added accelerator candidate extraction, deduplication, accept/reject service logic, API endpoints, and Sources page review UI.
- Addressed final review findings by persisting accepted candidates back to runtime `sources.yaml`, using profile `include_patterns` during discovery extraction, and broadening monthly discovery coverage across DPU/IPU/FPGA/DSA.
- Configured source YAML with 90 sources total: 13 NCCL, 1 SGLang, 59 concrete accelerator one-shot sources, and 17 monthly discovery sources.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_scheduler.py tests/test_discovery.py` -> 65 passed
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm test` -> 19 passed
  - `cd personal-wiki/apps/crawler_workbench/frontend && npm run build` -> pass, with existing Vite chunk-size warning
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `.codex/evaluations/tasks/compute-accelerator-monthly-discovery-01/20260627T201140Z-attempt-2/result.json` -> pass

## 2026-06-27 Compute Accelerator Domestic Crawl

- Expanded accelerator crawler coverage for domestic GPU/NPU/DPU/DSA/AI ASIC sources and retained existing global accelerator sources.
- Added PDF fetch support that saves original PDF attachments next to extracted Markdown raw captures and records attachment metadata/sha256 in frontmatter and DB metadata.
- Ran the formal domestic crawl into `ai_infra` raw evidence and crawler workbench state.
- Results:
  - Source profiles: 59 total accelerator profiles, 53 enabled and attempted, 6 disabled/skipped.
  - Succeeded: 51 sources, including 47 domestic accelerator sources.
  - Failed and recorded in manifest: `compute-accelerators-google-tpu` timed out, `compute-accelerators-microsoft-maia-200` returned HTTP 403.
  - Raw evidence: 53 manifest raw paths, including 2 saved PDF attachments.
  - DB state: 53 fetch runs, 51 raw items, 51 pending ingest tasks.
- Added hardening after review:
  - Reject unsafe `source_id` path segments before profile mirroring or raw writes.
  - Verify PDF attachment SHA-256 in formal crawl manifest checks.
  - Preserve PDF attachment paths in manifest raw evidence.
- Evidence:
  - `.codex/accelerator-crawl/compute-accelerator-domestic-crawl-01/manifest.json` -> verified
  - `.codex/evaluations/tasks/compute-accelerator-domestic-crawl-01/20260627T155014Z-attempt-1/result.json` -> pass
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_fetchers.py tests/test_hashing_raw_store.py tests/test_db_profiles.py` -> 72 passed
  - `pytest -q scripts/tests/test_compute_accelerator_formal_crawl.py` -> 14 passed
  - `python3 scripts/compute_accelerator_formal_crawl.py verify-manifest --repo-root . --manifest .codex/accelerator-crawl/compute-accelerator-domestic-crawl-01/manifest.json --min-succeeded 1` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass

## 2026-06-27 Compute Accelerator Formal Crawl

- Added a controlled formal crawl CLI and evaluator scenario for compute accelerator source profiles.
- Ran the formal crawl against enabled accelerator profiles using crawler workbench APIs and saved raw evidence for successful sources.
- Results:
  - Succeeded: `compute-accelerators-nvidia-h200`, `compute-accelerators-intel-gaudi-3`, `compute-accelerators-nvidia-bluefield-3`, `compute-accelerators-aws-trn2`.
  - Failed and recorded in manifest: `compute-accelerators-google-tpu` timed out, `compute-accelerators-microsoft-maia-200` returned HTTP 403.
  - Skipped disabled fragile sources: AMD MI325X, NXP i.MX95 NPU, AMD Alveo V80, Intel IPU E2100, MLPerf training, TechPowerUp GPU DB.
- Raw evidence:
  - `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-nvidia-h200/20260627T102027151096Z-www-nvidia-com-en-us-data-center-h200-7d05aa2873.md`
  - `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-intel-gaudi-3/20260627T102038339892Z-www-intel-com-content-www-us-en-content-details-817486-intel-gaudi-3-ai-accelerator-white-72421ce95f.md`
  - `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-nvidia-bluefield-3/20260627T102038871241Z-www-nvidia-com-en-us-networking-products-data-processing-unit-d517920f8d.md`
  - `personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-aws-trn2/20260627T102039887117Z-aws-amazon-com-ec2-instance-types-trn2-9d15dc4a0c.md`
- Evidence:
  - `python3 scripts/compute_accelerator_formal_crawl.py run --repo-root . --output-dir .codex/accelerator-crawl/compute-accelerator-formal-crawl-01` -> 4 succeeded, 2 failed, 6 skipped disabled
  - `.codex/accelerator-crawl/compute-accelerator-formal-crawl-01/manifest.json` -> verified
  - `pytest -q scripts/tests/test_compute_accelerator_formal_crawl.py` -> 8 passed
  - `python3 scripts/compute_accelerator_formal_crawl.py verify-manifest --repo-root . --manifest .codex/accelerator-crawl/compute-accelerator-formal-crawl-01/manifest.json --min-succeeded 1` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `.codex/evaluations/tasks/compute-accelerator-formal-crawl-01/20260627T102325Z-attempt-1/result.json` -> pass

## 2026-06-27 Harness Evaluator Demo

- Prepared the Step4 demo output for `harness-evaluator-demo-01`.
- Ran the task verify command and a fresh task-level evaluator attempt for required scenario `EUS-01`.
- Validated the evaluator `result.json` contract against `input.json`.
- Marked `harness-evaluator-demo-01` done in `tasks.json`.
- Evidence:
  - `python3 scripts/harness_evaluator_demo.py write-expected --output-dir .codex/evaluator-demo/harness-evaluator-demo-01` -> pass
  - `python3 scripts/harness_evaluator_demo.py assert-expected --output-dir .codex/evaluator-demo/harness-evaluator-demo-01` -> pass
  - `python3 scripts/harness_evaluator_cli.py prepare-task --repo-root . --task-id harness-evaluator-demo-01 --attempt 1` -> `.codex/evaluations/tasks/harness-evaluator-demo-01/20260627T095240Z-attempt-1`
  - `.codex/evaluations/tasks/harness-evaluator-demo-01/20260627T095240Z-attempt-1/result.json` -> pass

## 2026-06-27 Wiki Crawler E2E Evaluator

- Re-ran the wiki crawler end-to-end evaluator on current `main`.
- Confirmed fetch, approval queue, approved ingest, raw crawler evidence, wiki page output, index/backlinks flow, and domain/full wiki validation in the isolated fixture repo.
- Marked `wiki-crawler-e2e-eval-01` done in `tasks.json`.
- Evidence:
  - `python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01` -> pass
  - `.codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01/result.json` -> pass
  - `.codex/evaluations/tasks/wiki-crawler-e2e-eval-01/20260627T091913Z-attempt-4/result.json` -> pass

## 2026-06-27 Compute Accelerator Spec Catalog

- Built the seed structured catalog under `personal-wiki/domains/ai_infra/data/compute_accelerators/`.
- Added curated wiki pages for source policy, field glossary, catalog overview, and crawler conventions.
- Added `validate-accelerators` to check schema, source refs, observations, resolved fields, shard expansion, duplicate resolved fields, and S5 review policy.
- Added crawler source metadata validation and sample accelerator source profiles.
- Marked fragile/unfetchable source profiles disabled until fetch stability or specialized fetch methods are available.
- Addressed final review findings by adding NPU/IPU seed coverage, enforcing S2/S3/S4 resolved-field policy, and validating field `value_type`.
- Evidence:
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `PYTHONPATH=personal-wiki/tests pytest -q personal-wiki/tests/test_accelerator_catalog.py` -> 21 passed
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py` -> 25 passed
  - `.codex/evaluations/tasks/compute-accelerator-spec-catalog-01/20260626T185023Z-attempt-2/result.json` -> pass

## 2026-06-27 Harness Step4 Wiki Crawler E2E

- Installed harness steps 1-3 and Step4 evaluator gates.
- Added `wiki-crawler-e2e-eval-01` as an independent evaluator scenario for the wiki crawler workflow.
- Fixed Step4 auto-gate behavior for sessions whose recorded task branch differs from the current git branch.
- Fixed read-only evaluator prompt evidence by inlining `artifacts.json` and bounded small artifact excerpts.
- Fixed crawler E2E helper repeatability by rebuilding isolated state with each fixture worktree.
- Evidence:
  - `.codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01/result.json` -> pass
  - `.codex/evaluations/tasks/harness-evaluator-demo-01/20260626T165353Z-attempt-1/result.json` -> pass
  - `.codex/evaluations/tasks/wiki-crawler-e2e-eval-01/20260626T165232Z-attempt-3/result.json` -> pass
- Verification:
  - `bash init.sh` -> pass
  - `python3 -m json.tool tasks.json > /dev/null` -> pass
  - `python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate` -> pass
  - `python3 -m unittest scripts.tests.test_wiki_crawler_e2e_evaluator -v` -> pass
  - `python3 -m unittest scripts.tests.test_harness_evaluator_orchestrator -v` -> pass
  - `python3 -m unittest scripts.tests.test_harness_evaluator_hooks -v` -> pass
  - `python3 harness-step4-evaluator-gates/scripts/test_step4_skill.py` -> pass
  - `python3 harness-step4-evaluator-gates/scripts/run_live_smoke.py --repo-root . --task-id harness-evaluator-demo-01` -> pass
  - `python3 scripts/harness_evaluator_cli.py prepare-task --repo-root . --task-id wiki-crawler-e2e-eval-01 --attempt 1` -> pass
  - `python3 scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver fake --task-id wiki-crawler-e2e-eval-01 --repo-root . --max-attempts 2` -> pass
  - `git diff --check` -> pass
- Note: current `prepare-task` CLI requires explicit `--attempt`; the original plan command without it exits with argparse usage error.

## 2026-06-27 初始化 Harness

- 完成 harness step1：建立 root `AGENTS.md` 和 docs 知识库。
- 完成 harness step2：填充架构、约定、技术决策和质量标准。
- 完成 harness step3：建立 `init.sh`、`tasks.json` 和 `progress.md`。
- tasks.json 初始任务数：1 个。
- 当前焦点：安装 Step4 evaluator gates，并用 `wiki-crawler-e2e-eval-01` 独立验证 wiki crawler 端到端功能。
- 下次从这里开始：运行 `bash init.sh`，读取 `tasks.json`，推进 priority=high 且 status=pending 的任务。

- harness-evaluator-demo-01 live smoke implementation finished (20260626T162540Z).
- harness-evaluator-demo-01 live smoke implementation finished (20260626T163449Z).
- harness-evaluator-demo-01 live smoke implementation finished (20260626T164415Z).
- harness-evaluator-demo-01 live smoke implementation finished (20260626T165329Z).
