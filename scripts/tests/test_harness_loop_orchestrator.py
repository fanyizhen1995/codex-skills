import tempfile
import unittest
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_contracts import (
    read_json_file,
    run_dir_for,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_run_payload,
)
from scripts.harness_loop_orchestrator import (
    confirm_preflight,
    create_preflight_run,
    main,
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
            preflight = preflight_path.read_text(encoding="utf-8")
            self.assertIn("Build the thing", preflight)
            self.assertIn("Fallback Questionnaire", preflight)

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

    def test_create_preflight_run_rejects_autonomous_knowledge_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "demand_development"):
                create_preflight_run(
                    repo_root=repo_root,
                    mode="autonomous-knowledge",
                    requirement="Crawl knowledge",
                    run_id="demo-run",
                    confirm=True,
                )

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
                main(
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

            def write_planner_output(**kwargs: object) -> None:
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

            def do_not_write_planner_output(**kwargs: object) -> None:
                attempts.append(int(kwargs["attempt"]))

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

            def do_not_write_generator_result(**kwargs: object) -> None:
                attempts.append(int(kwargs["attempt"]))

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
                main(["plan", "--repo-root", str(repo_root), "--run-id", "demo-run", "--driver", "fake"]),
                0,
            )
            self.assertEqual(
                main(["generate", "--repo-root", str(repo_root), "--run-id", "demo-run", "--driver", "fake"]),
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
            self.assertEqual(evaluator_result["status"], "pass")
            self.assertEqual(evaluator_result["task_id"], "demo-run-task")
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["last_result"], "pass")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")
            self.assertEqual(run["attempts"]["evaluator"], 1)

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
            self.assertEqual(evaluator_result["status"], "blocked")
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


if __name__ == "__main__":
    unittest.main()
