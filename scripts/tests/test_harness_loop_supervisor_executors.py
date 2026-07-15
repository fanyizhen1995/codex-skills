from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import scripts.harness_loop_orchestrator as legacy
from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)


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
    from scripts.loop_supervisor.registry import worker_executable_action_types

    expected = set(worker_executable_action_types())

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

    assert not hasattr(legacy, "_run_loop")
    assert not hasattr(legacy, "_run_autonomous")
    assert not hasattr(legacy, "_run_demand_multi")

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


def test_legacy_multi_round_and_auditor_runtime_surfaces_are_removed() -> None:
    removed_files = (
        Path("scripts/harness_loop_phase2_smoke.py"),
        Path("scripts/harness_loop_phase3_smoke.py"),
        Path("scripts/harness_ai_infra_meta_loop_smoke.py"),
        Path("scripts/harness_loop_auditor.py"),
    )
    assert all(not path.exists() for path in removed_files)
    assert all(
        not hasattr(legacy, name)
        for name in ("_run_loop", "_run_autonomous", "_run_demand_multi", "_run_auditor")
    )
