import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_auto_resume import resume_once
from scripts.harness_loop_contracts import read_json_file, run_dir_for, write_json_file
from scripts.harness_loop_orchestrator import create_preflight_run
from scripts.tests.test_harness_loop_orchestrator import init_git_repo, seed_open_must_fix_audit


def seed_audit_blocked_parent(repo_root: Path, run_id: str) -> None:
    init_git_repo(repo_root)
    run = create_preflight_run(
        repo_root=repo_root,
        mode="demand-development",
        requirement="Resume audit blocked parent",
        run_id=run_id,
        confirm=True,
    )
    run.update(
        {
            "run_kind": "parent",
            "phase": "audit_blocked",
            "next_action": "create_audit_remediation_task",
            "last_result": "blocked",
            "child_run_ids": [],
            "current_child_run_id": "",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 1,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 1,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "Resume audit blocked parent",
                "current_progress": "Auditor blocked",
                "next_step": "Create remediation child",
                "decision_needed": "No",
            },
            "accepted_changed_paths": [],
        }
    )
    write_json_file(run_dir_for(repo_root, run_id) / "run.json", run)
    seed_open_must_fix_audit(repo_root, run_id)


def seed_autonomous_dirty_path_blocked_run(repo_root: Path, run_id: str) -> None:
    init_git_repo(repo_root)
    run = create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement="Resume dirty-path blocked autonomous run",
        run_id=run_id,
        domain="ai_infra",
        confirm=True,
    )
    run.update(
        {
            "phase": "stopped_blocked",
            "next_action": "inspect_autonomous_dirty_paths",
            "last_result": "blocked",
            "task_id": f"{run_id}-parent-1",
        }
    )
    write_json_file(run_dir_for(repo_root, run_id) / "run.json", run)


def seed_autonomous_required_evidence_blocked_run(repo_root: Path, run_id: str) -> None:
    init_git_repo(repo_root)
    run = create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement="Resume required evidence blocked autonomous run",
        run_id=run_id,
        domain="ai_infra",
        confirm=True,
    )
    run.update(
        {
            "phase": "stopped_blocked",
            "next_action": "inspect_required_evidence",
            "last_result": "blocked",
            "task_id": f"{run_id}-parent-4",
        }
    )
    write_json_file(run_dir_for(repo_root, run_id) / "run.json", run)


def seed_autonomous_commit_blocked_run(repo_root: Path, run_id: str) -> None:
    init_git_repo(repo_root)
    run = create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement="Resume commit-blocked autonomous run",
        run_id=run_id,
        domain="ai_infra",
        confirm=True,
    )
    run.update(
        {
            "phase": "stopped_blocked",
            "next_action": "inspect_autonomous_commit",
            "last_result": "blocked",
            "task_id": f"{run_id}-parent-5",
        }
    )
    write_json_file(run_dir_for(repo_root, run_id) / "run.json", run)


def seed_autonomous_planning_run(repo_root: Path, run_id: str) -> None:
    init_git_repo(repo_root)
    create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement="Continue autonomous run",
        run_id=run_id,
        domain="ai_infra",
        confirm=True,
    )


class HarnessLoopAutoResumeTests(unittest.TestCase):
    def test_resume_once_finds_worktree_audit_blocked_parent_and_runs_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            worktree_root = project_root / ".worktrees" / "audit-worktree"
            worktree_root.mkdir(parents=True)
            seed_audit_blocked_parent(worktree_root, "audit-stuck")

            result = resume_once(
                project_root=project_root,
                include_worktrees=True,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
                max_tasks=1,
            )

            self.assertEqual(result["resumed_count"], 1, json.dumps(result, indent=2, ensure_ascii=False))
            self.assertEqual(result["resumed"][0]["run_id"], "audit-stuck")
            self.assertEqual(result["resumed"][0]["repo_root"], str(worktree_root))
            run = read_json_file(run_dir_for(worktree_root, "audit-stuck") / "run.json")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["last_result"], "pass")
            self.assertEqual(run["_audit_remediation"]["status"], "resolved")
            self.assertFalse(
                (run_dir_for(worktree_root, "audit-stuck") / "audit-reports" / "audit-002.json").exists()
            )
            remediation = read_json_file(
                run_dir_for(worktree_root, "audit-stuck")
                / "audit-remediation-result.json"
            )
            self.assertEqual(remediation["new_audit_report"], "")

    def test_resume_once_dry_run_finds_autonomous_dirty_path_blocked_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            seed_autonomous_dirty_path_blocked_run(project_root, "dirty-stuck")

            result = resume_once(
                project_root=project_root,
                include_worktrees=False,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
                max_tasks=3,
                dry_run=True,
            )

            self.assertEqual(result["candidate_count"], 1, json.dumps(result, indent=2, ensure_ascii=False))
            self.assertEqual(result["dry_run_count"], 1)
            self.assertEqual(result["resumed"][0]["run_id"], "dirty-stuck")
            self.assertEqual(result["resumed"][0]["phase"], "stopped_blocked")
            self.assertEqual(result["resumed"][0]["next_action"], "inspect_autonomous_dirty_paths")

    def test_resume_once_dry_run_finds_autonomous_required_evidence_blocked_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            seed_autonomous_required_evidence_blocked_run(project_root, "evidence-stuck")

            result = resume_once(
                project_root=project_root,
                include_worktrees=False,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
                max_tasks=3,
                dry_run=True,
            )

            self.assertEqual(result["candidate_count"], 1, json.dumps(result, indent=2, ensure_ascii=False))
            self.assertEqual(result["dry_run_count"], 1)
            self.assertEqual(result["resumed"][0]["run_id"], "evidence-stuck")
            self.assertEqual(result["resumed"][0]["phase"], "stopped_blocked")
            self.assertEqual(result["resumed"][0]["next_action"], "inspect_required_evidence")

    def test_resume_once_dry_run_finds_autonomous_commit_blocked_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            seed_autonomous_commit_blocked_run(project_root, "commit-stuck")

            result = resume_once(
                project_root=project_root,
                include_worktrees=False,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
                max_tasks=3,
                dry_run=True,
            )

            self.assertEqual(result["candidate_count"], 1, json.dumps(result, indent=2, ensure_ascii=False))
            self.assertEqual(result["dry_run_count"], 1)
            self.assertEqual(result["resumed"][0]["run_id"], "commit-stuck")
            self.assertEqual(result["resumed"][0]["next_action"], "inspect_autonomous_commit")

    def test_resume_once_dry_run_finds_autonomous_planning_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            seed_autonomous_planning_run(project_root, "planning-run")

            result = resume_once(
                project_root=project_root,
                include_worktrees=False,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
                max_tasks=3,
                dry_run=True,
            )

            self.assertEqual(result["candidate_count"], 1, json.dumps(result, indent=2, ensure_ascii=False))
            self.assertEqual(result["resumed"][0]["run_id"], "planning-run")
            self.assertEqual(result["resumed"][0]["phase"], "planning")
            self.assertEqual(result["resumed"][0]["next_action"], "run_autonomous_planner")

    def test_resume_once_skips_run_locked_by_another_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            seed_autonomous_planning_run(project_root, "planning-run")

            with patch(
                "scripts.harness_loop_orchestrator.acquire_run_lock",
                side_effect=__import__("scripts.harness_loop_runtime_lock", fromlist=["RunLockBusy"]).RunLockBusy(
                    "planning-run", "other-executor"
                ),
            ):
                result = resume_once(
                    project_root=project_root,
                    include_worktrees=False,
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=3,
                    max_tasks=1,
                )

            self.assertEqual(result["locked_count"], 1)
            self.assertEqual(result["locked"][0]["status"], "locked_by_other_executor")


if __name__ == "__main__":
    unittest.main()
