# 项目进度记录

> 每次 session 完成任务后，在顶部追加记录。不要删除历史。
> 格式：`## YYYY-MM-DD 任务名`

---

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
