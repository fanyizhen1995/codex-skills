#!/usr/bin/env python3
"""Isolated process, runtime, and browser evaluator for Loop Supervisor."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.harness_loop_orchestrator as legacy
import scripts.loop_dashboard_supervisor_playwright as dashboard_browser
from scripts.harness_loop_contracts import default_limits, read_json_file
from scripts.harness_loop_runtime_lock import acquire_run_lock
from scripts.loop_dashboard_supervisor_playwright import (
    collect_output,
    seed_fixture as seed_dashboard_fixture,
    start_dashboard,
    terminate as terminate_dashboard,
    wait_for_dashboard,
)
from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.reconciler import _state_fingerprint, reconcile_once
from scripts.loop_supervisor.reviewer import (
    run_queued_reviewer,
    schedule_due_reviews,
)
from scripts.loop_supervisor.store import SupervisorStore
from scripts.loop_supervisor.worker import worker_once


PARENT22_RUN_ID = "parent-22-e2e"
PARENT22_TASK_ID = "parent-22-task"
CURSOR_SECRET = "loop-supervisor-e2e-cursor-secret-2026-07-15"


class EvaluationError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output-dir",
        default=".codex/loop-supervisor-e2e/loop-supervisor-unification-01",
    )
    return parser.parse_args(argv)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def require(condition: object, message: str) -> None:
    if not condition:
        raise EvaluationError(message)


def run_current_health_browser_actions(
    dashboard_url: str,
    output_dir: Path,
    fixture_root: Path,
) -> dict[str, object]:
    evidence = dashboard_browser.run_browser_actions(
        dashboard_url,
        output_dir,
        fixture_root,
    )
    require(
        isinstance(evidence.get("health_contract"), Mapping),
        "current health browser evidence was not captured",
    )
    return evidence


def init_git_repository(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "e2e@example.invalid"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Loop Supervisor E2E"],
        cwd=root,
        check=True,
    )
    (root / "README.md").write_text("isolated loop supervisor e2e\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "test: initialize isolated supervisor fixture"],
        cwd=root,
        check=True,
    )


def process_environment(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + current if current else "")
    return env


def start_process(
    repo_root: Path,
    command: list[str],
    *,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.Popen[str]:
    env = process_environment(repo_root)
    env.update(extra_env or {})
    return subprocess.Popen(
        command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_process(process: subprocess.Popen[str] | None) -> dict[str, Any]:
    if process is None:
        return {"returncode": None, "stdout": "", "stderr": ""}
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    stdout, stderr = process.communicate(timeout=5)
    return {
        "returncode": process.returncode,
        "stdout": stdout[-8_000:],
        "stderr": stderr[-8_000:],
    }


def wait_until(
    predicate: Callable[[], Any],
    description: str,
    *,
    timeout: float = 20,
) -> Any:
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(0.1)
    raise EvaluationError(f"timed out waiting for {description}; last={last!r}")


def action_rows(store: SupervisorStore, run_id: str) -> list[dict[str, Any]]:
    return [row for row in store.fetch_all("actions") if row["run_id"] == run_id]


def seed_planning_run(root: Path) -> None:
    legacy.create_preflight_run(
        repo_root=root,
        mode="autonomous-knowledge",
        requirement="Exercise duplicate reconcile and Worker lease reclaim",
        run_id="duplicate-reconcile-run",
        domain="fixture",
        confirm=True,
    )


def seed_parent22_partial_fixture(root: Path) -> dict[str, object]:
    run_dir = root / ".codex" / "loop-runs" / PARENT22_RUN_ID
    run_dir.mkdir(parents=True)
    changed_path = "knowledge/parent-22.md"
    changed_file = root / changed_path
    changed_file.parent.mkdir(parents=True)
    changed_file.write_text("# Parent 22 fixture\n\nRecovered evidence.\n", encoding="utf-8")
    run: dict[str, object] = {
        "run_id": PARENT22_RUN_ID,
        "loop_lineage_id": "ai-infra-lineage",
        "policy": "autonomous_knowledge",
        "phase": "generating",
        "task_id": PARENT22_TASK_ID,
        "domain": "ai_infra",
        "branch": "fixture",
        "worktree": str(root.resolve()),
        "requirement": "Recover the parent-22 structural fixture",
        "constraints": [],
        "stop_conditions": ["secret exposure"],
        "baseline_dirty_paths": [],
        "allowed_paths": ["knowledge/**"],
        "denylist_paths": [".env", ".codex/secrets/**"],
        "manual_confirm_paths": [],
        "required_evidence": ["gap proof"],
        "attempts": {
            "planner": 1,
            "generator": 4,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": default_limits(),
        "last_result": "fail",
        "next_action": "run_autonomous_generator",
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
        "state_revision": 3,
    }
    write_json(run_dir / "run.json", run)
    write_json(
        run_dir / "planner-output.json",
        {
            "task_id": PARENT22_TASK_ID,
            "policy": "autonomous_knowledge",
            "task_kind": "autonomous_implementation_task",
            "title": "Parent 22 fixture",
            "goal": "Produce one scoped knowledge page",
            "non_goals": [],
            "allowed_paths": ["knowledge/**"],
            "denylist_paths": [".env", ".codex/secrets/**"],
            "verify_commands": ["python3 -m pytest -q fixture"],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/fixture.json",
            "stop_conditions": ["secret exposure"],
            "next_planning_hint": "Evaluate independently",
            "skill_invocations": [],
        },
    )
    for attempt in (3, 4):
        stdout_path = run_dir / f"generator-attempt-{attempt}.stdout.log"
        stderr_path = run_dir / f"generator-attempt-{attempt}.stderr.log"
        stdout_path.write_text("bounded partial output\n", encoding="utf-8")
        stderr_path.write_text("operation timed out\n", encoding="utf-8")
        write_json(
            run_dir / f"generator-attempt-{attempt}.json",
            {
                "run_id": PARENT22_RUN_ID,
                "role": "generator",
                "attempt": attempt,
                "started_at": f"2026-07-15T00:0{attempt}:00Z",
                "finished_at": f"2026-07-15T00:0{attempt}:30Z",
                "exit_code": 124,
                "status": "timeout",
                "prompt_path": str(run_dir / "generator-prompt.md"),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "output_json_path": str(run_dir / "generator-result.json"),
                "diff_patch_path": "",
                "verify_log_paths": [],
            },
        )
    verify_dir = run_dir / "scenario-commands"
    verify_dir.mkdir()
    verify_stdout = verify_dir / "command-1.stdout.log"
    verify_stderr = verify_dir / "command-1.stderr.log"
    verify_stdout.write_text("1 passed\n", encoding="utf-8")
    verify_stderr.write_text("", encoding="utf-8")
    write_json(
        run_dir / "scenario-command-results.json",
        {
            "status": "pass",
            "results": [
                {
                    "command": "python3 -m pytest -q fixture",
                    "cwd": str(root.resolve()),
                    "exit_code": 0,
                    "stdout_path": str(verify_stdout),
                    "stderr_path": str(verify_stderr),
                    "duration_seconds": 1,
                    "status": "pass",
                }
            ],
        },
    )
    gap_path = run_dir / "gap-proofs" / f"{PARENT22_TASK_ID}.json"
    write_json(
        gap_path,
        {
            "task_id": PARENT22_TASK_ID,
            "layer": "runtime",
            "candidate": {
                "title": "Parent 22 fixture",
                "source_type": "paper",
                "identity_key": "fixture:parent-22",
            },
            "local_checks": {
                "raw_manifest_scan": "not present",
                "wiki_search": "not present",
                "domain_index_scan": "not present",
            },
            "gap_reason": "No existing fixture page",
            "planned_outputs": [changed_path],
        },
    )
    write_json(
        run_dir / "required-evidence-manifest.json",
        {
            "run_id": PARENT22_RUN_ID,
            "task_id": PARENT22_TASK_ID,
            "generated_at": "2026-07-15T00:05:00Z",
            "items": [
                {
                    "evidence_id": "gap-proof",
                    "task_id": PARENT22_TASK_ID,
                    "status": "pass",
                    "summary": "gap proof",
                    "artifacts": [f"gap-proofs/{PARENT22_TASK_ID}.json"],
                }
            ],
        },
    )
    write_json(
        run_dir / "dirty-paths-result.json",
        {
            "allowed": True,
            "actual_paths": [changed_path],
            "declared_paths": [changed_path],
            "baseline_paths": [],
            "baseline_changed_paths": [],
            "ignored_paths": [],
            "unexpected_paths": [],
        },
    )
    write_json(
        run_dir / "autonomous-scope-result.json",
        {
            "allowed": True,
            "allowed_paths": [changed_path],
            "denied_paths": [],
            "manual_confirm_paths": [],
            "findings": [],
        },
    )
    write_json(
        run_dir / "artifact-manifest.json",
        {
            "status": "pass",
            "scanned_paths": [changed_path],
            "redacted_paths": [],
            "omitted_paths": [],
            "manifest_path": str(run_dir / "artifact-manifest.json"),
            "redaction_manifest_path": str(run_dir / "redaction-manifest.json"),
            "original_hashes": {
                changed_path: hashlib.sha256(changed_file.read_bytes()).hexdigest()
            },
            "redaction_map": [],
            "findings": [],
        },
    )
    write_json(run_dir / "redaction-manifest.json", {"redactions": []})
    return run


def seed_parent_completion(
    store: SupervisorStore,
    root: Path,
    *,
    run_id: str,
    parent: int,
    previous_run_id: str = "",
) -> None:
    run_dir = root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "state_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "stopped_budget",
        "run_kind": "single",
        "domain": "fixture",
        "branch": "main",
        "worktree": str(root),
        "loop_lineage_id": "review-lineage",
        "previous_run_id": previous_run_id,
        "task_id": f"parent-{parent}",
        "parent_task_counter": parent,
        "_autonomous_completed_task_ids": [f"parent-{parent}"],
        "requirement": "Exercise project-global Reviewer cadence",
        "constraints": ["Preserve evidence"],
        "stop_conditions": ["All acceptance checks pass"],
        "last_result": "pass",
        "next_action": "none",
        "baseline_dirty_paths": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": {},
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    run_path = run_dir / "run.json"
    write_json(run_path, payload)
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": 1,
            "repo_relative_root": ".",
            "loop_lineage_id": "review-lineage",
            "parent_run_id": previous_run_id,
            "policy": "autonomous_knowledge",
            "phase": "stopped_budget",
            "status": "actionable",
            "state_fingerprint": _state_fingerprint(payload),
            "summary": json.dumps(
                {
                    "completed_semantic_parent_ids": [f"parent-{parent}"],
                    "parent_task_counter": parent,
                    "task_id": f"parent-{parent}",
                },
                sort_keys=True,
            ),
            "artifact_refs": [run_path.relative_to(root).as_posix()],
        }
    )


def accepted_review_driver(invocations: list[str]) -> Callable[..., dict[str, object]]:
    def driver(**kwargs: object) -> dict[str, object]:
        require(kwargs.get("role") == "supervisor_reviewer", "Reviewer role was not canonical")
        review_id = str(kwargs["run_id"])
        review_dir = Path(str(kwargs["run_dir"]))
        bundle_path = next(review_dir.glob("review-*-evidence.json"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        evidence_refs = list(bundle["evidence_hashes"].values())
        write_json(
            Path(str(kwargs["output_json_path"])),
            {
                "schema_version": 1,
                "review_id": review_id,
                "scope": "project",
                "decision": "continue",
                "affected_run_ids": [],
                "summary": "The isolated project remains aligned with its objective.",
                "evidence_refs": evidence_refs,
                "findings": [],
                "skill_governance": [],
                "next_review_after_parent_tasks": 2,
            },
        )
        invocations.append(review_id)
        return {"status": "pass", "exit_code": 0}

    return driver


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def run_evaluation(repo_root: Path, output_dir: Path) -> dict[str, object]:
    process_logs: dict[str, object] = {}
    suspicious: list[dict[str, str]] = []
    launched = ["loop-supervisor", "loop-supervisor-worker", "loop-dashboard"]
    with tempfile.TemporaryDirectory(prefix="loop-supervisor-e2e-") as temporary:
        project_root = Path(temporary) / "project"
        project_root.mkdir()
        init_git_repository(project_root)
        seed_planning_run(project_root)

        supervisor = start_process(
            repo_root,
            [
                sys.executable,
                "-m",
                "scripts.loop_supervisor.cli",
                "watch",
                "--project-root",
                str(project_root),
                "--interval-seconds",
                "1",
                "--max-ticks",
                "3",
                "--no-include-worktrees",
            ],
        )
        supervisor_stdout, supervisor_stderr = supervisor.communicate(timeout=20)
        process_logs["loop-supervisor"] = {
            "returncode": supervisor.returncode,
            "stdout": supervisor_stdout[-8_000:],
            "stderr": supervisor_stderr[-8_000:],
        }
        require(supervisor.returncode == 0, f"Supervisor failed: {supervisor_stderr}")

        with SupervisorStore.open(project_root) as store:
            store.migrate()
            duplicate_actions = action_rows(store, "duplicate-reconcile-run")
            require(len(duplicate_actions) == 1, "repeated reconcile created duplicate actions")
            reconcile_once(project_root, store, include_worktrees=False)
            require(
                len(action_rows(store, "duplicate-reconcile-run")) == 1,
                "counterexample reconcile created a duplicate action",
            )
            suspicious.append(
                {
                    "case": "duplicate reconcile after a third tick",
                    "counterexample_rerun": "pass",
                    "evidence": duplicate_actions[0]["action_id"],
                }
            )
            action_id = str(duplicate_actions[0]["action_id"])

        crash_worker: subprocess.Popen[str] | None = None
        lock = acquire_run_lock(
            project_root,
            "duplicate-reconcile-run",
            owner="e2e-crash-barrier",
            blocking=True,
        )
        token = lock.__enter__()
        del token
        try:
            crash_worker = start_process(
                repo_root,
                [
                    sys.executable,
                    "-m",
                    "scripts.loop_supervisor.cli",
                    "worker",
                    "--project-root",
                    str(project_root),
                    "--worker-id",
                    "crashed-worker",
                    "--poll-seconds",
                    "0.1",
                ],
            )

            def crashed_worker_leased() -> bool:
                with SupervisorStore.open(project_root) as probe:
                    row = probe.get_action(action_id)
                    return row.status == "leased" and row.lease_owner == "crashed-worker"

            wait_until(crashed_worker_leased, "crashed Worker lease")
            crash_worker.kill()
            crash_worker.wait(timeout=5)
            process_logs["crashed-worker"] = stop_process(crash_worker)
        finally:
            lock.__exit__(None, None, None)

        with SupervisorStore.open(project_root) as store:
            store._connection.execute(
                "UPDATE actions SET lease_expires_at = '2000-01-01T00:00:00.000000Z' WHERE action_id = ?",
                (action_id,),
            )
            store._connection.execute(
                "UPDATE workers SET heartbeat_at = '2000-01-01T00:00:00.000000Z' WHERE worker_id = 'crashed-worker'"
            )

        replacement = start_process(
            repo_root,
            [
                sys.executable,
                "-m",
                "scripts.loop_supervisor.cli",
                "worker",
                "--project-root",
                str(project_root),
                "--worker-id",
                "replacement-worker",
                "--poll-seconds",
                "0.1",
            ],
        )

        def reclaimed_and_completed() -> bool:
            with SupervisorStore.open(project_root) as probe:
                row = probe.get_action(action_id)
                return row.status == "completed"

        wait_until(reclaimed_and_completed, "replacement Worker completion")
        process_logs["loop-supervisor-worker"] = stop_process(replacement)
        with SupervisorStore.open(project_root) as store:
            attempts = [
                row
                for row in store.fetch_all("action_attempts")
                if row["action_id"] == action_id
            ]
            require(len(attempts) == 1, "crashed lease was reclaimed more than once")
            require(
                attempts[0]["worker_id"] == "replacement-worker",
                "replacement Worker provenance is absent",
            )
            probe = store.lease_next_action(
                "reclaim-counterexample",
                lease_seconds=5,
                heartbeat_stale_seconds=1,
                allowed_action_types={ActionType.RUN_PLANNER.value},
            )
            require(probe is None, "completed action was reclaimed again")
            suspicious.append(
                {
                    "case": "completed stale lease reclaimed a second time",
                    "counterexample_rerun": "pass",
                    "evidence": attempts[0]["attempt_id"],
                }
            )

            completed_fixture = legacy.load_run(
                project_root, "duplicate-reconcile-run"
            )
            completed_fixture["phase"] = "stopped_no_action"
            completed_fixture["next_action"] = "none"
            completed_fixture["last_result"] = "pass"
            legacy.save_run(project_root, completed_fixture)
            reconcile_once(project_root, store, include_worktrees=False)

            seed_parent22_partial_fixture(project_root)
            first = reconcile_once(project_root, store, include_worktrees=False).action_for(
                PARENT22_RUN_ID
            )
            require(first is not None, "partial Generator action was not reconciled")
            require(first.action_type is ActionType.RUN_GENERATOR, "unexpected source action")
            for index in range(1, 4):
                leased = store.claim_pending_action(
                    first.action_id,
                    f"retry-worker-{index}",
                    lease_seconds=60,
                    expected_queue_owner=ActionOwner.WORKER,
                )
                require(leased is not None, f"retryable Generator attempt {index} was not leased")
                store.complete_action(
                    leased.action_id,
                    f"retry-worker-{index}",
                    ActionResult(
                        result_class=ActionResultClass.RETRYABLE_FAILURE,
                        summary="Selected model is at capacity",
                        failure_key=f"worker:{leased.action_id}:capacity",
                        error_class="model_capacity",
                    ),
                )
                recovery = reconcile_once(project_root, store, include_worktrees=False)
                if index < 3:
                    for failure in store.fetch_all("failures"):
                        state = json.loads(failure["resolution"])
                        if state.get("kind") != "episode":
                            continue
                        state["retry_at"] = "2000-01-01T00:00:00+00:00"
                        store._connection.execute(
                            "UPDATE failures SET resolution = ? WHERE failure_key = ?",
                            (json.dumps(state, sort_keys=True), failure["failure_key"]),
                        )
                    recovery = reconcile_once(
                        project_root, store, include_worktrees=False
                    )
            alternate = recovery.action_for(PARENT22_RUN_ID)
            require(alternate is not None, "partial recovery action was not queued")
            require(
                alternate.action_type is ActionType.RECOVER_GENERATOR_RESULT,
                "Supervisor reran Generator instead of recovering its result",
            )
            require(alternate.payload.get("recovery_failure_key"), "recovery lacks provenance")

        recovered = worker_once(project_root, "recovery-worker")
        require(recovered.status == "completed", f"Generator recovery failed: {recovered}")
        require(
            recovered.action_id == alternate.action_id,
            "Worker executed a different action instead of Generator recovery",
        )
        with SupervisorStore.open(project_root) as store:
            evaluator_action = reconcile_once(
                project_root, store, include_worktrees=False
            ).action_for(PARENT22_RUN_ID)
            require(evaluator_action is not None, "Evaluator was not queued after recovery")
            require(
                evaluator_action.action_type is ActionType.RUN_EVALUATOR,
                "recovery did not require independent Evaluator",
            )
        evaluated = worker_once(project_root, "evaluator-worker")
        require(evaluated.status == "completed", f"Evaluator failed: {evaluated}")
        recovered_payload = read_json_file(
            project_root / ".codex" / "loop-runs" / PARENT22_RUN_ID / "generator-result.json"
        )
        evaluator_payload = read_json_file(
            project_root / ".codex" / "loop-runs" / PARENT22_RUN_ID / "evaluator-result.json"
        )
        require(
            recovered_payload["recovery"]["recovered_from_attempts"] == [3, 4],
            "recovery attempt provenance is incomplete",
        )
        require(evaluator_payload["status"] == "pass", "independent Evaluator did not pass")
        suspicious.append(
            {
                "case": "recovered envelope bypassed independent Evaluator",
                "counterexample_rerun": "pass",
                "evidence": str(evaluator_payload["task_id"]),
            }
        )

        legacy.create_preflight_run(
            repo_root=project_root,
            mode="autonomous-knowledge",
            requirement="Independent continuation for decision isolation",
            run_id="independent-continuation",
            domain="fixture",
            confirm=True,
        )
        with SupervisorStore.open(project_root) as store:
            store.open_user_decision(
                scope="run",
                run_id=PARENT22_RUN_ID,
                failure_key="e2e:run-scoped-decision",
                summary="Only parent-22 needs an operator decision.",
                required_decision="Resolve parent-22 only.",
            )
            reconciled = reconcile_once(project_root, store, include_worktrees=False)
            independent_action = reconciled.action_for("independent-continuation")
            require(independent_action is not None, "independent continuation was not queued")
            leased = store.lease_next_action(
                "decision-isolation-worker",
                lease_seconds=60,
                heartbeat_stale_seconds=1,
            )
            require(leased is not None, "run-scoped decision blocked all actions")
            require(
                leased.run_id == "independent-continuation",
                "run-scoped decision did not isolate the affected run",
            )
            store.complete_action(
                leased.action_id,
                "decision-isolation-worker",
                ActionResult(
                    result_class=ActionResultClass.SUCCESS,
                    summary="independent continuation remained runnable",
                ),
            )
            require(
                not any(
                    row["scope"] == "global" and row["status"] == "open"
                    for row in store.fetch_all("user_decisions")
                ),
                "run-scoped decision created a global stop",
            )
            suspicious.append(
                {
                    "case": "run-scoped decision stopped an independent continuation",
                    "counterexample_rerun": "pass",
                    "evidence": leased.action_id,
                }
            )

            seed_parent_completion(store, project_root, run_id="review-parent-1", parent=1)
            seed_parent_completion(
                store,
                project_root,
                run_id="review-parent-2",
                parent=2,
                previous_run_id="review-parent-1",
            )
            scheduled = schedule_due_reviews(
                store, now=datetime.now(UTC) + timedelta(minutes=11)
            )
            require(len(scheduled) == 1, "two parents did not coalesce to one Reviewer action")
            store._connection.execute(
                "UPDATE actions SET not_before = '' WHERE action_id = ?",
                (scheduled[0].action_id,),
            )
            reviewer_invocations: list[str] = []
            review_result = run_queued_reviewer(
                store,
                reviewer_id="fixture-reviewer",
                driver=accepted_review_driver(reviewer_invocations),
                timeout_seconds=10,
                heartbeat_seconds=0.1,
            )
            require(review_result is not None, "Reviewer action was not leased")
            require(review_result.status == "review_complete", "real Reviewer fixture failed")
            require(len(reviewer_invocations) == 1, "Reviewer fixture invocation count is not one")
            require(
                schedule_due_reviews(
                    store, now=datetime.now(UTC) + timedelta(minutes=22)
                )
                == [],
                "same two parents scheduled a second Review",
            )

            seed_parent_completion(
                store,
                project_root,
                run_id="review-parent-3",
                parent=3,
                previous_run_id="review-parent-2",
            )
            seed_parent_completion(
                store,
                project_root,
                run_id="review-parent-4",
                parent=4,
                previous_run_id="review-parent-3",
            )
            timeout_action = schedule_due_reviews(
                store, now=datetime.now(UTC) + timedelta(minutes=33)
            )
            require(len(timeout_action) == 1, "second Reviewer cadence was not scheduled")
            store._connection.execute(
                "UPDATE actions SET not_before = '' WHERE action_id = ?",
                (timeout_action[0].action_id,),
            )
            timeout_calls: list[str] = []

            def timeout_driver(**kwargs: object) -> dict[str, object]:
                timeout_calls.append(str(kwargs["run_id"]))
                return {"status": "timeout", "exit_code": 124}

            degraded = run_queued_reviewer(
                store,
                reviewer_id="timeout-reviewer",
                driver=timeout_driver,
                timeout_seconds=10,
                heartbeat_seconds=0.1,
            )
            require(degraded is not None, "timeout Reviewer action was not leased")
            require(degraded.status == "review_degraded", "timeout did not degrade Review")
            require(degraded.blocks_safe_runs is False, "Reviewer timeout did not fail open")
            require(len(timeout_calls) == 1, "timeout Reviewer was invoked more than once")
            require(
                not any(
                    row["scope"] == "global" and row["status"] == "open"
                    for row in store.fetch_all("user_decisions")
                ),
                "Reviewer timeout opened a global decision",
            )
            suspicious.append(
                {
                    "case": "Reviewer timeout created a global stop",
                    "counterexample_rerun": "pass",
                    "evidence": degraded.review_id,
                }
            )

        browser_root = Path(temporary) / "browser-project"
        browser_root.mkdir()
        init_git_repository(browser_root)
        seed_dashboard_fixture(repo_root, browser_root)
        dashboard_port = free_port()
        dashboard = start_dashboard(repo_root, browser_root, dashboard_port)
        dashboard_url = f"http://127.0.0.1:{dashboard_port}"
        try:
            wait_for_dashboard(dashboard_url, browser_root, dashboard)
            browser_dir = output_dir / "browser"
            browser_evidence = run_current_health_browser_actions(
                dashboard_url, browser_dir, browser_root
            )
        finally:
            terminate_dashboard(dashboard)
            dashboard_output = collect_output(dashboard)
        process_logs["loop-dashboard"] = dashboard_output
        source_screenshot = (
            output_dir / "browser" / "loop-supervisor-unification-desktop.png"
        )
        target_screenshot = output_dir / "browser" / "loop-supervisor-e2e-desktop.png"
        shutil.copy2(source_screenshot, target_screenshot)

        help_result = subprocess.run(
            [sys.executable, "-m", "scripts.loop_supervisor.cli", "--help"],
            cwd=repo_root,
            env=process_environment(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        public_help = help_result.stdout.lower()
        for removed in ("auditor", "auto-resume", "orchestrator"):
            require(removed not in public_help, f"legacy public role remains in CLI: {removed}")

        with SupervisorStore.open(project_root) as store:
            integrity = "ok" if store.database_integrity_ok() else "failed"
            seeded_record_count = sum(
                store.count(table)
                for table in (
                    "runs",
                    "actions",
                    "action_attempts",
                    "reviews",
                    "user_decisions",
                    "services",
                )
            )
            database_evidence = {
                "action_count": store.count("actions"),
                "attempt_count": store.count("action_attempts"),
                "review_count": store.count("reviews"),
                "run_count": store.count("runs"),
                "worker_count": store.count("workers"),
            }
            review_rows = store.fetch_all("reviews")
            require(
                any(row["status"] == "review_complete" for row in review_rows),
                "accepted Reviewer row is absent",
            )
            require(
                any(row["status"] == "review_degraded" for row in review_rows),
                "degraded Reviewer row is absent",
            )

        commit_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )

        scenarios = [
            {
                "scenario_id": "duplicate-reconcile",
                "status": "pass",
                "summary": "Three Supervisor ticks retained one idempotent action.",
                "evidence": [action_id],
            },
            {
                "scenario_id": "worker-crash-lease-reclaim",
                "status": "pass",
                "summary": "A killed Worker lease was reclaimed once by a replacement process.",
                "evidence": [attempts[0]["attempt_id"]],
            },
            {
                "scenario_id": "partial-generator-recovery",
                "status": "pass",
                "summary": "Attempts 3/4 reconstructed Generator result and an independent Evaluator passed.",
                "evidence": [
                    f".codex/loop-runs/{PARENT22_RUN_ID}/generator-result.json",
                    f".codex/loop-runs/{PARENT22_RUN_ID}/evaluator-result.json",
                ],
            },
            {
                "scenario_id": "run-scoped-decision-isolation",
                "status": "pass",
                "summary": "A run-scoped decision did not block an independent continuation.",
                "evidence": [leased.action_id],
            },
            {
                "scenario_id": "reviewer-two-parent-cadence",
                "status": "pass",
                "summary": "Two semantic parents triggered one validated project-global Reviewer fixture invocation.",
                "evidence": reviewer_invocations,
            },
            {
                "scenario_id": "reviewer-timeout-fail-open",
                "status": "pass",
                "summary": "Reviewer timeout recorded review_degraded without a global stop.",
                "evidence": timeout_calls,
            },
            {
                "scenario_id": "dashboard-tabs-and-pagination",
                "status": "pass",
                "summary": "Desktop/mobile browser checks covered exact tabs and cursor pagination.",
                "evidence": [
                    str(target_screenshot),
                    str(output_dir / "browser" / "loop-supervisor-unification-mobile.png"),
                ],
            },
            {
                "scenario_id": "legacy-role-removal",
                "status": "pass",
                "summary": "Browser and canonical CLI expose no Auditor, auto-resume, or orchestrator role.",
                "evidence": ["canonical CLI --help", "browser visible text"],
            },
        ]
        return {
            "status": "pass",
            "task_id": "loop-supervisor-unification-01",
            "scenario_results": scenarios,
            "runtime_evidence": {
                "temporary_git_repository": True,
                "temporary_project_root": str(project_root),
                "sqlite_integrity": integrity,
                "seeded_record_count": seeded_record_count,
                "git_commit_count": commit_count,
                "launched_processes": launched,
                "independent_inspections": [
                    "database_rows",
                    "action_leases",
                    "run_files",
                    "action_provenance",
                    "browser_content",
                    "git_commits",
                ],
                "fixture_only_rendering": False,
                "database": database_evidence,
                "dashboard_url": dashboard_url,
            },
            "browser_evidence": browser_evidence,
            "suspicious_case_checks": suspicious,
            "process_logs": process_logs,
            "rerun_command": (
                "python3 scripts/loop_supervisor_e2e_evaluator.py --repo-root . "
                "--output-dir .codex/loop-supervisor-e2e/loop-supervisor-unification-01"
            ),
        }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    os.environ["LOOP_SUPERVISOR_AGENT_DRIVER"] = "fake"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = run_evaluation(repo_root, output_dir)
    except BaseException as exc:
        result = {
            "status": "fail",
            "task_id": "loop-supervisor-unification-01",
            "error": f"{exc.__class__.__name__}: {exc}",
        }
        write_json(output_dir / "result.json", result)
        print(result["error"], file=sys.stderr)
        return 1
    write_json(output_dir / "result.json", result)
    print(json.dumps({"status": "pass", "output_dir": str(output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
