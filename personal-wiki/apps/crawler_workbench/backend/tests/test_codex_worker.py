import subprocess

import pytest
from fastapi.testclient import TestClient

from crawler_workbench.codex_worker import build_query_prompt, run_codex_job
from crawler_workbench.db import connect, migrate
from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


def test_query_prompt_requires_personal_wiki_manager_and_no_edits(tmp_path):
    prompt = build_query_prompt("ai_infra", "NCCL trend?", persist=False)
    assert "使用 personal-wiki-manager" in prompt
    assert "目标 domain: ai_infra" in prompt
    assert "不要修改文件" in prompt
    assert "引用路径" in prompt


def test_codex_job_uses_fake_codex_executable(tmp_path):
    fake = tmp_path / "codex"
    fake.write_text("#!/usr/bin/env bash\necho answer from fake codex\n", encoding="utf-8")
    fake.chmod(0o755)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command=str(fake))
    with connect(settings.database_path) as db:
        migrate(db)
        job_id = run_codex_job(settings, db, "query", "ai_infra", "Question", persist=False)
        row = db.execute("select status, stdout, exit_code from codex_jobs where id = ?", (job_id,)).fetchone()
    assert row["status"] == "succeeded"
    assert "answer from fake codex" in row["stdout"]
    assert row["exit_code"] == 0


def test_codex_job_records_missing_executable_as_failed(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command=str(tmp_path / "missing-codex"))
    with connect(settings.database_path) as db:
        migrate(db)
        job_id = run_codex_job(settings, db, "query", "ai_infra", "Question", persist=False)
        row = db.execute("select status, stderr, exit_code, finished_at from codex_jobs where id = ?", (job_id,)).fetchone()
    assert row["status"] == "failed"
    assert "missing-codex" in row["stderr"]
    assert row["exit_code"] == -1
    assert row["finished_at"] is not None


def test_codex_job_records_timeout_as_failed(tmp_path, monkeypatch):
    def raise_timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr("crawler_workbench.codex_worker.subprocess.run", raise_timeout)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command="codex")
    with connect(settings.database_path) as db:
        migrate(db)
        job_id = run_codex_job(settings, db, "query", "ai_infra", "Question", persist=False)
        row = db.execute("select status, stderr, exit_code, finished_at from codex_jobs where id = ?", (job_id,)).fetchone()
    assert row["status"] == "failed"
    assert "timed out" in row["stderr"]
    assert row["exit_code"] == -1
    assert row["finished_at"] is not None


def test_query_only_codex_job_uses_read_only_sandbox(tmp_path, monkeypatch):
    fake = tmp_path / "codex"
    args_path = tmp_path / "args.txt"
    monkeypatch.setenv("CODEX_ARGS_PATH", str(args_path))
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$@" > "$CODEX_ARGS_PATH"\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command=str(fake))
    with connect(settings.database_path) as db:
        migrate(db)
        run_codex_job(settings, db, "query", "ai_infra", "Question", persist=False)
    args = args_path.read_text(encoding="utf-8").splitlines()
    assert "--ask-for-approval" not in args
    assert args[args.index("--cd") + 1] == str(settings.repo_root)
    assert args[args.index("--sandbox") + 1] == "read-only"


def test_persist_codex_job_uses_workspace_write_sandbox(tmp_path, monkeypatch):
    fake = tmp_path / "codex"
    args_path = tmp_path / "args.txt"
    monkeypatch.setenv("CODEX_ARGS_PATH", str(args_path))
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$@" > "$CODEX_ARGS_PATH"\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command=str(fake))
    with connect(settings.database_path) as db:
        migrate(db)
        run_codex_job(settings, db, "query", "ai_infra", "Question", persist=True)
    args = args_path.read_text(encoding="utf-8").splitlines()
    assert "--ask-for-approval" not in args
    assert args[args.index("--cd") + 1] == str(settings.repo_root)
    assert args[args.index("--sandbox") + 1] == "workspace-write"


def test_codex_job_rejects_non_query_job_type_before_creating_row(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command="codex")
    with connect(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="Only query codex jobs are supported"):
            run_codex_job(settings, db, "ingest", "ai_infra", "Question", persist=False)
        count = db.execute("select count(*) as count from codex_jobs").fetchone()["count"]
    assert count == 0


def test_ask_endpoint_requires_question(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post("/api/ask", json={"domain": "ai_infra"})
    assert response.status_code == 400


def test_ask_endpoint_rejects_string_persist(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/ask",
            json={"domain": "ai_infra", "question": "NCCL trend?", "persist": "false"},
        )
    assert response.status_code == 400
