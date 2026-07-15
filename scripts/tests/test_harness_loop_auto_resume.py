from __future__ import annotations

from pathlib import Path

import pytest

from scripts.loop_supervisor.models import ActionType
from scripts.loop_supervisor.reconciler import desired_action_for_run


def test_legacy_auto_resume_runtime_is_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not (root / "scripts/harness_loop_auto_resume.py").exists()


@pytest.mark.parametrize(
    "next_action",
    [
        "inspect_autonomous_dirty_paths",
        "inspect_required_evidence",
        "inspect_autonomous_commit",
        "retry_autonomous_push",
    ],
)
def test_registry_replaces_auto_resume_actionable_state_list(next_action: str) -> None:
    action = desired_action_for_run(
        {
            "run_id": "recoverable-run",
            "state_revision": 1,
            "policy": "autonomous_knowledge",
            "phase": "stopped_blocked",
            "next_action": next_action,
            "task_id": "parent-22",
        }
    )

    assert action is not None
    assert action.action_type is ActionType.RECOVER_GENERATOR_RESULT
