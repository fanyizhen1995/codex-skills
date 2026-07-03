from __future__ import annotations

import httpx
from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import migrate, open_db
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.fetch_service import ChannelNotReadyError, run_source_once
from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


class StaticFetcher:
    def fetch(self, profile):
        return [FetchResult("https://api.example.com/doc", "Doc", "hello", "text/markdown")]


def _insert_channel(
    db,
    channel_id: str,
    *,
    base_url: str = "https://api.example.com",
    kind: str = "api",
    enabled: int = 1,
    auth_required: int = 0,
    auth_mode: str = "none",
    auth_state: str = "ready",
    probe_url: str | None = None,
) -> None:
    if base_url == "https://api.example.com":
        base_url = f"https://{channel_id}.example.com"
    db.execute(
        """
        insert into channels (
          id, target_domain, name, base_url, base_url_normalized, probe_url,
          kind, connector, trust_level, enabled, auth_required, auth_mode, auth_state
        )
        values (?, 'ai_infra', ?, ?, ?, ?, ?, 'generic', 'trusted', ?, ?, ?, ?)
        """,
        (
            channel_id,
            channel_id,
            base_url,
            base_url,
            probe_url,
            kind,
            enabled,
            auth_required,
            auth_mode,
            auth_state,
        ),
    )
    db.commit()


def _insert_source(db, source_id: str, channel_id: str) -> None:
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, auth_state, channel_id, topic, enabled
        )
        values (?, ?, 'web', 'ai_infra', 'https://api.example.com/doc', 'trusted',
                'manual', 1, 0, 'ready', ?, 'topic', 1)
        """,
        (source_id, source_id, channel_id),
    )
    db.commit()


def _probe_client(routes: dict[str, httpx.Response | Exception]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        result = routes.get(str(request.url), httpx.Response(404, text="not found"))
        if isinstance(result, Exception):
            raise result
        return result

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("channel_id", "response", "expected_status", "expected_summary"),
    [
        ("public-ready", httpx.Response(200, text="ok"), "ready", "HTTP 200"),
        ("auth-failed", httpx.Response(401, text="bad synthetic-token-for-test"), "auth_failed", "HTTP 401"),
        ("forbidden", httpx.Response(403, text="forbidden"), "auth_failed", "HTTP 403"),
        (
            "login-wall",
            httpx.Response(200, text='<html><form action="/login"><input name="password"></form></html>'),
            "needs_browser",
            "login form detected",
        ),
        ("captcha", httpx.Response(200, text="captcha required"), "needs_browser", "captcha marker detected"),
        ("js-shell", httpx.Response(200, text="<html><script>app()</script></html>"), "needs_browser", "JS shell"),
    ],
)
def test_probe_records_http_readiness_states(tmp_path, channel_id, response, expected_status, expected_summary):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(
            db,
            channel_id,
            base_url=f"https://{channel_id}.example.com",
            probe_url=f"https://{channel_id}.example.com/probe",
        )

        from crawler_workbench.channel_probe import run_channel_probe

        result = run_channel_probe(
            settings,
            db,
            channel_id,
            client=_probe_client({f"https://{channel_id}.example.com/probe": response}),
        )
        channel = db.execute("select auth_state, last_probe_status, last_probe_summary from channels where id = ?", (channel_id,)).fetchone()
        probe_row = db.execute("select status, http_status, summary from channel_probe_runs where channel_id = ?", (channel_id,)).fetchone()

    assert result["status"] == expected_status
    assert expected_summary in result["summary"]
    assert "synthetic-token-for-test" not in str(result)
    assert channel["auth_state"] == expected_status
    assert channel["last_probe_status"] == expected_status
    assert expected_summary in channel["last_probe_summary"]
    assert probe_row["status"] == expected_status
    assert expected_summary in probe_row["summary"]
    assert "synthetic-token-for-test" not in probe_row["summary"]


def test_probe_records_missing_secret_and_unsupported_states(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(
            db,
            "auth-missing",
            auth_required=1,
            auth_mode="token",
            auth_state="needs_auth_config",
        )
        _insert_channel(db, "mcp-channel", kind="mcp", auth_state="unsupported")

        from crawler_workbench.channel_probe import run_channel_probe

        missing = run_channel_probe(settings, db, "auth-missing")
        unsupported = run_channel_probe(settings, db, "mcp-channel")

    assert missing["status"] == "needs_auth_config"
    assert "secret not configured" in missing["summary"]
    assert unsupported["status"] == "unsupported"
    assert "not supported" in unsupported["summary"]


def test_probe_records_network_failure(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db, "network-failed", probe_url="https://network-failed.example.com/probe")

        from crawler_workbench.channel_probe import run_channel_probe

        result = run_channel_probe(
            settings,
            db,
            "network-failed",
            client=_probe_client({"https://network-failed.example.com/probe": httpx.ConnectTimeout("timed out")}),
        )
        channel = db.execute("select auth_state, last_probe_status from channels where id = 'network-failed'").fetchone()

    assert result["status"] == "network_failed"
    assert "timed out" in result["summary"]
    assert channel["auth_state"] == "network_failed"
    assert channel["last_probe_status"] == "network_failed"


def test_probe_api_returns_history_and_never_leaks_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db, "public-ready", probe_url="https://public-ready.example.com/probe")

    with TestClient(app) as client:
        response = client.post("/api/channels/public-ready/probe")
        assert response.status_code == 200
        history = client.get("/api/channels/public-ready/probe-runs")
        assert history.status_code == 200
        assert history.json()
        assert "synthetic-token-for-test" not in str(history.json())


@pytest.mark.parametrize(
    ("channel_update", "expected"),
    [
        ({"enabled": 0, "auth_state": "ready"}, "channel disabled"),
        ({"enabled": 1, "auth_state": "needs_auth_config"}, "channel not ready: needs_auth_config"),
        ({"enabled": 1, "auth_state": "auth_failed"}, "channel not ready: auth_failed"),
        ({"enabled": 1, "auth_state": "needs_browser"}, "channel not ready: needs_browser"),
        ({"enabled": 1, "auth_state": "unsupported"}, "channel not ready: unsupported"),
    ],
)
def test_source_run_blocks_on_channel_readiness_and_records_failed_run(tmp_path, channel_update, expected):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db, "blocked-channel")
        _insert_source(db, "src", "blocked-channel")
        db.execute(
            "update channels set enabled = ?, auth_state = ? where id = 'blocked-channel'",
            (channel_update["enabled"], channel_update["auth_state"]),
        )
        db.commit()

        with pytest.raises(ChannelNotReadyError, match=expected):
            run_source_once(settings, db, "src", fetcher=StaticFetcher())

        fetch_run = db.execute("select status, error from fetch_runs where source_id = 'src'").fetchone()

    assert fetch_run["status"] == "failed"
    assert expected in fetch_run["error"]


def test_channel_and_source_crud_apis_support_domain_channel_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)

    with TestClient(app) as client:
        created = client.post(
            "/api/channels",
            json={
                "target_domain": "ai_infra",
                "name": "GitHub",
                "base_url": "https://github.com",
                "kind": "web",
                "connector": "github",
                "trust_level": "trusted",
                "auth_required": False,
                "auth_mode": "none",
                "notes": "base channel",
            },
        )
        assert created.status_code == 200
        channel = created.json()
        assert channel["id"]
        assert channel["base_url"] == "https://github.com"

        updated = client.patch(f"/api/channels/{channel['id']}", json={"notes": "updated", "enabled": False})
        assert updated.status_code == 200
        assert updated.json()["notes"] == "updated"
        assert updated.json()["enabled"] is False

        source = client.post(
            "/api/sources",
            json={
                "id": "nccl-github",
                "name": "NCCL GitHub",
                "type": "github",
                "target_domain": "ai_infra",
                "url": "https://github.com/NVIDIA/nccl",
                "channel_id": channel["id"],
                "trust_level": "trusted",
                "schedule": "manual",
                "auto_ingest": False,
                "auth_required": False,
                "baseline_on_first_run": False,
                "topic": "NCCL",
                "enabled": True,
            },
        )
        assert source.status_code == 200
        assert source.json()["channel_id"] == channel["id"]
        assert source.json()["fetcher_type"] == "github_repo"

        patched_source = client.patch("/api/sources/nccl-github", json={"enabled": False, "topic": "NCCL repo"})
        assert patched_source.status_code == 200
        assert patched_source.json()["enabled"] is False
        assert patched_source.json()["topic"] == "NCCL repo"

        delete_channel = client.delete(f"/api/channels/{channel['id']}")
        assert delete_channel.status_code == 409

        delete_source = client.delete("/api/sources/nccl-github")
        assert delete_source.status_code == 200
        assert delete_source.json()["deleted"] is True

        delete_channel_after_source = client.delete(f"/api/channels/{channel['id']}")
        assert delete_channel_after_source.status_code == 200
        assert delete_channel_after_source.json()["deleted"] is True
