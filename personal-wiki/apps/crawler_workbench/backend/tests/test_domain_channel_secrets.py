from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import migrate, open_db
from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


def _insert_channel(db, channel_id: str = "ai-infra-api-example-com", *, auth_required: int = 1) -> None:
    db.execute(
        """
        insert into channels (
          id, target_domain, name, base_url, base_url_normalized, kind, connector,
          trust_level, enabled, auth_required, auth_mode, auth_state
        )
        values (?, 'ai_infra', 'Example API', 'https://api.example.com',
                'https://api.example.com', 'api', 'generic', 'trusted',
                1, ?, 'token', 'needs_auth_config')
        """,
        (channel_id, auth_required),
    )
    db.commit()


def test_channel_secret_write_replace_delete_never_returns_plaintext(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db)

    with TestClient(app) as client:
        created = client.post(
            "/api/channels/ai-infra-api-example-com/secret",
            json={"secret_kind": "token", "secret": "synthetic-token-for-test"},
        )
        assert created.status_code == 200
        created_payload = created.json()
        assert created_payload["secret_configured"] is True
        assert "synthetic-token-for-test" not in str(created_payload)

        channels = client.get("/api/channels", params={"domain": "ai_infra"}).json()
        channel = next(item for item in channels if item["id"] == "ai-infra-api-example-com")
        assert channel["secret_configured"] is True
        assert channel["auth_state"] == "ready"
        assert "synthetic-token-for-test" not in str(channels)

        replaced = client.post(
            "/api/channels/ai-infra-api-example-com/secret",
            json={"secret_kind": "token", "secret": "replacement-synthetic-token"},
        )
        assert replaced.status_code == 200
        assert "replacement-synthetic-token" not in str(replaced.json())

        deleted = client.delete("/api/channels/ai-infra-api-example-com/secret")
        assert deleted.status_code == 200
        assert deleted.json()["secret_configured"] is False

        channel_after_delete = next(
            item for item in client.get("/api/channels", params={"domain": "ai_infra"}).json()
            if item["id"] == "ai-infra-api-example-com"
        )
        assert channel_after_delete["secret_configured"] is False
        assert channel_after_delete["auth_state"] == "needs_auth_config"

    key_path = settings.resolved_state_dir / "secrets.key"
    assert key_path.exists()
    if hasattr(key_path.stat(), "st_mode"):
        assert key_path.stat().st_mode & 0o077 == 0

    with open_db(settings.database_path) as db:
        rows = db.execute("select secret_kind, ciphertext from channel_secrets").fetchall()
    assert rows == []


def test_missing_secret_key_fails_closed_when_encrypted_rows_exist(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db)

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/channels/ai-infra-api-example-com/secret",
            json={"secret_kind": "token", "secret": "synthetic-token-for-test"},
        )
        assert response.status_code == 200

    key_path = settings.resolved_state_dir / "secrets.key"
    key_path.unlink()

    from crawler_workbench.channel_secrets import SecretKeyUnavailableError, get_channel_secret

    with open_db(settings.database_path) as db:
        with pytest.raises(SecretKeyUnavailableError):
            get_channel_secret(settings, db, "ai-infra-api-example-com")


def test_secret_plaintext_is_not_stored_in_database(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_channel(db)

    with TestClient(app) as client:
        response = client.post(
            "/api/channels/ai-infra-api-example-com/secret",
            json={"secret_kind": "token", "secret": "synthetic-token-for-test"},
        )
        assert response.status_code == 200

    db_bytes = settings.database_path.read_bytes()
    assert b"synthetic-token-for-test" not in db_bytes

