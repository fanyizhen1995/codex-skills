# Planner Generator Evaluator Loop Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the Phase 1 demand-development loop with task-contract evaluator input, scenario command artifacts, retry evidence, cleanup/recovery, and artifact hygiene.

**Architecture:** Extend the existing loop layer instead of replacing it. `scripts/harness_loop_contracts.py` owns new contracts, `scripts/harness_evaluator_cli.py` owns task-contract bundle preparation, `scripts/harness_loop_artifacts.py` owns scenario command and redaction utilities, and `scripts/harness_loop_orchestrator.py` coordinates phase transitions and cleanup. Phase 2 still runs `demand_development`; `autonomous_knowledge` remains Phase 3.

**Tech Stack:** Python 3 standard library, `unittest`, existing evaluator harness, existing loop CLI, git subprocess commands.

---

## File Structure

- Modify `scripts/harness_loop_contracts.py`: validators for `task-contract.json`, `artifact-hygiene-result.json`, scenario command results, and cleanup result shape.
- Create `scripts/harness_loop_artifacts.py`: run scenario commands, collect stdout/stderr/exit code evidence, scan artifacts for size and sensitive text, write redaction manifests.
- Modify `scripts/harness_evaluator_cli.py`: support `prepare-task --task-contract <path>` and include `scenario_commands`, `artifact_paths`, `required_services`, and contract metadata in evaluator bundle `input.json`.
- Modify `scripts/harness_loop_orchestrator.py`: add task-contract creation/use, repair retry loop, artifact hygiene phase, cleanup phase, and resumable `run` behavior.
- Modify `scripts/tests/test_harness_loop_contracts.py`: contract validator coverage.
- Create `scripts/tests/test_harness_loop_artifacts.py`: scenario command and artifact hygiene unit tests.
- Modify `scripts/tests/test_harness_evaluator_cli.py` or create it if absent: `task-contract.json` bundle preparation tests.
- Modify `scripts/tests/test_harness_loop_orchestrator.py`: Phase 2 state transition, retry, cleanup, and hygiene tests.
- Modify `docs/harness/planner-generator-evaluator-loop.md`: Phase 2 operator commands and artifact rules.
- Modify `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json`: user-facing evaluator scenario for Phase 2.
- Modify `tasks.json` and `progress.md`: mark Phase 2 complete after implementation.

## Task 1: Add Phase 2 Contracts

**Files:**
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`

- [x] **Step 1: Write failing tests for task-contract validation**

Add these imports in `scripts/tests/test_harness_loop_contracts.py`:

```python
from scripts.harness_loop_contracts import (
    default_limits,
    normalize_policy_id,
    read_json_file,
    run_dir_for,
    validate_agent_attempt_payload,
    validate_artifact_hygiene_result_payload,
    validate_evaluator_result_payload,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_scenario_command_result_payload,
    validate_task_contract_payload,
    validate_run_payload,
    write_json_file,
)
```

Add helper and tests near the existing payload helpers:

```python
    def _task_contract_payload(self) -> dict:
        return {
            "task_id": "phase-2-task",
            "title": "Phase 2 task",
            "description": "Exercise task contract bundle preparation.",
            "verify_commands": ["python3 -m unittest scripts.tests.test_harness_loop_contracts -v"],
            "scenario_commands": ["python3 -c \"print('scenario-ok')\""],
            "artifact_paths": ["docs/harness/planner-generator-evaluator-loop.md"],
            "required_services": ["crawler_workbench_backend"],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "PGE-PHASE2-TASK-CONTRACT",
                    "user_goal": "Prepare an evaluator bundle from a temporary task contract.",
                    "prerequisites": ["Temporary task contract exists."],
                    "steps": ["Run prepare-task with --task-contract."],
                    "expected_outcomes": ["input.json includes scenario commands."],
                    "failure_signals": ["Bundle ignores task contract fields."],
                }
            ],
        }

    def test_validate_task_contract_payload_accepts_phase_2_shape(self) -> None:
        validate_task_contract_payload(self._task_contract_payload())

    def test_validate_task_contract_payload_rejects_missing_scenario_commands(self) -> None:
        payload = self._task_contract_payload()
        del payload["scenario_commands"]
        with self.assertRaisesRegex(ValueError, "scenario_commands"):
            validate_task_contract_payload(payload)

    def test_validate_task_contract_payload_rejects_non_list_required_services(self) -> None:
        payload = self._task_contract_payload()
        payload["required_services"] = "backend"
        with self.assertRaisesRegex(ValueError, "required_services"):
            validate_task_contract_payload(payload)
```

- [x] **Step 2: Write failing tests for scenario command result and hygiene contracts**

Add:

```python
    def test_validate_scenario_command_result_payload_accepts_command_evidence(self) -> None:
        validate_scenario_command_result_payload(
            {
                "command": "python3 -c \"print('ok')\"",
                "cwd": "/tmp/repo",
                "exit_code": 0,
                "stdout_path": ".codex/loop-runs/demo/scenario-commands/command-1.stdout.log",
                "stderr_path": ".codex/loop-runs/demo/scenario-commands/command-1.stderr.log",
                "duration_seconds": 0,
                "status": "pass",
            }
        )

    def test_validate_scenario_command_result_payload_rejects_unknown_status(self) -> None:
        payload = {
            "command": "python3 -c \"print('ok')\"",
            "cwd": "/tmp/repo",
            "exit_code": 0,
            "stdout_path": "stdout.log",
            "stderr_path": "stderr.log",
            "duration_seconds": 0,
            "status": "success",
        }
        with self.assertRaisesRegex(ValueError, "status"):
            validate_scenario_command_result_payload(payload)

    def test_validate_artifact_hygiene_result_payload_accepts_redaction_manifest(self) -> None:
        validate_artifact_hygiene_result_payload(
            {
                "status": "redacted",
                "scanned_paths": ["artifact.txt"],
                "redacted_paths": ["artifact.redacted.txt"],
                "omitted_paths": [],
                "manifest_path": ".codex/loop-runs/demo/artifact-manifest.json",
                "redaction_manifest_path": ".codex/loop-runs/demo/redaction-manifest.json",
                "original_hashes": {"artifact.txt": "abc123"},
                "redaction_map": [{"path": "artifact.txt", "rule_id": "token", "replacement": "[REDACTED]"}],
                "findings": [{"path": "artifact.txt", "severity": "warning", "message": "token redacted"}],
            }
        )
```

- [x] **Step 3: Run contract tests to verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
```

Expected: fail with imports or missing validator functions.

- [x] **Step 4: Implement Phase 2 validators**

In `scripts/harness_loop_contracts.py`, add constants after `ALLOWED_LAST_RESULTS`:

```python
ALLOWED_SCENARIO_COMMAND_STATUSES = frozenset({"pass", "fail", "timeout"})
ALLOWED_ARTIFACT_HYGIENE_STATUSES = frozenset({"pass", "redacted", "blocked"})
```

Add validator functions after `validate_evaluator_result_payload`:

```python
def validate_task_contract_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "task contract payload")
    _require_keys(
        payload,
        {
            "task_id",
            "title",
            "description",
            "verify_commands",
            "scenario_commands",
            "artifact_paths",
            "required_services",
            "evaluator_driver",
            "eval_policy",
            "allowed_scope",
            "must_simulate",
            "user_scenarios",
        },
        "task contract payload",
    )
    for key in ("task_id", "title", "description", "evaluator_driver", "allowed_scope"):
        _require_string(payload, key)
    for key in ("verify_commands", "scenario_commands", "artifact_paths", "required_services", "user_scenarios"):
        _require_list(payload, key)
    _require_object(payload["eval_policy"], "eval_policy")
    _require_bool(payload, "must_simulate")


def validate_scenario_command_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "scenario command result payload")
    _require_keys(
        payload,
        {
            "command",
            "cwd",
            "exit_code",
            "stdout_path",
            "stderr_path",
            "duration_seconds",
            "status",
        },
        "scenario command result payload",
    )
    for key in ("command", "cwd", "stdout_path", "stderr_path"):
        _require_string(payload, key)
    _require_int(payload, "exit_code")
    _require_int(payload, "duration_seconds")
    _require_enum(payload, "status", ALLOWED_SCENARIO_COMMAND_STATUSES)


def validate_artifact_hygiene_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "artifact hygiene result payload")
    _require_keys(
        payload,
        {
            "status",
            "scanned_paths",
            "redacted_paths",
            "omitted_paths",
            "manifest_path",
            "redaction_manifest_path",
            "original_hashes",
            "redaction_map",
            "findings",
        },
        "artifact hygiene result payload",
    )
    _require_enum(payload, "status", ALLOWED_ARTIFACT_HYGIENE_STATUSES)
    for key in ("scanned_paths", "redacted_paths", "omitted_paths", "redaction_map", "findings"):
        _require_list(payload, key)
    for key in ("manifest_path", "redaction_manifest_path"):
        _require_string(payload, key)
    _require_object(payload["original_hashes"], "original_hashes")
```

- [x] **Step 5: Run tests and commit**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
```

Expected: all contract tests pass.

Commit:

```bash
git add scripts/harness_loop_contracts.py scripts/tests/test_harness_loop_contracts.py
git commit -m "feat(harness): add loop phase 2 contracts"
```

## Task 2: Add Task Contract Support To Evaluator CLI

**Files:**
- Modify: `scripts/harness_evaluator_cli.py`
- Create or modify: `scripts/tests/test_harness_evaluator_cli.py`

- [x] **Step 1: Write failing evaluator CLI tests**

If `scripts/tests/test_harness_evaluator_cli.py` does not exist, create it:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_evaluator_cli import create_task_bundle, main


class HarnessEvaluatorCliTests(unittest.TestCase):
    def _task_contract(self) -> dict:
        return {
            "task_id": "contract-task",
            "title": "Contract task",
            "description": "Temporary contract task.",
            "verify_commands": ["python3 -m json.tool tasks.json"],
            "scenario_commands": ["python3 -c \"print('scenario-ok')\""],
            "artifact_paths": ["tasks.json"],
            "required_services": ["backend"],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "CONTRACT-01",
                    "user_goal": "Use task contract.",
                    "prerequisites": ["Task contract exists."],
                    "steps": ["Prepare bundle."],
                    "expected_outcomes": ["input.json includes contract data."],
                    "failure_signals": ["input.json omits contract data."],
                }
            ],
        }

    def test_create_task_bundle_accepts_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            contract_path = repo_root / "task-contract.json"
            contract_path.write_text(json.dumps(self._task_contract()), encoding="utf-8")

            bundle_dir = create_task_bundle(repo_root, "ignored-task", 1, task_contract_path=contract_path)

            input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(input_payload["task_id"], "contract-task")
            self.assertEqual(input_payload["verify_commands"], ["python3 -m json.tool tasks.json"])
            self.assertEqual(input_payload["scenario_commands"], ["python3 -c \"print('scenario-ok')\""])
            self.assertEqual(input_payload["artifact_paths"], ["tasks.json"])
            self.assertEqual(input_payload["required_services"], ["backend"])
            self.assertEqual(input_payload["allowed_scope"], "local_repo_and_harness")
            self.assertEqual(input_payload["scenario_source"], str(contract_path))

    def test_prepare_task_cli_accepts_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            contract_path = repo_root / "task-contract.json"
            contract_path.write_text(json.dumps(self._task_contract()), encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "prepare-task",
                        "--repo-root",
                        str(repo_root),
                        "--task-id",
                        "ignored-task",
                        "--attempt",
                        "1",
                        "--task-contract",
                        str(contract_path),
                    ]
                ),
                0,
            )
            bundles = list((repo_root / ".codex" / "evaluations" / "tasks" / "contract-task").glob("*-attempt-1"))
            self.assertEqual(len(bundles), 1)
```

- [x] **Step 2: Run evaluator CLI tests to verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_evaluator_cli -v
```

Expected: fail because `create_task_bundle` and CLI do not accept `task_contract_path`.

- [x] **Step 3: Implement task contract input**

In `scripts/harness_evaluator_cli.py`, import validators:

```python
try:
    from scripts.harness_loop_contracts import read_json_file, validate_task_contract_payload
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import read_json_file, validate_task_contract_payload
```

Change `create_task_bundle` signature:

```python
def create_task_bundle(
    repo_root: Path,
    task_id: str,
    attempt: int,
    *,
    bundle_name: str | None = None,
    task_contract_path: Path | None = None,
) -> Path:
```

At the start of `create_task_bundle`, branch on `task_contract_path`:

```python
    if task_contract_path is not None:
        contract = read_json_file(task_contract_path)
        validate_task_contract_payload(contract)
        task_id = str(contract["task_id"])
        scenario_contract = {
            "must_simulate": contract["must_simulate"],
            "source": str(task_contract_path),
            "user_scenarios": contract["user_scenarios"],
        }
        verify_commands = list(contract["verify_commands"])
        artifact_paths = list(contract["artifact_paths"])
        allowed_scope = str(contract["allowed_scope"])
        scenario_commands = list(contract["scenario_commands"])
        required_services = list(contract["required_services"])
        evaluator_driver = str(contract["evaluator_driver"])
        eval_policy = dict(contract["eval_policy"])
    else:
        scenario_contract = load_task_scenarios(repo_root, task_id)
        verify_commands = _verify_commands(repo_root, task_id)
        artifact_paths = []
        allowed_scope = _effective_task_scope(repo_root, task_id)
        scenario_commands = []
        required_services = []
        evaluator_driver = ""
        eval_policy = resolve_task_eval_policy(repo_root, task_id)
```

Include the new fields in `input_payload`:

```python
        "verify_commands": verify_commands,
        "artifact_paths": artifact_paths,
        "allowed_scope": allowed_scope,
        "scenario_commands": scenario_commands,
        "required_services": required_services,
        "evaluator_driver": evaluator_driver,
        "eval_policy": eval_policy,
```

Update `prepare_task`:

```python
    task_contract_path = Path(args.task_contract) if args.task_contract else None
    bundle_dir = create_task_bundle(repo_root, args.task_id, args.attempt, task_contract_path=task_contract_path)
```

Add parser arg:

```python
    prepare_task_parser.add_argument("--task-contract", default="")
```

- [x] **Step 4: Run tests and commit**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_evaluator_cli -v
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
```

Expected: evaluator CLI and scenario tests pass.

Commit:

```bash
git add scripts/harness_evaluator_cli.py scripts/tests/test_harness_evaluator_cli.py
git commit -m "feat(harness): support evaluator task contracts"
```

## Task 3: Add Scenario Command Artifact Collection

**Files:**
- Create: `scripts/harness_loop_artifacts.py`
- Create: `scripts/tests/test_harness_loop_artifacts.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [x] **Step 1: Write failing artifact helper tests**

Create `scripts/tests/test_harness_loop_artifacts.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_loop_artifacts import run_scenario_commands


class HarnessLoopArtifactsTests(unittest.TestCase):
    def test_run_scenario_commands_writes_stdout_stderr_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            manifest_path = run_scenario_commands(
                repo_root=repo_root,
                run_dir=run_dir,
                commands=[
                    "python3 -c \"import sys; print('out'); print('err', file=sys.stderr)\"",
                ],
                timeout_seconds=30,
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(len(manifest["results"]), 1)
            result = manifest["results"][0]
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["exit_code"], 0)
            self.assertIn("out", Path(result["stdout_path"]).read_text(encoding="utf-8"))
            self.assertIn("err", Path(result["stderr_path"]).read_text(encoding="utf-8"))

    def test_run_scenario_commands_marks_failed_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            manifest_path = run_scenario_commands(
                repo_root=repo_root,
                run_dir=run_dir,
                commands=["python3 -c \"raise SystemExit(2)\""],
                timeout_seconds=30,
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["results"][0]["exit_code"], 2)
```

- [x] **Step 2: Run artifact helper tests to verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_artifacts -v
```

Expected: fail because module does not exist.

- [x] **Step 3: Implement `run_scenario_commands`**

Create `scripts/harness_loop_artifacts.py`:

```python
#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path

try:
    from scripts.harness_loop_contracts import validate_scenario_command_result_payload, write_json_file
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import validate_scenario_command_result_payload, write_json_file


def run_scenario_commands(
    repo_root: Path,
    run_dir: Path,
    commands: list[str],
    timeout_seconds: int,
) -> Path:
    evidence_dir = run_dir / "scenario-commands"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, command in enumerate(commands, start=1):
        stdout_path = evidence_dir / f"command-{index}.stdout.log"
        stderr_path = evidence_dir / f"command-{index}.stderr.log"
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=repo_root,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
            status = "pass" if exit_code == 0 else "fail"
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = _decode_timeout_stream(exc.output)
            stderr = _decode_timeout_stream(exc.stderr)
            status = "timeout"
        duration_seconds = int(time.monotonic() - started)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        payload = {
            "command": command,
            "cwd": str(repo_root),
            "exit_code": exit_code,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "duration_seconds": duration_seconds,
            "status": status,
        }
        validate_scenario_command_result_payload(payload)
        results.append(payload)

    manifest = {
        "status": "pass" if all(item["status"] == "pass" for item in results) else "fail",
        "results": results,
    }
    return write_json_file(run_dir / "scenario-command-results.json", manifest)


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
```

- [x] **Step 4: Add orchestrator scenario command integration test**

In `scripts/tests/test_harness_loop_orchestrator.py`, add:

```python
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
            scenario_manifest = read_json_file(run_dir / "scenario-command-results.json")
            self.assertEqual(scenario_manifest["status"], "pass")
            stdout_path = Path(scenario_manifest["results"][0]["stdout_path"])
            self.assertIn("scenario artifact", stdout_path.read_text(encoding="utf-8"))
```

- [x] **Step 5: Run orchestrator test to verify it fails**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests.test_run_evaluator_runs_scenario_commands_from_task_contract -v
```

Expected: fail because orchestrator does not read `task-contract.json` or run scenario commands.

- [x] **Step 6: Implement orchestrator integration**

In `scripts/harness_loop_orchestrator.py`, import:

```python
try:
    from scripts.harness_loop_artifacts import run_scenario_commands
except ModuleNotFoundError:
    from harness_loop_artifacts import run_scenario_commands
```

In `run_evaluator`, before building the evaluator command, add:

```python
    task_contract_path = run_dir / "task-contract.json"
    scenario_command_results_path = ""
    if task_contract_path.exists():
        task_contract = read_json_file(task_contract_path)
        validate_task_contract_payload(task_contract)
        scenario_commands = list(task_contract["scenario_commands"])
        if scenario_commands:
            scenario_command_results_path = str(
                run_scenario_commands(
                    repo_root=root,
                    run_dir=run_dir,
                    commands=scenario_commands,
                    timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
                )
            )
```

Import `validate_task_contract_payload`.

Include `scenario_command_results_path` in `evaluator_payload`:

```python
        "scenario_command_results_path": scenario_command_results_path,
```

Update `validate_evaluator_result_payload` in Task 1 implementation to allow this extra required field if you choose to make it required; otherwise leave it optional by not validating extra keys. The existing validator permits extra keys.

- [x] **Step 7: Run tests and commit**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_orchestrator -v
```

Expected: pass.

Commit:

```bash
git add scripts/harness_loop_artifacts.py scripts/tests/test_harness_loop_artifacts.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): collect loop scenario command artifacts"
```

## Task 4: Add Artifact Hygiene And Cleanup Recovery

**Files:**
- Modify: `scripts/harness_loop_artifacts.py`
- Modify: `scripts/tests/test_harness_loop_artifacts.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [x] **Step 1: Write failing artifact hygiene tests**

Append to `scripts/tests/test_harness_loop_artifacts.py`:

```python
from scripts.harness_loop_artifacts import run_artifact_hygiene


class HarnessLoopArtifactHygieneTests(unittest.TestCase):
    def test_run_artifact_hygiene_redacts_sensitive_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "redacted")
            self.assertEqual(result["scanned_paths"], ["artifact.txt"])
            self.assertEqual(result["redacted_paths"], ["artifact.txt.redacted"])
            redacted = repo_root / "artifact.txt.redacted"
            self.assertIn("[REDACTED]", redacted.read_text(encoding="utf-8"))
            redaction_manifest = json.loads(Path(result["redaction_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(redaction_manifest["redactions"][0]["rule_id"], "authorization_header")

    def test_run_artifact_hygiene_omits_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "large.bin"
            artifact_path.write_bytes(b"x" * 20)

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["large.bin"],
                max_file_bytes=10,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], ["large.bin"])
```

- [x] **Step 2: Run hygiene tests to verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_artifacts.HarnessLoopArtifactHygieneTests -v
```

Expected: fail because `run_artifact_hygiene` does not exist.

- [x] **Step 3: Implement `run_artifact_hygiene`**

Append to `scripts/harness_loop_artifacts.py`:

```python
import hashlib

SENSITIVE_RULES = {
    "authorization_header": "Authorization:",
    "token_assignment": "token",
    "secret_assignment": "secret",
}


def run_artifact_hygiene(
    repo_root: Path,
    run_dir: Path,
    artifact_paths: list[str],
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 50 * 1024 * 1024,
) -> Path:
    scanned_paths: list[str] = []
    redacted_paths: list[str] = []
    omitted_paths: list[str] = []
    original_hashes: dict[str, str] = {}
    redaction_map: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    total_bytes = 0
    redactions: list[dict[str, str]] = []

    for relative_path in artifact_paths:
        path = repo_root / relative_path
        if not path.exists():
            omitted_paths.append(relative_path)
            findings.append({"path": relative_path, "severity": "warning", "message": "artifact missing"})
            continue
        size = path.stat().st_size
        total_bytes += size
        original_hashes[relative_path] = _sha256(path)
        if size > max_file_bytes or total_bytes > max_total_bytes:
            omitted_paths.append(relative_path)
            findings.append({"path": relative_path, "severity": "error", "message": "artifact too large"})
            continue
        scanned_paths.append(relative_path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            omitted_paths.append(relative_path)
            findings.append({"path": relative_path, "severity": "error", "message": "binary artifact omitted"})
            continue
        redacted_text, rules = _redact_text(text)
        if rules:
            redacted_relative = f"{relative_path}.redacted"
            redacted_path = repo_root / redacted_relative
            redacted_path.parent.mkdir(parents=True, exist_ok=True)
            redacted_path.write_text(redacted_text, encoding="utf-8")
            redacted_paths.append(redacted_relative)
            for rule_id in rules:
                redaction_map.append({"path": relative_path, "rule_id": rule_id, "replacement": "[REDACTED]"})
                redactions.append(
                    {
                        "path": relative_path,
                        "redacted_path": redacted_relative,
                        "rule_id": rule_id,
                        "original_sha256": original_hashes[relative_path],
                        "redacted_sha256": _sha256(redacted_path),
                    }
                )

    status = "blocked" if omitted_paths else "redacted" if redacted_paths else "pass"
    manifest_path = run_dir / "artifact-manifest.json"
    redaction_manifest_path = run_dir / "redaction-manifest.json"
    redaction_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    redaction_manifest_path.write_text(json.dumps({"redactions": redactions}, indent=2) + "\n", encoding="utf-8")
    payload = {
        "status": status,
        "scanned_paths": scanned_paths,
        "redacted_paths": redacted_paths,
        "omitted_paths": omitted_paths,
        "manifest_path": str(manifest_path),
        "redaction_manifest_path": str(redaction_manifest_path),
        "original_hashes": original_hashes,
        "redaction_map": redaction_map,
        "findings": findings,
    }
    return write_json_file(manifest_path, payload)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redact_text(text: str) -> tuple[str, list[str]]:
    rules: list[str] = []
    output_lines: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if lowered.startswith("authorization:"):
            output_lines.append("Authorization: [REDACTED]")
            rules.append("authorization_header")
        elif "token" in lowered or "secret" in lowered:
            output_lines.append("[REDACTED]")
            rules.append("token_or_secret")
        else:
            output_lines.append(line)
    return "\n".join(output_lines) + ("\n" if text.endswith("\n") else ""), sorted(set(rules))
```

- [x] **Step 4: Write failing orchestrator hygiene/cleanup tests**

Add to `scripts/tests/test_harness_loop_orchestrator.py`:

```python
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
```

- [x] **Step 5: Implement orchestrator hygiene and cleanup**

In `scripts/harness_loop_orchestrator.py`, import `run_artifact_hygiene` from `harness_loop_artifacts`.

Add:

```python
def run_artifact_hygiene_step(
    repo_root: Path | str,
    run_id: str,
    *,
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 50 * 1024 * 1024,
) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "artifact_hygiene":
        raise RuntimeError(f"run_artifact_hygiene_step requires phase artifact_hygiene; current phase is {run['phase']}")
    run_dir = run_dir_for(root, run_id)
    generator_result = read_json_file(run_dir / "generator-result.json")
    validate_generator_result_payload(generator_result)
    result_path = run_artifact_hygiene(
        repo_root=root,
        run_dir=run_dir,
        artifact_paths=list(generator_result["artifacts"]),
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )
    hygiene_result = read_json_file(result_path)
    validate_artifact_hygiene_result_payload(hygiene_result)
    run["attempts"]["artifact_hygiene"] = int(run["attempts"]["artifact_hygiene"]) + 1
    if hygiene_result["status"] == "blocked":
        run["phase"] = "stopped_blocked"
        run["last_result"] = "blocked"
        run["next_action"] = "inspect_artifact_hygiene"
    else:
        run["phase"] = "cleanup"
        run["next_action"] = "run_cleanup"
    save_run(root, run)
    return result_path
```

Add:

```python
def run_cleanup(repo_root: Path | str, run_id: str) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "cleanup":
        raise RuntimeError(f"run_cleanup requires phase cleanup; current phase is {run['phase']}")
    removed: list[str] = []
    for path_value in list(run["cleanup"].get("retained_artifacts", [])):
        path = Path(path_value)
        if path.exists() and ".worktrees" in path.parts:
            shutil.rmtree(path)
            removed.append(str(path))
    run["cleanup"]["worktrees_removed"].extend(removed)
    run["attempts"]["cleanup"] = int(run["attempts"]["cleanup"]) + 1
    run["phase"] = "passed_waiting_human_merge"
    run["next_action"] = "await_human_merge_confirmation"
    save_run(root, run)
    return write_json_file(run_dir_for(root, run_id) / "cleanup-result.json", {"status": "pass", "worktrees_removed": removed})
```

Import `shutil` and `validate_artifact_hygiene_result_payload`.

- [x] **Step 6: Run tests and commit**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_orchestrator -v
```

Expected: pass.

Commit:

```bash
git add scripts/harness_loop_artifacts.py scripts/tests/test_harness_loop_artifacts.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): add loop artifact hygiene cleanup"
```

## Task 5: Wire Phase 2 CLI, Scenario, Docs, And Completion Metadata

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Create: `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`
- Modify: `tasks.json`
- Modify: `progress.md`

- [x] **Step 1: Add failing CLI tests for hygiene and cleanup commands**

In `scripts/tests/test_harness_loop_orchestrator.py`, add:

```python
    def test_cli_accepts_artifact_hygiene_and_cleanup_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "CLI", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            artifact = repo_root / "artifact.txt"
            artifact.write_text("ok\n", encoding="utf-8")
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
                    "notes": "",
                },
            )
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            write_json_file(run_dir / "run.json", run)

            self.assertEqual(main(["artifact-hygiene", "--repo-root", str(repo_root), "--run-id", "demo-run"]), 0)
            self.assertEqual(main(["cleanup", "--repo-root", str(repo_root), "--run-id", "demo-run"]), 0)
            final_run = read_json_file(run_dir / "run.json")
            self.assertEqual(final_run["phase"], "passed_waiting_human_merge")
```

- [x] **Step 2: Implement parser commands**

In `_build_parser`, add:

```python
    hygiene = subparsers.add_parser("artifact-hygiene", help="Run artifact hygiene.")
    hygiene.add_argument("--repo-root", default=".")
    hygiene.add_argument("--run-id", required=True)

    cleanup = subparsers.add_parser("cleanup", help="Run cleanup.")
    cleanup.add_argument("--repo-root", default=".")
    cleanup.add_argument("--run-id", required=True)
```

In `main`, add:

```python
    elif args.command == "artifact-hygiene":
        run_artifact_hygiene_step(repo_root=args.repo_root, run_id=args.run_id)
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "cleanup":
        run_cleanup(repo_root=args.repo_root, run_id=args.run_id)
        payload = load_run(args.repo_root, args.run_id)
```

- [x] **Step 3: Update run loop to include hygiene/cleanup after evaluator pass**

Modify `run_evaluator` pass branch to set:

```python
    if result.returncode == 0:
        generator_result = read_json_file(run_dir / "generator-result.json")
        validate_generator_result_payload(generator_result)
        run["phase"] = "artifact_hygiene" if generator_result["artifacts"] else "passed_waiting_human_merge"
        run["next_action"] = "run_artifact_hygiene" if generator_result["artifacts"] else "await_human_merge_confirmation"
    else:
        run["phase"] = "repair_needed"
        run["next_action"] = "repair_from_evaluator_findings"
```

Modify `run_loop`:

```python
    if run["phase"] == "artifact_hygiene":
        run_artifact_hygiene_step(root, run_id)
        run = load_run(root, run_id)
    if run["phase"] == "cleanup":
        run_cleanup(root, run_id)
        run = load_run(root, run_id)
```

- [x] **Step 4: Add Phase 2 evaluator scenario contract**

Create `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json`:

```json
{
  "task_id": "planner-generator-evaluator-loop-phase-2-01",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "PGE-PHASE2-CONTRACT-ARTIFACTS",
      "user_goal": "As an operator, prepare a temporary evaluator task contract, run scenario command artifact collection, run artifact hygiene, and stop at the human merge gate.",
      "prerequisites": [
        "Repository root is writable.",
        "Fake drivers are available.",
        "No real Codex model call is required."
      ],
      "entrypoint": "python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement \"Phase 2 smoke demand loop\" --run-id evaluator-scenario-phase-2 --task-id planner-generator-evaluator-loop-phase-2-01 --confirm && python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id evaluator-scenario-phase-2 --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2",
      "steps": [
        "Create confirmed preflight.",
        "Run fake planner and generator.",
        "Run fake evaluator.",
        "Verify Phase 2 run state remains auditable and stops at human merge gate."
      ],
      "expected_outcomes": [
        ".codex/loop-runs/evaluator-scenario-phase-2/run.json exists.",
        "run.json phase is passed_waiting_human_merge.",
        "run.json next_action is await_human_merge_confirmation."
      ],
      "failure_signals": [
        "The loop executes without confirmed preflight.",
        "The loop reports complete instead of waiting for human merge.",
        "Phase 2 commands regress Phase 1 fake loop behavior."
      ],
      "cleanup": [
        "Remove .codex/loop-runs/evaluator-scenario-phase-2 after verification."
      ],
      "automation_hint": "shell"
    }
  ]
}
```

- [x] **Step 5: Update docs and tasks/progress completion**

In `docs/harness/planner-generator-evaluator-loop.md`, add a Phase 2 section:

```markdown
## Phase 2 Commands

`prepare-task --task-contract` allows evaluator bundles without registering
long-lived `tasks.json` entries. `scenario_commands` write stdout/stderr and a
manifest under `.codex/loop-runs/<run-id>/scenario-commands/`.

Artifact hygiene scans declared artifacts before cleanup. Sensitive text is
redacted with a `redaction-manifest.json`; oversized or binary artifacts are
omitted and block automatic progression.
```

In `tasks.json`, set `planner-generator-evaluator-loop-phase-2-01` status to `done` after final verification.

In `progress.md`, add top entry with actual evidence commands after they pass.

- [x] **Step 6: Final verification and commit**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_evaluator_cli scripts.tests.test_harness_evaluator_scenarios -v
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json >/dev/null
```

Expected: all tests and JSON commands pass.

Commit:

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-2-01.json docs/harness/planner-generator-evaluator-loop.md tasks.json progress.md
git commit -m "feat(harness): wire planner loop phase 2 workflow"
```

## Final Review

- [x] Run the full verification command from Task 5.
- [x] Run a fake smoke loop:

```bash
rm -rf .codex/loop-runs/phase-2-smoke
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Phase 2 smoke" --run-id phase-2-smoke --task-id planner-generator-evaluator-loop-phase-2-01 --confirm
python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id phase-2-smoke --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2
python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id phase-2-smoke
rm -rf .codex/loop-runs/phase-2-smoke
```

Expected final status: `phase=passed_waiting_human_merge`, `next_action=await_human_merge_confirmation`.

- [ ] Dispatch a final code reviewer for the full branch diff.
- [ ] Fix any Critical or Important findings.
- [ ] Use `superpowers:finishing-a-development-branch` to merge, PR, keep, or discard.
