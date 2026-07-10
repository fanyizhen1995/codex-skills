import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_auditor import (
    compute_deterministic_signals,
    rule_based_audit_report,
    write_deterministic_signals,
)
from scripts.harness_loop_contracts import (
    read_json_file,
    run_dir_for,
    validate_audit_report_payload,
    write_json_file,
)
from scripts.harness_loop_orchestrator import create_preflight_run, load_run, save_run


def init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "codex@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Codex"], cwd=repo_root, check=True)
    (repo_root / "README.md").write_text("temporary repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "commit", "-m", "test: initial"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_head(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def seed_child(repo_root: Path, parent: dict, index: int, *, evaluator_stdout: str, changed_path: str) -> str:
    child_id = f"{parent['run_id']}-child-{index:03d}"
    child = {
        "run_id": child_id,
        "run_kind": "child",
        "parent_run_id": parent["run_id"],
        "child_index": index,
        "policy": "demand_development",
        "phase": "passed",
        "task_id": f"{child_id}-task",
        "domain": "",
        "branch": "main",
        "worktree": str(repo_root),
        "requirement": f"child {index}",
        "constraints": [],
        "stop_conditions": ["passed"],
        "baseline_dirty_paths": [],
        "allowed_paths": [changed_path],
        "denylist_paths": [],
        "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
        "limits": parent["limits"],
        "last_result": "pass",
        "next_action": "return_to_parent_planner",
        "attempt_history": [],
        "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        "reader_summary": {
            "purpose": f"child {index}",
            "planner_action": "planned",
            "generator_action": "generated",
            "evaluator_action": "evaluated",
            "acceptance_result": "Passed",
        },
    }
    write_json_file(run_dir_for(repo_root, child_id) / "run.json", child)
    write_json_file(
        run_dir_for(repo_root, child_id) / "evaluator-result.json",
        {
            "status": "pass",
            "task_id": child["task_id"],
            "driver": "fake",
            "returncode": 0,
            "stdout": evaluator_stdout,
            "stderr": "",
        },
    )
    write_json_file(
        run_dir_for(repo_root, child_id) / "generator-result.json",
        {
            "task_id": child["task_id"],
            "status": "implemented",
            "changed_paths": [changed_path],
            "commit": "",
            "verify_commands": [],
            "verify_results": [],
            "artifacts": [changed_path],
            "cleanup_required": False,
            "notes": "seeded child",
        },
    )
    return child_id


class HarnessLoopAuditorTests(unittest.TestCase):
    def test_compute_deterministic_signals_counts_commits_since_previous_audit_not_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build audited feature",
                run_id="commit-run",
                confirm=True,
            )
            run = load_run(repo_root, "commit-run")

            first_payload = compute_deterministic_signals(repo_root, run)

            self.assertEqual(first_payload["summary"]["commits_since_last_audit"], 0)
            self.assertEqual(first_payload["git"]["head_sha"], git_head(repo_root))

            write_json_file(
                run_dir_for(repo_root, "commit-run") / "audit-reports" / "audit-001.json",
                {
                    "schema_version": 1,
                    "run_id": "commit-run",
                    "audit_id": "audit-001",
                    "created_at": "2026-07-08T00:00:00Z",
                    "created_by": "harness_loop_orchestrator",
                    "verdict": "pass",
                    "deterministic_signals": {
                        "artifact_path": ".codex/loop-runs/commit-run/deterministic-signals.json",
                        "artifact_sha256": "a" * 64,
                        "summary": first_payload["summary"],
                        "git_head_sha": first_payload["git"]["head_sha"],
                    },
                    "cadence": {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1},
                    "direction_control": {"action": "continue", "reason": "healthy"},
                    "finding_lifecycle": {"open_findings": [], "closed_findings": []},
                },
            )
            (repo_root / "CHANGELOG.md").write_text("one new commit\n", encoding="utf-8")
            subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "test: change"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            second_payload = compute_deterministic_signals(repo_root, run)

            self.assertEqual(second_payload["summary"]["commits_since_last_audit"], 1)
            self.assertEqual(second_payload["git"]["previous_audit_head_sha"], first_payload["git"]["head_sha"])

    def test_compute_deterministic_signals_reports_git_dirty_failure_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build audited feature",
                run_id="dirty-error-run",
                confirm=True,
            )

            def fake_run_git(_repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
                if args[:1] == ["status"]:
                    return subprocess.CompletedProcess(["git", *args], 128, "", "fatal: not a git repository")
                if args[:2] == ["rev-parse", "HEAD"]:
                    return subprocess.CompletedProcess(["git", *args], 0, "abc123\n", "")
                if args[:1] == ["rev-list"]:
                    return subprocess.CompletedProcess(["git", *args], 0, "0\n", "")
                return subprocess.CompletedProcess(["git", *args], 1, "", "unsupported")

            with patch("scripts.harness_loop_auditor._run_git", side_effect=fake_run_git):
                with self.assertRaisesRegex(RuntimeError, "git status failed"):
                    compute_deterministic_signals(repo_root, run)

    def test_compute_deterministic_signals_counts_parent_progress_and_repeated_evaluator_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build multi child feature",
                run_id="parent-run",
                confirm=True,
            )
            parent = load_run(repo_root, "parent-run")
            parent.update(
                {
                    "run_kind": "parent",
                    "phase": "planning",
                    "current_child_run_id": "",
                    "child_run_ids": [],
                    "backlog": [],
                    "accepted_changed_paths": ["generated/child-001.txt", "generated/child-002.txt"],
                    "aggregate_acceptance": {
                        "total": 3,
                        "passed": 2,
                        "failed": 0,
                        "blocked": 0,
                        "pending": 1,
                        "user_decision_required": False,
                    },
                    "reader_summary": {
                        "purpose": "Build multi child feature",
                        "current_progress": "2 children passed",
                        "next_step": "Run parent planner",
                        "decision_needed": "No",
                    },
                }
            )
            parent["child_run_ids"] = [
                seed_child(
                    repo_root,
                    parent,
                    1,
                    evaluator_stdout="same evaluator finding\n",
                    changed_path="generated/child-001.txt",
                ),
                seed_child(
                    repo_root,
                    parent,
                    2,
                    evaluator_stdout="same evaluator finding\n",
                    changed_path="generated/child-002.txt",
                ),
            ]
            save_run(repo_root, parent)

            payload = compute_deterministic_signals(repo_root, parent)

            summary = payload["summary"]
            self.assertEqual(summary["passed_children_since_last_audit"], 2)
            self.assertEqual(summary["same_evaluator_finding_count"], 2)
            self.assertEqual(summary["same_file_modified_consecutively"], 0)
            self.assertEqual(summary["unclassified_dirty_paths"], 0)
            self.assertEqual(payload["created_by"], "harness_loop_orchestrator")

    def test_compute_deterministic_signals_ignores_runtime_loop_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="locked-run",
                domain="ai_infra",
                confirm=True,
            )
            lock_path = repo_root / ".codex" / "loop-locks" / "locked-run.lock"
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text('{"owner":"test"}\n', encoding="utf-8")

            payload = compute_deterministic_signals(repo_root, run)

            self.assertEqual(payload["summary"]["unclassified_dirty_paths"], 0)

    def test_compute_deterministic_signals_groups_structured_evaluator_findings_by_stable_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build multi child feature",
                run_id="finding-parent",
                confirm=True,
            )
            parent = load_run(repo_root, "finding-parent")
            parent.update(
                {
                    "run_kind": "parent",
                    "phase": "planning",
                    "current_child_run_id": "",
                    "child_run_ids": [],
                    "backlog": [],
                    "accepted_changed_paths": ["generated/child-001.txt", "generated/child-002.txt"],
                    "aggregate_acceptance": {
                        "total": 2,
                        "passed": 2,
                        "failed": 0,
                        "blocked": 0,
                        "pending": 0,
                        "user_decision_required": False,
                    },
                    "reader_summary": {
                        "purpose": "Build multi child feature",
                        "current_progress": "2 children passed",
                        "next_step": "Run parent planner",
                        "decision_needed": "No",
                    },
                }
            )
            parent["child_run_ids"] = [
                seed_child(repo_root, parent, 1, evaluator_stdout="", changed_path="generated/child-001.txt"),
                seed_child(repo_root, parent, 2, evaluator_stdout="", changed_path="generated/child-002.txt"),
            ]
            for child_id, path_value in zip(parent["child_run_ids"], ["frontend/a.ts", "frontend/b.ts"], strict=True):
                child = read_json_file(run_dir_for(repo_root, child_id) / "run.json")
                write_json_file(
                    run_dir_for(repo_root, child_id) / "evaluator-result.json",
                    {
                        "status": "fail",
                        "task_id": child["task_id"],
                        "driver": "fake",
                        "returncode": 1,
                        "stdout": "",
                        "stderr": "",
                        "findings": [
                            {
                                "id": f"LD-{path_value}",
                                "severity": "major",
                                "category": "frontend_click",
                                "title": "Log filter broken",
                                "summary": f"Log filter failed for {path_value}.",
                                "evidence": [path_value],
                            }
                        ],
                    },
                )
            save_run(repo_root, parent)

            payload = compute_deterministic_signals(repo_root, parent)

            self.assertEqual(payload["summary"]["same_evaluator_finding_count"], 2)

    def test_write_deterministic_signals_persists_schema_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build thing",
                run_id="signal-run",
                confirm=True,
            )

            path = write_deterministic_signals(repo_root, run)

            payload = read_json_file(path)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["run_id"], "signal-run")
            self.assertEqual(payload["created_by"], "harness_loop_orchestrator")
            self.assertIn("summary", payload)

    def test_validate_audit_report_requires_signal_provenance_and_open_must_fix(self) -> None:
        valid = {
            "schema_version": 1,
            "run_id": "audited-run",
            "audit_id": "audit-001",
            "created_at": "2026-07-08T00:00:00Z",
            "created_by": "harness_loop_orchestrator",
            "verdict": "must_fix",
            "deterministic_signals": {
                "artifact_path": ".codex/loop-runs/audited-run/deterministic-signals.json",
                "artifact_sha256": "a" * 64,
                "summary": {"same_evaluator_finding_count": 2},
            },
            "cadence": {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1},
            "direction_control": {"action": "refocus", "reason": "repeated evaluator finding"},
            "finding_lifecycle": {
                "open_findings": [
                    {
                        "finding_id": "audit-001-repeat-001",
                        "severity": "must_fix",
                        "status": "open",
                        "title": "Repeated evaluator finding",
                        "summary": "Same evaluator finding repeated.",
                        "required_planner_action": "create_remediation_child",
                    }
                ],
                "closed_findings": [],
            },
        }

        validate_audit_report_payload(valid)

        missing_finding = json.loads(json.dumps(valid))
        missing_finding["finding_lifecycle"]["open_findings"] = []
        with self.assertRaisesRegex(ValueError, "open must_fix"):
            validate_audit_report_payload(missing_finding)

        missing_signal = json.loads(json.dumps(valid))
        missing_signal["deterministic_signals"]["artifact_path"] = ""
        with self.assertRaisesRegex(ValueError, "deterministic signal"):
            validate_audit_report_payload(missing_signal)

    def test_rule_based_audit_report_escalates_repeated_evaluator_findings(self) -> None:
        signals = {
            "schema_version": 1,
            "run_id": "audited-run",
            "computed_at": "2026-07-08T00:00:00Z",
            "created_by": "harness_loop_orchestrator",
            "summary": {
                "same_evaluator_finding_count": 2,
                "same_dirty_path_count": 0,
                "same_local_issue_rounds": 0,
            },
        }

        report = rule_based_audit_report(
            run_id="audited-run",
            audit_id="audit-001",
            signals=signals,
            signal_artifact_path=".codex/loop-runs/audited-run/deterministic-signals.json",
            signal_artifact_sha256="b" * 64,
        )

        self.assertEqual(report["verdict"], "must_fix")
        self.assertEqual(report["direction_control"]["action"], "refocus")
        validate_audit_report_payload(report)


if __name__ == "__main__":
    unittest.main()
