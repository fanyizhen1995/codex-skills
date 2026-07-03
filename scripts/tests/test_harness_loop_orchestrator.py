import io
import os
import shutil
import tempfile
import unittest
import json
import subprocess
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_contracts import (
    read_json_file,
    run_dir_for,
    validate_evaluator_result_payload,
    validate_generator_result_payload,
    validate_loop_state_payload,
    validate_planner_output_payload,
    validate_run_payload,
    write_json_file,
)
from scripts.harness_loop_autonomous import create_default_loop_state, write_loop_state
from scripts.harness_loop_orchestrator import (
    confirm_preflight,
    create_preflight_run,
    main,
    run_autonomous,
    run_demand_multi,
    status_for_run,
)


def write_fake_evaluator_scenario(repo_root: Path, task_id: str) -> Path:
    scenario_dir = repo_root / "docs" / "harness" / "evaluator-scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = scenario_dir / f"{task_id}.json"
    scenario_path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "EUS-01",
                        "user_goal": "Exercise the synthetic evaluator loop.",
                        "prerequisites": ["Temporary repository exists."],
                        "entrypoint": "python3 -c \"print('scenario-ok')\"",
                        "steps": ["Run the fake evaluator task loop."],
                        "expected_outcomes": ["Fake evaluator records a pass result."],
                        "failure_signals": ["Fake evaluator result is missing."],
                        "cleanup": ["TemporaryDirectory cleanup removes generated files."],
                        "automation_hint": "manual",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return scenario_path


def call_cli(argv: list[str]) -> int:
    with redirect_stdout(io.StringIO()):
        return main(argv)


def remove_fake_evaluator_attempts(eval_dir: Path) -> None:
    for attempt_dir in eval_dir.glob("fake-attempt-*"):
        if attempt_dir.is_dir():
            shutil.rmtree(attempt_dir, ignore_errors=True)
    try:
        eval_dir.rmdir()
    except OSError:
        pass


def remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (repo_root / "README.md").write_text("temporary repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def seed_no_action_loop_state(repo_root: Path, domain: str) -> dict[str, object]:
    state = create_default_loop_state(domain, "Expand wiki")
    state["candidate_backlog"] = []
    state["coverage_gaps"] = []
    state["known_sources"] = [
        {
            "id": "src-1",
            "title": "Source",
            "source": "manual",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["checked"],
        }
    ]
    state["no_action_evidence"] = [
        {
            "id": "scan-1",
            "title": "Scan",
            "source": "planner",
            "status": "complete",
            "updated_at": state["last_scan_at"],
            "evidence": ["no candidates"],
        }
    ]
    write_loop_state(repo_root, domain, state)
    return state


def seed_candidate_loop_state(repo_root: Path, domain: str) -> dict[str, object]:
    state = create_default_loop_state(domain, "Expand wiki")
    state["known_sources"] = [
        {
            "id": "src-1",
            "title": "Source",
            "source": "manual",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["checked"],
        }
    ]
    state["candidate_backlog"] = [
        {
            "id": "candidate-1",
            "title": "Capture synthetic source",
            "source": "planner",
            "status": "pending",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded candidate"],
        }
    ]
    write_loop_state(repo_root, domain, state)
    return state


class HarnessLoopOrchestratorTests(unittest.TestCase):
    def test_create_preflight_run_without_confirmation_writes_run_state_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=False,
            )

            run_dir = run_dir_for(repo_root, "demo-run")
            run_path = run_dir / "run.json"
            preflight_path = run_dir / "preflight.md"
            self.assertEqual(payload["phase"], "preflight")
            self.assertEqual(payload["next_action"], "await_preflight_confirmation")
            self.assertEqual(payload["policy"], "demand_development")
            self.assertTrue(run_path.exists())
            self.assertTrue(preflight_path.exists())
            saved_payload = read_json_file(run_path)
            validate_run_payload(saved_payload)
            self.assertEqual(saved_payload["phase"], "preflight")
            self.assertEqual(saved_payload["requirement"], "Build the thing")
            self.assertEqual(saved_payload["constraints"], [])
            self.assertEqual(saved_payload["stop_conditions"], ["passed_waiting_human_merge"])
            preflight = preflight_path.read_text(encoding="utf-8")
            self.assertIn("Build the thing", preflight)
            self.assertIn("Fallback Questionnaire", preflight)

    def test_create_preflight_run_captures_baseline_before_loop_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
            unrelated_path = repo_root / "unrelated.txt"
            unrelated_path.write_text("pre-existing user change\n", encoding="utf-8")

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            self.assertEqual(payload["baseline_dirty_paths"], ["?? unrelated.txt"])

    def test_create_preflight_run_rejects_path_escape_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "run_id"):
                create_preflight_run(
                    repo_root=repo_root,
                    mode="demand-development",
                    requirement="Build the thing",
                    run_id="../escape",
                    confirm=True,
                )

    def test_confirm_preflight_changes_phase_to_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=False,
            )

            payload = confirm_preflight(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(payload["phase"], "planned")
            self.assertEqual(payload["next_action"], "run_planner")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["phase"], "planned")
            self.assertEqual(saved_payload["next_action"], "run_planner")

    def test_create_preflight_run_captures_constraints_and_stop_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                constraints=["Only touch scripts/"],
                stop_conditions=["passed_waiting_human_merge", "stopped_blocked"],
                confirm=True,
            )

            self.assertEqual(payload["constraints"], ["Only touch scripts/"])
            self.assertEqual(payload["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["constraints"], ["Only touch scripts/"])
            self.assertEqual(saved_payload["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])

    def test_create_preflight_run_with_confirmation_starts_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            self.assertEqual(payload["phase"], "planned")
            self.assertEqual(payload["next_action"], "run_planner")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["phase"], "planned")
            self.assertEqual(saved_payload["next_action"], "run_planner")

    def test_create_preflight_run_accepts_autonomous_knowledge_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Crawl knowledge",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )

            self.assertEqual(payload["policy"], "autonomous_knowledge")
            self.assertEqual(payload["phase"], "planning")
            self.assertEqual(payload["domain"], "ai_infra")
            self.assertEqual(payload["next_action"], "run_autonomous_planner")
            self.assertIn("stopped_no_action", payload["stop_conditions"])
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(saved_payload)

    def test_confirm_preflight_preserves_autonomous_knowledge_start_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Crawl knowledge",
                run_id="demo-run",
                domain="ai_infra",
                confirm=False,
            )

            payload = confirm_preflight(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(payload["policy"], "autonomous_knowledge")
            self.assertEqual(payload["phase"], "planning")
            self.assertEqual(payload["next_action"], "run_autonomous_planner")

    def test_run_autonomous_stops_when_loop_state_has_fresh_no_action_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_no_action_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")
            self.assertEqual(status["next_action"], "none")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["attempts"]["generator"], 0)

    def test_run_autonomous_commits_allowlisted_change_then_returns_to_planning_and_stops_no_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")
            run_dir = run_dir_for(repo_root, "demo-run")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(generator_result["status"], "implemented")
            self.assertTrue(generator_result["commit"])
            changed_paths = set(generator_result["changed_paths"])
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", changed_paths)
            self.assertTrue(any(path.startswith("personal-wiki/domains/ai_infra/raw/loop-autonomous/") for path in changed_paths))
            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", committed_files.stdout)
            loop_state = read_json_file(repo_root / "personal-wiki" / "domains" / "ai_infra" / "loop-state.json")
            validate_loop_state_payload(loop_state)
            self.assertEqual(loop_state["last_planner_decision"], "no_action")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "stopped_no_action")
            self.assertEqual(run["attempts"]["planner"], 2)
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["attempts"]["evaluator"], 1)

    def test_run_autonomous_blocks_declared_paths_that_were_dirty_at_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            seed_candidate_loop_state(repo_root, "ai_infra")
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_dirty_paths")
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", dirty_result["baseline_changed_paths"])

    def test_run_autonomous_supports_codex_exec_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_agent_output(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                role = str(kwargs["role"])
                if role == "planner":
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-autonomous-task",
                            "policy": "autonomous_knowledge",
                            "task_kind": "autonomous_implementation_task",
                            "title": "Codex autonomous task",
                            "goal": "Expand wiki",
                            "non_goals": [],
                            "allowed_paths": [
                                "personal-wiki/domains/ai_infra/raw/**",
                                "personal-wiki/domains/ai_infra/loop-state.json",
                            ],
                            "denylist_paths": [],
                            "verify_commands": [],
                            "evaluator_scenarios_path": "",
                            "stop_conditions": ["stopped_no_action", "stopped_budget", "stopped_blocked"],
                            "next_planning_hint": "continue planning",
                        },
                    )
                elif role == "generator":
                    raw_note = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw" / "loop-autonomous" / "codex-task.md"
                    raw_note.parent.mkdir(parents=True, exist_ok=True)
                    raw_note.write_text("# Codex autonomous note\n", encoding="utf-8")
                    seed_no_action_loop_state(repo_root, "ai_infra")
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-autonomous-task",
                            "status": "implemented",
                            "changed_paths": [
                                "personal-wiki/domains/ai_infra/raw/loop-autonomous/codex-task.md",
                                "personal-wiki/domains/ai_infra/loop-state.json",
                            ],
                            "commit": "",
                            "verify_commands": [],
                            "verify_results": ["python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v"],
                            "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/codex-task.md"],
                            "cleanup_required": False,
                            "notes": "autonomous knowledge update without dependency changes",
                        },
                    )
                elif role == "evaluator":
                    write_json_file(
                        output_path,
                        {
                            "status": "pass",
                            "task_id": "codex-autonomous-task",
                            "driver": "codex-exec",
                            "returncode": 0,
                            "stdout": "codex autonomous evaluator pass\n",
                            "stderr": "",
                        },
                    )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": role,
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_agent_output):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="codex-exec",
                    generator_driver="codex-exec",
                    evaluator_driver="codex-exec",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_no_action")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(run["attempts"]["planner"], 2)
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertTrue(generator_result["commit"])

    def test_run_autonomous_retries_generator_failures_until_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            attempts: list[int] = []

            def fail_generator(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "fail",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=fail_generator):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(attempts, [1, 2])
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_generator")
            self.assertEqual(run["attempts"]["generator"], 2)

    def test_run_autonomous_generator_retry_limit_is_per_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "generating"
            run["next_action"] = "run_autonomous_generator"
            run["task_id"] = "demo-run-task-2"
            run["attempts"]["generator"] = 2
            write_json_file(run_dir / "run.json", run)
            attempts: list[int] = []

            def fail_generator(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "fail",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=fail_generator):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(attempts, [3, 4])
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_generator")
            self.assertEqual(run["attempts"]["generator"], 4)

    def test_run_autonomous_resumes_from_evaluating_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator._run_fake_autonomous_evaluator",
                side_effect=RuntimeError("interrupted evaluator"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted evaluator"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            interrupted = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(interrupted["phase"], "evaluating")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_resumes_from_artifact_hygiene_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator.run_artifact_hygiene_step",
                side_effect=RuntimeError("interrupted hygiene"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted hygiene"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            interrupted = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(interrupted["phase"], "artifact_hygiene")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_resumes_from_cleanup_after_commit_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator.run_cleanup",
                side_effect=RuntimeError("interrupted cleanup"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted cleanup"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            run_dir = run_dir_for(repo_root, "demo-run")
            interrupted = read_json_file(run_dir / "run.json")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(interrupted["phase"], "cleanup")
            self.assertTrue(generator_result["commit"])

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_blocks_undeclared_dirty_denylist_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            from scripts import harness_loop_orchestrator as orchestrator

            original_generator = orchestrator._write_fake_autonomous_generator_result

            def write_undeclared_dirty_path(*args: object, **kwargs: object) -> dict[str, object]:
                result = original_generator(*args, **kwargs)
                (repo_root / ".env").write_text("FAKE_SECRET=redacted\n", encoding="utf-8")
                return result

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=write_undeclared_dirty_path,
            ):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_dirty_paths")
            self.assertIn(".env", dirty_result["unexpected_paths"])

    def test_run_autonomous_blocks_and_records_commit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch("scripts.harness_loop_orchestrator.run_git_commit", side_effect=RuntimeError("commit failed")):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_commit")
            self.assertEqual(commit_result["status"], "blocked")
            self.assertIn("commit failed", commit_result["error"])

    def test_run_autonomous_blocks_denylist_changed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake-denylist",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_autonomous_scope")

    def test_run_autonomous_blocks_dependency_change_without_supply_chain_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake-dependency",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_supply_chain")

    def test_run_autonomous_checks_scope_before_supply_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            calls: list[str] = []

            from scripts.harness_loop_autonomous import ScopeCheckResult, SupplyChainCheckResult

            def record_scope(*args: object, **kwargs: object) -> ScopeCheckResult:
                calls.append("scope")
                return ScopeCheckResult(True, ["requirements.txt"], [], [], [])

            def record_supply_chain(*args: object, **kwargs: object) -> SupplyChainCheckResult:
                calls.append("supply_chain")
                return SupplyChainCheckResult(False, ["requirements.txt"], ["missing dependency evidence"])

            with patch("scripts.harness_loop_orchestrator.check_autonomous_scope", side_effect=record_scope):
                with patch("scripts.harness_loop_orchestrator.check_supply_chain", side_effect=record_supply_chain):
                    status = run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake-dependency",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=1,
                    )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(calls, ["scope", "supply_chain"])

    def test_cli_run_autonomous_accepts_fake_drivers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_no_action_loop_state(repo_root, "ai_infra")

            self.assertEqual(
                call_cli(
                    [
                        "run-autonomous",
                        "--repo-root",
                        str(repo_root),
                        "--run-id",
                        "demo-run",
                        "--planner-driver",
                        "fake",
                        "--generator-driver",
                        "fake",
                        "--evaluator-driver",
                        "fake",
                        "--max-eval-attempts",
                        "2",
                        "--max-tasks",
                        "3",
                    ]
                ),
                0,
            )
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["phase"], "stopped_no_action")

    def test_create_preflight_run_accepts_explicit_task_id_for_fake_planner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                task_id="explicit-task",
                confirm=True,
            )

            self.assertEqual(payload["task_id"], "explicit-task")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["task_id"], "explicit-task")

            from scripts.harness_loop_orchestrator import run_planner

            output_path = run_planner(repo_root, "demo-run", driver="fake")
            planner_output = read_json_file(output_path)
            self.assertEqual(planner_output["task_id"], "explicit-task")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "explicit-task")

    def test_cli_preflight_accepts_explicit_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            self.assertEqual(
                call_cli(
                    [
                        "preflight",
                        "--repo-root",
                        str(repo_root),
                        "--mode",
                        "demand-development",
                        "--requirement",
                        "Build through CLI",
                        "--run-id",
                        "demo-run",
                        "--task-id",
                        "explicit-task",
                        "--confirm",
                    ]
                ),
                0,
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "explicit-task")

    def test_cli_preflight_accepts_constraints_and_stop_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            self.assertEqual(
                call_cli(
                    [
                        "preflight",
                        "--repo-root",
                        str(repo_root),
                        "--mode",
                        "demand-development",
                        "--requirement",
                        "Build through CLI",
                        "--run-id",
                        "demo-run",
                        "--constraint",
                        "Only touch scripts/",
                        "--constraint",
                        "No commits",
                        "--stop-condition",
                        "passed_waiting_human_merge",
                        "--stop-condition",
                        "stopped_blocked",
                        "--confirm",
                    ]
                ),
                0,
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["constraints"], ["Only touch scripts/", "No commits"])
            self.assertEqual(run["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])

    def test_status_for_run_returns_run_id_policy_phase_next_action_and_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            status = status_for_run(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(
                status,
                {
                    "run_id": "demo-run",
                    "policy": "demand_development",
                    "phase": "planned",
                    "next_action": "run_planner",
                    "task_id": "",
                },
            )

    def test_fake_planner_writes_valid_planner_output_and_advances_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                constraints=["Keep scope tight"],
                stop_conditions=["passed_waiting_human_merge", "stopped_blocked"],
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_planner

            output_path = run_planner(repo_root, "demo-run", driver="fake")

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "planner-output.json")
            planner_output = read_json_file(output_path)
            validate_planner_output_payload(planner_output)
            self.assertEqual(planner_output["policy"], "demand_development")
            self.assertEqual(planner_output["task_kind"], "registered_task")
            self.assertEqual(planner_output["task_id"], "demo-run-task")
            self.assertEqual(planner_output["goal"], "Build the planner demo")
            self.assertEqual(planner_output["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["task_id"], "demo-run-task")
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")
            self.assertEqual(run["attempts"]["planner"], 1)

    def test_run_planner_rejects_unconfirmed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=False,
            )
            from scripts.harness_loop_orchestrator import run_planner

            with self.assertRaises(RuntimeError):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_run_planner_rejects_already_planned_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_planner

            run_planner(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "generating"):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_run_planner_rejects_after_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "evaluating"):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_codex_exec_planner_sets_run_task_id_from_validated_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_contracts import write_json_file
            from scripts.harness_loop_orchestrator import run_planner

            def write_planner_output(**kwargs: object) -> dict[str, object]:
                write_json_file(
                    kwargs["output_json_path"],
                    {
                        "task_id": "codex-task-id",
                        "policy": "demand_development",
                        "task_kind": "registered_task",
                        "title": "Codex planner task",
                        "goal": "Build with codex planner",
                        "non_goals": [],
                        "allowed_paths": [],
                        "denylist_paths": [],
                        "verify_commands": [],
                        "evaluator_scenarios_path": "",
                        "stop_conditions": ["passed_waiting_human_merge"],
                        "next_planning_hint": "",
                    },
                )
                return {"status": "pass", "run_id": "demo-run", "role": "planner", "attempt": 1}

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_planner_output):
                run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "codex-task-id")

    def test_codex_exec_planner_persists_attempt_before_missing_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_planner

            attempts: list[int] = []

            def do_not_write_planner_output(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "planner",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_planner_output):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_planner_output):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            self.assertEqual(attempts, [1, 2])

    def test_codex_exec_planner_failure_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "planner-output.json",
                {
                    "task_id": "stale-task-id",
                    "policy": "demand_development",
                    "task_kind": "registered_task",
                    "title": "Stale planner task",
                    "goal": "stale",
                    "non_goals": [],
                    "allowed_paths": [],
                    "denylist_paths": [],
                    "verify_commands": [],
                    "evaluator_scenarios_path": "",
                    "stop_conditions": ["passed_waiting_human_merge"],
                    "next_planning_hint": "",
                },
            )
            from scripts.harness_loop_orchestrator import run_planner

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "fail", "run_id": "demo-run", "role": "planner", "attempt": 1},
            ):
                with self.assertRaisesRegex(RuntimeError, "planner codex-exec attempt failed"):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")
            self.assertEqual(run["task_id"], "")

    def test_codex_exec_planner_pass_without_new_output_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "planner-output.json",
                {
                    "task_id": "stale-task-id",
                    "policy": "demand_development",
                    "task_kind": "registered_task",
                    "title": "Stale planner task",
                    "goal": "stale",
                    "non_goals": [],
                    "allowed_paths": [],
                    "denylist_paths": [],
                    "verify_commands": [],
                    "evaluator_scenarios_path": "",
                    "stop_conditions": ["passed_waiting_human_merge"],
                    "next_planning_hint": "",
                },
            )
            from scripts.harness_loop_orchestrator import run_planner

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "pass", "run_id": "demo-run", "role": "planner", "attempt": 1},
            ):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")
            self.assertEqual(run["task_id"], "")

    def test_run_generator_rejects_confirmed_preflight_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator

            with self.assertRaisesRegex(RuntimeError, "planned"):
                run_generator(repo_root, "demo-run", driver="fake")

    def test_fake_generator_writes_valid_generator_result_and_advances_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            output_path = run_generator(repo_root, "demo-run", driver="fake")

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "generator-result.json")
            generator_result = read_json_file(output_path)
            validate_generator_result_payload(generator_result)
            self.assertEqual(generator_result["task_id"], "demo-run-task")
            self.assertEqual(generator_result["status"], "implemented")
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "evaluating")
            self.assertEqual(run["next_action"], "run_evaluator")
            self.assertEqual(run["attempts"]["generator"], 1)

    def test_run_generator_rejects_already_generated_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "evaluating"):
                run_generator(repo_root, "demo-run", driver="fake")

    def test_codex_exec_generator_persists_attempt_before_missing_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            attempts: list[int] = []

            def do_not_write_generator_result(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_generator_result):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_generator_result):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            self.assertEqual(attempts, [1, 2])

    def test_codex_exec_generator_failure_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "stale result",
                },
            )

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "fail", "run_id": "demo-run", "role": "generator", "attempt": 1},
            ):
                with self.assertRaisesRegex(RuntimeError, "generator codex-exec attempt failed"):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

    def test_codex_exec_generator_pass_without_new_output_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "stale result",
                },
            )

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "pass", "run_id": "demo-run", "role": "generator", "attempt": 1},
            ):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

    def test_cli_plan_and_generate_accept_fake_driver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through CLI",
                run_id="demo-run",
                confirm=True,
            )

            self.assertEqual(
                call_cli(["plan", "--repo-root", str(repo_root), "--run-id", "demo-run", "--driver", "fake"]),
                0,
            )
            self.assertEqual(
                call_cli(["generate", "--repo-root", str(repo_root), "--run-id", "demo-run", "--driver", "fake"]),
                0,
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["phase"], "evaluating")
            self.assertEqual(run["next_action"], "run_evaluator")

    def test_fake_evaluator_writes_result_and_waits_for_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "demo-run-task")

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "evaluator-result.json")
            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "pass")
            self.assertEqual(evaluator_result["task_id"], "demo-run-task")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 0)
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["last_result"], "pass")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")
            self.assertNotIn("_post_hygiene_phase", run)
            self.assertEqual(run["attempts"]["evaluator"], 1)

    def test_run_evaluator_runs_scenario_commands_from_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run scenario command",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "contract-task")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('scenario artifact')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Artifact exists."],
                            "failure_signals": ["Artifact missing."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "pass")
            manifest_path = Path(evaluator_result["scenario_command_results_path"])
            self.assertEqual(manifest_path, run_dir / "scenario-command-results.json")
            manifest = read_json_file(manifest_path)
            self.assertEqual(manifest["status"], "pass")
            stdout_path = Path(manifest["results"][0]["stdout_path"])
            self.assertIn("scenario artifact", stdout_path.read_text(encoding="utf-8"))

    def test_run_evaluator_uses_task_contract_as_only_scenario_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run contract-only scenario",
                run_id="demo-run",
                task_id="contract-only-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-only-task",
                    "title": "Contract-only task",
                    "description": "Temporary contract task with no registered scenario file.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('contract only')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-ONLY-01",
                            "user_goal": "Use task contract scenarios.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Contract scenario passes."],
                            "failure_signals": ["Evaluator ignores task contract."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "pass")
            task_root = repo_root / ".codex" / "evaluations" / "tasks" / "contract-only-task"
            input_payload = read_json_file(task_root / "fake-attempt-2" / "input.json")
            self.assertEqual(input_payload["scenario_source"], str(run_dir / "task-contract.json"))
            self.assertEqual(input_payload["user_scenarios"][0]["scenario_id"], "CONTRACT-ONLY-01")

    def test_run_evaluator_fails_when_task_contract_scenario_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run failing scenario command",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "contract-task")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"raise SystemExit(7)\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Artifact exists."],
                            "failure_signals": ["Artifact missing."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "fail")
            self.assertNotEqual(evaluator_result["returncode"], 0)
            manifest_path = Path(evaluator_result["scenario_command_results_path"])
            self.assertEqual(manifest_path, run_dir / "scenario-command-results.json")
            manifest = read_json_file(manifest_path)
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["results"][0]["status"], "fail")
            self.assertEqual(manifest["results"][0]["exit_code"], 7)
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "artifact_hygiene")
            self.assertEqual(run["last_result"], "fail")
            self.assertEqual(run["next_action"], "run_artifact_hygiene")

    def test_codex_exec_evaluator_passes_task_contract_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run codex evaluator with task contract",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": [],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Use task contract scenarios.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Contract scenario passes."],
                            "failure_signals": ["Evaluator ignores task contract."],
                        }
                    ],
                },
            )
            completed = subprocess.CompletedProcess(
                args=["codex-evaluator"],
                returncode=0,
                stdout="codex evaluator stdout",
                stderr="",
            )

            with patch("scripts.harness_loop_orchestrator.subprocess.run", return_value=completed) as run_mock:
                run_evaluator(repo_root, "demo-run", driver="codex-exec", max_attempts=2)

            command = run_mock.call_args.args[0]
            self.assertIn("--task-contract", command)
            self.assertIn(str(run_dir / "task-contract.json"), command)

    def test_fake_evaluator_preserves_blocked_result_when_scenarios_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "blocked")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 1)
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "repair_needed")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "repair_from_evaluator_findings")

    def test_fake_evaluator_writes_synthetic_result_when_no_result_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            completed = subprocess.CompletedProcess(
                args=["fake-evaluator"],
                returncode=1,
                stdout="fake stdout",
                stderr="fake stderr",
            )

            with patch("scripts.harness_loop_orchestrator.subprocess.run", return_value=completed):
                output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "fail")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 1)
            self.assertEqual(evaluator_result["stdout"], "fake stdout")
            self.assertEqual(evaluator_result["stderr"], "fake stderr")
            self.assertEqual(evaluator_result["task_id"], "demo-run-task")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "repair_needed")
            self.assertEqual(run["last_result"], "fail")

    def test_run_loop_rejects_unconfirmed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=False,
            )
            from scripts.harness_loop_orchestrator import run_loop

            with self.assertRaisesRegex(RuntimeError, "preflight"):
                run_loop(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                )

    def test_run_loop_plans_generates_and_evaluates_from_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "demo-run-task")
            from scripts.harness_loop_orchestrator import run_loop

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            self.assertEqual(status["next_action"], "await_human_merge_confirmation")
            self.assertEqual(status["task_id"], "demo-run-task")

    def test_cli_accepts_artifact_hygiene_and_cleanup_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "CLI hygiene", "demo-run", confirm=True)
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("public artifact\n", encoding="utf-8")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": ["artifact.txt"],
                    "cleanup_required": False,
                    "notes": "needs hygiene",
                },
            )
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            run["next_action"] = "run_artifact_hygiene"
            write_json_file(run_dir / "run.json", run)

            self.assertEqual(
                call_cli(["artifact-hygiene", "--repo-root", str(repo_root), "--run-id", "demo-run"]),
                0,
            )
            self.assertEqual(
                call_cli(["cleanup", "--repo-root", str(repo_root), "--run-id", "demo-run"]),
                0,
            )

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")

    def test_run_loop_runs_hygiene_and_cleanup_after_evaluator_when_generator_has_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through hygiene loop",
                run_id="demo-run",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "demo-run-task")
            from scripts.harness_loop_orchestrator import run_generator, run_loop, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            generator_path = run_generator(repo_root, "demo-run", driver="fake")
            generator_result = read_json_file(generator_path)
            generator_result["artifacts"] = ["artifact.txt"]
            write_json_file(generator_path, generator_result)
            (repo_root / "artifact.txt").write_text("public artifact\n", encoding="utf-8")

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            self.assertEqual(status["next_action"], "await_human_merge_confirmation")
            self.assertTrue((run_dir / "artifact-manifest.json").exists())
            self.assertTrue((run_dir / "cleanup-result.json").exists())

    def test_run_loop_hygiene_redacts_scenario_command_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import run_generator, run_loop, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            generator_path = run_generator(repo_root, "demo-run", driver="fake")
            generator_result = read_json_file(generator_path)
            generator_result["artifacts"] = ["artifact.txt"]
            write_json_file(generator_path, generator_result)
            (repo_root / "artifact.txt").write_text("public artifact\n", encoding="utf-8")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            artifact_manifest = read_json_file(run_dir / "artifact-manifest.json")
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log",
                artifact_manifest["scanned_paths"],
            )
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted",
                artifact_manifest["redacted_paths"],
            )

    def test_run_loop_hygiene_runs_for_scenario_command_logs_without_generator_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through scenario-only hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import run_generator, run_loop, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            artifact_manifest = read_json_file(run_dir / "artifact-manifest.json")
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log",
                artifact_manifest["scanned_paths"],
            )
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted",
                artifact_manifest["redacted_paths"],
            )
            redacted_log = repo_root / ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted"
            self.assertNotIn("Authorization: Bearer secret-token", redacted_log.read_text(encoding="utf-8"))

    def test_run_evaluator_failing_scenario_commands_enter_artifact_hygiene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Fail through scenario-only hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token'); raise SystemExit(7)\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted before repair."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "fail")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "artifact_hygiene")
            self.assertEqual(run["last_result"], "fail")
            self.assertEqual(run["next_action"], "run_artifact_hygiene")

    def test_run_loop_rejects_unsupported_active_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_contracts import write_json_file
            from scripts.harness_loop_orchestrator import run_loop

            run_path = run_dir_for(repo_root, "demo-run") / "run.json"
            run = read_json_file(run_path)
            run["phase"] = "verifying"
            write_json_file(run_path, run)

            with self.assertRaisesRegex(RuntimeError, "unsupported.*verifying"):
                run_loop(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                )

    def test_run_artifact_hygiene_blocks_large_artifacts_and_records_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Hygiene", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            large_path = repo_root / "large.bin"
            large_path.write_bytes(b"x" * 20)
            generator_result = {
                "task_id": "demo-run-task",
                "status": "implemented",
                "changed_paths": [],
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": ["large.bin"],
                "cleanup_required": False,
                "notes": "needs hygiene",
            }
            write_json_file(run_dir / "generator-result.json", generator_result)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_artifact_hygiene_step

            result_path = run_artifact_hygiene_step(repo_root, "demo-run", max_file_bytes=10)

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "blocked")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "stopped_blocked")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_artifact_hygiene")

    def test_run_cleanup_records_removed_worktree_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(temp_worktree)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            run = read_json_file(run_dir / "run.json")
            self.assertIn(str(temp_worktree), run["cleanup"]["worktrees_removed"])
            self.assertEqual(run["phase"], "passed_waiting_human_merge")

    def test_run_cleanup_records_removed_relative_worktree_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [".worktrees/demo-run-attempt-1"]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            self.assertIn(".worktrees/demo-run-attempt-1", result["worktrees_removed"])

    def test_run_cleanup_accepts_absolute_retained_path_with_relative_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(temp_worktree)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            current_dir = Path.cwd()
            os.chdir(repo_root)
            try:
                result_path = run_cleanup(Path("."), "demo-run").resolve()
            finally:
                os.chdir(current_dir)

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            run = read_json_file(run_dir / "run.json")
            self.assertIn(str(temp_worktree), run["cleanup"]["worktrees_removed"])

    def test_run_cleanup_refuses_outside_worktrees_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            victim = parent / "outside" / ".worktrees" / "victim"
            victim.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(victim)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(victim.exists())
            self.assertNotIn(str(victim), result["worktrees_removed"])
            run = read_json_file(run_dir / "run.json")
            self.assertNotIn(str(victim), run["cleanup"]["worktrees_removed"])

    def test_run_cleanup_skips_absolute_symlink_retained_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            real_worktree = repo_root / ".worktrees" / "real"
            real_worktree.mkdir(parents=True)
            symlink_path = repo_root / ".worktrees" / "link"
            symlink_path.symlink_to(real_worktree, target_is_directory=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(symlink_path)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(symlink_path.is_symlink())
            self.assertTrue(real_worktree.exists())
            self.assertNotIn(str(symlink_path), result["worktrees_removed"])

    def test_run_cleanup_skips_relative_symlink_retained_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            real_worktree = repo_root / ".worktrees" / "real"
            real_worktree.mkdir(parents=True)
            symlink_path = repo_root / ".worktrees" / "link"
            symlink_path.symlink_to(real_worktree, target_is_directory=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [".worktrees/link"]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(symlink_path.is_symlink())
            self.assertTrue(real_worktree.exists())
            self.assertNotIn(".worktrees/link", result["worktrees_removed"])

    def test_run_cleanup_skips_when_worktrees_root_is_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            outside_worktrees = parent / "outside-worktrees"
            repo_root.mkdir()
            outside_worktrees.mkdir()
            (repo_root / ".worktrees").symlink_to(outside_worktrees)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            victim = repo_root / ".worktrees" / "victim"
            victim.mkdir()
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(victim)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue((outside_worktrees / "victim").exists())
            self.assertNotIn(str(victim), result["worktrees_removed"])
            run = read_json_file(run_dir / "run.json")
            self.assertNotIn(str(victim), run["cleanup"]["worktrees_removed"])

    def test_phase_1_scenario_entrypoint_passes_self_contained_task_id(self) -> None:
        scenario_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "planner-generator-evaluator-loop-phase-1-01.json"
        )

        scenario = read_json_file(scenario_path)
        entrypoint = scenario["user_scenarios"][0]["entrypoint"]
        self.assertIn("--task-id planner-generator-evaluator-loop-phase-1-01", entrypoint)

    def test_phase_2_smoke_helper_exercises_contract_hygiene_cleanup(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        run_id = "evaluator-scenario-phase-2-test"
        task_id = "planner-generator-evaluator-loop-phase-2-01"
        run_dir = run_dir_for(repo_root, run_id)
        smoke_artifact = repo_root / ".codex" / "tmp" / "phase-2-smoke-artifact.txt"
        eval_dir = repo_root / ".codex" / "evaluations" / "tasks" / task_id
        shutil.rmtree(run_dir, ignore_errors=True)
        remove_fake_evaluator_attempts(eval_dir)
        smoke_artifact.unlink(missing_ok=True)
        try:
            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_loop_phase2_smoke.py",
                    "--repo-root",
                    str(repo_root),
                    "--run-id",
                    run_id,
                    "--task-id",
                    task_id,
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")
            self.assertTrue((run_dir / "scenario-command-results.json").exists())
            self.assertTrue((run_dir / "artifact-manifest.json").exists())
            self.assertTrue((run_dir / "cleanup-result.json").exists())
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)
            remove_fake_evaluator_attempts(eval_dir)
            smoke_artifact.unlink(missing_ok=True)
            remove_empty_directory(repo_root / ".codex" / "loop-runs")
            remove_empty_directory(repo_root / ".codex" / "tmp")

    def test_phase_2_scenario_entrypoint_uses_smoke_helper(self) -> None:
        scenario_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "planner-generator-evaluator-loop-phase-2-01.json"
        )

        scenario = read_json_file(scenario_path)
        entrypoint = scenario["user_scenarios"][0]["entrypoint"]
        self.assertIn("scripts/harness_loop_phase2_smoke.py", entrypoint)
        self.assertIn("--run-id evaluator-scenario-phase-2", entrypoint)
        self.assertIn("--task-id planner-generator-evaluator-loop-phase-2-01", entrypoint)

    def test_phase_2_smoke_helper_rejects_path_traversal_ids_before_cleanup(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        from scripts.harness_loop_phase2_smoke import run_phase2_smoke

        with self.assertRaisesRegex(ValueError, "run_id"):
            run_phase2_smoke(repo_root, "../../docs", "planner-generator-evaluator-loop-phase-2-01")

        with self.assertRaisesRegex(ValueError, "task_id"):
            run_phase2_smoke(repo_root, "safe-run-id", "../planner-generator-evaluator-loop-phase-2-01")


class HarnessLoopDemandMultiTaskTests(unittest.TestCase):
    def _create_parent(self, repo_root: Path, run_id: str = "parent-run") -> dict[str, object]:
        payload = create_preflight_run(
            repo_root=repo_root,
            mode="demand-development",
            requirement="Build multi child feature",
            run_id=run_id,
            confirm=True,
        )
        payload["run_kind"] = "parent"
        payload["phase"] = "planning"
        payload["next_action"] = "run_parent_planner"
        payload["child_run_ids"] = []
        payload["current_child_run_id"] = ""
        payload["backlog"] = []
        payload["aggregate_acceptance"] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "pending": 0,
            "user_decision_required": False,
        }
        payload["reader_summary"] = {
            "purpose": "Build multi child feature",
            "current_progress": "Planning",
            "next_step": "Create first child",
            "decision_needed": "No",
        }
        payload["accepted_changed_paths"] = []
        write_json_file(run_dir_for(repo_root, run_id) / "run.json", payload)
        return payload

    def test_run_demand_multi_fake_completes_three_children_and_waits_for_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "parent-run") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent["child_run_ids"]), 3)
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(parent["aggregate_acceptance"]["pending"], 0)
            self.assertTrue(parent["accepted_changed_paths"])
            self.assertFalse((repo_root / ".git" / "MERGE_HEAD").exists())
            for child_run_id in parent["child_run_ids"]:
                child = read_json_file(run_dir_for(repo_root, child_run_id) / "run.json")
                self.assertEqual(child["run_kind"], "child")
                self.assertEqual(child["phase"], "passed")
                self.assertEqual(child["parent_run_id"], "parent-run")

    def test_run_demand_multi_repairs_same_failed_child_before_next_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "repair-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="repair-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "repair-parent") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(len(parent["child_run_ids"]), 3)
            child2 = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][1]) / "run.json")
            self.assertEqual(child2["phase"], "passed")
            events = (run_dir_for(repo_root, child2["run_id"]) / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("repair", events)

    def test_run_demand_multi_blocks_when_child_repair_attempts_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "exhausted-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="exhausted-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=1,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "exhausted-parent") / "run.json")
            child2 = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][1]) / "run.json")
            child2_events = (run_dir_for(repo_root, child2["run_id"]) / "events.jsonl").read_text(encoding="utf-8")
            parent_events = (run_dir_for(repo_root, "exhausted-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["phase"], "stopped_blocked")
            self.assertEqual(parent["last_result"], "blocked")
            self.assertTrue(parent["aggregate_acceptance"]["user_decision_required"])
            self.assertNotEqual(child2["phase"], "passed")
            self.assertEqual(child2["last_result"], "fail")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 1)
            self.assertIn("Evaluator failed child", child2_events)
            self.assertIn("max attempts exhausted", parent_events)

    def test_run_demand_multi_terminal_rerun_returns_status_without_new_children(self) -> None:
        for run_id, expected_phase, planner_driver, max_children in [
            ("terminal-blocked", "stopped_blocked", "fake-blocked", 3),
            ("terminal-passed", "passed_waiting_human_merge", "fake", 2),
        ]:
            with self.subTest(run_id=run_id), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, run_id)
                run_demand_multi(
                    repo_root=repo_root,
                    run_id=run_id,
                    planner_driver=planner_driver,
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=max_children,
                )
                parent_before = read_json_file(run_dir_for(repo_root, run_id) / "run.json")
                child_ids_before = list(parent_before["child_run_ids"])
                aggregate_before = dict(parent_before["aggregate_acceptance"])

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=run_id,
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=max_children,
                )

                parent_after = read_json_file(run_dir_for(repo_root, run_id) / "run.json")
                self.assertEqual(payload["phase"], expected_phase)
                self.assertEqual(parent_after["phase"], expected_phase)
                self.assertEqual(parent_after["child_run_ids"], child_ids_before)
                self.assertEqual(parent_after["aggregate_acceptance"], aggregate_before)

    def test_run_demand_multi_rejects_child_run_id_without_nested_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "child-reject-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="child-reject-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            parent = read_json_file(run_dir_for(repo_root, "child-reject-parent") / "run.json")
            child_run_id = parent["child_run_ids"][0]

            with self.assertRaisesRegex((RuntimeError, ValueError), "parent"):
                run_demand_multi(
                    repo_root=repo_root,
                    run_id=child_run_id,
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=2,
                )

            nested_child_run_id = f"{child_run_id}-child-001"
            self.assertFalse(run_dir_for(repo_root, nested_child_run_id).exists())

    def test_run_demand_multi_planner_blocked_or_failed_creates_no_child(self) -> None:
        for planner_driver, expected_reason in [
            ("fake-blocked", "fake planner blocked"),
            ("fake-failed", "fake planner failed"),
        ]:
            with self.subTest(planner_driver=planner_driver), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, f"{planner_driver}-parent")

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=f"{planner_driver}-parent",
                    planner_driver=planner_driver,
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=3,
                )

                parent = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "run.json")
                planner_output = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "planner-output.json")
                self.assertEqual(payload["phase"], "stopped_blocked")
                self.assertEqual(parent["child_run_ids"], [])
                self.assertEqual(planner_output["blocked_reason"], expected_reason)

    def test_run_demand_multi_writes_child_task_contract_and_stops_on_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "budget-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="budget-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=0,
            )

            parent = read_json_file(run_dir_for(repo_root, "budget-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_budget")
            self.assertEqual(parent["child_run_ids"], [])

            self._create_parent(repo_root, "contract-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="contract-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            contract_parent = read_json_file(run_dir_for(repo_root, "contract-parent") / "run.json")
            child_run_id = contract_parent["child_run_ids"][0]
            task_contract = read_json_file(run_dir_for(repo_root, child_run_id) / "task-contract.json")
            self.assertEqual(task_contract["task_id"], f"{child_run_id}-task")
            self.assertEqual(task_contract["evaluator_driver"], "harness_auto_gate")
            self.assertTrue(task_contract["must_simulate"])


if __name__ == "__main__":
    unittest.main()
