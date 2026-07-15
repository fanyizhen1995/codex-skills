from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


SCENARIO_IDS = {
    "duplicate-reconcile",
    "worker-crash-lease-reclaim",
    "partial-generator-recovery",
    "run-scoped-decision-isolation",
    "reviewer-two-parent-cadence",
    "reviewer-timeout-fail-open",
    "dashboard-tabs-and-pagination",
    "legacy-role-removal",
}


def test_scenario_registry_declares_isolated_runtime_evaluator() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scenario = json.loads(
        (
            repo_root
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "loop-supervisor-unification-01.json"
        ).read_text(encoding="utf-8")
    )

    runtime = next(
        item
        for item in scenario["user_scenarios"]
        if item["scenario_id"] == "LOOP-SUPERVISOR-ISOLATED-RUNTIME-E2E"
    )
    assert "scripts/loop_supervisor_e2e_evaluator.py" in runtime["entrypoint"]
    serialized = json.dumps(runtime, ensure_ascii=False)
    for requirement in (
        "Worker crash",
        "recover_generator_result",
        "run-scoped",
        "Reviewer timeout",
        "Auditor",
    ):
        assert requirement in serialized


def test_isolated_loop_supervisor_evaluator_exercises_runtime_and_browser(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = tmp_path / "loop-supervisor-e2e"

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "loop_supervisor_e2e_evaluator.py"),
            "--repo-root",
            str(repo_root),
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "pass"
    assert {item["scenario_id"] for item in result["scenario_results"]} == SCENARIO_IDS
    assert all(item["status"] == "pass" for item in result["scenario_results"])

    runtime = result["runtime_evidence"]
    assert runtime["temporary_git_repository"] is True
    assert runtime["sqlite_integrity"] == "ok"
    assert runtime["seeded_record_count"] > 20
    assert runtime["git_commit_count"] >= 1
    assert set(runtime["launched_processes"]) == {
        "loop-supervisor",
        "loop-supervisor-worker",
        "loop-dashboard",
    }
    assert set(runtime["independent_inspections"]) >= {
        "database_rows",
        "action_leases",
        "run_files",
        "action_provenance",
        "browser_content",
        "git_commits",
    }
    assert runtime["fixture_only_rendering"] is False

    browser = result["browser_evidence"]
    health = browser["health_contract"]
    assert health["requested_endpoint"] == "/api/supervisor/health"
    assert health["health_request_count"] >= 1
    assert health["raw_service_history_requests_before_projection"] == 0
    assert health["raw_freshness_history_requests_before_projection"] == 0
    assert health["current_health_established_without_raw_history"] is True
    assert health["stale_projection_honest"] is True
    assert health["ui_status"] == "Supervisor \u964d\u7ea7"
    assert "supervisor-worker" in health["stale_service_ids"]

    assert set(browser["assertions"]) >= {
        "selected-tab-only direct URL request timing",
        "tab independence after refresh",
        "page-size 50 persists independently",
        "mobile table scrolling remains internal",
        "delayed health transition cannot overwrite run UI",
        "current health uses the bounded health endpoint without raw history paging",
        "stale current-health projection remains degraded",
    }

    suspicious = result["suspicious_case_checks"]
    assert suspicious
    assert all(item["counterexample_rerun"] == "pass" for item in suspicious)
    assert (output_dir / "browser" / "loop-supervisor-e2e-desktop.png").is_file()
