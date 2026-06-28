# 项目进度记录

> 每次 session 完成任务后，在顶部追加记录。不要删除历史。
> 格式：`## YYYY-MM-DD 任务名`

---

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
