from __future__ import annotations

import inspect
from pathlib import Path
import subprocess

import pytest

import scripts.harness_loop_orchestrator as legacy
from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.registry import REGISTRY
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore


def _request(action_type: ActionType) -> ActionRequest:
    return ActionRequest(
        action_id=f"action-{action_type.value}",
        run_id="run-1",
        run_revision=0,
        policy="demand_development",
        phase="planning",
        action_type=action_type,
        idempotency_key=f"key-{action_type.value}",
        payload={"driver": "fake"},
    )


def test_handler_table_exactly_covers_registry_executable_actions() -> None:
    from scripts.loop_supervisor.executor import ACTION_HANDLERS, executable_action_types

    expected = {
        rule.action_type
        for rule in REGISTRY.values()
        if not rule.terminal and not rule.user_escalation
    }

    assert executable_action_types() == expected
    assert set(ACTION_HANDLERS) == expected
    assert len(set(ACTION_HANDLERS.values())) == len(ACTION_HANDLERS)
    assert ACTION_HANDLERS[ActionType.COMMIT]


def test_each_handler_is_bounded_and_returns_action_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import executor

    calls: list[str] = []

    def fake_primitive(repo_root: Path, request: ActionRequest) -> ActionResult:
        assert repo_root == tmp_path
        calls.append(request.action_type.value)
        return ActionResult(ActionResultClass.SUCCESS, request.action_type.value)

    for primitive_name in executor.BOUNDED_PRIMITIVE_NAMES.values():
        monkeypatch.setattr(legacy, primitive_name, fake_primitive)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("multi-round loop called by bounded executor")

    monkeypatch.setattr(legacy, "run_loop", forbidden)
    monkeypatch.setattr(legacy, "run_autonomous", forbidden)
    monkeypatch.setattr(legacy, "run_demand_multi", forbidden)

    for action_type, handler in executor.ACTION_HANDLERS.items():
        result = handler(tmp_path, _request(action_type))
        assert isinstance(result, ActionResult)

    assert calls == [action_type.value for action_type in executor.ACTION_HANDLERS]


def test_dispatcher_rejects_non_executable_action(tmp_path: Path) -> None:
    from scripts.loop_supervisor.executor import execute_action

    with pytest.raises(ValueError, match="not executable"):
        execute_action(_request(ActionType.ASK_USER), tmp_path)


def test_executor_source_does_not_drive_multi_round_entrypoints() -> None:
    from scripts.loop_supervisor import executor

    source = inspect.getsource(executor)
    assert "run_" + "autonomous(" not in source
    assert "run_" + "demand_multi(" not in source
    assert "run_" + "loop(" not in source


def test_bounded_commit_stops_at_committed_and_next_reconcile_queues_push(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"], cwd=tmp_path, check=True
    )
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="autonomous-knowledge",
        requirement="Expand fixture knowledge",
        run_id="commit-run",
        domain="fixture",
        confirm=True,
    )
    changed_relative = "personal-wiki/domains/fixture/raw/source.md"
    changed_path = tmp_path / changed_relative
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("bounded commit evidence\n", encoding="utf-8")
    run = legacy.load_run(tmp_path, "commit-run")
    run["phase"] = "cleanup"
    run["next_action"] = "commit_autonomous_changes"
    run["task_id"] = "commit-task"
    legacy.save_run(tmp_path, run)
    generator_path = tmp_path / ".codex/loop-runs/commit-run/generator-result.json"
    generator_path.write_text(
        """{
  "task_id": "commit-task",
  "status": "implemented",
  "changed_paths": ["personal-wiki/domains/fixture/raw/source.md"],
  "commit": "",
  "verify_commands": [],
  "verify_results": [],
  "artifacts": [],
  "cleanup_required": false,
  "notes": "bounded commit fixture"
}\n""",
        encoding="utf-8",
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        first = reconcile_once(tmp_path, store, include_worktrees=False)
        commit_action = first.action_for("commit-run")
        assert commit_action is not None
        assert commit_action.action_type is ActionType.COMMIT

        result = execute_action(commit_action, tmp_path)

        assert result.result_class is ActionResultClass.SUCCESS
        committed = legacy.load_run(tmp_path, "commit-run")
        assert committed["phase"] == "committed"
        assert committed["next_action"] == "push_autonomous_commit"
        assert committed["phase"] not in {"passed_waiting_human_merge", "cleanup"}

        second = reconcile_once(tmp_path, store, include_worktrees=False)
        push_action = second.action_for("commit-run")

    assert push_action is not None
    assert push_action.action_type is ActionType.PUSH
