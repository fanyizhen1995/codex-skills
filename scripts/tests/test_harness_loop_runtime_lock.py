from pathlib import Path

import pytest

from scripts.harness_loop_runtime_lock import (
    RunLockBusy,
    acquire_repository_mutation_lock,
    acquire_run_lock,
    repository_mutation_lock_path,
    run_lock_path,
    validate_run_lock_token,
)


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


def test_run_lock_token_binds_run_directory_identity(tmp_path: Path) -> None:
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text('{"run_id":"demo-run"}\n', encoding="utf-8")

    with acquire_run_lock(tmp_path, "demo-run", owner="executor") as token:
        assert token.run_directory_identity == (
            run_dir.stat().st_dev,
            run_dir.stat().st_ino,
        )
        displaced = run_dir.with_name("demo-run-old")
        run_dir.rename(displaced)
        run_dir.mkdir()
        with pytest.raises(ValueError, match="directory ownership changed"):
            validate_run_lock_token(token, tmp_path, "demo-run")


def test_repository_lock_metadata_is_replaced_and_lock_is_reusable(tmp_path: Path) -> None:
    path = repository_mutation_lock_path(tmp_path)

    with acquire_repository_mutation_lock(tmp_path, owner="worker-one") as first:
        assert first["owner"] == "worker-one"
        assert first["pid"] > 0

    with acquire_repository_mutation_lock(tmp_path, owner="worker-two") as second:
        assert second["owner"] == "worker-two"

    assert path.exists()


def test_repository_lock_is_released_when_owner_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="action failed"):
        with acquire_repository_mutation_lock(tmp_path, owner="worker-one"):
            raise RuntimeError("action failed")

    with acquire_repository_mutation_lock(tmp_path, owner="worker-two") as metadata:
        assert metadata["owner"] == "worker-two"
