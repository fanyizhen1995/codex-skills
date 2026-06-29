from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
import os

from fastapi.testclient import TestClient

from crawler_workbench.db import migrate, open_db
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.main import create_app
from crawler_workbench.manual_ingest import manual_source_id, run_manual_url_ingest
from crawler_workbench.settings import Settings


class StaticFetcher:
    def __init__(self, results: list[FetchResult]) -> None:
        self.results = results

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        return self.results


def ok_process(stdout: str = "ok\n") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=stdout, stderr="")


def init_git_repo(path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def seed_wiki(settings: Settings) -> None:
    domain_root = settings.wiki_root / "domains" / "ai_infra"
    (domain_root / "wiki").mkdir(parents=True, exist_ok=True)
    (domain_root / "DOMAIN.md").write_text("# AI Infra\n", encoding="utf-8")
    (domain_root / "ingest.md").write_text("# Ingest Log\n", encoding="utf-8")
    (settings.wiki_root / "WIKI.md").parent.mkdir(parents=True, exist_ok=True)
    (settings.wiki_root / "WIKI.md").write_text("# Wiki\n", encoding="utf-8")
    source_cli = Path(__file__).resolve().parents[4] / "tools" / "wiki_cli"
    target_cli = settings.wiki_root / "tools" / "wiki_cli"
    shutil.copytree(source_cli, target_cli, dirs_exist_ok=True)


def test_run_manual_url_ingest_fetches_runs_task_and_commits(tmp_path):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / ".state")
    seed_wiki(settings)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True, text=True)

    codex_calls: list[str] = []

    def codex_runner(_settings: Settings, prompt: str) -> subprocess.CompletedProcess[str]:
        codex_calls.append(prompt)
        page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "references" / "manual-url.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        raw_capture = next((settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler").glob("manual-url-example-com-doc-*/*.md"))
        source_ref = os.path.relpath(raw_capture, page.parent).replace(os.sep, "/")
        page.write_text(
            "---\n"
            "domain: ai_infra\n"
            "type: Reference\n"
            "title: Manual URL\n"
            "description: Manual URL ingest test page.\n"
            "status: reviewed\n"
            "source_refs:\n"
            f"  - {source_ref}\n"
            "---\n"
            "# Manual URL\n\n"
            "Source-backed note.\n",
            encoding="utf-8",
        )
        return ok_process("codex ok\n")

    with open_db(settings.database_path) as db:
        migrate(db)
        result = run_manual_url_ingest(
            settings,
            db,
            url="https://example.com/doc?utm_source=x",
            domain="ai_infra",
            auto_commit_enabled=True,
            fetcher=StaticFetcher(
                [
                    FetchResult(
                        canonical_url="https://example.com/doc",
                        title="Example Manual Doc",
                        content="# Example Manual Doc\n\nManual source content.",
                        content_type="text/html",
                        metadata={"source_url": "https://example.com/doc"},
                    )
                ]
            ),
            codex_runner=codex_runner,
        )

        source = db.execute("select * from source_profiles where id = ?", (result["source_id"],)).fetchone()
        raw_item = db.execute("select * from raw_items where source_id = ?", (result["source_id"],)).fetchone()
        task = db.execute("select * from ingest_tasks where id = ?", (result["task_id"],)).fetchone()
        commit_record = db.execute("select * from commit_records where id = ?", (task["commit_id"],)).fetchone()

    assert result["status"] == "succeeded"
    assert result["source_id"].startswith("manual-url-example-com-doc-")
    assert result["fetch"]["changed_count"] == 1
    assert result["task_id"] == task["id"]
    assert result["commit_sha"] == commit_record["commit_sha"]
    assert source["type"] == "web"
    assert source["target_domain"] == "ai_infra"
    assert source["schedule"] == "manual"
    assert source["run_policy"] == "once"
    assert source["auto_ingest"] == 1
    assert raw_item["canonical_url"] == "https://example.com/doc"
    assert task["status"] == "succeeded"
    assert codex_calls and "入库 raw/crawler/" in codex_calls[0]


def test_run_manual_url_ingest_reports_skipped_when_url_is_unchanged(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_wiki(settings)
    fetcher = StaticFetcher(
        [
            FetchResult(
                canonical_url="https://example.com/doc",
                title="Example Manual Doc",
                content="# Example Manual Doc\n\nManual source content.",
                content_type="text/html",
                metadata={"source_url": "https://example.com/doc"},
            )
        ]
    )

    with open_db(settings.database_path) as db:
        migrate(db)
        first = run_manual_url_ingest(
            settings,
            db,
            url="https://example.com/doc",
            domain="ai_infra",
            auto_commit_enabled=False,
            fetcher=fetcher,
            codex_runner=lambda _settings, _prompt: ok_process(),
        )
        second = run_manual_url_ingest(
            settings,
            db,
            url="https://example.com/doc",
            domain="ai_infra",
            auto_commit_enabled=False,
            fetcher=fetcher,
            codex_runner=lambda _settings, _prompt: ok_process(),
        )

    assert first["status"] in {"succeeded", "failed"}
    assert second["status"] == "skipped"
    assert second["reason"] == "no changed content fetched"
    assert second["fetch"]["skipped_count"] == 1


def test_manual_ingest_api_validates_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/manual-ingests", json={"url": "   ", "domain": "ai_infra"})

    assert response.status_code == 400


def test_manual_source_id_is_stable_for_tracking_query_variants():
    assert manual_source_id("https://example.com/doc?utm_source=x") == manual_source_id("HTTPS://example.com/doc")
