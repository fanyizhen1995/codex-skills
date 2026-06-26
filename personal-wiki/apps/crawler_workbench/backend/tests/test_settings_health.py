from fastapi.testclient import TestClient

from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


def test_settings_defaults_point_at_personal_wiki(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    assert settings.bind_host == "0.0.0.0"
    assert settings.bind_port == 8765
    assert settings.wiki_root == tmp_path / "personal-wiki"
    assert settings.database_path == tmp_path / ".state" / "workbench.sqlite3"
    assert "codex" in settings.codex_command


def test_health_endpoint_reports_warning(tmp_path):
    app = create_app(Settings(repo_root=tmp_path, state_dir=tmp_path / ".state"))
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["bind_host"] == "0.0.0.0"
    assert data["authenticated"] is False
    assert "trusted network" in data["warning"]
