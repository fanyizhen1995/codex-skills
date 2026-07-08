import json
import tempfile
import unittest
from pathlib import Path

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
            self.assertTrue((run_dir_for(worktree_root, "audit-stuck") / "audit-reports" / "audit-002.json").exists())


if __name__ == "__main__":
    unittest.main()
