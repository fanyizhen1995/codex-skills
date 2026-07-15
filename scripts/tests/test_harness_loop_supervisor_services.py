from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import threading
from types import SimpleNamespace
import time

import pytest

from scripts.loop_supervisor.models import ActionResultClass
from scripts.loop_supervisor.store import SupervisorStore


class FakeClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 15, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


def _store(project_root: Path, clock: FakeClock) -> SupervisorStore:
    store = SupervisorStore.open(project_root, clock=clock)
    store.migrate()
    return store


def _healthy_contract_probe(
    endpoint: str, _timeout_seconds: float
) -> dict[str, object]:
    if "/api/wiki/metrics" in endpoint:
        payload: object = {
            "counts": {"wiki_page_count": 1, "raw_file_count": 2},
            "sizes": {"wiki_bytes": 100, "raw_bytes": 200},
            "health": {"status": "attention", "score": 80},
        }
    elif "/api/search" in endpoint:
        payload = [
            {
                "domain": "ai_infra",
                "path": "domains/ai_infra/wiki/runtime.md",
                "title": "Runtime",
                "snippet": "supervisor runtime",
                "score": 0.0,
            }
        ]
    elif endpoint.endswith("/api/supervisor"):
        payload = {
            "status": "available",
            "schema_version": 14,
            "counts": {},
            "diagnostics": [],
        }
    elif endpoint.endswith("/api/health"):
        payload = {"status": "ok"}
    else:
        payload = None
    return {
        "status": "healthy",
        "summary": "HTTP 200",
        "details": {"status_code": 200},
        "payload": payload,
    }


def _healthy_process_probe(
    session_name: str, _timeout_seconds: float
) -> dict[str, object]:
    return {
        "session_name": session_name,
        "session_exists": True,
        "process_id": 2000 + len(session_name),
        "process_alive": True,
        "command": "python3",
    }


def _write_runtime_evidence(
    project_root: Path,
    service_id: str,
    *,
    process_id: int,
    code_fingerprint: str,
    heartbeat_at: str | None,
) -> Path:
    from scripts.loop_supervisor import services

    path = project_root / ".codex/service-runtime" / f"{service_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "service": service_id,
        "tmux_session": services._SERVICE_SESSIONS[service_id],
        "pid": process_id,
        "cwd": str(project_root),
        "code_fingerprint": code_fingerprint,
    }
    if heartbeat_at is not None:
        payload["heartbeat_at"] = heartbeat_at
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def test_runtime_probes_real_targets_and_deduplicates_unchanged_observations(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()
    calls: list[str] = []

    def healthy_probe(endpoint: str, _timeout_seconds: float) -> dict[str, object]:
        calls.append(endpoint)
        return _healthy_contract_probe(endpoint, _timeout_seconds)

    with _store(tmp_path, clock) as store:
        first = observe_runtime_health(
            tmp_path,
            store,
            http_probe=healthy_probe,
            process_probe=_healthy_process_probe,
            process_id=4242,
            version="test-version",
        )
        initial_services = store.fetch_all("services")
        initial_freshness = store.fetch_all("freshness_checks")

        second = observe_runtime_health(
            tmp_path,
            store,
            http_probe=healthy_probe,
            process_probe=_healthy_process_probe,
            process_id=4242,
            version="test-version",
        )

        assert {row["service_id"] for row in initial_services} == {
            "crawler-backend",
            "crawler-frontend",
            "loop-dashboard",
            "loop-supervisor",
            "supervisor-worker",
        }
        assert {row["status"] for row in initial_services if row["service_id"] != "supervisor-worker"} == {"healthy"}
        assert next(row for row in initial_services if row["service_id"] == "supervisor-worker")["status"] == "offline"
        assert {row["target"] for row in initial_freshness} == {"wiki", "search", "dashboard"}
        assert {row["status"] for row in initial_freshness} == {"fresh"}
        assert first["writes"] == {"services": 5, "freshness_checks": 3}
        assert second["writes"] == {"services": 0, "freshness_checks": 0}
        assert store.fetch_all("services") == initial_services
        assert store.fetch_all("freshness_checks") == initial_freshness
        assert len(calls) == 12


def test_runtime_marks_endpoint_probe_failure_unhealthy_without_secret_details(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def failed_probe(_endpoint: str, _timeout_seconds: float) -> dict[str, object]:
        return {
            "status": "unhealthy",
            "summary": "timeout",
            "details": {"error_class": "timeout", "authorization": "Bearer secret-value"},
        }

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=failed_probe,
            process_probe=_healthy_process_probe,
            version="test-version",
        )

        services = {row["service_id"]: row for row in store.fetch_all("services")}
        freshness = {row["target"]: row for row in store.fetch_all("freshness_checks")}

    assert services["crawler-backend"]["status"] == "unhealthy"
    backend_details = json.loads(services["crawler-backend"]["details_json"])
    assert backend_details["error_class"] == "timeout"
    assert backend_details["reachable"] is False
    assert freshness["wiki"]["status"] == "stale"
    assert "secret-value" not in str(services) + str(freshness)


def test_runtime_projects_worker_heartbeat_then_stale_state(tmp_path: Path) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def healthy_probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        return _healthy_contract_probe(endpoint, timeout_seconds)

    with _store(tmp_path, clock) as store:
        store.record_worker_heartbeat("worker-01")
        clock.advance(seconds=60)
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=healthy_probe,
            process_probe=_healthy_process_probe,
            version="test-version",
        )
        healthy = next(
            row for row in store.fetch_all("services") if row["service_id"] == "supervisor-worker"
        )

        clock.advance(seconds=1)
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=healthy_probe,
            process_probe=_healthy_process_probe,
            version="test-version",
        )
        stale = next(
            row for row in store.fetch_all("services") if row["service_id"] == "supervisor-worker"
        )

    assert healthy["status"] == "healthy"
    healthy_details = json.loads(healthy["details_json"])
    assert healthy_details["alive_worker_ids"] == ["worker-01"]
    assert healthy_details["workers"][0]["worker_id"] == "worker-01"
    assert healthy_details["workers"][0]["heartbeat_at"] == healthy["heartbeat_at"]
    assert stale["status"] == "stale"
    stale_details = json.loads(stale["details_json"])
    assert stale_details["alive_worker_ids"] == []
    assert stale_details["workers"][0]["status"] == "stale"


def test_stopped_worker_process_degrades_at_heartbeat_boundary_then_stales(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def stopped_worker_process(
        session_name: str, timeout_seconds: float
    ) -> dict[str, object]:
        process = _healthy_process_probe(session_name, timeout_seconds)
        if session_name == "loop-supervisor-worker":
            process.update(
                {
                    "session_exists": False,
                    "process_id": None,
                    "process_alive": False,
                    "command": "",
                }
            )
        return process

    with _store(tmp_path, clock) as store:
        store.touch_worker("worker-01")
        clock.advance(seconds=60)
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=stopped_worker_process,
            version="test-version",
        )
        boundary = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "supervisor-worker"
        )

        clock.advance(seconds=1)
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=stopped_worker_process,
            version="test-version",
        )
        expired = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "supervisor-worker"
        )

    boundary_details = json.loads(boundary["details_json"])
    expired_details = json.loads(expired["details_json"])
    assert boundary["status"] == "degraded"
    assert boundary["process_id"] is None
    assert boundary_details["tmux_session_exists"] is False
    assert boundary_details["process_alive"] is False
    assert boundary_details["alive_worker_ids"] == ["worker-01"]
    assert expired["status"] == "stale"
    assert expired_details["alive_worker_ids"] == []
    assert expired_details["workers"][0]["status"] == "stale"


def test_canonical_once_runs_runtime_health_producer(
    tmp_path: Path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    observed: list[Path] = []
    keeper_calls: list[Path] = []
    printed: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "run_supervisor_once", lambda _config: {"status": "healthy"})
    monkeypatch.setattr(
        cli,
        "observe_runtime_health",
        lambda root, _store, **options: observed.append(root)
        or {"writes": {"services": 5}, "runtime_mode": options["runtime_mode"]},
    )
    monkeypatch.setattr(
        cli,
        "run_service_keeper_once",
        lambda root, _store: keeper_calls.append(root)
        or {"claimed": 1, "completed": 1, "failed": 0, "action_ids": ["restart-1"]},
    )
    monkeypatch.setattr(cli, "_print_json", printed.append)

    result = cli._run_supervisor(
        tmp_path,
        SimpleNamespace(
            command="once",
            interval_seconds=30,
            include_worktrees=True,
            dry_run=False,
            max_ticks=0,
        ),
    )

    assert result == 0
    assert observed == [tmp_path.resolve()]
    assert keeper_calls == [tmp_path.resolve()]
    assert printed == [
        {
            "status": "healthy",
            "service_health": {
                "writes": {"services": 5},
                "runtime_mode": "once",
            },
            "service_keeper": {
                "claimed": 1,
                "completed": 1,
                "failed": 0,
                "action_ids": ["restart-1"],
            },
        }
    ]


def test_watch_launches_one_nonblocking_supervisor_service_keeper(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import cli

    entered = threading.Event()
    release = threading.Event()
    calls: list[Path] = []

    def keeper(root: Path, _store: SupervisorStore) -> dict[str, object]:
        calls.append(root)
        entered.set()
        assert release.wait(timeout=5)
        return {"claimed": 0, "completed": 0, "failed": 0, "action_ids": []}

    monkeypatch.setattr(cli, "_service_keeper_thread", None)
    monkeypatch.setattr(cli, "run_service_keeper_once", keeper)

    first = cli._launch_service_keeper(tmp_path.resolve())
    assert first == {"status": "launched"}
    assert entered.wait(timeout=5)
    second = cli._launch_service_keeper(tmp_path.resolve())

    assert second == {"status": "running"}
    assert calls == [tmp_path.resolve()]
    release.set()
    assert cli._service_keeper_thread is not None
    cli._service_keeper_thread.join(timeout=5)
    assert not cli._service_keeper_thread.is_alive()


def test_watch_keeps_producing_service_health_when_an_active_run_is_locked(
    tmp_path: Path, monkeypatch
) -> None:
    from scripts.harness_loop_runtime_lock import acquire_run_lock
    from scripts.loop_supervisor import cli

    run_dir = tmp_path / ".codex" / "loop-runs" / "active"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "active",
                "policy": "autonomous_knowledge",
                "phase": "planning",
                "task_id": "active-parent-1",
                "worktree": str(tmp_path),
                "last_result": "none",
                "next_action": "run_autonomous_planner",
                "commit": "abc123",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    observed_modes: list[str] = []
    monkeypatch.setattr(
        cli,
        "observe_runtime_health",
        lambda _root, _store, **options: observed_modes.append(options["runtime_mode"])
        or {"writes": {"services": 0, "freshness_checks": 0}},
    )
    monkeypatch.setattr(cli, "_print_json", lambda _payload: None)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        cli, "_launch_service_keeper", lambda _root: {"status": "launched"}
    )
    watch_args = SimpleNamespace(
        command="watch",
        interval_seconds=1,
        include_worktrees=False,
        dry_run=False,
        max_ticks=2,
    )

    with acquire_run_lock(tmp_path, "active", owner="worker:active", blocking=True):
        assert cli._run_supervisor(tmp_path, watch_args) == 0
        with SupervisorStore.open(tmp_path) as store:
            assert store.count("runs") == 0
            assert store.count("actions") == 0

    once_args = SimpleNamespace(
        command="once",
        interval_seconds=30,
        include_worktrees=False,
        dry_run=False,
        max_ticks=0,
    )
    assert cli._run_supervisor(tmp_path, once_args) == 0
    with SupervisorStore.open(tmp_path) as store:
        assert store.count("runs") == 1
        assert store.count("actions") == 1

    assert observed_modes == ["watch", "watch", "once"]


def test_runtime_probes_independent_endpoints_with_one_timeout_budget(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def delayed_probe(_endpoint: str, _timeout_seconds: float) -> dict[str, object]:
        time.sleep(0.05)
        return _healthy_contract_probe(_endpoint, _timeout_seconds)

    with _store(tmp_path, clock) as store:
        started = time.monotonic()
        observe_runtime_health(tmp_path, store, http_probe=delayed_probe, version="test-version")
        elapsed = time.monotonic() - started

    assert elapsed < 0.2


def test_freshness_requires_each_endpoint_json_contract(tmp_path: Path) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def invalid_contract_probe(
        endpoint: str, timeout_seconds: float
    ) -> dict[str, object]:
        result = _healthy_contract_probe(endpoint, timeout_seconds)
        if "/api/wiki/metrics" in endpoint:
            result["payload"] = {"items": []}
        elif "/api/search" in endpoint:
            result["payload"] = [{"title": "missing required fields"}]
        elif endpoint.endswith("/api/supervisor"):
            result["payload"] = {
                "status": "available",
                "diagnostics": [{"code": "schema_problem"}],
            }
        return result

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=invalid_contract_probe,
            version="test-version",
        )
        freshness = {
            row["target"]: row for row in store.fetch_all("freshness_checks")
        }

    assert {row["status"] for row in freshness.values()} == {"stale"}
    assert freshness["wiki"]["summary"] == "wiki response contract mismatch"
    assert freshness["search"]["summary"] == "search response contract mismatch"
    assert freshness["dashboard"]["summary"] == "dashboard diagnostics present"


def test_empty_search_response_is_stale(tmp_path: Path) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def empty_search_probe(
        endpoint: str, timeout_seconds: float
    ) -> dict[str, object]:
        result = _healthy_contract_probe(endpoint, timeout_seconds)
        if "/api/search" in endpoint:
            result["payload"] = []
        return result

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=empty_search_probe,
            process_probe=_healthy_process_probe,
            version="test-version",
        )
        search = next(
            row
            for row in store.fetch_all("freshness_checks")
            if row["target"] == "search"
        )

    assert search["status"] == "stale"
    assert search["summary"] == "search response contract mismatch"


def test_running_service_reports_its_old_fingerprint_not_new_repo_revision(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()
    current_revision = "b" * 40
    old_fingerprint = f"sha256:{'1' * 64}"
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(current_revision + "\n", encoding="ascii")
    dashboard_code = (
        tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    )
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'new-code'\n", encoding="utf-8")
    runtime_path = tmp_path / ".codex/service-runtime/loop-dashboard.json"
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "service": "loop-dashboard",
                "tmux_session": "loop-dashboard",
                "pid": 1103,
                "cwd": str(tmp_path),
                "code_fingerprint": old_fingerprint,
                "heartbeat_at": "2026-07-15T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=_healthy_process_probe,
        )
        dashboard = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "loop-dashboard"
        )

    details = json.loads(dashboard["details_json"])
    assert dashboard["status"] == "degraded"
    assert dashboard["version"] == old_fingerprint
    assert dashboard["version"] != current_revision[:12]
    assert details["version_verified"] is False
    assert details["running_version"] == old_fingerprint
    assert details["expected_version"] != old_fingerprint


def test_restart_rejects_reused_old_positive_pid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResultClass

    dashboard_code = tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'replacement'\n", encoding="utf-8")
    fingerprint = services._service_code_fingerprint(tmp_path, "loop-dashboard")
    old_process_id = 1103
    restarted = False

    def process_probe(session_name: str, _timeout: float) -> dict[str, object]:
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": old_process_id,
            "process_alive": restarted,
            "command": "python3",
        }

    def endpoint_probe(_endpoint: str, _timeout: float) -> dict[str, object]:
        return {
            "status": "healthy" if restarted else "unhealthy",
            "summary": "HTTP 200" if restarted else "connection error",
            "details": {"status_code": 200} if restarted else {},
        }

    def run_tmux(
        arguments: tuple[str, ...], _cwd: Path, _timeout: float
    ) -> dict[str, object]:
        nonlocal restarted
        if arguments[0] == "new-session":
            restarted = True
            _write_runtime_evidence(
                tmp_path,
                "loop-dashboard",
                process_id=old_process_id,
                code_fingerprint=fingerprint,
                heartbeat_at=services._utc_now(),
            )
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(services, "_tmux_process_probe", process_probe)
    monkeypatch.setattr(services, "_http_probe", endpoint_probe)
    monkeypatch.setattr(services, "_run_tmux_command", run_tmux)
    monkeypatch.setattr(services.time, "sleep", lambda _seconds: None)

    result = services.restart_managed_service(tmp_path, "loop-dashboard")

    assert result.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert "replacement pid not verified" in result.summary


def test_managed_runtime_wrapper_emits_pid_bound_heartbeat_and_fingerprint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services

    dashboard_code = tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'runtime-wrapper'\n", encoding="utf-8")

    class Child:
        returncode = 0
        polls = 0

        def poll(self) -> int | None:
            self.polls += 1
            return None if self.polls == 1 else self.returncode

        def wait(self) -> int:
            return self.returncode

    child = Child()
    monkeypatch.setattr(
        services,
        "_start_managed_child",
        lambda root, service: child,
    )
    monkeypatch.setattr(services.time, "sleep", lambda _seconds: None)

    returncode = services.run_managed_service_runtime(
        tmp_path,
        "loop-dashboard",
        heartbeat_interval_seconds=0.01,
    )
    payload = json.loads(
        (tmp_path / ".codex/service-runtime/loop-dashboard.json").read_text(
            encoding="utf-8"
        )
    )

    assert returncode == 0
    assert payload["service"] == "loop-dashboard"
    assert payload["pid"] > 0
    assert payload["heartbeat_at"]
    assert payload["code_fingerprint"] == services._service_code_fingerprint(
        tmp_path, "loop-dashboard"
    )
    assert "uvicorn loop_dashboard.main:app" in payload["command"]


def test_managed_runtime_binds_fingerprint_to_each_child_launch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services

    dashboard_code = tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'first-launch'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "add", dashboard_code.relative_to(tmp_path).as_posix()],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test: first launch"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    first_launch_fingerprint = services._service_code_fingerprint(
        tmp_path, "loop-dashboard"
    )
    first_launch_head = services._code_version(tmp_path)

    class Child:
        def __init__(self) -> None:
            self.polls = 0

        def poll(self) -> int | None:
            self.polls += 1
            return None if self.polls == 1 else 0

        def wait(self) -> int:
            return 0

    children: list[Child] = []

    def start_child(_root: Path, _service: object) -> Child:
        child = Child()
        children.append(child)
        return child

    sleep_calls = 0

    def change_source_during_first_child(_seconds: float) -> None:
        nonlocal sleep_calls
        if sleep_calls == 0:
            dashboard_code.write_text("APP = 'second-launch'\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", dashboard_code.relative_to(tmp_path).as_posix()],
                cwd=tmp_path,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: second launch"],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
        sleep_calls += 1

    monkeypatch.setattr(services, "_start_managed_child", start_child)
    monkeypatch.setattr(services.time, "sleep", change_source_during_first_child)

    services.run_managed_service_runtime(
        tmp_path, "loop-dashboard", heartbeat_interval_seconds=0.01
    )
    first_payload = json.loads(
        (tmp_path / ".codex/service-runtime/loop-dashboard.json").read_text(
            encoding="utf-8"
        )
    )
    second_launch_fingerprint = services._service_code_fingerprint(
        tmp_path, "loop-dashboard"
    )
    second_launch_head = services._code_version(tmp_path)
    services.run_managed_service_runtime(
        tmp_path, "loop-dashboard", heartbeat_interval_seconds=0.01
    )
    second_payload = json.loads(
        (tmp_path / ".codex/service-runtime/loop-dashboard.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(children) == 2
    assert first_launch_fingerprint != second_launch_fingerprint
    assert first_launch_head != second_launch_head
    assert first_payload["code_fingerprint"] == first_launch_fingerprint
    assert first_payload["git_head"] == first_launch_head
    assert second_payload["code_fingerprint"] == second_launch_fingerprint
    assert second_payload["git_head"] == second_launch_head


def test_managed_runtime_child_runs_shell_template_without_execing_cd(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services

    calls: list[tuple[list[str], dict[str, object]]] = []

    def popen(arguments: list[str], **options: object) -> object:
        calls.append((arguments, options))
        return object()

    monkeypatch.setattr(services, "_Popen", popen)

    services._start_managed_child(
        tmp_path.resolve(), services._MANAGED_SERVICES["loop-dashboard"]
    )

    assert calls[0][0][:2] == ["bash", "-lc"]
    assert calls[0][0][2].startswith("cd ")
    assert not calls[0][0][2].startswith("exec cd ")


def test_dashboard_managed_child_receives_stable_private_cursor_secret(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services

    calls: list[dict[str, object]] = []

    def popen(_arguments: list[str], **options: object) -> object:
        calls.append(options)
        return object()

    monkeypatch.setattr(services, "_Popen", popen)

    service = services._MANAGED_SERVICES["loop-dashboard"]
    services._start_managed_child(tmp_path.resolve(), service)
    services._start_managed_child(tmp_path.resolve(), service)

    secret_path = tmp_path / ".codex/session-state/loop-dashboard/cursor-secret"
    secret = secret_path.read_text(encoding="ascii").strip()
    first_environment = calls[0]["env"]
    second_environment = calls[1]["env"]

    assert isinstance(first_environment, dict)
    assert isinstance(second_environment, dict)
    assert len(secret.encode()) >= 32
    assert secret_path.stat().st_mode & 0o777 == 0o600
    assert first_environment["LOOP_DASHBOARD_CURSOR_SECRET"] == secret
    assert second_environment["LOOP_DASHBOARD_CURSOR_SECRET"] == secret


@pytest.mark.parametrize(
    ("heartbeat_at", "fingerprint_kind", "expected_summary"),
    [
        (None, "expected", "heartbeat not verified"),
        ("2000-01-01T00:00:00Z", "expected", "heartbeat not verified"),
        ("current", "old", "runtime code fingerprint mismatch"),
    ],
)
def test_restart_requires_independent_runtime_heartbeat_and_fingerprint_evidence(
    tmp_path: Path,
    monkeypatch,
    heartbeat_at: str | None,
    fingerprint_kind: str,
    expected_summary: str,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResultClass

    dashboard_code = tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'replacement'\n", encoding="utf-8")
    expected_fingerprint = services._service_code_fingerprint(
        tmp_path, "loop-dashboard"
    )
    emitted_fingerprint = (
        expected_fingerprint if fingerprint_kind == "expected" else f"sha256:{'1' * 64}"
    )
    restarted = False
    emitted_heartbeat: str | None = None

    def process_probe(session_name: str, _timeout: float) -> dict[str, object]:
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": 2203 if restarted else 1103,
            "process_alive": restarted,
            "command": "python3",
        }

    def endpoint_probe(_endpoint: str, _timeout: float) -> dict[str, object]:
        return {
            "status": "healthy" if restarted else "unhealthy",
            "summary": "HTTP 200" if restarted else "connection error",
            "details": {"status_code": 200} if restarted else {},
        }

    def run_tmux(
        arguments: tuple[str, ...], _cwd: Path, _timeout: float
    ) -> dict[str, object]:
        nonlocal emitted_heartbeat, restarted
        if arguments[0] == "new-session":
            restarted = True
            emitted_heartbeat = (
                services._utc_now() if heartbeat_at == "current" else heartbeat_at
            )
            _write_runtime_evidence(
                tmp_path,
                "loop-dashboard",
                process_id=2203,
                code_fingerprint=emitted_fingerprint,
                heartbeat_at=emitted_heartbeat,
            )
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(services, "_tmux_process_probe", process_probe)
    monkeypatch.setattr(services, "_http_probe", endpoint_probe)
    monkeypatch.setattr(services, "_run_tmux_command", run_tmux)
    monkeypatch.setattr(services.time, "sleep", lambda _seconds: None)

    result = services.restart_managed_service(tmp_path, "loop-dashboard")
    persisted = json.loads(
        (tmp_path / ".codex/service-runtime/loop-dashboard.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert expected_summary in result.summary
    assert persisted["code_fingerprint"] == emitted_fingerprint
    assert persisted.get("heartbeat_at") == emitted_heartbeat


def test_changing_observations_coalesce_into_one_restart_operation(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionType

    probe_state = {
        "process_id": 1103,
        "error_class": "connection_error",
    }

    def process_probe(session_name: str, timeout_seconds: float) -> dict[str, object]:
        if session_name != "loop-dashboard":
            return _healthy_process_probe(session_name, timeout_seconds)
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": probe_state["process_id"],
            "process_alive": False,
            "command": "python3",
        }

    def endpoint_probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        if endpoint.endswith(":8766/api/health"):
            return {
                "status": "unhealthy",
                "summary": "connection error",
                "details": {"error_class": probe_state["error_class"]},
            }
        return _healthy_contract_probe(endpoint, timeout_seconds)

    with _store(tmp_path, FakeClock()) as store:
        options = {
            "http_probe": endpoint_probe,
            "process_probe": process_probe,
            "version": "test-version",
        }
        services.observe_runtime_health(tmp_path, store, **options)
        first = [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
            and json.loads(row["payload_json"])["service_id"] == "loop-dashboard"
        ]
        assert len(first) == 1
        first_payload = json.loads(first[0]["payload_json"])

        probe_state.update(process_id=None, error_class="timeout")
        services.observe_runtime_health(tmp_path, store, **options)
        changed = [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
            and json.loads(row["payload_json"])["service_id"] == "loop-dashboard"
        ]

    assert len(changed) == 1
    assert changed[0]["action_id"] == first[0]["action_id"]
    assert json.loads(changed[0]["payload_json"])[
        "observed_state_fingerprint"
    ] != first_payload["observed_state_fingerprint"]


def test_recovery_cancels_pending_restart_and_next_outage_gets_new_operation(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionType

    state = {"down": True}

    def process_probe(session_name: str, timeout_seconds: float) -> dict[str, object]:
        if session_name != "loop-dashboard":
            return _healthy_process_probe(session_name, timeout_seconds)
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": 1103,
            "process_alive": not state["down"],
            "command": "python3",
        }

    def endpoint_probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        if endpoint.endswith(":8766/api/health") and state["down"]:
            return {
                "status": "unhealthy",
                "summary": "connection error",
                "details": {"error_class": "connection_error"},
            }
        return _healthy_contract_probe(endpoint, timeout_seconds)

    def dashboard_actions(store: SupervisorStore) -> list[dict[str, object]]:
        return [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
            and json.loads(row["payload_json"])["service_id"] == "loop-dashboard"
        ]

    with _store(tmp_path, FakeClock()) as store:
        store.touch_worker("worker-01")
        options = {
            "http_probe": endpoint_probe,
            "process_probe": process_probe,
            "version": "test-version",
        }
        services.observe_runtime_health(tmp_path, store, **options)
        first = dashboard_actions(store)[0]

        state["down"] = False
        services.observe_runtime_health(tmp_path, store, **options)
        recovered = dashboard_actions(store)

        state["down"] = True
        services.observe_runtime_health(tmp_path, store, **options)
        next_outage = dashboard_actions(store)

    assert recovered[0]["status"] == "cancelled"
    assert len(next_outage) == 2
    assert next_outage[0]["action_id"] == first["action_id"]
    assert next_outage[1]["action_id"] != first["action_id"]
    assert next_outage[1]["status"] == "pending"


def test_expired_prior_outage_lease_is_cancelled_before_current_outage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResult, ActionResultClass

    clock = FakeClock()
    restart_calls: list[str] = []

    def restart(_root: Path, service_id: str) -> ActionResult:
        restart_calls.append(service_id)
        return ActionResult(ActionResultClass.SUCCESS, "current outage recovered")

    monkeypatch.setattr(services, "restart_managed_service", restart)
    with _store(tmp_path, clock) as store:
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        action_a = services._enqueue_service_restart_actions(tmp_path, store)[0]
        leased_a = store.claim_service_restart_action(
            action_a,
            "crashed-supervisor",
            service_id="loop-dashboard",
            outage_id=str(store.get_action(action_a).payload["outage_id"]),
            lease_seconds=10,
        )
        assert leased_a is not None

        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="healthy",
            details={"endpoint_verified": True, "process_alive": True},
        )
        services._enqueue_service_restart_actions(tmp_path, store)
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        action_b = services._enqueue_service_restart_actions(tmp_path, store)[0]
        assert action_b != action_a

        clock.advance(seconds=11)
        stale_pass = services.run_service_keeper_once(
            tmp_path, store, owner_id="recovered-supervisor"
        )
        stale_a = store.get_action(action_a)
        pending_b = store.get_action(action_b)

        current_pass = services.run_service_keeper_once(
            tmp_path, store, owner_id="recovered-supervisor"
        )
        completed_b = store.get_action(action_b)
        attempts = store.fetch_all("action_attempts")

    assert stale_pass["claimed"] == 0
    assert stale_a.status == "cancelled"
    assert pending_b.status == "pending"
    assert restart_calls == ["loop-dashboard"]
    assert current_pass["claimed"] == 1
    assert completed_b.status == "completed"
    assert len(attempts) == 1
    assert attempts[0]["action_id"] == action_b


def test_reobserving_current_cancelled_outage_rearms_without_duplicate(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import services

    with _store(tmp_path, FakeClock()) as store:
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        action_id = services._enqueue_service_restart_actions(tmp_path, store)[0]
        action_payload = json.loads(store.fetch_all("actions")[0]["payload_json"])
        store.cancel_pending_service_restarts(
            "loop-dashboard", outage_id=action_payload["outage_id"]
        )

        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": True},
        )
        observed = services._enqueue_service_restart_actions(tmp_path, store)
        actions = store.fetch_all("actions")

    assert observed == [action_id]
    assert len(actions) == 1
    assert actions[0]["status"] == "pending"


def test_unhealthy_endpoint_and_offline_worker_do_not_gain_synthetic_heartbeats(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import services

    def process_probe(session_name: str, timeout_seconds: float) -> dict[str, object]:
        if session_name == "loop-supervisor-worker":
            return {
                "session_name": session_name,
                "session_exists": False,
                "process_id": None,
                "process_alive": False,
                "command": "",
            }
        return _healthy_process_probe(session_name, timeout_seconds)

    def endpoint_probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        if endpoint.endswith(":8766/api/health"):
            return {
                "status": "unhealthy",
                "summary": "connection error",
                "details": {"error_class": "connection_error"},
            }
        return _healthy_contract_probe(endpoint, timeout_seconds)

    with _store(tmp_path, FakeClock()) as store:
        services.observe_runtime_health(
            tmp_path,
            store,
            http_probe=endpoint_probe,
            process_probe=process_probe,
            version="test-version",
        )
        rows = {row["service_id"]: row for row in store.fetch_all("services")}

    assert rows["loop-dashboard"]["heartbeat_at"] == ""
    assert rows["supervisor-worker"]["heartbeat_at"] == ""


def test_dead_tmux_process_queues_one_restart_and_supervisor_verifies_replacement(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionType

    dashboard_code = (
        tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    )
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'replacement'\n", encoding="utf-8")
    restarted = False
    dead_process_id = 1103
    commands: list[tuple[str, ...]] = []
    fingerprint = services._service_code_fingerprint(tmp_path, "loop-dashboard")

    def process_probe(session_name: str, _timeout_seconds: float) -> dict[str, object]:
        if session_name == "loop-dashboard":
            return {
                "session_name": session_name,
                "session_exists": True,
                "process_id": 2203 if restarted else dead_process_id,
                "process_alive": restarted,
                "command": "python3",
            }
        return _healthy_process_probe(session_name, _timeout_seconds)

    def endpoint_probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        if endpoint.endswith(":8766/api/health") and not restarted:
            return {
                "status": "unhealthy",
                "summary": "connection error",
                "details": {"error_class": "connection_error"},
            }
        return _healthy_contract_probe(endpoint, timeout_seconds)

    with _store(tmp_path, FakeClock()) as store:
        store.touch_worker("worker-01")
        observe_options = {
            "http_probe": endpoint_probe,
            "process_probe": process_probe,
            "version": "test-version",
        }
        services.observe_runtime_health(tmp_path, store, **observe_options)
        dead_process_id = 1203
        services.observe_runtime_health(tmp_path, store, **observe_options)
        restart_actions = [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
        ]

    assert len(restart_actions) == 1
    assert restart_actions[0]["status"] == "pending"
    assert json.loads(restart_actions[0]["payload_json"])["service_id"] == "loop-dashboard"

    def run_tmux(
        arguments: tuple[str, ...], _cwd: Path, _timeout_seconds: float
    ) -> dict[str, object]:
        nonlocal restarted
        commands.append(arguments)
        if arguments[0] == "new-session":
            restarted = True
            _write_runtime_evidence(
                tmp_path,
                "loop-dashboard",
                process_id=2203,
                code_fingerprint=fingerprint,
                heartbeat_at=services._utc_now(),
            )
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(services, "_run_tmux_command", run_tmux)
    monkeypatch.setattr(services, "_tmux_process_probe", process_probe)
    monkeypatch.setattr(services, "_http_probe", endpoint_probe)
    monkeypatch.setattr(services.time, "sleep", lambda _seconds: None)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        result = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )
        attempts = store.fetch_all("action_attempts")
        actions = [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
        ]
        dashboard = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "loop-dashboard"
        )

    details = json.loads(dashboard["details_json"])
    assert result["completed"] == 1
    assert len(actions) == 1
    assert actions[0]["status"] == "completed"
    assert len(attempts) == 1
    assert attempts[0]["worker_id"] == "supervisor-service-keeper-test"
    assert [command[0] for command in commands] == ["kill-session", "new-session"]
    assert dashboard["status"] == "healthy"
    assert dashboard["process_id"] == 2203
    assert dashboard["heartbeat_at"]
    assert dashboard["version"].startswith("sha256:")
    assert details["endpoint_verified"] is True
    assert details["pid_verified"] is True
    assert details["heartbeat_verified"] is True
    assert details["version_verified"] is True


def test_offline_worker_without_any_heartbeat_queues_restart_for_supervisor(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionType

    def process_probe(session_name: str, timeout_seconds: float) -> dict[str, object]:
        if session_name == "loop-supervisor-worker":
            return {
                "session_name": session_name,
                "session_exists": False,
                "process_id": None,
                "process_alive": False,
                "command": "",
            }
        return _healthy_process_probe(session_name, timeout_seconds)

    with _store(tmp_path, FakeClock()) as store:
        services.observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=process_probe,
            version="test-version",
        )
        actions = [
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
        ]

    assert len(actions) == 1
    assert json.loads(actions[0]["payload_json"])["service_id"] == "supervisor-worker"
    assert actions[0]["queue_owner"] == "supervisor"


def test_supervisor_service_keeper_executes_without_worker_heartbeat(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import (
        ActionOwner,
        ActionRequest,
        ActionResult,
        ActionResultClass,
        ActionType,
    )

    monkeypatch.setattr(
        services,
        "restart_managed_service",
        lambda _root, service_id: ActionResult(
            ActionResultClass.SUCCESS,
            f"restarted {service_id}",
        ),
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_service_observation(
            service_id="supervisor-worker",
            status="offline",
            details={"worker_count": 0, "process_alive": False},
        )
        outage_id = json.loads(store.fetch_all("services")[0]["details_json"])[
            "outage_id"
        ]
        request = ActionRequest(
            action_id="service-restart-supervisor-worker-outage-1",
            run_id="service-keeper",
            run_revision=0,
            policy="autonomous_knowledge",
            phase="repair_needed",
            action_type=ActionType.RESTART_SERVICE,
            idempotency_key=f"service-restart:supervisor-worker:{outage_id}",
            queue_owner=ActionOwner.SUPERVISOR,
            repo_relative_root=".",
            task_id=f"service:supervisor-worker:{outage_id}",
            next_action=ActionType.RESTART_SERVICE.value,
            payload={"service_id": "supervisor-worker", "outage_id": outage_id},
        )
        store.enqueue_action(request)
        report = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-a"
        )
        action = store.get_action(request.action_id)
        attempts = store.fetch_all("action_attempts")
        workers = store.fetch_all("workers")

    assert report == {
        "claimed": 1,
        "completed": 1,
        "failed": 0,
        "action_ids": [request.action_id],
    }
    assert action.status == "completed"
    assert len(attempts) == 1
    assert attempts[0]["worker_id"] == "supervisor-service-keeper-a"
    assert workers == []


def test_retryable_service_restart_rearms_same_outage_after_cadence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResult, ActionResultClass

    clock = FakeClock()
    outcomes = iter(
        (
            ActionResult(
                ActionResultClass.RETRYABLE_FAILURE,
                "replacement not ready",
                failure_key="service-restart:loop-dashboard",
                error_class="service_verification_failed",
                checkpoint="service-restart:verification-failed",
            ),
            ActionResult(
                ActionResultClass.SUCCESS,
                "replacement verified",
                checkpoint="service-restart:verified",
            ),
        )
    )
    restart_calls: list[str] = []

    def restart(_root: Path, service_id: str) -> ActionResult:
        restart_calls.append(service_id)
        return next(outcomes)

    monkeypatch.setattr(services, "restart_managed_service", restart)
    with _store(tmp_path, clock) as store:
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        action_id = services._enqueue_service_restart_actions(tmp_path, store)[0]

        first = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )
        services._enqueue_service_restart_actions(tmp_path, store)
        rearmed = store.get_action(action_id)

        clock.advance(seconds=5)
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": True},
        )
        services._enqueue_service_restart_actions(tmp_path, store)
        clock.advance(seconds=5)
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        services._enqueue_service_restart_actions(tmp_path, store)
        coalesced = store.get_action(action_id)
        before_deadline = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )

        clock.advance(seconds=services.SERVICE_CADENCE_SECONDS - 10)
        second = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )
        action = store.get_action(action_id)
        actions = store.fetch_all("actions")
        attempts = store.fetch_all("action_attempts")

    assert first["failed"] == 1
    assert rearmed.status == "pending"
    assert rearmed.not_before == "2026-07-15T00:00:30.000000Z"
    assert coalesced.not_before == rearmed.not_before
    assert before_deadline["claimed"] == 0
    assert second["claimed"] == 1
    assert second["completed"] == 1
    assert action.status == "completed"
    assert len(actions) == 1
    assert restart_calls == ["loop-dashboard", "loop-dashboard"]
    assert [row["result_class"] for row in attempts] == [
        ActionResultClass.RETRYABLE_FAILURE.value,
        ActionResultClass.SUCCESS.value,
    ]


@pytest.mark.parametrize(
    "result_class",
    [ActionResultClass.TERMINAL_FAILURE, ActionResultClass.POLICY_BLOCK],
)
def test_terminal_service_restart_failure_is_not_rearmed(
    tmp_path: Path,
    monkeypatch,
    result_class: ActionResultClass,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResult

    clock = FakeClock()
    monkeypatch.setattr(
        services,
        "restart_managed_service",
        lambda _root, _service_id: ActionResult(
            result_class,
            "restart rejected by policy",
            failure_key="service-restart:loop-dashboard",
            error_class="service_restart_policy",
            checkpoint="service-restart:rejected",
        ),
    )
    with _store(tmp_path, clock) as store:
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False, "process_alive": False},
        )
        action_id = services._enqueue_service_restart_actions(tmp_path, store)[0]
        services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )

        services._enqueue_service_restart_actions(tmp_path, store)
        clock.advance(seconds=services.SERVICE_CADENCE_SECONDS)
        later = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )
        action = store.get_action(action_id)
        attempts = store.fetch_all("action_attempts")

    assert action.status == "failed"
    assert action.not_before == ""
    assert later["claimed"] == 0
    assert len(attempts) == 1


def test_two_supervisor_service_keeper_claimers_execute_one_restart(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import (
        ActionOwner,
        ActionRequest,
        ActionResult,
        ActionResultClass,
        ActionType,
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False},
        )
        outage_id = json.loads(store.fetch_all("services")[0]["details_json"])[
            "outage_id"
        ]
        request = ActionRequest(
            action_id="service-restart-loop-dashboard-outage-1",
            run_id="service-keeper",
            run_revision=0,
            policy="autonomous_knowledge",
            phase="repair_needed",
            action_type=ActionType.RESTART_SERVICE,
            idempotency_key=f"service-restart:loop-dashboard:{outage_id}",
            queue_owner=ActionOwner.SUPERVISOR,
            repo_relative_root=".",
            task_id=f"service:loop-dashboard:{outage_id}",
            next_action=ActionType.RESTART_SERVICE.value,
            payload={"service_id": "loop-dashboard", "outage_id": outage_id},
        )
        store.enqueue_action(request)

    entered = threading.Event()
    release = threading.Event()
    restart_calls: list[str] = []
    reports: list[dict[str, object]] = []

    def restart(_root: Path, service_id: str) -> ActionResult:
        restart_calls.append(service_id)
        entered.set()
        assert release.wait(timeout=5)
        return ActionResult(ActionResultClass.SUCCESS, "replacement verified")

    def claim(owner_id: str) -> None:
        with SupervisorStore.open(tmp_path) as store:
            store.migrate()
            reports.append(
                services.run_service_keeper_once(
                    tmp_path, store, owner_id=owner_id
                )
            )

    monkeypatch.setattr(services, "restart_managed_service", restart)
    first = threading.Thread(target=claim, args=("supervisor-a",))
    second = threading.Thread(target=claim, args=("supervisor-b",))
    first.start()
    assert entered.wait(timeout=5)
    second.start()
    second.join(timeout=5)
    release.set()
    first.join(timeout=5)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        attempts = store.fetch_all("action_attempts")

    assert not first.is_alive()
    assert not second.is_alive()
    assert restart_calls == ["loop-dashboard"]
    assert len(attempts) == 1
    assert sum(int(report["claimed"]) for report in reports) == 1


def test_service_keeper_cancels_superseded_pending_identity_before_restart(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import (
        ActionOwner,
        ActionRequest,
        ActionResult,
        ActionResultClass,
        ActionType,
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_service_observation(
            service_id="loop-dashboard",
            status="unhealthy",
            details={"endpoint_verified": False},
        )
        outage_id = json.loads(store.fetch_all("services")[0]["details_json"])[
            "outage_id"
        ]
        requests = [
            ActionRequest(
                action_id=f"legacy-service-restart-{index}",
                run_id="service-keeper",
                run_revision=0,
                policy="autonomous_knowledge",
                phase="repair_needed",
                action_type=ActionType.RESTART_SERVICE,
                idempotency_key=f"service-restart:loop-dashboard:{outage_id}-{index}",
                queue_owner=ActionOwner.SUPERVISOR,
                repo_relative_root=".",
                task_id=f"service:loop-dashboard:{outage_id}:{index}",
                next_action=ActionType.RESTART_SERVICE.value,
                payload={
                    "service_id": "loop-dashboard",
                    "outage_id": outage_id,
                    "observed_state_fingerprint": f"sha256:{index:064x}",
                },
            )
            for index in (1, 2)
        ]
        for request in requests:
            store.enqueue_action(request)

    restart_calls: list[str] = []

    def restart(_root: Path, service_id: str) -> ActionResult:
        restart_calls.append(service_id)
        return ActionResult(ActionResultClass.SUCCESS, "replacement verified")

    monkeypatch.setattr(services, "restart_managed_service", restart)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        report = services.run_service_keeper_once(
            tmp_path, store, owner_id="supervisor-service-keeper-test"
        )
        actions = store.fetch_all("actions")
        attempts = store.fetch_all("action_attempts")

    assert report["claimed"] == 1
    assert restart_calls == ["loop-dashboard"]
    assert len(attempts) == 1
    assert {row["status"] for row in actions} == {"completed", "cancelled"}


def test_recovered_worker_id_is_not_replaced_by_hard_coded_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResultClass

    worker_code = tmp_path / "scripts/loop_supervisor/worker.py"
    worker_code.parent.mkdir(parents=True)
    worker_code.write_text("WORKER = 'healthy'\n", encoding="utf-8")
    fingerprint = services._service_code_fingerprint(tmp_path, "supervisor-worker")
    _write_runtime_evidence(
        tmp_path,
        "supervisor-worker",
        process_id=2203,
        code_fingerprint=fingerprint,
        heartbeat_at=services._utc_now(),
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.record_worker_heartbeat("worker-01")

    monkeypatch.setattr(
        services,
        "_tmux_process_probe",
        lambda session_name, _timeout: {
            "session_name": session_name,
            "session_exists": True,
            "process_id": 2203,
            "process_alive": True,
            "command": "python3",
        },
    )
    monkeypatch.setattr(
        services,
        "_run_tmux_command",
        lambda *_args: pytest.fail("already recovered worker was replaced"),
    )

    result = services.restart_managed_service(tmp_path, "supervisor-worker")

    assert result.result_class is ActionResultClass.SUCCESS
    assert result.checkpoint == "service-restart:already-healthy"


def test_restart_action_does_not_replace_service_that_recovered_before_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import services
    from scripts.loop_supervisor.models import ActionResultClass

    dashboard_code = (
        tmp_path / "apps/loop_dashboard/backend/loop_dashboard/main.py"
    )
    dashboard_code.parent.mkdir(parents=True)
    dashboard_code.write_text("APP = 'already-healthy'\n", encoding="utf-8")
    fingerprint = services._service_code_fingerprint(tmp_path, "loop-dashboard")
    runtime_path = tmp_path / ".codex/service-runtime/loop-dashboard.json"
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "service": "loop-dashboard",
                "tmux_session": "loop-dashboard",
                "pid": 2203,
                "cwd": str(tmp_path),
                "code_fingerprint": fingerprint,
                    "heartbeat_at": services._utc_now(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        services,
        "_tmux_process_probe",
        lambda session_name, _timeout: {
            "session_name": session_name,
            "session_exists": True,
            "process_id": 2203,
            "process_alive": True,
            "command": "python3",
        },
    )
    monkeypatch.setattr(
        services,
        "_http_probe",
        lambda _endpoint, _timeout: {
            "status": "healthy",
            "summary": "HTTP 200",
            "details": {"status_code": 200},
        },
    )
    monkeypatch.setattr(
        services,
        "_run_tmux_command",
        lambda *_args: pytest.fail("verified healthy service was replaced"),
    )

    result = services.restart_managed_service(tmp_path, "loop-dashboard")

    assert result.result_class is ActionResultClass.SUCCESS
    assert result.checkpoint == "service-restart:already-healthy"


def test_http_probe_parses_bounded_json_payload(monkeypatch) -> None:
    from scripts.loop_supervisor import services

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def getcode(self) -> int:
            return 200

        def read(self, limit: int) -> bytes:
            assert limit <= services.MAX_RESPONSE_BYTES + 1
            return b'{"status":"available","diagnostics":[]}'

    class Opener:
        def open(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr(services, "build_opener", lambda *_args: Opener())

    result = services._http_probe("http://127.0.0.1:8766/api/supervisor", 1.0)

    assert result["payload"] == {"status": "available", "diagnostics": []}


@pytest.mark.parametrize(
    ("endpoint", "expected_accept"),
    [
        ("http://127.0.0.1:5173/", "text/html"),
        ("http://127.0.0.1:8766/api/health", "application/json"),
    ],
)
def test_http_probe_uses_endpoint_appropriate_accept_header(
    monkeypatch,
    endpoint: str,
    expected_accept: str,
) -> None:
    from scripts.loop_supervisor import services

    observed_accept: list[str | None] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def getcode(self) -> int:
            return 200

        def read(self, _limit: int) -> bytes:
            return b""

    class Opener:
        def open(self, request, **_kwargs: object) -> Response:
            observed_accept.append(request.get_header("Accept"))
            return Response()

    monkeypatch.setattr(services, "build_opener", lambda *_args: Opener())

    result = services._http_probe(endpoint, 1.0)

    assert result["status"] == "healthy"
    assert observed_accept == [expected_accept]


def test_freshness_summary_is_redacted_and_bounded(tmp_path: Path) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def unsafe_probe(_endpoint: str, _timeout_seconds: float) -> dict[str, object]:
        return {
            "status": "unhealthy",
            "summary": "token=secret-value " + "x" * 5000,
            "details": {"error_class": "probe_error"},
        }

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=unsafe_probe,
            version="test-version",
        )
        summaries = [row["summary"] for row in store.fetch_all("freshness_checks")]

    assert summaries
    assert all("secret-value" not in summary for summary in summaries)
    assert all("[REDACTED]" in summary for summary in summaries)
    assert all(len(summary) <= 1024 for summary in summaries)


def test_wiki_freshness_uses_bounded_metrics_contract(tmp_path: Path) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()
    endpoints: list[str] = []

    def probe(endpoint: str, timeout_seconds: float) -> dict[str, object]:
        endpoints.append(endpoint)
        return _healthy_contract_probe(endpoint, timeout_seconds)

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=probe,
            process_probe=_healthy_process_probe,
            version="test-version",
        )
        wiki = next(
            row
            for row in store.fetch_all("freshness_checks")
            if row["target"] == "wiki"
        )

    assert any(endpoint.endswith("/api/wiki/metrics") for endpoint in endpoints)
    assert not any("/api/wiki/pages" in endpoint for endpoint in endpoints)
    assert wiki["status"] == "fresh"


def test_watch_projects_process_session_reachability_and_worker_heartbeat(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()
    pids = {
        "personal-wiki-crawler-backend": 1101,
        "personal-wiki-crawler-frontend": 1102,
        "loop-dashboard": 1103,
        "loop-supervisor": 1104,
        "loop-supervisor-worker": 1105,
    }

    def process_probe(session_name: str, _timeout_seconds: float) -> dict[str, object]:
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": pids[session_name],
            "process_alive": True,
            "command": "python3",
        }

    with _store(tmp_path, clock) as store:
        store.record_worker_heartbeat("worker-01")
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=process_probe,
            process_id=4242,
            version="test-version",
            runtime_mode="watch",
        )
        services = {row["service_id"]: row for row in store.fetch_all("services")}

    backend = services["crawler-backend"]
    backend_details = backend["details_json"]
    assert backend["process_id"] == 1101
    assert '"reachable":true' in backend_details
    assert '"tmux_session":"personal-wiki-crawler-backend"' in backend_details
    assert '"tmux_session_exists":true' in backend_details
    assert '"process_alive":true' in backend_details
    assert '"freshness":"fresh"' in backend_details
    assert backend["version"] == "test-version"

    supervisor = services["loop-supervisor"]
    assert supervisor["status"] == "healthy"
    assert supervisor["process_id"] == 4242
    assert '"runtime_mode":"watch"' in supervisor["details_json"]
    assert '"tmux_session":"loop-supervisor"' in supervisor["details_json"]

    worker = services["supervisor-worker"]
    assert worker["process_id"] == 1105
    assert worker["heartbeat_at"] == "2026-07-15T00:00:00.000000Z"
    assert '"worker_id":"worker-01"' in worker["details_json"]
    assert '"heartbeat_at":"2026-07-15T00:00:00.000000Z"' in worker["details_json"]


def test_idle_worker_watch_touches_each_poll_and_projects_matching_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.loop_supervisor import worker as worker_runtime
    from scripts.loop_supervisor.services import observe_runtime_health

    touches: list[str] = []
    original_touch = SupervisorStore.touch_worker

    def tracking_touch(store: SupervisorStore, worker_id: str) -> dict[str, object]:
        touches.append(worker_id)
        return original_touch(store, worker_id)

    polls = 0

    def idle_once(_project_root: Path, _worker_id: str):
        nonlocal polls
        polls += 1
        if polls == 2:
            worker_runtime.request_stop("test complete")
        return worker_runtime.WorkerResult(status="idle")

    monkeypatch.setattr(SupervisorStore, "touch_worker", tracking_touch)
    monkeypatch.setattr(worker_runtime, "worker_once", idle_once)
    worker_runtime.clear_stop_request()
    try:
        worker_runtime.worker_watch(tmp_path, "idle-worker", poll_seconds=0.001)
    finally:
        worker_runtime.clear_stop_request()

    def process_probe(session_name: str, _timeout_seconds: float) -> dict[str, object]:
        return {
            "session_name": session_name,
            "session_exists": True,
            "process_id": 1105 if session_name == "loop-supervisor-worker" else 1100,
            "process_alive": True,
            "command": "python3",
        }

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        workers = store.fetch_all("workers")
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=process_probe,
            version="test-version",
            runtime_mode="watch",
        )
        service = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "supervisor-worker"
        )

    details = json.loads(service["details_json"])
    assert polls == 2
    assert touches == ["idle-worker", "idle-worker"]
    assert len(workers) == 1
    assert service["status"] == "healthy"
    assert service["process_id"] == 1105
    assert service["heartbeat_at"] == workers[0]["heartbeat_at"]
    assert details["tmux_session"] == "loop-supervisor-worker"
    assert details["workers"] == [
        {
            "heartbeat_at": workers[0]["heartbeat_at"],
            "status": "healthy",
            "worker_id": "idle-worker",
        }
    ]


def test_once_does_not_publish_transient_process_as_healthy_supervisor(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.services import observe_runtime_health

    clock = FakeClock()

    def process_probe(session_name: str, _timeout_seconds: float) -> dict[str, object]:
        return {
            "session_name": session_name,
            "session_exists": None,
            "process_id": None,
            "process_alive": None,
            "command": "",
        }

    with _store(tmp_path, clock) as store:
        observe_runtime_health(
            tmp_path,
            store,
            http_probe=_healthy_contract_probe,
            process_probe=process_probe,
            process_id=4242,
            version="test-version",
            runtime_mode="once",
        )
        supervisor = next(
            row
            for row in store.fetch_all("services")
            if row["service_id"] == "loop-supervisor"
        )

    assert supervisor["status"] == "unavailable"
    assert supervisor["process_id"] is None
    assert '"runtime_mode":"once"' in supervisor["details_json"]
    assert '"process_scope":"one_shot"' in supervisor["details_json"]


def test_tmux_probe_returns_bounded_process_evidence(monkeypatch) -> None:
    from scripts.loop_supervisor import services

    class Process:
        returncode = 0

        def communicate(self, timeout: float):
            assert timeout == 1.0
            return "loop-dashboard|1234|0|python3\n", ""

        def kill(self) -> None:
            raise AssertionError("healthy tmux probe must not be killed")

    monkeypatch.setattr(services, "_Popen", lambda *_args, **_kwargs: Process())

    result = services._tmux_process_probe("loop-dashboard", 1.0)

    assert result == {
        "session_name": "loop-dashboard",
        "session_exists": True,
        "process_id": 1234,
        "process_alive": True,
        "command": "python3",
    }
