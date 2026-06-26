# Personal Wiki Crawler Workbench Design

## Goal

Build a local single-user workbench that can regularly crawl agreed source topics, ingest trusted changes into `personal-wiki`, visualize the existing wiki, and trigger Codex-powered wiki queries without requiring a separate API key configuration.

## Scope

The first version is a local service bound to `0.0.0.0` for use on a trusted network. It does not implement user login or multi-user authorization. The UI must clearly show that it is unauthenticated and intended only for trusted-network exposure.

Supported source types in the first version:

- Generic web pages.
- RSS feeds.
- GitHub releases, issues, and pull requests.
- arXiv and paper metadata/pages.

Sources marked as requiring authentication must not crawl automatically until the user explicitly configures the access method.

## Non-Goals

- Cloud deployment.
- Multi-user access control.
- Vector search or embedding storage.
- Browser automation for complex authenticated sites.
- Bypassing website access controls or anti-crawling protections.
- Replacing `raw/` and `wiki/` as the durable fact and curated layers.

## Architecture

Use `FastAPI + SQLite FTS5 + React/Vite`.

The system is split into these components:

- `Crawler Profiles`: source configuration, trust level, schedule, auth mode, topic, target domain, and ingest policy.
- `Scheduler`: periodic runner for enabled source profiles.
- `Fetchers`: source-specific fetch logic for web, RSS, GitHub, and arXiv/papers.
- `Workbench DB`: SQLite database for source profiles, fetch history, diff metadata, task state, search index, validation runs, Codex jobs, and commit records.
- `Ingest Pipeline`: converts fetched raw items into wiki updates through the existing `personal-wiki-manager` workflow.
- `Codex Worker`: invokes local `codex exec`, reusing the user's local Codex auth and config.
- `FastAPI Backend`: exposes source, run, queue, search, query, graph, validation, commit, and settings APIs.
- `React Frontend`: operations-first UI with knowledge and source workbenches.

`personal-wiki` remains the durable repository. SQLite is a local workbench/cache layer, not the source of truth.

## Data Flow

### Crawl Flow

1. Scheduler selects due trusted source profiles.
2. Fetcher reads source content and metadata.
3. System compares `etag`, `last-modified`, canonical URL, and content hash against previous runs.
4. New or changed content is written under the target domain's `raw/` tree.
5. A raw item and ingest task are recorded in SQLite.
6. Duplicate or unchanged content is recorded as skipped.

### Ingest Flow

The system uses a hybrid ingest policy:

- Trusted source with low-risk change:
  `raw -> ingest-plan -> wiki -> compact -> index -> validate -> commit`.
- New, auth-required, untrusted, high-risk, or large change:
  create a pending ingest task and show it in the UI for user confirmation.

The ingest pipeline must preserve `source_refs`, update `ingest.md`, compact large raw evidence, rebuild indexes/backlinks where relevant, run validation, and only commit when validation passes.

### Query Flow

1. User asks a question in the Knowledge Workbench.
2. Backend creates a Codex job.
3. Codex Worker invokes local `codex exec` in the repository:
   ```bash
   codex exec --cd /home/fyz/codex-skills --sandbox workspace-write --ask-for-approval never "<prompt>"
   ```
4. Prompt requires `personal-wiki-manager`, target domain, source path citations, and no API key handling by the web app.
5. Backend streams or polls job status.
6. UI shows the final answer, cited wiki/raw paths, and any suggested durable wiki update.

Query-only jobs must instruct Codex to avoid edits. Query-to-wiki or ingest jobs can edit the workspace only when the job requires persistence, and those jobs must run validation.

## Authentication for Sources

Source auth is configured per source profile. The system supports these auth methods:

- Environment variable token reference.
- Command-based token provider.
- User-provided HTTP header template.
- User-provided cookie file path.

Sensitive values are never stored in wiki files and are never committed to Git. SQLite may store only non-secret references, such as env var names or local file paths. A source with `auth_required = true` starts in `needs_auth_config` and does not run until the user confirms the access method.

The UI must show:

- Target host/domain.
- Requested auth method.
- What the crawler will access.
- Whether the source is eligible for auto-ingest.

## Auto-Commit Policy

Trusted source auto-ingest may commit automatically only when all of these are true:

- The source profile is trusted.
- No auth warning or policy warning is active.
- The ingest task completes.
- `index` and `validate` pass.
- No unrelated dirty files are staged.

Untrusted, auth-required, high-risk, failed, or manually triggered tasks remain uncommitted and visible in the queue.

Auto-commit creates one commit per successful trusted source run. If a scheduler cycle processes multiple trusted sources, each source run commits independently after its own validation pass. The commit message identifies the source profile and target domain, for example:

```text
chore(wiki): ingest ai_infra nccl release updates
```

## Frontend Information Architecture

The default first screen is Operations Console.

Top-level navigation:

- Overview.
- Source Subscriptions.
- Ingest Queue.
- Knowledge Workbench.
- Source Workbench.
- Settings.

### Operations Console

Shows crawler and ingest operations first:

- Run health.
- Next scheduled runs.
- Auth warnings.
- Pending ingest and validation failures.
- Recent auto-commits.
- Fetch/change/failure trends.

### Knowledge Workbench

Supports reading and querying wiki knowledge:

- Full-text search over wiki pages and indexed raw metadata.
- Codex question box.
- Answer panel with cited paths.
- Related wiki pages.
- Wiki graph/backlinks visualization.
- Topic timeline and relationship visualizations.

### Source Workbench

Supports source management and crawler inspection:

- Source cards grouped by type and domain.
- Trust level, schedule, auth state, and last run.
- Fetch history and change diff.
- Source coverage visualization.
- Crawl timeline.
- Topic heat map.
- Failure reason distribution.

## Backend API Sketch

Initial endpoints:

- `GET /api/health`
- `GET /api/domains`
- `GET /api/sources`
- `POST /api/sources`
- `PATCH /api/sources/{id}`
- `POST /api/sources/{id}/run`
- `GET /api/runs`
- `GET /api/queue`
- `POST /api/queue/{id}/approve`
- `POST /api/queue/{id}/reject`
- `GET /api/search?q=...&domain=...`
- `POST /api/ask`
- `GET /api/jobs/{id}`
- `GET /api/graph?domain=...`
- `POST /api/validate`
- `POST /api/commit`
- `GET /api/settings`

Long-running crawl, ingest, validate, and Codex jobs run in background workers. The first version uses FastAPI background tasks plus a SQLite-backed job queue. The frontend polls job status endpoints at a short interval while a job is active.

## SQLite Model Sketch

Core tables:

- `source_profiles`
- `source_auth_refs`
- `fetch_runs`
- `raw_items`
- `content_versions`
- `ingest_tasks`
- `codex_jobs`
- `validation_runs`
- `commit_records`
- `wiki_search_fts`

`wiki_search_fts` indexes curated wiki page title, description, aliases, tags, body excerpt, source refs, and raw item metadata. Full raw content can remain compressed on disk and does not need to be copied into SQLite.

Source profiles are declared in YAML files under a local app config directory and mirrored into SQLite for runtime queries. SQLite stores state, run history, and normalized profile fields; YAML remains the hand-editable configuration source.

## Error Handling

- Fetch failure: record run status and error, keep previous content unchanged.
- Auth failure: mark source as `needs_auth_config` or `auth_failed`.
- Duplicate content: record skipped item with matched hash.
- Large content: write raw, create pending task, and avoid automatic wiki expansion.
- Ingest failure: store Codex output and leave task pending/failure.
- Validation failure: do not commit; show validation issues in UI.
- Dirty Git state: block auto-commit unless dirty files are owned by the current task.

## Security Boundaries

The app is local single-user and unauthenticated. It binds to `0.0.0.0` only because the user requested remote access on a trusted network. The UI and startup log must warn that there is no login.

The backend can trigger `codex exec`; therefore, the service must not be exposed to untrusted networks. The app must not print or persist Codex auth tokens, API keys, source cookies, or token values.

## Testing Strategy

Backend:

- Unit tests for source profile validation.
- Unit tests for URL canonicalization and content hashing.
- Fetcher tests with fixture responses for web, RSS, GitHub, and arXiv.
- SQLite migration/model tests.
- Ingest policy tests for trusted, untrusted, auth-required, high-risk, and validation-failed cases.
- Codex Worker tests using a fake `codex` executable.
- API tests with FastAPI test client.

Frontend:

- Component tests for operations dashboard, source cards, queue, search, and job status.
- Basic Playwright smoke test for the three workbench views.

End-to-end:

- Create a test domain.
- Add a trusted local HTTP fixture source.
- Run crawl.
- Verify raw item, ingest task, index rebuild, validation pass, and commit decision.

## Implementation Phases

### Phase 1: Local Backend Skeleton

Create FastAPI app, settings, SQLite connection, migrations, health endpoint, and source profile CRUD.

### Phase 2: Fetchers and Scheduler

Implement web, RSS, GitHub, and arXiv fetchers with content hashing and run records. Add manual run endpoint and simple scheduler loop.

### Phase 3: Search and Graph APIs

Index existing wiki pages into SQLite FTS5. Expose search and graph endpoints using existing wiki graph data.

### Phase 4: Codex Worker

Add `codex exec` job runner, job status API, output capture, and query prompt templates that reuse `personal-wiki-manager`.

### Phase 5: Ingest Queue and Auto-Commit

Implement hybrid ingest policy, approval/rejection endpoints, validation capture, compact step integration, and trusted-source auto-commit.

### Phase 6: React Workbench

Build operations-first UI, source workbench, knowledge workbench, visualizations, search, and Codex job status.
