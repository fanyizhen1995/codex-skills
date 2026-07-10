from pathlib import Path

import pytest

from scripts.harness_loop_runtime_lock import RunLockBusy, acquire_run_lock, run_lock_path


def test_run_lock_is_repo_local_and_rejects_second_executor(tmp_path: Path) -> None:
    expected = tmp_path / ".codex" / "loop-locks" / "demo-run.lock"

    with acquire_run_lock(tmp_path, "demo-run", owner="executor-one") as first:
        assert run_lock_path(tmp_path, "demo-run") == expected
        assert first["owner"] == "executor-one"
        assert expected.exists()
        with pytest.raises(RunLockBusy) as raised:
            with acquire_run_lock(tmp_path, "demo-run", owner="executor-two"):
                pass

    assert raised.value.run_id == "demo-run"
    assert raised.value.current_owner == "executor-one"


def test_run_lock_validates_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_id"):
        with acquire_run_lock(tmp_path, "../escape", owner="executor"):
            pass
