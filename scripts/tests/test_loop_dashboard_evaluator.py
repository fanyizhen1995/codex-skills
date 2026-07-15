import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_governance_repo_fixture(root: Path, *, expansion_phase: str = "stopped_budget") -> None:
    scenario_src = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "harness"
        / "evaluator-scenarios"
        / "ai-infra-loop-governance-dev-01.json"
    )
    scenario_dst = root / "docs" / "harness" / "evaluator-scenarios" / "ai-infra-loop-governance-dev-01.json"
    scenario_dst.parent.mkdir(parents=True, exist_ok=True)
    scenario_dst.write_text(scenario_src.read_text(encoding="utf-8"), encoding="utf-8")

    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev" / "run.json",
        {
            "run_id": "ai-infra-loop-governance-dev",
            "policy": "demand_development",
            "run_kind": "parent",
            "phase": "child_running",
            "child_run_ids": ["ai-infra-loop-governance-dev-child-001"],
            "current_child_run_id": "ai-infra-loop-governance-dev-child-001",
            "backlog": [
                {"task_id": "queue-001", "title": "queue item", "status": "queued"},
                {"task_id": "blocked-001", "title": "blocked item", "status": "blocked"},
            ],
            "reader_summary": {
                "purpose": "governance parent",
                "current_progress": "1 child running",
                "next_step": "Inspect blocked child and queued needs",
                "decision_needed": "Yes",
            },
        },
    )
    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-expansion-2026-07-07-r10" / "run.json",
        {
            "run_id": "ai-infra-expansion-2026-07-07-r10",
            "phase": expansion_phase,
        },
    )
    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev-child-001" / "evaluator-result.json",
        {
            "formal_verification": {"status": "pass", "required_counterexample_reruns": []},
            "formal_verification_artifact_paths": [
                ".codex/loop-runs/ai-infra-loop-governance-dev-child-001/formal-proof.txt"
            ],
            "verdict_reason": "No unresolved confirmed formal bug remains.",
        },
    )
    _write_json(
        root / "personal-wiki" / "domains" / "ai_infra" / "manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json",
        {
            "channels": [{"name": "vendor"}],
            "sources": [{"url": "https://example.com/spec"}],
        },
    )


def _scenario_statuses(payload: dict) -> dict[str, str]:
    return {item["scenario_id"]: item["status"] for item in payload["scenario_results"]}


class LoopDashboardEvaluatorGovernanceTests(unittest.TestCase):
    def test_supervisor_unification_scenario_dispatches_to_browser_owner(self) -> None:
        from scripts import loop_dashboard_evaluator as evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            output_dir = Path(tmp) / "output"
            (repo_root / "scripts").mkdir(parents=True)
            browser_script = repo_root / "scripts" / "loop_dashboard_supervisor_playwright.py"
            browser_script.write_text("# fixture browser owner\n", encoding="utf-8")

            def run_child(command, **_kwargs):
                result_path = Path(command[command.index("--result-json") + 1])
                result_path.write_text(
                    json.dumps(
                        {
                            "status": "pass",
                            "scenario_id": "LOOP-SUPERVISOR-UNIFICATION-BROWSER-E2E",
                            "summary": "browser pass",
                            "checked": ["desktop", "mobile"],
                            "browser_evidence": {"desktop_screenshot": "desktop.png"},
                        }
                    ),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 0, stdout="child stdout", stderr="")

            with patch("scripts.loop_dashboard_evaluator.subprocess.run", side_effect=run_child) as run:
                status = evaluator.run_loop_supervisor_unification_evaluator(
                    repo_root,
                    output_dir,
                    port=9876,
                )

            self.assertEqual(status, 0)
            command = run.call_args.args[0]
            self.assertIn(str(browser_script), command)
            self.assertIn("--port", command)
            self.assertEqual(json.loads((output_dir / "result.json").read_text())["status"], "pass")

    def test_supervisor_unification_browser_owner_has_real_fixture_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        owner_path = repo_root / "scripts" / "loop_dashboard_supervisor_playwright.py"
        scenario_path = (
            repo_root
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "loop-supervisor-unification-01.json"
        )

        owner = owner_path.read_text(encoding="utf-8")
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))

        self.assertIn("SupervisorStore.open", owner)
        self.assertIn("LOOP_DASHBOARD_CURSOR_SECRET", owner)
        for collection in ("actions", "reviews", "user_decisions", "inventory", "events.jsonl", ".stdout.log"):
            self.assertIn(collection, owner)
        for count in ("ACTION_COUNT = 26", "REVIEW_COUNT = 26", "DECISION_COUNT = 26", "SKILL_COUNT = 26", "EVENT_COUNT = 26", "LOG_COUNT = 26"):
            self.assertIn(count, owner)
        for viewport in ('"width": 1440, "height": 1000', '"width": 390, "height": 844'):
            self.assertIn(viewport, owner)
        for behavior in ("下一页", "第 21-26 条，共 26 条", "action-001", "scrollWidth", "refresh", "log-detail"):
            self.assertIn(behavior, owner)
        for artifact in (
            "planner-output.json",
            "generator-result.json",
            "evaluator-result.json",
            "task-contract.json",
            "run-detail-desktop.png",
        ):
            self.assertIn(artifact, owner)
        for assertion in (
            "selected-tab-only",
            "tab independence",
            "page-size 50",
            "complete task description",
            "mobile table scrolling",
            "page-21 reload",
            "many-run/tab URL bound",
            "delayed health transition",
            "attempt page 21",
            "visible run/tab pager pressure",
            "current health uses the bounded health endpoint",
            "stale current-health projection remains degraded",
        ):
            self.assertIn(assertion, owner)
        self.assertIn("FIXTURE_RUN_COUNT = 5", owner)
        self.assertIn("FRESHNESS_COUNT = 103", owner)
        self.assertIn('f"fixture-run-{index:03d}"', owner)
        self.assertIn("freshness-hidden-stale", owner)
        self.assertIn("visible run/tab pager pressure", owner)
        self.assertIn('"/api/supervisor/health"', owner)
        self.assertIn("current_health_established_without_raw_history", owner)
        self.assertNotIn("complete health did not request hidden service pages", owner)
        self.assertNotIn("new window.LoopPagination.CursorPager", owner)
        self.assertIn('"--no-access-log"', owner)
        self.assertEqual(scenario["task_id"], "loop-supervisor-unification-01")
        self.assertTrue(scenario["must_simulate"])
        serialized = json.dumps(scenario, ensure_ascii=False)
        self.assertIn("pagination.js -> supervisor.js -> app.js", serialized)
        self.assertIn("20/50/100", serialized)
        self.assertIn("--scenario loop-supervisor-unification-01", serialized)

    def test_isolated_dashboard_child_injects_evaluator_cursor_secret(self) -> None:
        from scripts import loop_dashboard_evaluator as evaluator

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            evaluator.os.environ,
            {},
            clear=True,
        ), patch.object(evaluator.subprocess, "Popen") as popen:
            repo_root = Path(tmp)
            fixture_root = repo_root / "fixture"

            evaluator.start_dashboard(repo_root, fixture_root, 18766)

        child_env = popen.call_args.kwargs["env"]
        self.assertEqual(
            child_env["LOOP_DASHBOARD_CURSOR_SECRET"],
            evaluator.EVALUATOR_CURSOR_SECRET,
        )
        self.assertGreaterEqual(
            len(child_env["LOOP_DASHBOARD_CURSOR_SECRET"].encode()),
            32,
        )

    def test_auditor_engine_fixture_is_historical_disabled_and_read_only(self) -> None:
        from scripts import loop_dashboard_evaluator as evaluator

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            evaluator,
            "compute_deterministic_signals",
            side_effect=AssertionError("historical fixture must not compute active signals"),
            create=True,
        ), patch.object(
            evaluator,
            "rule_based_audit_report",
            side_effect=AssertionError("historical fixture must not run Auditor"),
            create=True,
        ), patch.object(
            evaluator,
            "run_demand_multi",
            side_effect=AssertionError("historical fixture must not enter audit_blocked"),
            create=True,
        ):
            repo_root = Path(tmp)
            evaluator.seed_auditor_engine_fixture(repo_root)
            run_dir = (
                repo_root
                / ".codex"
                / "loop-runs"
                / evaluator.AUDITOR_ENGINE_RUN_ID
            )

            run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            historical_report = json.loads(
                (run_dir / "audit-reports" / "audit-001.json").read_text(
                    encoding="utf-8"
                )
            )
            migration_result = json.loads(
                (run_dir / "audit-remediation-result.json").read_text(encoding="utf-8")
            )

            self.assertNotIn(run["phase"], {"audit_pending", "auditing", "audit_blocked"})
            self.assertEqual(run["legacy_audit_migration"]["status"], "migrated")
            self.assertEqual(historical_report["audit_id"], "audit-001")
            self.assertEqual(historical_report["verdict"], "must_fix")
            self.assertEqual(
                historical_report["created_by"], "historical_pre_cutover_auditor"
            )
            self.assertEqual(migration_result["audit_id"], "audit-001")
            self.assertEqual(migration_result["status"], "pass")
            self.assertEqual(
                migration_result["migration_mode"], "disabled_legacy_auditor"
            )
            self.assertEqual(migration_result["new_audit_report"], "")
            self.assertFalse((run_dir / "audit-reports" / "audit-002.json").exists())

    def test_auditor_engine_fixture_rejects_successor_audit_report(self) -> None:
        from scripts import loop_dashboard_evaluator as evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            evaluator.seed_auditor_engine_fixture(repo_root)
            run_dir = (
                repo_root
                / ".codex"
                / "loop-runs"
                / evaluator.AUDITOR_ENGINE_RUN_ID
            )
            _write_json(
                run_dir / "audit-reports" / "audit-002.json",
                {"audit_id": "audit-002", "verdict": "pass"},
            )

            with self.assertRaisesRegex(RuntimeError, "must not produce a successor"):
                evaluator.validate_historical_auditor_fixture(run_dir)

    def test_loop_supervisor_scenario_seeds_contract_artifacts_without_synthetic_run(self) -> None:
        from scripts.loop_dashboard_evaluator import seed_loop_supervisor_fixture

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_loop_supervisor_fixture(repo_root)

            self.assertTrue((repo_root / ".codex" / "supervisor" / "supervisor-state.json").exists())
            self.assertTrue((repo_root / ".codex" / "supervisor" / "service-health.json").exists())
            self.assertTrue((repo_root / ".codex" / "supervisor" / "continuation-plans.jsonl").exists())
            self.assertTrue((repo_root / ".codex" / "supervisor" / "freshness-targets.jsonl").exists())
            self.assertTrue((repo_root / ".codex" / "supervisor" / "needs-user-decisions" / "retry-ceiling.json").exists())
            self.assertTrue((repo_root / ".codex" / "loop-runs" / "supervisor-autonomous-budget-run" / "run.json").exists())
            self.assertFalse((repo_root / ".codex" / "loop-runs" / "loop-supervisor").exists())
            self.assertFalse((repo_root / ".codex" / "loop-runs" / "supervisor").exists())
            budget_run = json.loads(
                (repo_root / ".codex" / "loop-runs" / "supervisor-autonomous-budget-run" / "run.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(budget_run["policy"], "autonomous_knowledge")
            service_health = json.loads(
                (repo_root / ".codex" / "supervisor" / "service-health.json").read_text(encoding="utf-8")
            )
            dashboard = next(item for item in service_health["services"] if item["service"] == "loop-dashboard")
            self.assertEqual(dashboard["data_freshness"]["status_label"], "暂无 freshness target")
            backend = next(item for item in service_health["services"] if item["service"] == "crawler-backend")
            self.assertEqual(backend["data_freshness"]["target_id"], "ai-infra-parent-14-atlas-300i-a2")
            self.assertIn("search", backend["data_freshness"]["checks"])
            self.assertIn("wiki-page", backend["data_freshness"]["checks"])
            self.assertEqual(backend["running_version"]["freshness"], "unavailable")
            self.assertFalse(backend["running_version"]["matches_expected"])
            self.assertEqual(
                backend["running_version"]["runtime_metadata_path"],
                ".codex/service-runtime/crawler-backend.json",
            )
            self.assertIn("runtime metadata missing", backend["running_version"]["evidence"])
            frontend = next(item for item in service_health["services"] if item["service"] == "crawler-frontend")
            self.assertEqual(frontend["data_freshness"]["target_id"], "ai-infra-parent-14-atlas-300i-a2")
            self.assertEqual(frontend["data_freshness"]["checks"], ["frontend-visible"])
            self.assertEqual(frontend["running_version"]["freshness"], "stale")
            self.assertIn("stale", frontend["running_version"]["evidence"])
            self.assertEqual(
                frontend["running_version"]["runtime_metadata_path"],
                ".codex/service-runtime/crawler-frontend.json",
            )

    def test_loop_supervisor_scenario_contract_uses_scenario_entrypoint(self) -> None:
        scenario_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "loop-supervisor-01.json"
        )

        payload = json.loads(scenario_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["task_id"], "loop-supervisor-01")
        self.assertTrue(payload["must_simulate"])
        self.assertTrue(payload["user_scenarios"])
        for scenario in payload["user_scenarios"]:
            self.assertIn("--scenario loop-supervisor-01", scenario["entrypoint"])
        scenario_text = json.dumps(payload, ensure_ascii=False)
        for expected in [
            "全局 Supervisor 面板",
            "服务行显示正常、版本不可用、版本过期",
            "幂等键只出现一次",
            "需要用户决策",
            "Auditor 区分控制输入和质量判断",
            "暂无数据/不可用",
        ]:
            self.assertIn(expected, scenario_text)

    def test_governance_evaluator_fails_when_required_artifacts_are_missing(self) -> None:
        from scripts.loop_dashboard_evaluator import run_governance_evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / ".codex" / "loop-dashboard-eval" / "ai-infra-loop-governance-dev-01"

            exit_code = run_governance_evaluator(repo_root, output_dir)

            self.assertEqual(exit_code, 1)
            payload = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["scenario_results"][0]["scenario_id"], "E2E-0")
            self.assertTrue(
                any(
                    "docs/harness/evaluator-scenarios/ai-infra-loop-governance-dev-01.json" in item
                    for item in payload["diagnostics"]
                )
            )

    def test_governance_e2e_0_tracks_preflight_artifact_gate(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root)
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "blocked",
                    "artifact_paths": [".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json"],
                    "missing_artifacts": [".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json"],
                    "findings": ["identity-key-audit.json status must be pass"],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "children_summary": {"total": 1, "blocked": 1, "passed": 0, "pending": 0},
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-0"], "fail")

    def test_governance_e2e_1_tracks_stopped_budget_takeover(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root, expansion_phase="child_running")
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "pass",
                    "artifact_paths": [
                        ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/top.json",
                    ],
                    "missing_artifacts": [],
                    "findings": [],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "children_summary": {"total": 1, "blocked": 1, "passed": 0, "pending": 0},
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-1"], "fail")

    def test_governance_e2e_2_requires_dashboard_parent_child_queue_visibility(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root)
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "pass",
                    "artifact_paths": [
                        ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/top.json",
                    ],
                    "missing_artifacts": [],
                    "findings": [],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-2"], "fail")

    def test_governance_evaluator_writes_result_json_on_governance_exception(self) -> None:
        from scripts import loop_dashboard_evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / ".codex" / "loop-dashboard-eval" / "ai-infra-loop-governance-dev-01"
            argv = [
                "loop_dashboard_evaluator.py",
                "--repo-root",
                str(repo_root),
                "--output-dir",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv), patch(
                "scripts.loop_dashboard_evaluator.evaluate_governance_repo",
                side_effect=RuntimeError("boom"),
            ):
                exit_code = loop_dashboard_evaluator.main()

            self.assertEqual(exit_code, 1)
            result_path = output_dir / "result.json"
            self.assertTrue(result_path.exists())
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["scenario_results"][0]["scenario_id"], "E2E-7")
            self.assertIn("boom", payload["diagnostics"][0])
            self.assertIn("generated_at", payload)

    def test_governance_e2e_7_accepts_completed_parent_waiting_for_merge(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root)
            parent_path = repo_root / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev" / "run.json"
            parent = json.loads(parent_path.read_text(encoding="utf-8"))
            parent.update(
                {
                    "phase": "passed_waiting_human_merge",
                    "last_result": "pass",
                    "next_action": "await_human_merge_confirmation",
                    "current_child_run_id": "",
                    "aggregate_acceptance": {
                        "total": 1,
                        "passed": 1,
                        "failed": 0,
                        "blocked": 0,
                        "pending": 0,
                        "user_decision_required": True,
                    },
                }
            )
            parent_path.write_text(json.dumps(parent), encoding="utf-8")
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "pass",
                    "artifact_paths": [
                        ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/top.json",
                    ],
                    "missing_artifacts": [],
                    "findings": [],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "phase": "passed_waiting_human_merge",
                    "next_action": "await_human_merge_confirmation",
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "passed",
                            "reader_summary": {"acceptance_result": "Passed"},
                        }
                    ],
                    "children_summary": {"total": 1, "blocked": 0, "passed": 1, "pending": 0},
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-7"], "pass")


if __name__ == "__main__":
    unittest.main()
