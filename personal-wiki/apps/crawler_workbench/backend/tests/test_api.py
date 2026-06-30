from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from crawler_workbench.db import migrate, open_db
from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


def _insert_source_profile(db, source_id: str, schedule: str, auth_state: str = "ready", enabled: int = 1, next_run_at=None):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, auth_state, topic, enabled, next_run_at
        )
        values (?, ?, 'web', 'ai_infra', 'https://example.com', 'trusted', ?, 0, 0, ?, 'topic', ?, ?)
        """,
        (source_id, source_id, schedule, auth_state, enabled, next_run_at),
    )


def _insert_pending_task(db, settings: Settings, source_id: str = "src", url: str = "https://vllm.ai/blog/nccl") -> int:
    _insert_source_profile(db, source_id, "manual")
    raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / source_id / "item.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw", encoding="utf-8")
    raw_item_id = db.execute(
        """
        insert into raw_items (
          source_id, target_domain, canonical_url, raw_path, title,
          content_hash, content_bytes, metadata_json
        )
        values (?, 'ai_infra', ?, ?, 'Item', 'hash', 3, '{}')
        """,
        (source_id, url, str(raw)),
    ).lastrowid
    task_id = db.execute(
        """
        insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
        values (?, ?, 'ai_infra', 'pending', 'manual', 'needs review')
        """,
        (source_id, raw_item_id),
    ).lastrowid
    db.commit()
    return int(task_id)


def test_domains_endpoint_lists_domain_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    (settings.wiki_root / "domains" / "ai_infra").mkdir(parents=True)
    (settings.wiki_root / "domains" / "python").mkdir()
    (settings.wiki_root / "WIKI.md").write_text("# Wiki\n", encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/domains")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "ai_infra", "name": "ai_infra"},
        {"id": "python", "name": "python"},
    ]


def test_settings_endpoint_reports_runtime_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", bind_host="127.0.0.1", bind_port=9876)

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["bind_host"] == "127.0.0.1"
    assert data["bind_port"] == 9876
    assert data["authenticated"] is False
    assert "No login" in data["warning"]
    assert data["wiki_root"] == str(settings.wiki_root)
    assert data["database_path"] == str(settings.database_path)


def test_wiki_metrics_endpoint_reports_counts_sizes_and_light_health(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    wiki_root = settings.wiki_root
    domain_root = wiki_root / "domains" / "ai_infra"
    raw_path = domain_root / "raw" / "crawler" / "src" / "item.md"
    for path, text in [
        (wiki_root / "WIKI.md", "# Wiki\n"),
        (wiki_root / "apps" / "crawler_workbench" / "node_modules" / "bundle.js", "tool artifact\n"),
        (domain_root / "wiki" / "index.md", "# Index\n"),
        (domain_root / "wiki" / "nccl.md", "# NCCL\n"),
        (raw_path, "raw evidence\n"),
        (wiki_root / "global" / "wiki" / "gpu.md", "# GPU\n"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values ('src', 'ai_infra', 'https://example.com/item', ?, 'Item', 'hash', 13, '{}')
            """,
            (str(raw_path),),
        )
        db.execute(
            """
            insert into validation_runs (target_domain, status, command, output, created_at)
            values ('ai_infra', 'succeeded', 'validate --domain ai_infra', 'No validation issues', '2026-06-26 02:00:00')
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/wiki/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["counts"]["domain_count"] == 1
    assert data["counts"]["wiki_page_count"] == 3
    assert data["counts"]["raw_file_count"] == 1
    assert data["counts"]["raw_item_count"] == 1
    assert data["counts"]["total_file_count"] == 5
    expected_content_bytes = sum(
        path.stat().st_size
        for root in (wiki_root / "domains", wiki_root / "global", wiki_root / "WIKI.md")
        for path in ([root] if root.is_file() else root.rglob("*"))
        if path.is_file()
    )
    assert data["sizes"]["total_bytes"] == expected_content_bytes
    assert data["sizes"]["raw_bytes"] == raw_path.stat().st_size
    assert data["health"]["status"] == "healthy"
    assert data["health"]["score"] == 100
    assert data["health"]["latest_validation_status"] == "succeeded"
    assert data["health"]["latest_validation_at"] == "2026-06-26 02:00:00"


def test_wiki_pages_endpoint_lists_curated_pages(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    wiki_root = settings.wiki_root
    domain_wiki = wiki_root / "domains" / "ai_infra" / "wiki"
    for path, text in [
        (
            domain_wiki / "index.md",
            "---\ntitle: Index\n---\n# Index\n",
        ),
        (
            domain_wiki / "projects" / "index.md",
            "---\ntitle: Projects\n---\n# Projects\n",
        ),
        (
            domain_wiki / "projects" / "nccl.md",
            """---
domain: ai_infra
type: project
title: NCCL Tracker
description: NCCL curated notes
status: draft
tags:
  - nccl
  - networking
source_refs:
  - raw/crawler/nccl/item.md
---
# NCCL Tracker
""",
        ),
        (
            domain_wiki / "references" / "sglang.md",
            """---
domain: ai_infra
type: reference
title: SGLang
description: Serving notes
status: reviewed
tags:
  - inference
source_refs:
  - raw/crawler/sglang/item.md
---
# SGLang
""",
        ),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/pages", params={"domain": "ai_infra"})

    assert response.status_code == 200
    data = response.json()
    assert [page["path"] for page in data] == ["projects/nccl.md", "references/sglang.md"]
    assert data[0] == {
        "domain": "ai_infra",
        "path": "projects/nccl.md",
        "full_path": "domains/ai_infra/wiki/projects/nccl.md",
        "type": "project",
        "title": "NCCL Tracker",
        "description": "NCCL curated notes",
        "status": "draft",
        "tags": ["nccl", "networking"],
        "source_refs": ["raw/crawler/nccl/item.md"],
    }


def test_wiki_page_endpoint_reads_content_and_body_without_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "projects" / "nccl.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    content = """---
domain: ai_infra
type: project
title: NCCL Tracker
description: NCCL curated notes
status: draft
tags:
  - nccl
source_refs:
  - raw/crawler/nccl/item.md
---
# NCCL Tracker

Body text.
"""
    page.write_text(content, encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/page", params={"domain": "ai_infra", "path": "projects/nccl.md"})

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "projects/nccl.md"
    assert data["full_path"] == "domains/ai_infra/wiki/projects/nccl.md"
    assert data["title"] == "NCCL Tracker"
    assert data["content"] == content
    assert data["body"] == "# NCCL Tracker\n\nBody text.\n"


def test_wiki_page_endpoint_handles_symlinked_repo_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    real_repo = tmp_path / "real-repo"
    symlinked_repo = tmp_path / "linked-repo"
    real_repo.mkdir()
    symlinked_repo.symlink_to(real_repo, target_is_directory=True)
    settings = Settings(repo_root=symlinked_repo, state_dir=tmp_path / ".state")
    page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "projects" / "nccl.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("---\ntitle: NCCL Tracker\n---\n# NCCL Tracker\n", encoding="utf-8")

    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/wiki/page", params={"domain": "ai_infra", "path": "projects/nccl.md"})

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "projects/nccl.md"
    assert data["full_path"] == "domains/ai_infra/wiki/projects/nccl.md"


def test_wiki_page_endpoint_rejects_parent_path_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/page", params={"domain": "ai_infra", "path": "../raw/secret.md"})
        backslash_response = client.get("/api/wiki/page", params={"domain": "ai_infra", "path": r"projects\nccl.md"})

    assert response.status_code == 400
    assert backslash_response.status_code == 400


def test_runs_endpoint_exposes_failure_reason_for_failed_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'failed', current_timestamp, 0, 0, 0, 'fetch exploded')
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/runs")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["source_id"] == "src"
    assert data[0]["status"] == "failed"
    assert data[0]["error"] == "fetch exploded"
    assert data[0]["failure_reason"] == "fetch exploded"
    assert data[0]["failed_count"] == 1


def test_sources_endpoint_exposes_latest_fetch_run_state(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, started_at, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'failed', '2026-06-26 01:00:00', '2026-06-26 01:00:05', 0, 0, 0, 'old failure')
            """
        )
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, started_at, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'succeeded', '2026-06-26 02:00:00', '2026-06-26 02:00:10', 1, 1, 0, null)
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/sources")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "src"
    assert data[0]["last_run_at"] == "2026-06-26 02:00:10"
    assert data[0]["last_run_status"] == "succeeded"


def test_example_sources_include_daily_ai_infra_tracking_sources():
    import yaml

    config_path = Path(__file__).parents[2] / "config" / "sources.example.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in data["sources"]}

    assert sources["nccl-release-notes"] == {
        "id": "nccl-release-notes",
        "name": "NCCL release notes",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        "trust_level": "trusted",
        "schedule": "daily",
        "auto_ingest": True,
        "auth_required": False,
        "baseline_on_first_run": True,
        "topic": "NCCL release notes",
    }
    assert sources["nccl-github-closed-issues"]["url"] == "https://api.github.com/repos/NVIDIA/nccl/issues?sort=updated&direction=desc"
    assert sources["nccl-github-closed-issues"]["type"] == "github"
    assert sources["nccl-github-closed-issues"]["schedule"] == "daily"
    assert sources["nccl-github-closed-issues"]["auto_ingest"] is True
    assert sources["nccl-github-closed-issues"]["baseline_on_first_run"] is True
    assert sources["sglang-github-closed-issues-prs"]["url"] == "https://api.github.com/repos/sgl-project/sglang?sort=updated&direction=desc"
    assert sources["sglang-github-closed-issues-prs"]["type"] == "github"
    assert sources["sglang-github-closed-issues-prs"]["schedule"] == "daily"
    assert sources["sglang-github-closed-issues-prs"]["auto_ingest"] is True
    assert sources["sglang-github-closed-issues-prs"]["baseline_on_first_run"] is True
    for source_id, expected_url in {
        "kubernetes-github-closed-issues": "https://api.github.com/repos/kubernetes/kubernetes/issues?state=closed&sort=updated&direction=desc",
        "volcano-github-closed-issues": "https://api.github.com/repos/volcano-sh/volcano/issues?state=closed&sort=updated&direction=desc",
        "kueue-github-closed-issues": "https://api.github.com/repos/kubernetes-sigs/kueue/issues?state=closed&sort=updated&direction=desc",
    }.items():
        assert sources[source_id]["url"] == expected_url
        assert sources[source_id]["type"] == "github"
        assert sources[source_id]["schedule"] == "monthly"
        assert sources[source_id]["run_policy"] == "scheduled"
        assert sources[source_id]["auto_ingest"] is False
        assert sources[source_id]["auth_required"] is True
        assert sources[source_id]["auth_method"] == "env_token"
        assert sources[source_id]["auth_ref"] == "GITHUB_TOKEN"
        assert sources[source_id]["auth_state"] == "ready"
        assert sources[source_id]["baseline_on_first_run"] is True
    assert sources["nccl-technical-blog"]["url"] == "https://developer.nvidia.com/blog/tag/nccl/feed/"
    assert sources["nccl-technical-blog"]["type"] == "rss"
    assert sources["nccl-technical-blog"]["schedule"] == "weekly"
    assert sources["nccl-technical-blog"]["fetch_article_body"] is True
    assert "NCCL" in sources["nccl-technical-blog"]["include_keywords"]
    assert sources["nccl-github-releases"]["url"] == "https://github.com/NVIDIA/nccl/releases.atom"
    assert sources["nccl-github-releases"]["schedule"] == "weekly"
    assert sources["nccl-arxiv-papers"]["type"] == "arxiv"
    assert sources["nccl-arxiv-papers"]["schedule"] == "weekly"


def test_trust_queue_source_endpoint_sets_manual_source_and_approves_task(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        task_id = _insert_pending_task(db, settings)

    with TestClient(app) as client:
        response = client.post(f"/api/queue/{task_id}/trust-source", json={"mode": "manual"})

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "vllm.ai"
    assert data["approved_count"] == 1
    with open_db(settings.database_path) as db:
        profile = db.execute("select schedule, auto_ingest from source_profiles where id = 'src'").fetchone()
        task = db.execute("select status from ingest_tasks where id = ?", (task_id,)).fetchone()
    assert profile["schedule"] == "manual"
    assert profile["auto_ingest"] == 1
    assert task["status"] == "approved"


def test_trust_queue_source_endpoint_sets_monthly_schedule(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        task_id = _insert_pending_task(db, settings)

    with TestClient(app) as client:
        response = client.post(f"/api/queue/{task_id}/trust-source", json={"mode": "scheduled", "frequency": "monthly"})

    assert response.status_code == 200
    with open_db(settings.database_path) as db:
        profile = db.execute("select schedule, auto_ingest from source_profiles where id = 'src'").fetchone()
    assert profile["schedule"] == "monthly"
    assert profile["auto_ingest"] == 1
