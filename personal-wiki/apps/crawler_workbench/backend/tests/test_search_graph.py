import pytest
from fastapi.testclient import TestClient

from crawler_workbench.db import connect, migrate
from crawler_workbench.graph_api import domain_graph
from crawler_workbench.main import create_app
from crawler_workbench.search import rebuild_search_index, search_wiki
from crawler_workbench.settings import Settings


PAGE = """---
type: reference
title: NCCL Release Notes
description: NCCL release trend summary
domain: ai_infra
status: reviewed
tags:
  - nccl
source_refs:
  - domains/ai_infra/raw/links/nccl.md
---

# NCCL Release Notes

NCCL recently emphasizes RAS, profiler support, and network plugin changes.
"""


def test_search_index_finds_wiki_page(tmp_path):
    wiki_dir = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "references"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "nccl-release-notes.md").write_text(PAGE, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        count = rebuild_search_index(settings, db, domain="ai_infra")
        results = search_wiki(db, "profiler", domain="ai_infra")
    assert count == 1
    assert results[0]["title"] == "NCCL Release Notes"


def test_search_index_handles_malformed_frontmatter_per_page(tmp_path):
    wiki_dir = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "references"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "valid.md").write_text(PAGE, encoding="utf-8")
    (wiki_dir / "broken.md").write_text(
        """---
title: [unterminated
---

# Broken Page

Malformed metadata should not hide searchable anomaly details.
""",
        encoding="utf-8",
    )
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        count = rebuild_search_index(settings, db, domain="ai_infra")
        valid_results = search_wiki(db, "profiler", domain="ai_infra")
        broken_results = search_wiki(db, "anomaly", domain="ai_infra")

    assert count == 2
    assert valid_results[0]["title"] == "NCCL Release Notes"
    assert broken_results[0]["title"] == "broken"


def test_rebuild_rejects_nested_domain_before_deleting_existing_rows(tmp_path):
    wiki_dir = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "references"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "nccl-release-notes.md").write_text(PAGE, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        rebuild_search_index(settings, db, domain="ai_infra")
        before = search_wiki(db, "profiler", domain="ai_infra")

        with pytest.raises(ValueError, match="Invalid domain"):
            rebuild_search_index(settings, db, domain="team/ai")

        after = search_wiki(db, "profiler", domain="ai_infra")

    assert before
    assert after == before


def test_search_rejects_nested_domain(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="Invalid domain"):
            search_wiki(db, "profiler", domain="team/ai")


def test_search_special_characters_do_not_crash(tmp_path):
    wiki_dir = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "references"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "nccl-release-notes.md").write_text(PAGE, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        rebuild_search_index(settings, db, domain="ai_infra")
        results = search_wiki(db, '"profiler" OR (', domain="ai_infra")

    assert isinstance(results, list)


def test_search_api_returns_400_for_invalid_domain(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)

    with TestClient(app) as client:
        search_response = client.get("/api/search", params={"q": "profiler", "domain": "team/ai"})
        rebuild_response = client.post("/api/search/rebuild", params={"domain": "team/ai"})

    assert search_response.status_code == 400
    assert "Invalid domain" in search_response.json()["detail"]
    assert rebuild_response.status_code == 400
    assert "Invalid domain" in rebuild_response.json()["detail"]


def test_graph_api_uses_existing_wiki_graph(tmp_path):
    root = tmp_path / "personal-wiki"
    wiki_dir = root / "domains" / "ai_infra" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "a.md").write_text(PAGE.replace("NCCL Release Notes", "A") + "\n[Go](b.md)\n", encoding="utf-8")
    (wiki_dir / "b.md").write_text(PAGE.replace("NCCL Release Notes", "B"), encoding="utf-8")
    graph = domain_graph(Settings(repo_root=tmp_path, state_dir=tmp_path / ".state"), "ai_infra")
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == [{"source": "domains/ai_infra/wiki/a", "target": "domains/ai_infra/wiki/b"}]
