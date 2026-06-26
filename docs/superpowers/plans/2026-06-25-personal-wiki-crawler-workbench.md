# Personal Wiki Crawler Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, unauthenticated, trusted-network crawler and workbench for `personal-wiki` that can crawl agreed sources, manage ingest queues, visualize wiki content, and run Codex-powered wiki queries through the existing local Codex configuration.

**Architecture:** Add a self-contained app under `personal-wiki/apps/crawler_workbench/`. The backend uses FastAPI, SQLite FTS5, source-specific fetchers, existing `personal-wiki/tools/wiki_cli` commands, subprocess-backed Codex jobs, and safe Git operations; the frontend uses React/Vite with Chinese operations-first pages for source management, ingest operations, search, graph visualization, and query jobs.

**Tech Stack:** Python 3.12, FastAPI, SQLite FTS5, Pydantic, PyYAML, httpx, feedparser, uvicorn, pytest, React, TypeScript, Vite, lucide-react, Recharts, Vitest, Playwright.

---

## Scope

This plan implements the design in `docs/superpowers/specs/2026-06-25-personal-wiki-crawler-workbench-design.md`.

Version 1 delivers:

- Backend service binding to `0.0.0.0` with startup and UI warnings that there is no login.
- YAML source profiles mirrored into SQLite.
- Fetch support for web pages, RSS feeds, GitHub releases/issues/pull requests, and arXiv/paper metadata pages.
- Auth-required source records that pause in `needs_auth_config` until the user configures a non-secret reference.
- Manual source runs and a simple in-process scheduler.
- Raw capture with content hashing, duplicate detection, run history, and pending ingest tasks.
- Hybrid ingest behavior: trusted low-risk changes can run `raw -> ingest-plan -> wiki -> compact -> index -> validate -> commit`; untrusted, auth-required, high-risk, large, failed, or validation-failed tasks remain in the queue.
- Codex query jobs through `codex exec`, reusing local Codex config and requiring `personal-wiki-manager`.
- Full-text search over curated wiki pages and raw metadata with SQLite FTS5.
- Graph/backlink API based on existing wiki CLI graph code.
- Chinese frontend with Operations Console, Source Subscriptions, Ingest Queue, Knowledge Workbench, Source Workbench, and Settings.
- Frontend visualizations in both Knowledge Workbench and Source Workbench.

Version 1 does not implement multi-user login, cloud deployment, embedding/vector search, browser automation, or access-control bypassing.

## File Map

Backend app:

- Create: `personal-wiki/apps/crawler_workbench/README.md`  
  App runbook, trusted-network warning, source profile format, and local development commands.

- Create: `personal-wiki/apps/crawler_workbench/backend/requirements.txt`  
  Runtime and test dependencies for the backend.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/__init__.py`  
  Backend package marker and version constant.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/settings.py`  
  Pydantic settings, repo path discovery, bind host/port, Codex command settings, state directory paths, and max auto-ingest size.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`  
  FastAPI app factory, CORS setup for the Vite dev server, router registration, startup database initialization, scheduler startup, and unauthenticated warning log.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`  
  SQLite connection helper, row factory, migration runner, and transaction helper.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`  
  SQLite schema for source profiles, auth references, runs, raw items, content versions, ingest tasks, Codex jobs, validation runs, commit records, and FTS5 search.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/models.py`  
  Shared enums and dataclasses for profile type, trust level, auth state, run status, ingest status, and job status.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`  
  Pydantic request and response models for all API endpoints.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`  
  YAML profile loading, validation, SQLite mirroring, CRUD helpers, and auth reference state changes.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/hashing.py`  
  URL canonicalization, slug generation, normalized text hashing, and content hash helpers.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/raw_store.py`  
  Writes fetched content into the target domain `raw/` tree and records raw metadata.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/__init__.py`  
  Fetcher registry.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/base.py`  
  Fetch result model and fetcher protocol.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/web.py`  
  Generic web fetcher using httpx with conditional request headers.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/rss.py`  
  RSS fetcher using feedparser.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/github.py`  
  GitHub fetcher for releases, closed issues, and closed pull requests through the GitHub REST API.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/arxiv.py`  
  arXiv fetcher using the public Atom API and paper landing pages.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`  
  Manual run orchestration: fetch, diff, raw write, run records, duplicate skip, and ingest task creation.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/policy.py`  
  Auto-ingest eligibility decisions for trusted, untrusted, auth-required, high-risk, and large changes.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/wiki_cli.py`  
  Thin subprocess wrapper around existing `personal-wiki/tools/wiki_cli/cli.py`.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/ingest.py`  
  Ingest task approval/rejection and trusted-source pipeline execution.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/codex_worker.py`  
  Codex prompt builder and subprocess job runner using local `codex exec`.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/search.py`  
  FTS5 indexing for curated wiki pages plus raw metadata and search endpoint helpers.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/graph_api.py`  
  Graph/backlink adapter using existing `wiki_cli.graph`.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/git_ops.py`  
  Dirty-state checks, task-owned staging, and auto-commit record creation.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/scheduler.py`  
  In-process due-source loop with run locking and clean shutdown.

- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`  
  FastAPI router for health, domains, sources, runs, queue, search, jobs, graph, validation, commit, and settings.

Backend tests:

- Create: `personal-wiki/apps/crawler_workbench/backend/tests/conftest.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_settings_health.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_hashing_raw_store.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetchers.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_search_graph.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_codex_worker.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_ingest_git.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`

Frontend app:

- Create: `personal-wiki/apps/crawler_workbench/frontend/package.json`
- Create: `personal-wiki/apps/crawler_workbench/frontend/index.html`
- Create: `personal-wiki/apps/crawler_workbench/frontend/tsconfig.json`
- Create: `personal-wiki/apps/crawler_workbench/frontend/vite.config.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/main.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/Layout.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/StatusBadge.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/TrendChart.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/WikiGraph.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/OverviewPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/QueuePage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/KnowledgePage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourceWorkbenchPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SettingsPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/tests/smoke.spec.ts`

Shared docs and local config:

- Modify: `.gitignore`  
  Ignore local workbench state, backend virtualenv, SQLite databases, frontend node modules, and frontend build output.

- Create: `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`  
  Example web, RSS, GitHub, and arXiv source profiles.

## Working Rules

- Use `apply_patch` for manual edits.
- Keep commits scoped to the files in each task.
- Do not stage or commit existing unrelated dirty files in `hami-gpu-flow-task-lifecycle/`, `.mindfs/`, or `.superpowers/`.
- Backend tests run from `personal-wiki/apps/crawler_workbench/backend` with `PYTHONPATH=.`.
- Frontend tests run from `personal-wiki/apps/crawler_workbench/frontend`.
- Every backend endpoint returns deterministic JSON for tests.
- Every long-running backend operation creates a row in SQLite before work starts and updates that row when it finishes.
- Secrets are never written to wiki files, Git commits, logs, or frontend responses. Store only env var names, command names, header template names, and cookie file paths.
- Auto-commit stages only task-owned paths and aborts when unrelated staged changes exist.
- Query-only Codex jobs include an explicit no-edit instruction. Query-to-wiki, ingest, validate, and commit jobs can modify files only for the named domain/task.

## Task 1: Backend Scaffold, Settings, and Health

**Files:**
- Modify: `.gitignore`
- Create: `personal-wiki/apps/crawler_workbench/backend/requirements.txt`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/__init__.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/settings.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/conftest.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_settings_health.py`

- [ ] **Step 1: Write failing health and settings tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/conftest.py`:

```python
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(REPO_ROOT))
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_settings_health.py`:

```python
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
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_settings_health.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'crawler_workbench'`.

- [ ] **Step 3: Add backend dependencies and ignore rules**

Use `apply_patch` to append these lines to `.gitignore`:

```gitignore
.personal-wiki-workbench/
personal-wiki/apps/crawler_workbench/backend/.venv/
personal-wiki/apps/crawler_workbench/backend/.pytest_cache/
personal-wiki/apps/crawler_workbench/**/*.sqlite3
personal-wiki/apps/crawler_workbench/frontend/node_modules/
personal-wiki/apps/crawler_workbench/frontend/dist/
personal-wiki/apps/crawler_workbench/frontend/playwright-report/
personal-wiki/apps/crawler_workbench/frontend/test-results/
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/requirements.txt`:

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
PyYAML
httpx
feedparser
pytest
pytest-asyncio
```

- [ ] **Step 4: Implement settings, app factory, and health route**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/__init__.py`:

```python
__version__ = "0.1.0"
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/settings.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PW_WORKBENCH_", arbitrary_types_allowed=True)

    repo_root: Path = Field(default_factory=lambda: Path.cwd().resolve())
    state_dir: Path | None = None
    bind_host: str = "0.0.0.0"
    bind_port: int = 8765
    max_auto_ingest_bytes: int = 2_000_000
    scheduler_interval_seconds: int = 60
    codex_command: str = "codex"

    @property
    def wiki_root(self) -> Path:
        return self.repo_root / "personal-wiki"

    @property
    def resolved_state_dir(self) -> Path:
        return self.state_dir or (self.repo_root / ".personal-wiki-workbench")

    @property
    def database_path(self) -> Path:
        return self.resolved_state_dir / "workbench.sqlite3"

    @property
    def sources_yaml_path(self) -> Path:
        return self.resolved_state_dir / "sources.yaml"

    @property
    def trusted_network_warning(self) -> str:
        return "No login is enabled. Expose this service only on a trusted network."
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "bind_host": settings.bind_host,
        "bind_port": settings.bind_port,
        "authenticated": False,
        "warning": settings.trusted_network_warning,
    }
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`:

```python
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .settings import Settings


LOG = logging.getLogger("crawler_workbench")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings(repo_root=_discover_repo_root())
    resolved.resolved_state_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Personal Wiki Crawler Workbench", version="0.1.0")
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.on_event("startup")
    def warn_unauthenticated() -> None:
        LOG.warning(resolved.trusted_network_warning)

    return app


def _discover_repo_root() -> str:
    from pathlib import Path

    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "personal-wiki" / "WIKI.md").exists():
            return str(candidate)
    return str(current)


app = create_app()
```

- [ ] **Step 5: Run the health tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_settings_health.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add .gitignore personal-wiki/apps/crawler_workbench/backend
git commit -m "feat(workbench): add backend health scaffold"
```

Expected: commit includes only Task 1 files.

## Task 2: SQLite Schema and Source Profile Store

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/models.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`
- Create: `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`

- [ ] **Step 1: Write failing profile store tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`:

```python
from pathlib import Path

from crawler_workbench.db import connect, migrate
from crawler_workbench.profiles import load_profiles_from_yaml, mirror_profiles
from crawler_workbench.settings import Settings


PROFILE_YAML = """
sources:
  - id: nccl-releases
    name: NCCL release notes
    type: web
    target_domain: ai_infra
    url: https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: NCCL release history
  - id: private-github
    name: Private GitHub issues
    type: github
    target_domain: ai_infra
    url: https://api.github.com/repos/example/private/issues
    trust_level: untrusted
    schedule: manual
    auto_ingest: false
    auth_required: true
    auth_method: env_token
    auth_ref: GITHUB_TOKEN
    topic: private issue audit
"""


def test_schema_migration_creates_profile_tables(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        tables = {
            row["name"]
            for row in db.execute("select name from sqlite_master where type = 'table'")
        }
    assert "source_profiles" in tables
    assert "source_auth_refs" in tables
    assert "fetch_runs" in tables
    assert "wiki_search_fts" in tables


def test_yaml_profiles_mirror_to_sqlite(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        profiles = load_profiles_from_yaml(yaml_path)
        mirror_profiles(db, profiles)
        rows = db.execute("select id, type, auth_state from source_profiles order by id").fetchall()
    assert [row["id"] for row in rows] == ["nccl-releases", "private-github"]
    assert rows[0]["auth_state"] == "ready"
    assert rows[1]["auth_state"] == "needs_auth_config"
```

- [ ] **Step 2: Run the failing profile tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_db_profiles.py -q
```

Expected: FAIL with missing `crawler_workbench.db`.

- [ ] **Step 3: Add schema and database helpers**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql` with the exact schema:

```sql
create table if not exists source_profiles (
  id text primary key,
  name text not null,
  type text not null check (type in ('web', 'rss', 'github', 'arxiv')),
  target_domain text not null,
  url text not null,
  trust_level text not null check (trust_level in ('trusted', 'untrusted')),
  schedule text not null,
  auto_ingest integer not null default 0,
  auth_required integer not null default 0,
  auth_state text not null default 'ready',
  auth_method text,
  auth_ref text,
  topic text not null,
  enabled integer not null default 1,
  last_run_at text,
  next_run_at text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists source_auth_refs (
  source_id text primary key references source_profiles(id) on delete cascade,
  auth_method text not null,
  auth_ref text not null,
  state text not null,
  updated_at text not null default current_timestamp
);

create table if not exists fetch_runs (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  status text not null,
  started_at text not null default current_timestamp,
  finished_at text,
  fetched_count integer not null default 0,
  changed_count integer not null default 0,
  skipped_count integer not null default 0,
  error text
);

create table if not exists raw_items (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  fetch_run_id integer references fetch_runs(id) on delete set null,
  target_domain text not null,
  canonical_url text not null,
  raw_path text not null,
  title text not null,
  content_hash text not null,
  content_bytes integer not null,
  metadata_json text not null,
  created_at text not null default current_timestamp
);

create table if not exists content_versions (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  canonical_url text not null,
  content_hash text not null,
  etag text,
  last_modified text,
  raw_item_id integer references raw_items(id) on delete set null,
  created_at text not null default current_timestamp,
  unique(source_id, canonical_url, content_hash)
);

create table if not exists ingest_tasks (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  raw_item_id integer references raw_items(id) on delete set null,
  target_domain text not null,
  status text not null,
  risk_level text not null,
  reason text not null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  codex_job_id integer,
  validation_run_id integer,
  commit_id integer
);

create table if not exists codex_jobs (
  id integer primary key autoincrement,
  job_type text not null,
  target_domain text,
  prompt text not null,
  status text not null,
  stdout text not null default '',
  stderr text not null default '',
  exit_code integer,
  created_at text not null default current_timestamp,
  started_at text,
  finished_at text
);

create table if not exists validation_runs (
  id integer primary key autoincrement,
  target_domain text,
  status text not null,
  command text not null,
  output text not null default '',
  created_at text not null default current_timestamp
);

create table if not exists commit_records (
  id integer primary key autoincrement,
  source_id text,
  target_domain text not null,
  commit_sha text not null,
  message text not null,
  created_at text not null default current_timestamp
);

create virtual table if not exists wiki_search_fts using fts5(
  path,
  domain,
  title,
  description,
  body,
  source_refs,
  raw_metadata
);
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`:

```python
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
```

- [ ] **Step 4: Add profile models and YAML mirror**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/models.py`:

```python
from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    WEB = "web"
    RSS = "rss"
    GITHUB = "github"
    ARXIV = "arxiv"


class TrustLevel(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class AuthState(StrEnum):
    READY = "ready"
    NEEDS_AUTH_CONFIG = "needs_auth_config"
    AUTH_FAILED = "auth_failed"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`:

```python
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import yaml

from .models import AuthState


REQUIRED_PROFILE_KEYS = {
    "id",
    "name",
    "type",
    "target_domain",
    "url",
    "trust_level",
    "schedule",
    "auto_ingest",
    "auth_required",
    "topic",
}


def load_profiles_from_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("sources", [])
    if not isinstance(profiles, list):
        raise ValueError("sources must be a list")
    for profile in profiles:
        missing = sorted(REQUIRED_PROFILE_KEYS - set(profile))
        if missing:
            raise ValueError(f"profile {profile.get('id', '<unknown>')} missing keys: {', '.join(missing)}")
    return profiles


def mirror_profiles(connection: sqlite3.Connection, profiles: list[dict[str, Any]]) -> None:
    for profile in profiles:
        auth_required = bool(profile["auth_required"])
        auth_state = AuthState.NEEDS_AUTH_CONFIG if auth_required else AuthState.READY
        connection.execute(
            """
            insert into source_profiles (
              id, name, type, target_domain, url, trust_level, schedule,
              auto_ingest, auth_required, auth_state, auth_method, auth_ref, topic, enabled, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
            on conflict(id) do update set
              name = excluded.name,
              type = excluded.type,
              target_domain = excluded.target_domain,
              url = excluded.url,
              trust_level = excluded.trust_level,
              schedule = excluded.schedule,
              auto_ingest = excluded.auto_ingest,
              auth_required = excluded.auth_required,
              auth_state = excluded.auth_state,
              auth_method = excluded.auth_method,
              auth_ref = excluded.auth_ref,
              topic = excluded.topic,
              enabled = excluded.enabled,
              updated_at = current_timestamp
            """,
            (
                profile["id"],
                profile["name"],
                profile["type"],
                profile["target_domain"],
                profile["url"],
                profile["trust_level"],
                profile["schedule"],
                int(bool(profile["auto_ingest"])),
                int(auth_required),
                auth_state.value,
                profile.get("auth_method"),
                profile.get("auth_ref"),
                profile["topic"],
                int(bool(profile.get("enabled", True))),
            ),
        )
        if auth_required and profile.get("auth_method") and profile.get("auth_ref"):
            connection.execute(
                """
                insert into source_auth_refs (source_id, auth_method, auth_ref, state, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                on conflict(source_id) do update set
                  auth_method = excluded.auth_method,
                  auth_ref = excluded.auth_ref,
                  state = excluded.state,
                  updated_at = current_timestamp
                """,
                (profile["id"], profile["auth_method"], profile["auth_ref"], auth_state.value),
            )
    connection.commit()


def list_profiles(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute("select * from source_profiles order by id").fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 5: Add API schemas, source endpoints, and startup migration**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


class SourceProfileResponse(BaseModel):
    id: str
    name: str
    type: str
    target_domain: str
    url: str
    trust_level: str
    schedule: str
    auto_ingest: bool
    auth_required: bool
    auth_state: str
    topic: str
    enabled: bool


class HealthResponse(BaseModel):
    status: str
    bind_host: str
    bind_port: int
    authenticated: bool
    warning: str
```

Modify `main.py` startup to open the database, run migrations, mirror YAML profiles, and store `app.state.db_path`.

```python
from .db import connect, migrate
from .profiles import load_profiles_from_yaml, mirror_profiles


def initialize_database(app: FastAPI) -> None:
    settings = app.state.settings
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, load_profiles_from_yaml(settings.sources_yaml_path))
    app.state.db_path = settings.database_path
```

Call `initialize_database(app)` before returning the app from `create_app`.

Modify `api.py` to include `GET /api/sources`:

```python
from .db import connect
from .profiles import list_profiles


@router.get("/sources")
def sources(request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as db:
        rows = list_profiles(db)
    return [
        {
            **row,
            "auto_ingest": bool(row["auto_ingest"]),
            "auth_required": bool(row["auth_required"]),
            "enabled": bool(row["enabled"]),
        }
        for row in rows
    ]
```

- [ ] **Step 6: Add example source configuration**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`:

```yaml
sources:
  - id: nccl-release-notes
    name: NCCL release notes
    type: web
    target_domain: ai_infra
    url: https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: NCCL release notes
  - id: sglang-github-closed
    name: SGLang closed issues and pull requests
    type: github
    target_domain: ai_infra
    url: https://api.github.com/repos/sgl-project/sglang
    trust_level: untrusted
    schedule: manual
    auto_ingest: false
    auth_required: false
    topic: SGLang closed issues and pull requests
  - id: llm-serving-arxiv
    name: LLM serving arXiv search
    type: arxiv
    target_domain: ai_infra
    url: http://export.arxiv.org/api/query?search_query=all:LLM+serving&start=0&max_results=25
    trust_level: untrusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: LLM serving papers
```

- [ ] **Step 7: Run profile tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_db_profiles.py tests/test_settings_health.py -q
```

Expected: PASS with all tests passing.

- [ ] **Step 8: Commit Task 2**

Run:

```bash
git add personal-wiki/apps/crawler_workbench
git commit -m "feat(workbench): add sqlite source profiles"
```

Expected: commit includes schema, profile code, tests, and example config.

## Task 3: Hashing, Raw Storage, and Fetcher Contracts

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/hashing.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/raw_store.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/__init__.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/base.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_hashing_raw_store.py`

- [ ] **Step 1: Write failing hashing and raw-store tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_hashing_raw_store.py`:

```python
import json

from crawler_workbench.hashing import canonicalize_url, content_hash, slugify_url
from crawler_workbench.raw_store import write_raw_item
from crawler_workbench.settings import Settings


def test_canonicalize_url_and_hash_are_stable():
    assert canonicalize_url("HTTPS://Example.com:443/a/../b?utm_source=x&z=1") == "https://example.com/b?z=1"
    assert content_hash(" hello\nworld ") == content_hash("hello\nworld")
    assert slugify_url("https://example.com/a/b?z=1").startswith("example-com-a-b")


def test_write_raw_item_creates_domain_raw_file(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw = write_raw_item(
        settings=settings,
        source_id="nccl-release-notes",
        target_domain="ai_infra",
        canonical_url="https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        title="NCCL release notes",
        content="# NCCL\ncontent",
        metadata={"kind": "web"},
    )
    assert raw.path.exists()
    assert raw.path.as_posix().endswith(".md")
    text = raw.path.read_text(encoding="utf-8")
    assert "source_id: nccl-release-notes" in text
    assert "canonical_url: https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html" in text
    assert "# NCCL" in text
    metadata = json.loads(raw.metadata_json)
    assert metadata["kind"] == "web"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_hashing_raw_store.py -q
```

Expected: FAIL with missing `crawler_workbench.hashing`.

- [ ] **Step 3: Implement hashing helpers**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/hashing.py`:

```python
from __future__ import annotations

import hashlib
import posixpath
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.hostname.lower() if parsed.hostname else parsed.netloc.lower()
    if parsed.port and not ((scheme == "https" and parsed.port == 443) or (scheme == "http" and parsed.port == 80)):
        netloc = f"{netloc}:{parsed.port}"
    path = posixpath.normpath(parsed.path or "/")
    if parsed.path.endswith("/") and not path.endswith("/"):
        path += "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def content_hash(content: str | bytes) -> str:
    if isinstance(content, bytes):
        data = content.strip()
    else:
        data = content.strip().encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def slugify_url(url: str, max_length: int = 90) -> str:
    parsed = urlsplit(canonicalize_url(url))
    value = f"{parsed.netloc}{parsed.path}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:max_length].strip("-") or "source"
```

- [ ] **Step 4: Implement fetcher contract and raw writer**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class FetchResult:
    canonical_url: str
    title: str
    content: str
    content_type: str
    metadata: dict[str, object] = field(default_factory=dict)
    etag: str | None = None
    last_modified: str | None = None


class Fetcher(Protocol):
    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        raise NotImplementedError
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/__init__.py`:

```python
from __future__ import annotations

from .base import FetchResult, Fetcher

__all__ = ["FetchResult", "Fetcher"]
```

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/raw_store.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .hashing import content_hash, slugify_url
from .settings import Settings


@dataclass(frozen=True)
class RawWrite:
    path: Path
    content_hash: str
    content_bytes: int
    metadata_json: str


def write_raw_item(
    settings: Settings,
    source_id: str,
    target_domain: str,
    canonical_url: str,
    title: str,
    content: str,
    metadata: dict[str, object],
) -> RawWrite:
    now = datetime.now(timezone.utc)
    raw_dir = settings.wiki_root / "domains" / target_domain / "raw" / "crawler" / source_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    digest = content_hash(content)
    path = raw_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slugify_url(canonical_url)}-{digest[:10]}.md"
    metadata_json = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    body = (
        "---\n"
        f"source_id: {source_id}\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"canonical_url: {canonical_url}\n"
        f"captured_at: {now.isoformat()}\n"
        f"content_hash: {digest}\n"
        "---\n\n"
        f"{content.strip()}\n"
    )
    path.write_text(body, encoding="utf-8")
    return RawWrite(
        path=path,
        content_hash=digest,
        content_bytes=len(body.encode("utf-8")),
        metadata_json=metadata_json,
    )
```

- [ ] **Step 5: Run hashing and raw tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_hashing_raw_store.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_hashing_raw_store.py
git commit -m "feat(workbench): add raw capture helpers"
```

Expected: commit includes hashing, raw writer, fetcher contract, and tests.

## Task 4: Web, RSS, GitHub, and arXiv Fetchers

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/web.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/rss.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/github.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/arxiv.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers/__init__.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetchers.py`

- [ ] **Step 1: Write failing fetcher tests with fake transports**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_fetchers.py`:

```python
import httpx

from crawler_workbench.fetchers.arxiv import ArxivFetcher
from crawler_workbench.fetchers.github import GitHubFetcher
from crawler_workbench.fetchers.rss import RssFetcher
from crawler_workbench.fetchers.web import WebFetcher


def client_for(status_code: int, text: str, headers: dict[str, str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=text, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_web_fetcher_returns_markdownish_result():
    fetcher = WebFetcher(client=client_for(200, "<html><title>Doc</title><body><h1>Hello</h1></body></html>", {"etag": "abc"}))
    results = fetcher.fetch({"url": "https://example.com/doc", "name": "Doc"})
    assert len(results) == 1
    assert results[0].title == "Doc"
    assert "Hello" in results[0].content
    assert results[0].etag == "abc"


def test_rss_fetcher_returns_entries():
    rss = """<?xml version="1.0"?><rss><channel><title>Feed</title><item><title>One</title><link>https://example.com/1</link><description>Body</description></item></channel></rss>"""
    fetcher = RssFetcher(client=client_for(200, rss))
    results = fetcher.fetch({"url": "https://example.com/feed.xml", "name": "Feed"})
    assert [result.title for result in results] == ["One"]
    assert results[0].canonical_url == "https://example.com/1"


def test_github_fetcher_closed_issues_and_prs():
    payload = '[{"html_url":"https://github.com/o/r/issues/1","title":"Issue","state":"closed","pull_request":null,"body":"fixed"},{"html_url":"https://github.com/o/r/pull/2","title":"PR","state":"closed","pull_request":{"url":"x"},"body":"merged"}]'
    fetcher = GitHubFetcher(client=client_for(200, payload))
    results = fetcher.fetch({"url": "https://api.github.com/repos/o/r", "name": "Repo"})
    assert [result.title for result in results] == ["Issue", "PR"]
    assert results[0].metadata["github_kind"] == "issue"
    assert results[1].metadata["github_kind"] == "pull_request"


def test_arxiv_fetcher_returns_papers():
    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2401.00001v1</id><title>Paper Title</title><summary>Paper summary</summary><published>2024-01-01T00:00:00Z</published></entry></feed>"""
    fetcher = ArxivFetcher(client=client_for(200, atom))
    results = fetcher.fetch({"url": "http://export.arxiv.org/api/query?search_query=all:test", "name": "Papers"})
    assert results[0].title == "Paper Title"
    assert "Paper summary" in results[0].content
```

- [ ] **Step 2: Run failing fetcher tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_fetchers.py -q
```

Expected: FAIL with missing fetcher modules.

- [ ] **Step 3: Implement fetchers**

Implement each fetcher with these concrete rules:

```python
# web.py
# - Constructor accepts httpx.Client | None.
# - fetch(profile) GETs profile["url"] with timeout 30.
# - raise_for_status() on HTTP errors.
# - Title comes from <title> when present, else profile["name"].
# - Content is a concise Markdown capture containing URL, title, headers, and stripped text.
# - Return one FetchResult.

# rss.py
# - Constructor accepts httpx.Client | None.
# - fetch(profile) GETs profile["url"].
# - feedparser.parse(response.text).
# - Return one FetchResult per entry using entry.link, entry.title, and entry.summary/description.

# github.py
# - Constructor accepts httpx.Client | None.
# - For base repo URL https://api.github.com/repos/{owner}/{repo}, request:
#   /issues?state=closed&per_page=100
#   /pulls?state=closed&per_page=100
# - For profile URLs ending in /issues or /pulls, request only that endpoint.
# - Accept GITHUB_TOKEN when profile auth_ref equals GITHUB_TOKEN or environment has GITHUB_TOKEN.
# - Store issue number, state, labels, closed_at, merged_at, and github_kind metadata.
# - Content includes title, URL, state, labels, body, and closure/merge timestamps.

# arxiv.py
# - Constructor accepts httpx.Client | None.
# - GET profile["url"].
# - Parse Atom XML with xml.etree.ElementTree.
# - Return one FetchResult per entry with id URL, title, summary, authors, published, and updated metadata.
```

Use only `httpx`, `feedparser`, `json`, `os`, `re`, `html.parser`, and `xml.etree.ElementTree`; do not add BeautifulSoup for version 1.

- [ ] **Step 4: Add fetcher registry**

Modify `fetchers/__init__.py`:

```python
from __future__ import annotations

from .arxiv import ArxivFetcher
from .base import FetchResult, Fetcher
from .github import GitHubFetcher
from .rss import RssFetcher
from .web import WebFetcher


def fetcher_for(source_type: str) -> Fetcher:
    if source_type == "web":
        return WebFetcher()
    if source_type == "rss":
        return RssFetcher()
    if source_type == "github":
        return GitHubFetcher()
    if source_type == "arxiv":
        return ArxivFetcher()
    raise ValueError(f"Unsupported source type: {source_type}")


__all__ = ["FetchResult", "Fetcher", "fetcher_for"]
```

- [ ] **Step 5: Run fetcher tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_fetchers.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetchers personal-wiki/apps/crawler_workbench/backend/tests/test_fetchers.py
git commit -m "feat(workbench): add source fetchers"
```

Expected: commit includes fetcher modules and tests.

## Task 5: Manual Fetch Runs, Diffing, and Ingest Policy

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/policy.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py`

- [ ] **Step 1: Write failing policy and run-service tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py`:

```python
from crawler_workbench.db import connect, migrate
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.fetch_service import run_source_once
from crawler_workbench.policy import ingest_decision
from crawler_workbench.profiles import mirror_profiles
from crawler_workbench.settings import Settings


class StaticFetcher:
    def __init__(self, results):
        self.results = results

    def fetch(self, profile):
        return self.results


def profile(auto_ingest=True, trust_level="trusted", auth_required=False):
    return {
        "id": "src",
        "name": "Source",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com",
        "trust_level": trust_level,
        "schedule": "manual",
        "auto_ingest": auto_ingest,
        "auth_required": auth_required,
        "topic": "topic",
    }


def test_ingest_decision_blocks_untrusted_and_large():
    assert ingest_decision(profile(trust_level="untrusted"), 10).status == "pending"
    assert ingest_decision(profile(auth_required=True), 10).status == "pending"
    assert ingest_decision(profile(), 3_000_000, max_auto_ingest_bytes=2_000_000).status == "pending"
    assert ingest_decision(profile(), 10).status == "approved"


def test_run_source_once_records_raw_item_and_ingest_task(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    result = FetchResult(
        canonical_url="https://example.com/doc",
        title="Doc",
        content="hello",
        content_type="text/markdown",
        metadata={"kind": "test"},
    )
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        summary = run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
        tasks = db.execute("select status, reason from ingest_tasks").fetchall()
        raw_items = db.execute("select raw_path, content_hash from raw_items").fetchall()
    assert summary["changed_count"] == 1
    assert tasks[0]["status"] == "approved"
    assert "trusted" in tasks[0]["reason"]
    assert raw_items[0]["raw_path"].endswith(".md")


def test_run_source_once_skips_duplicate_hash(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    result = FetchResult("https://example.com/doc", "Doc", "hello", "text/markdown")
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
        second = run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
    assert second["skipped_count"] == 1
    assert second["changed_count"] == 0
```

- [ ] **Step 2: Run failing service tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_fetch_service_policy.py -q
```

Expected: FAIL with missing `crawler_workbench.fetch_service`.

- [ ] **Step 3: Implement ingest policy**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestDecision:
    status: str
    risk_level: str
    reason: str


def ingest_decision(
    profile: dict[str, object],
    content_bytes: int,
    max_auto_ingest_bytes: int = 2_000_000,
) -> IngestDecision:
    if bool(profile.get("auth_required")):
        return IngestDecision("pending", "auth_required", "source requires auth configuration and user confirmation")
    if profile.get("trust_level") != "trusted":
        return IngestDecision("pending", "untrusted", "source is not trusted for automatic ingest")
    if not bool(profile.get("auto_ingest")):
        return IngestDecision("pending", "manual", "auto ingest is disabled")
    if content_bytes > max_auto_ingest_bytes:
        return IngestDecision("pending", "large", "content is larger than automatic ingest limit")
    return IngestDecision("approved", "low", "trusted low-risk source eligible for automatic ingest")
```

- [ ] **Step 4: Implement run service**

Implement `run_source_once(settings, db, source_id, fetcher=None)` with these operations:

```python
# 1. Read source profile by id; raise ValueError when missing or disabled.
# 2. Insert fetch_runs row with status='running'.
# 3. Resolve fetcher via fetcher_for(profile["type"]) unless a test fetcher is passed.
# 4. For each FetchResult:
#    - check content_versions for same source_id, canonical_url, and content hash.
#    - duplicate: increment skipped_count.
#    - changed: write raw via write_raw_item, insert raw_items, insert content_versions.
#    - call ingest_decision(profile, raw_write.content_bytes, settings.max_auto_ingest_bytes).
#    - insert ingest_tasks with the decision status, risk_level, and reason.
# 5. Update fetch_runs with status='succeeded', counts, and finished_at.
# 6. On exception, update fetch_runs status='failed' and error text, then re-raise.
# 7. Return a dict with fetch_run_id, fetched_count, changed_count, and skipped_count.
```

Use ISO timestamps from SQLite `current_timestamp`; keep Python timestamps out of DB rows in this service.

- [ ] **Step 5: Add manual run API and run history API**

Modify `api.py` with:

```python
@router.post("/sources/{source_id}/run")
def run_source(source_id: str, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    with connect(settings.database_path) as db:
        return run_source_once(settings, db, source_id)


@router.get("/runs")
def runs(request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as db:
        rows = db.execute("select * from fetch_runs order by id desc limit 100").fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 6: Run service tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_fetch_service_policy.py -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py
git commit -m "feat(workbench): add manual source runs"
```

Expected: commit includes policy, fetch service, API additions, and tests.

## Task 6: Search Index and Graph API

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/search.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/graph_api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_search_graph.py`

- [ ] **Step 1: Write failing search and graph tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_search_graph.py`:

```python
from crawler_workbench.db import connect, migrate
from crawler_workbench.graph_api import domain_graph
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


def test_graph_api_uses_existing_wiki_graph(tmp_path):
    root = tmp_path / "personal-wiki"
    wiki_dir = root / "domains" / "ai_infra" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "a.md").write_text(PAGE.replace("NCCL Release Notes", "A") + "\n[Go](b.md)\n", encoding="utf-8")
    (wiki_dir / "b.md").write_text(PAGE.replace("NCCL Release Notes", "B"), encoding="utf-8")
    graph = domain_graph(Settings(repo_root=tmp_path, state_dir=tmp_path / ".state"), "ai_infra")
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == [{"source": "domains/ai_infra/wiki/a", "target": "domains/ai_infra/wiki/b"}]
```

- [ ] **Step 2: Run failing search and graph tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_search_graph.py -q
```

Expected: FAIL with missing `crawler_workbench.search`.

- [ ] **Step 3: Implement search indexer**

Implement `search.py` with:

```python
# public functions:
# - rebuild_search_index(settings, db, domain: str | None = None) -> int
# - search_wiki(db, query: str, domain: str | None = None, limit: int = 20) -> list[dict[str, object]]
#
# behavior:
# - Delete existing wiki_search_fts rows for the domain when domain is provided.
# - Walk personal-wiki/domains/{domain}/wiki/**/*.md excluding index.md and backlinks.json.
# - Parse simple YAML frontmatter with yaml.safe_load.
# - Insert path, domain, title, description, body excerpt, joined source_refs, and empty raw_metadata.
# - Add raw item rows from raw_items as raw_metadata rows with title and canonical_url.
# - Use FTS5 MATCH for non-empty query and bm25(wiki_search_fts) ranking.
# - Return path, domain, title, description, snippet, and score fields.
```

- [ ] **Step 4: Implement graph adapter**

Implement `graph_api.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

from .settings import Settings


def _load_graph_module(repo_root: Path):
    graph_path = repo_root / "personal-wiki" / "tools" / "wiki_cli" / "graph.py"
    spec = importlib.util.spec_from_file_location("workbench_wiki_graph", graph_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load wiki graph module from {graph_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def domain_graph(settings: Settings, domain: str | None = None) -> dict[str, object]:
    graph_module = _load_graph_module(settings.repo_root)
    return graph_module.build_graph(settings.wiki_root, domain)
```

- [ ] **Step 5: Add search and graph endpoints**

Modify `api.py`:

```python
@router.get("/search")
def search(q: str, request: Request, domain: str | None = None) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as db:
        return search_wiki(db, q, domain=domain)


@router.post("/search/rebuild")
def rebuild_search(request: Request, domain: str | None = None) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as db:
        count = rebuild_search_index(request.app.state.settings, db, domain=domain)
    return {"indexed": count}


@router.get("/graph")
def graph(request: Request, domain: str | None = None) -> dict[str, object]:
    return domain_graph(request.app.state.settings, domain)
```

- [ ] **Step 6: Run search and graph tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_search_graph.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 7: Commit Task 6**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_search_graph.py
git commit -m "feat(workbench): add search and graph APIs"
```

Expected: commit includes search, graph, API additions, and tests.

## Task 7: Codex Worker and Query Jobs

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/codex_worker.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_codex_worker.py`

- [ ] **Step 1: Write failing Codex worker tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_codex_worker.py`:

```python
from pathlib import Path

from crawler_workbench.codex_worker import build_query_prompt, run_codex_job
from crawler_workbench.db import connect, migrate
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
```

- [ ] **Step 2: Run failing Codex tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_codex_worker.py -q
```

Expected: FAIL with missing `crawler_workbench.codex_worker`.

- [ ] **Step 3: Implement prompt builder and job runner**

Implement `codex_worker.py` with:

```python
# public functions:
# - build_query_prompt(domain: str, question: str, persist: bool) -> str
# - run_codex_job(settings, db, job_type: str, domain: str | None, user_input: str, persist: bool = False) -> int
#
# prompt for persist=False:
# 使用 personal-wiki-manager，目标 domain: {domain}，基于已有 wiki/raw 回答 "{question}"，引用路径；不要修改文件，不要运行写入命令，只返回答案和引用。
#
# prompt for persist=True:
# 使用 personal-wiki-manager，目标 domain: {domain}，基于已有 wiki/raw 回答 "{question}"，引用路径；如果答案有长期复用价值，沉淀进最小合适 curated wiki 页面，然后 index+validate 并报告文件。
#
# subprocess command:
# [settings.codex_command, "exec", "--cd", str(settings.repo_root), "--sandbox", "workspace-write", "--ask-for-approval", "never", prompt]
#
# DB behavior:
# - insert codex_jobs pending row with prompt
# - update to running with started_at
# - subprocess.run capture_output=True text=True timeout=1800
# - update succeeded when returncode == 0 else failed
# - store stdout, stderr, exit_code, finished_at
# - return job id
```

- [ ] **Step 4: Add ask and jobs endpoints**

Modify `api.py`:

```python
@router.post("/ask")
def ask(payload: dict[str, object], request: Request) -> dict[str, object]:
    domain = str(payload["domain"])
    question = str(payload["question"])
    persist = bool(payload.get("persist", False))
    with connect(request.app.state.settings.database_path) as db:
        job_id = run_codex_job(request.app.state.settings, db, "query", domain, question, persist=persist)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def job(job_id: int, request: Request) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as db:
        row = db.execute("select * from codex_jobs where id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return dict(row)
```

- [ ] **Step 5: Run Codex worker tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_codex_worker.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit Task 7**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_codex_worker.py
git commit -m "feat(workbench): add codex query jobs"
```

Expected: commit includes Codex worker, endpoints, and tests.

## Task 8: Wiki CLI, Ingest Queue, Validation, and Auto-Commit

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/wiki_cli.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/git_ops.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/ingest.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_ingest_git.py`

- [ ] **Step 1: Write failing ingest and Git safety tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_ingest_git.py`:

```python
import subprocess

from crawler_workbench.db import connect, migrate
from crawler_workbench.git_ops import git_dirty_paths, paths_owned_by_task
from crawler_workbench.ingest import list_queue
from crawler_workbench.settings import Settings


def init_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def test_list_queue_returns_pending_tasks(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        db.execute(
            "insert into ingest_tasks (source_id, target_domain, status, risk_level, reason) values (?, ?, ?, ?, ?)",
            ("src", "ai_infra", "pending", "untrusted", "needs review"),
        )
        db.commit()
        rows = list_queue(db)
    assert rows[0]["status"] == "pending"
    assert rows[0]["reason"] == "needs review"


def test_git_dirty_paths_and_owned_paths(tmp_path):
    init_git_repo(tmp_path)
    owned = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "x.md"
    other = tmp_path / "other.txt"
    owned.parent.mkdir(parents=True)
    owned.write_text("x", encoding="utf-8")
    other.write_text("y", encoding="utf-8")
    dirty = git_dirty_paths(tmp_path)
    assert "personal-wiki/domains/ai_infra/wiki/x.md" in dirty
    assert paths_owned_by_task(dirty, ["personal-wiki/domains/ai_infra/"]) is False
```

- [ ] **Step 2: Run failing ingest tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_ingest_git.py -q
```

Expected: FAIL with missing `crawler_workbench.git_ops`.

- [ ] **Step 3: Implement wiki CLI wrapper**

Implement `wiki_cli.py` with:

```python
# public functions:
# - wiki_cli_command(settings, *args) -> list[str]
# - run_wiki_cli(settings, *args) -> subprocess.CompletedProcess[str]
# - run_ingest_plan(settings, domain: str, raw_path: str) -> subprocess.CompletedProcess[str]
# - run_index(settings, domain: str) -> subprocess.CompletedProcess[str]
# - run_backlinks(settings, domain: str) -> subprocess.CompletedProcess[str]
# - run_validate(settings, domain: str | None = None) -> subprocess.CompletedProcess[str]
#
# command format:
# ["python", "personal-wiki/tools/wiki_cli/cli.py", "--root", "personal-wiki", ...]
# cwd is settings.repo_root
# capture stdout/stderr as text
```

- [ ] **Step 4: Implement Git safety helpers**

Implement `git_ops.py` with:

```python
# public functions:
# - git_dirty_paths(repo_root: Path) -> set[str]
# - paths_owned_by_task(paths: set[str], owned_prefixes: list[str]) -> bool
# - auto_commit(repo_root: Path, paths: list[str], message: str) -> str
#
# dirty command:
# git status --porcelain
#
# paths_owned_by_task behavior:
# - return True when every dirty path starts with one of the owned prefixes
# - return False when any dirty path is outside all prefixes
#
# auto_commit behavior:
# - git add -- <paths>
# - git diff --cached --quiet returns no commit and raises ValueError("no staged changes")
# - git commit -m message
# - git rev-parse HEAD returns commit sha
```

- [ ] **Step 5: Implement ingest queue and trusted pipeline**

Implement `ingest.py` with:

```python
# public functions:
# - list_queue(db) -> list[dict[str, object]]
# - approve_task(settings, db, task_id: int) -> dict[str, object]
# - reject_task(db, task_id: int, reason: str) -> dict[str, object]
# - run_approved_task(settings, db, task_id: int, auto_commit_enabled: bool) -> dict[str, object]
#
# run_approved_task operations:
# 1. Load ingest task and raw_item.
# 2. Mark task running.
# 3. Run wiki CLI ingest-plan for the raw path.
# 4. Run Codex job with prompt:
#    使用 personal-wiki-manager，目标 domain: {domain}，入库 {raw_path}，按 raw->ingest-plan->wiki->compact->index->validate 完整流程处理；大型资料 raw 保完整但可 gzip 压缩，wiki 只沉淀索引/综合/关键结论，优先更新已有页面，报告文件和验证结果。
# 5. Run wiki CLI index and backlinks --write-json for the domain.
# 6. Run wiki CLI validate --domain {domain}; insert validation_runs row.
# 7. If validation exit code is non-zero, mark task failed and do not commit.
# 8. If auto_commit_enabled, verify dirty paths are owned by:
#    personal-wiki/domains/{domain}/
#    personal-wiki/global/
# 9. Commit with message:
#    chore(wiki): ingest {domain} {source_id}
# 10. Insert commit_records row and mark task succeeded.
```

- [ ] **Step 6: Add queue, approve, reject, validate, and commit endpoints**

Modify `api.py`:

```python
@router.get("/queue")
def queue(request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as db:
        return list_queue(db)


@router.post("/queue/{task_id}/approve")
def approve(task_id: int, request: Request) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as db:
        return approve_task(request.app.state.settings, db, task_id)


@router.post("/queue/{task_id}/reject")
def reject(task_id: int, payload: dict[str, object], request: Request) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as db:
        return reject_task(db, task_id, str(payload.get("reason", "rejected by user")))


@router.post("/validate")
def validate(payload: dict[str, object], request: Request) -> dict[str, object]:
    domain = payload.get("domain")
    result = run_validate(request.app.state.settings, str(domain) if domain else None)
    return {"status": "succeeded" if result.returncode == 0 else "failed", "stdout": result.stdout, "stderr": result.stderr}
```

- [ ] **Step 7: Run ingest and Git tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_ingest_git.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 8: Run all backend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q
```

Expected: PASS with every backend test passing.

- [ ] **Step 9: Commit Task 8**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_ingest_git.py
git commit -m "feat(workbench): add ingest queue pipeline"
```

Expected: commit includes wiki CLI wrapper, queue pipeline, Git safety, API additions, and tests.

## Task 9: Scheduler Loop

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/scheduler.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`

- [ ] **Step 1: Write failing scheduler/API tests**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings


def test_domains_endpoint_lists_domain_directories(tmp_path):
    (tmp_path / "personal-wiki" / "domains" / "ai_infra").mkdir(parents=True)
    app = create_app(Settings(repo_root=tmp_path, state_dir=tmp_path / ".state"))
    client = TestClient(app)
    response = client.get("/api/domains")
    assert response.status_code == 200
    assert response.json() == [{"id": "ai_infra", "name": "ai_infra"}]


def test_settings_endpoint_includes_warning(tmp_path):
    app = create_app(Settings(repo_root=tmp_path, state_dir=tmp_path / ".state"))
    client = TestClient(app)
    data = client.get("/api/settings").json()
    assert data["bind_host"] == "0.0.0.0"
    assert data["authenticated"] is False
    assert "No login" in data["warning"]
```

- [ ] **Step 2: Run failing API tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_api.py -q
```

Expected: FAIL because `/api/domains` and `/api/settings` are absent.

- [ ] **Step 3: Implement scheduler**

Implement `scheduler.py` with:

```python
# public class:
# class Scheduler:
#     def __init__(self, settings: Settings) -> None
#     async def start(self) -> None
#     async def stop(self) -> None
#     async def run_once(self) -> int
#
# behavior:
# - run_once selects enabled profiles where schedule != 'manual' and auth_state = 'ready'.
# - for version 1, due logic treats every non-manual profile with next_run_at null or <= current_timestamp as due.
# - call run_source_once for each due source.
# - update next_run_at based on schedule:
#   hourly: +1 hour
#   daily: +1 day
#   weekly: +7 days
# - start creates an asyncio task that sleeps settings.scheduler_interval_seconds between run_once calls.
# - stop cancels the task cleanly.
```

Hook scheduler into `main.py` startup and shutdown only when `PW_WORKBENCH_DISABLE_SCHEDULER` is not set to `1`.

- [ ] **Step 4: Add domains and settings endpoints**

Modify `api.py`:

```python
@router.get("/domains")
def domains(request: Request) -> list[dict[str, str]]:
    domains_dir = request.app.state.settings.wiki_root / "domains"
    if not domains_dir.exists():
        return []
    return [
        {"id": path.name, "name": path.name}
        for path in sorted(domains_dir.iterdir())
        if path.is_dir()
    ]


@router.get("/settings")
def settings(request: Request) -> dict[str, object]:
    resolved = request.app.state.settings
    return {
        "bind_host": resolved.bind_host,
        "bind_port": resolved.bind_port,
        "authenticated": False,
        "warning": resolved.trusted_network_warning,
        "wiki_root": str(resolved.wiki_root),
        "database_path": str(resolved.database_path),
    }
```

- [ ] **Step 5: Run API tests and all backend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest tests/test_api.py -q
PYTHONPATH=. pytest -q
```

Expected: both commands pass.

- [ ] **Step 6: Commit Task 9**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests/test_api.py
git commit -m "feat(workbench): add scheduler and utility APIs"
```

Expected: commit includes scheduler, domains/settings endpoints, and tests.

## Task 10: Frontend Shell, API Client, and Chinese Navigation

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/frontend/package.json`
- Create: `personal-wiki/apps/crawler_workbench/frontend/index.html`
- Create: `personal-wiki/apps/crawler_workbench/frontend/tsconfig.json`
- Create: `personal-wiki/apps/crawler_workbench/frontend/vite.config.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/main.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/Layout.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/StatusBadge.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`

- [ ] **Step 1: Add frontend package and test shell**

Use `apply_patch` to create `package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc && vite build",
    "test": "vitest run",
    "test:ui": "playwright test"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest",
    "lucide-react": "latest",
    "recharts": "latest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "@playwright/test": "latest",
    "vitest": "latest",
    "jsdom": "latest"
  }
}
```

Use `apply_patch` to create `App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("shows operations-first Chinese navigation and trusted-network warning", () => {
    render(<App />);
    expect(screen.getByText("运维控制台")).toBeInTheDocument();
    expect(screen.getByText("知识工作台")).toBeInTheDocument();
    expect(screen.getByText("来源工作台")).toBeInTheDocument();
    expect(screen.getByText(/无登录/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run failing frontend test**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm install
npm test
```

Expected: FAIL because `src/App.tsx` does not exist.

- [ ] **Step 3: Implement frontend shell**

Create the Vite/React shell with:

```tsx
// App.tsx contract
// - Top-level state: active page key.
// - Navigation labels in Chinese:
//   运维控制台, 来源订阅, 入库队列, 知识工作台, 来源工作台, 设置
// - Persistent warning banner:
//   "无登录：仅可暴露在可信网络。后端可触发本机 Codex。"
// - Default active page: overview.
// - Use lucide-react icons for navigation buttons.
// - Import page components from src/pages.
```

Create `Layout.tsx` with compact sidebar navigation, active button state, and a main content region.

Create `StatusBadge.tsx` with statuses: `ready`, `pending`, `running`, `succeeded`, `failed`, `needs_auth_config`, `trusted`, `untrusted`.

Create `styles.css` with:

```css
:root {
  color: #172026;
  background: #f6f7f9;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

button,
input,
textarea,
select {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px 1fr;
}

.sidebar {
  background: #101820;
  color: #f7fafc;
  padding: 16px;
}

.nav-button {
  width: 100%;
  height: 38px;
  border: 0;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  color: inherit;
  background: transparent;
  cursor: pointer;
}

.nav-button.active {
  background: #2f6f73;
}

.main {
  min-width: 0;
  padding: 18px 22px;
}

.warning {
  border: 1px solid #c97b2e;
  background: #fff7ed;
  color: #6f3d12;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 14px;
}
```

Use restrained, multi-hue UI colors: dark neutral sidebar, teal active states, amber warning, green/red status accents.

- [ ] **Step 4: Run frontend test**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
```

Expected: PASS with the App test passing.

- [ ] **Step 5: Commit Task 10**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/frontend .gitignore
git commit -m "feat(workbench): add frontend shell"
```

Expected: commit includes frontend shell and tests.

## Task 11: Operations Console and Source Workbench Visualizations

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/TrendChart.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/OverviewPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/QueuePage.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourceWorkbenchPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`

- [ ] **Step 1: Extend frontend tests for operations and source visuals**

Add tests asserting these Chinese labels render:

```tsx
expect(screen.getByText("运行健康")).toBeInTheDocument();
expect(screen.getByText("待处理入库")).toBeInTheDocument();
expect(screen.getByText("抓取趋势")).toBeInTheDocument();
expect(screen.getByText("来源覆盖")).toBeInTheDocument();
expect(screen.getByText("失败原因分布")).toBeInTheDocument();
```

- [ ] **Step 2: Run failing frontend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
```

Expected: FAIL because the new page labels are absent.

- [ ] **Step 3: Implement API client and types**

Create typed functions:

```ts
export async function getHealth(): Promise<HealthResponse>;
export async function getSources(): Promise<SourceProfile[]>;
export async function runSource(id: string): Promise<RunSummary>;
export async function getRuns(): Promise<FetchRun[]>;
export async function getQueue(): Promise<IngestTask[]>;
export async function approveTask(id: number): Promise<Record<string, unknown>>;
export async function rejectTask(id: number, reason: string): Promise<Record<string, unknown>>;
```

Use `fetch` with base URL from `import.meta.env.VITE_API_BASE ?? "http://localhost:8765"`.

- [ ] **Step 4: Implement operations pages**

Implement:

```tsx
// OverviewPage
// - Run health block
// - Next scheduled runs block
// - Auth warnings block
// - Pending ingest block
// - Validation failures block
// - Recent auto-commits block
// - TrendChart for fetch/change/failure counts

// SourcesPage
// - Source rows grouped by type and domain
// - Trust, schedule, auth state, last run
// - Run button with Play icon

// QueuePage
// - Pending/running/failed task list
// - Approve button with Check icon
// - Reject button with X icon

// SourceWorkbenchPage
// - Source coverage visualization by domain/type
// - Crawl timeline
// - Topic heat map
// - Failure reason distribution
```

Use Recharts for bar, line, and pie visuals. Use fixed chart container heights to prevent layout shift.

- [ ] **Step 5: Run frontend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
```

Expected: PASS with all frontend unit tests passing.

- [ ] **Step 6: Commit Task 11**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/frontend/src
git commit -m "feat(workbench): add operations and source views"
```

Expected: commit includes operations console, source subscriptions, ingest queue, and source visualization UI.

## Task 12: Knowledge Workbench Search, Query, and Graph Visualization

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/components/WikiGraph.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/KnowledgePage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`

- [ ] **Step 1: Add knowledge workbench tests**

Add tests asserting:

```tsx
expect(screen.getByText("全文搜索")).toBeInTheDocument();
expect(screen.getByText("Codex 查询")).toBeInTheDocument();
expect(screen.getByText("引用路径")).toBeInTheDocument();
expect(screen.getByText("知识关系图")).toBeInTheDocument();
expect(screen.getByText("主题时间线")).toBeInTheDocument();
```

- [ ] **Step 2: Run failing frontend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
```

Expected: FAIL because knowledge workbench controls are absent.

- [ ] **Step 3: Add knowledge API client methods**

Add:

```ts
export async function searchWiki(query: string, domain?: string): Promise<SearchResult[]>;
export async function askCodex(domain: string, question: string, persist: boolean): Promise<{ job_id: number }>;
export async function getJob(id: number): Promise<CodexJob>;
export async function getGraph(domain?: string): Promise<WikiGraphResponse>;
export async function rebuildSearch(domain?: string): Promise<{ indexed: number }>;
```

- [ ] **Step 4: Implement `WikiGraph`**

Create a lightweight SVG relationship graph:

```tsx
// Props: nodes and edges.
// Layout: deterministic circular layout.
// Nodes: small circles with title tooltip and type color.
// Edges: SVG lines.
// Empty state text: "暂无关系数据".
// Fixed height: 360px.
```

- [ ] **Step 5: Implement `KnowledgePage`**

Implement:

```tsx
// Controls:
// - Domain selector
// - Search input and Search button
// - Codex question textarea
// - Persist checkbox labeled "有长期价值时沉淀进 curated wiki"
// - Ask button
//
// Panels:
// - Search results with path/title/description
// - Answer panel polling /api/jobs/{id} every 1500ms while pending/running
// - Cited path section named "引用路径"
// - Related wiki pages
// - WikiGraph visualization
// - Topic timeline visualization using Recharts
```

The persisted-query checkbox defaults to unchecked. The prompt still asks Codex to use `personal-wiki-manager` through the backend.

- [ ] **Step 6: Run frontend tests and build**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
npm run build
```

Expected: both commands pass.

- [ ] **Step 7: Commit Task 12**

Run:

```bash
git add personal-wiki/apps/crawler_workbench/frontend/src
git commit -m "feat(workbench): add knowledge workbench"
```

Expected: commit includes search, query, graph, and timeline UI.

## Task 13: Documentation, Run Scripts, and End-to-End Smoke

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/README.md`
- Create: `personal-wiki/apps/crawler_workbench/frontend/tests/smoke.spec.ts`
- Modify: `personal-wiki/apps/crawler_workbench/backend/requirements.txt`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/package.json`

- [ ] **Step 1: Add runbook**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/README.md` with:

```markdown
# Personal Wiki Crawler Workbench

This is a local single-user workbench for `personal-wiki`.

## Security Boundary

The service has no login. It can trigger local `codex exec` and write to this repository. Bind it to `0.0.0.0` only on a trusted network.

## Backend

```bash
cd personal-wiki/apps/crawler_workbench/backend
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
PW_WORKBENCH_REPO_ROOT=/home/fyz/codex-skills uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765
```

## Frontend

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm install
VITE_API_BASE=http://localhost:8765 npm run dev -- --host 0.0.0.0
```

## Source Profiles

Copy `config/sources.example.yaml` to `.personal-wiki-workbench/sources.yaml`, then edit source ids, domains, URLs, schedules, and trust levels.

Auth-required profiles store only references:

- `auth_method: env_token` with `auth_ref: GITHUB_TOKEN`
- `auth_method: command` with `auth_ref: local-token-command`
- `auth_method: header_template` with `auth_ref: local-header-template-name`
- `auth_method: cookie_file` with `auth_ref: /local/path/cookies.txt`

Do not store token values in wiki files or Git.

## Validation

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q

cd ../frontend
npm test
npm run build
```
```

- [ ] **Step 2: Add Playwright smoke test**

Use `apply_patch` to create `personal-wiki/apps/crawler_workbench/frontend/tests/smoke.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test("workbench pages render", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("运维控制台")).toBeVisible();
  await expect(page.getByText("无登录")).toBeVisible();
  await page.getByRole("button", { name: /知识工作台/ }).click();
  await expect(page.getByText("Codex 查询")).toBeVisible();
  await page.getByRole("button", { name: /来源工作台/ }).click();
  await expect(page.getByText("来源覆盖")).toBeVisible();
});
```

Configure Playwright in `package.json` through the existing `test:ui` script. Use Vite's web server option in `playwright.config.ts` when adding the config file:

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  webServer: {
    command: "npm run dev -- --host 127.0.0.1",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true
  },
  use: {
    baseURL: "http://127.0.0.1:5173"
  }
});
```

- [ ] **Step 3: Run full backend verification**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q
```

Expected: PASS with every backend test passing.

- [ ] **Step 4: Run full frontend verification**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
npm run build
npm run test:ui
```

Expected: PASS for unit tests, build, and Playwright smoke.

- [ ] **Step 5: Run personal wiki validation**

Run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
```

Expected: both commands print `No validation issues`.

- [ ] **Step 6: Commit Task 13**

Run:

```bash
git add personal-wiki/apps/crawler_workbench
git commit -m "docs(workbench): add runbook and smoke tests"
```

Expected: commit includes README and Playwright smoke coverage.

## Final Verification Before Handoff

- [ ] **Step 1: Run backend tests**

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend tests and build**

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
npm run build
```

Expected: frontend tests and production build pass.

- [ ] **Step 3: Run Playwright smoke**

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm run test:ui
```

Expected: smoke test passes for Operations Console, Knowledge Workbench, and Source Workbench.

- [ ] **Step 4: Run wiki validation**

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
```

Expected: both commands print `No validation issues`.

- [ ] **Step 5: Start backend for user access**

```bash
cd personal-wiki/apps/crawler_workbench/backend
PW_WORKBENCH_REPO_ROOT=/home/fyz/codex-skills uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765
```

Expected: server listens on `0.0.0.0:8765` and logs the trusted-network warning.

- [ ] **Step 6: Start frontend for user access**

```bash
cd personal-wiki/apps/crawler_workbench/frontend
VITE_API_BASE=http://localhost:8765 npm run dev -- --host 0.0.0.0
```

Expected: Vite prints a network URL and the UI renders in Chinese.
