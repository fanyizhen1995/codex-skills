# Domain Channel Management Design

## Goal

Add domain-scoped channel management to Crawler Workbench so each wiki domain can manage its durable access boundaries separately from concrete crawl targets.

The feature must let the user manage base sites or tools such as `https://github.com`, `https://api.github.com`, `https://arxiv.org`, an internal portal, an MCP server, or a local command source. A channel owns authentication, access probing, trust state, and access failure history. A source remains the specific knowledge crawl target under that channel, such as `https://github.com/NVIDIA/nccl` for NCCL issues, releases, or repository metadata.

## Requirements

- SQLite becomes the runtime source of truth for channel and source configuration.
- Existing `sources.yaml` is imported only once when the runtime database is empty. After that, YAML is an optional seed/export artifact, not an automatic override.
- Channel secrets are stored in a local encrypted SQLite table. The encryption key is generated under the workbench state directory for local single-user convenience.
- The frontend gets a dedicated Domain Channels page for channel, secret, probe, and child-source management.
- Probe history is retained per channel. The UI shows the latest probe status in lists and the recent history in the channel detail panel.
- Browser-like channels are represented in the data model, but first-version verification uses HTTP probing only and records `needs_browser` when HTTP is insufficient.

## Definitions

### Channel

A channel is an access and authentication boundary. It answers:

- What base entry point will be accessed?
- How is it authenticated?
- Can it currently be reached?
- Does it need browser or future visual automation?
- Which sources depend on it?

Examples:

- `https://github.com`
- `https://api.github.com`
- `https://github.com/NVIDIA`
- `https://developer.nvidia.com/blog`
- `https://internal.example.com/team-a`
- `mcp://local-research-tools`
- `command://local-vendor-export`

### Source

A source is a concrete crawl target and ingest policy under a channel. It answers:

- Which URL, query, tool, or command output should be collected?
- Which fetcher or collector should run?
- Which domain should receive raw evidence and ingest tasks?
- What schedule, filters, and auto-ingest policy apply?

Examples:

- NCCL closed issues from `https://github.com/NVIDIA/nccl`
- NCCL GitHub releases from `https://github.com/NVIDIA/nccl/releases`
- NVIDIA blog RSS entries matching NCCL keywords
- arXiv query results for a topic
- A future MCP tool call that lists internal design docs

## Data Model

### `channels`

Add a new `channels` table:

- `id text primary key`
- `target_domain text not null`
- `name text not null`
- `base_url text not null`
- `base_url_normalized text not null`
- `probe_url text`
- `probe_method text not null default 'GET'`
- `probe_config_json text not null default '{}'`
- `kind text not null`
- `connector text not null default 'generic'`
- `trust_level text not null default 'untrusted'`
- `enabled integer not null default 1`
- `auth_required integer not null default 0`
- `auth_mode text not null default 'none'`
- `auth_state text not null default 'ready'`
- `last_probe_status text`
- `last_probe_at text`
- `last_probe_summary text`
- `notes text not null default ''`
- `created_at text not null default current_timestamp`
- `updated_at text not null default current_timestamp`

`base_url_normalized` is unique per domain. The default normalizer uses origin or host-like boundaries, but the user may choose a more specific base URL such as `https://github.com/NVIDIA`.

`probe_url` is optional and defaults to `base_url`. It exists because the best credential check is often not the same as the base URL. For example, a channel may represent `https://github.com` while token validation uses `https://api.github.com/user`.

`kind` describes access style, not a specific website:

- `web`
- `api`
- `mcp`
- `browser`
- `command`

`connector` describes the optional site or protocol adapter:

- `generic`
- `github`
- `arxiv`
- `rss`
- future values such as `lark`, `notion`, `huggingface`

`auth_mode` values:

- `none`
- `token`
- `cookie`
- `header`
- `basic`
- `command`
- `oauth_placeholder`

`auth_state` values:

- `ready`
- `needs_auth_config`
- `auth_failed`
- `needs_browser`
- `network_failed`
- `unsupported`

### `channel_secrets`

Add a local encrypted secret table:

- `id text primary key`
- `channel_id text not null references channels(id) on delete cascade`
- `secret_kind text not null`
- `ciphertext blob not null`
- `nonce blob not null`
- `created_at text not null default current_timestamp`
- `updated_at text not null default current_timestamp`

Each channel has at most one active encrypted secret payload in the first version. The payload can represent a token, cookie, header set, or basic-auth tuple depending on `auth_mode`.

The workbench generates a key file under the state directory, for example `.personal-wiki-workbench/secrets.key`, with owner-only file permissions when the platform supports them. The UI never reads secret plaintext back. It can only replace a secret or report that one is configured.

This is a local convenience model, not a hardened vault. If the SQLite database and key file are both copied, the secrets can be decrypted.

### `channel_probe_runs`

Add a probe history table:

- `id integer primary key autoincrement`
- `channel_id text not null references channels(id) on delete cascade`
- `status text not null`
- `started_at text not null default current_timestamp`
- `finished_at text`
- `http_status integer`
- `final_url text`
- `summary text not null default ''`
- `error text`

Probe records intentionally do not store full response bodies, raw headers, cookies, or screenshots. Summaries should be short and diagnostic, such as `HTTP 401 from api.github.com`, `login form detected`, `captcha marker detected`, `HTML shell too small; likely JS-rendered`, or `connection timeout after 30s`.

### `source_profiles`

Keep `source_profiles` as the runtime table for concrete crawl targets, but add a channel relationship and split old type semantics:

- Add `channel_id text references channels(id) on delete restrict`.
- Add `fetcher_type text` as the concrete collection mode.
- Keep existing schedule, topic, trust, enabled, run policy, baseline, auto-ingest, and `config_json` behavior.
- Gradually deprecate source-owned auth fields after channel auth is fully adopted.

Channel `trust_level` describes whether this access boundary is trusted for automated use. Source `trust_level` remains the ingest-policy trust for a concrete knowledge target. Effective auto-ingest requires both a ready/enabled trusted channel and a trusted auto-ingest source.

Source `fetcher_type` values:

- `web_page`
- `rss_feed`
- `github_repo`
- `github_issues`
- `github_releases`
- `arxiv_query`
- `api_endpoint`
- `mcp_tool`
- `browser_flow`

During migration, existing `type` values map as follows:

- `web` -> `web_page`
- `rss` -> `rss_feed`
- `github` -> inferred `github_issues`, `github_releases`, or `github_repo` when possible, otherwise `github_repo`
- `arxiv` -> `arxiv_query`

Existing backend code can continue using the old `type` field as a compatibility adapter until fetchers are migrated to `fetcher_type`.
During that period, source create/update APIs must write both `type` and `fetcher_type` consistently so existing scheduler and fetcher dispatch do not regress.

## Migration

1. Run normal schema migration to create channel tables and add source columns.
2. If `source_profiles` is empty and `sources.yaml` exists, import the YAML once.
3. For each source without `channel_id`, create or reuse a channel based on the source URL.
4. The default channel boundary is the URL origin or host, but users can later edit the channel base URL to a finer boundary.
5. Preserve existing source ids and raw evidence references.
6. Stop mirroring YAML into SQLite on every app startup. After initial import, SQLite owns runtime configuration. Later YAML edits do not override the database unless a separate manual import tool is added.

Example migration:

```text
source:
  id = nccl-github-closed-issues
  url = https://api.github.com/repos/NVIDIA/nccl/issues?sort=updated&direction=desc
  type = github

channel:
  base_url = https://api.github.com
  kind = api
  connector = github
  auth_mode = token

source after migration:
  channel_id = api-github-com
  fetcher_type = github_issues
```

## Backend API

Channel endpoints:

- `GET /api/channels?domain=ai_infra`
- `POST /api/channels`
- `PATCH /api/channels/{channel_id}`
- `DELETE /api/channels/{channel_id}`
- `POST /api/channels/{channel_id}/secret`
- `DELETE /api/channels/{channel_id}/secret`
- `POST /api/channels/{channel_id}/probe`
- `GET /api/channels/{channel_id}/probe-runs`

Delete a channel only when no source is attached. Deleting a secret removes encrypted payload only; probe history remains because it must not contain plaintext secrets.

Source endpoints:

- `GET /api/sources?domain=ai_infra&channel_id=...`
- `POST /api/sources`
- `PATCH /api/sources/{source_id}`
- `DELETE /api/sources/{source_id}`
- `POST /api/sources/{source_id}/run`

Existing `GET /api/sources` remains compatible and returns added fields such as `channel_id`, `channel_name`, `channel_base_url`, and `channel_auth_state`.

Deleting a source should be conservative. If a source has raw items, fetch runs, or ingest tasks, the first version should disable it instead of physically deleting its row, preserving DB traceability for existing raw evidence. Hard delete is allowed only for unused draft sources.

## Runtime Flow

### Source Run

1. Scheduler selects a due enabled source.
2. Backend loads the source and its channel.
3. If the channel is disabled, missing required auth, not ready, or marked `needs_browser`, the run records a failed or skipped `fetch_runs` row with a clear reason.
4. Fetcher receives source configuration plus resolved channel auth.
5. Fetched content continues through `raw_store`, `content_versions`, ingest policy, and `ingest_tasks` unchanged.

Example channel-blocked run errors:

- `channel not ready: auth_failed`
- `channel needs auth configuration`
- `channel needs browser access`
- `channel disabled`

### Channel Probe

1. User clicks Verify Access.
2. Backend resolves the channel auth mode and configured secret.
3. For `web` and `api`, backend performs a small HTTP request to `probe_url` or `base_url`.
4. For `browser`, backend still performs HTTP probing in the first version and records `needs_browser` when the response looks like a login wall, captcha, or JS-only shell.
5. For `mcp` and `command`, the first version performs only configuration checks or explicitly allowlisted lightweight pings. It must not execute arbitrary local commands or MCP tools from user-provided strings.
6. Every result is inserted into `channel_probe_runs` and copied into the channel's latest probe fields.

Probe status mapping:

- Public or authenticated 2xx/3xx with meaningful response -> `ready`
- Required secret absent -> `needs_auth_config`
- 401/403 or rejected credential -> `auth_failed`
- Login form, captcha marker, or JS-only shell -> `needs_browser`
- DNS, connect, or timeout failure -> `network_failed`
- Unsupported kind or auth mode -> `unsupported`

Probe detection may inspect response text in memory for login or captcha markers, but persisted records must store only short summaries and status metadata.

## Frontend

Add a top-level `Domain Channels` page based on the approved mockup.

Layout:

- Left rail: domain list, channel/source search, status filters.
- Main panel: channel table with `name`, `base_url`, `kind`, `connector`, `auth`, latest probe, and source count.
- Right detail panel: selected channel editor, secret status, child sources, and probe history.

Channel actions:

- Create channel.
- Edit channel base URL, kind, connector, trust, enabled state, auth mode, and notes.
- Replace or delete secret.
- Verify access.
- Disable channel.
- Delete channel when empty.

Source actions under a selected channel:

- Create source.
- Edit source URL, fetcher type, topic, schedule, baseline, auto-ingest, enabled state, and config JSON.
- Run source manually.
- Disable or delete source configuration. Existing raw evidence is not removed.

The existing Source Subscriptions page should be reduced over time to source run inspection and manual run controls. Channel auth and base URL management move to the Domain Channels page.

## Security

The workbench remains a local unauthenticated single-user service. It may bind to `0.0.0.0` only on a trusted network.

Security constraints:

- Do not write secrets to wiki files, raw evidence, YAML, logs, probe summaries, or Git.
- Do not return secret plaintext from any API.
- Clear secret inputs in the frontend immediately after successful submission.
- Warn in the UI and README that the SQLite database plus `secrets.key` can decrypt stored secrets.
- Create `secrets.key` with restrictive permissions and fail closed if encrypted secrets exist but the key file is missing or unreadable.
- Treat state directory backups as secret-bearing backups.
- Treat command-based auth as a future allowlisted-provider feature unless a safe provider registry exists.
- Keep OAuth as `oauth_placeholder` until a separate authorization flow is designed.

## Non-Goals

- Full OAuth login.
- Real browser automation, Playwright sessions, manual browser login, screenshot storage, or local visual model inference.
- MCP permission model and full MCP execution.
- Secret export to YAML.
- Deleting or rewriting existing raw evidence.
- Replacing the raw/wiki knowledge model.

## Loop Development Mode

This feature must be implemented through the repository's `demand_development`
Planner -> Generator -> Evaluator loop, not as an untracked ad hoc change.
This design document is preflight input. Implementation starts only after the
user confirms entry into the loop and the Planner creates registered
`tasks.json` entries plus evaluator scenarios for the selected phase. Temporary
task contracts may be used as evaluator input, but they do not replace
registered demand-development tasks for this feature.

Because the feature crosses schema, backend APIs, frontend UI, scheduler/run
behavior, and secret handling, it must be split into independently evaluable
loop tasks rather than one large generator pass.

### Required Task Split

1. `crawler-domain-channels-model-01`
   - Scope: schema migration, SQLite-as-source-of-truth import rules,
     `channels` and `source_profiles.channel_id`, compatibility adapters, and
     source/channel listing APIs.
   - Evaluator focus: existing sources still load from an empty DB seeded from
     YAML once; non-empty DB is not overwritten; existing source run and queue
     behavior do not regress.

2. `crawler-domain-channels-probe-secrets-01`
   - Scope: encrypted channel secret storage, key-file lifecycle, probe APIs,
     probe history, channel readiness checks, and source-run blocking reasons.
   - Evaluator focus: secret plaintext is never returned or written to logs;
     probe states are persisted; disabled/auth-failed/needs-browser channels
     prevent source runs with clear evidence.

3. `crawler-domain-channels-ui-01`
   - Scope: Domain Channels page, channel CRUD, secret replacement UI, probe
     history display, child source CRUD, and compatibility with existing
     Sources/Queue pages.
   - Evaluator focus: Playwright or equivalent UI scenario creates a channel,
     replaces a secret without echoing it, runs a probe, creates a source under
     the channel, and confirms existing pages still render.

4. `crawler-domain-channels-live-e2e-01`
   - Scope: integrated backend/frontend validation against an isolated
     workbench state directory.
   - Evaluator focus: service restart evidence, API and UI visibility,
     source-run/raw-item/queue continuity, and artifact hygiene for any logs
     that might include access diagnostics.

The Planner may merge adjacent tasks only when it can still produce a small
task contract with bounded paths, clear scenario commands, and meaningful
repair attempts. It must not merge secret handling and UI work into a task that
cannot be evaluated independently.

### Concrete Task Contracts

Each task must be registered in `tasks.json` with all required fields,
`requires_eval=true`, and the standard task-level eval policy. The Planner must
generate matching scenario files under
`docs/harness/evaluator-scenarios/<task-id>.json` before handing work to the
Generator.

Common contract fields for all four tasks:

- `priority`: `high`
- `requires_eval`: `true`
- `eval_policy.task_level_required`: `true`
- `eval_policy.final_level_required`: `false`
- `eval_policy.task_scope`: `local_repo_and_personal_wiki`
- `eval_policy.final_scope`: `report_and_artifacts`
- `eval_policy.max_task_eval_attempts`: `3`
- `eval_policy.max_final_eval_attempts`: `2`
- Loop limits: `max_generator_attempts_per_task=2`,
  `max_eval_attempts_per_task=3`, `max_wall_time_minutes=90`
- Stop conditions: `passed_waiting_human_merge`, `stopped_blocked`,
  `stopped_budget`
- Real secret values, runtime state DBs, key files, token dumps, cookies, and
  unredacted auth artifacts are always denied. Source and test files with names
  such as `channel_secrets.py` or `test_domain_channel_secrets.py` are allowed
  only when listed in `allowed_paths` or created under an allowed source/test
  directory and must contain no real credentials.

#### `crawler-domain-channels-model-01`

Allowed paths:

- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/**`
- `personal-wiki/apps/crawler_workbench/backend/tests/**`
- `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`
- `docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json`
- `tasks.json`
- `progress.md`

Denylist paths:

- `.env`, `.env.*`
- `.personal-wiki-workbench/**`
- runtime credential or key artifacts matching `**/*secret*`, `**/*token*`,
  `**/*key*`
- `personal-wiki/domains/**/raw/**`
- `personal-wiki/domains/**/wiki/**`
- frontend files, except when the Planner explicitly merges this with the UI
  task after user confirmation

Verify command:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py tests/test_db_profiles.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_scheduler.py && cd /home/fyz/codex-skills && python3 -m json.tool tasks.json >/dev/null && python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json >/dev/null && git diff --check
```

Scenario entrypoint:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py
```

Scenario must prove:

- Empty isolated DB imports `sources.yaml` once.
- Non-empty DB is not overwritten by later YAML changes.
- Existing source IDs and raw evidence references are preserved.
- Sources receive generated channel IDs.
- Existing source listing and source run behavior still work.

#### `crawler-domain-channels-probe-secrets-01`

Allowed paths:

- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/**`
- `personal-wiki/apps/crawler_workbench/backend/tests/**`
- `docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json`
- `tasks.json`
- `progress.md`

Denylist paths:

- `.env`, `.env.*`
- `.personal-wiki-workbench/**`
- runtime credential or key artifacts matching `**/*secret*`, `**/*token*`,
  `**/*key*`; source/test files for encrypted-secret implementation are allowed
  only under the allowed backend source/test paths and must contain no real
  secret values
- `personal-wiki/domains/**`
- frontend files, except generated API type updates when the UI task is
  explicitly merged

Verify command:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py tests/test_fetch_service_policy.py tests/test_api.py && cd /home/fyz/codex-skills && python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json >/dev/null && git diff --check
```

Scenario entrypoint:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py
```

Scenario must prove:

- Secret plaintext is accepted only on write/replace APIs and is never returned
  by read APIs.
- Probe runs persist `ready`, `needs_auth_config`, `auth_failed`,
  `needs_browser`, `network_failed`, and `unsupported`.
- Probe summaries do not include secret values, authorization headers, cookies,
  or raw response bodies.
- Missing or unreadable key file fails closed when encrypted secrets exist.
- Source runs are blocked with clear `fetch_runs.error` messages when their
  channel is disabled, not ready, or `needs_browser`.

#### `crawler-domain-channels-ui-01`

Allowed paths:

- `personal-wiki/apps/crawler_workbench/frontend/src/**`
- `personal-wiki/apps/crawler_workbench/frontend/tests/**`
- `personal-wiki/apps/crawler_workbench/frontend/package*.json` only when
  Planner records dependency necessity and supply-chain evidence
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- `docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json`
- `tasks.json`
- `progress.md`

Denylist paths:

- `.env`, `.env.*`
- `.personal-wiki-workbench/**`
- runtime credential or key artifacts matching `**/*secret*`, `**/*token*`,
  `**/*key*`
- `personal-wiki/domains/**`
- backend persistence/fetcher code unless the task is explicitly widened by
  user-approved Planner output

Verify command:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx && npm run build && npm run test:ui && cd /home/fyz/codex-skills && python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json >/dev/null && git diff --check
```

Scenario entrypoint:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm run test:ui
```

Scenario must prove:

- A user can navigate to the Domain Channels page.
- The page shows domains, channels, source counts, selected channel details,
  and probe history.
- Creating/editing a channel sends the expected API payload.
- Replacing a secret clears the input and does not render the plaintext secret
  anywhere after submission.
- Creating a child source under a selected channel is visible in the UI.
- Existing Sources and Queue navigation still render.

#### `crawler-domain-channels-live-e2e-01`

Allowed paths:

- `scripts/**`
- `docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json`
- `.codex/evaluations/tasks/crawler-domain-channels-live-e2e-01/**` after
  artifact hygiene
- `.codex/loop-runs/**` after artifact hygiene
- `tasks.json`
- `progress.md`

Denylist paths:

- `.env`, `.env.*`
- `.personal-wiki-workbench/**`
- raw state databases, key files, cookies, token dumps, Playwright traces with
  unredacted form values, and any real credential material

Verify command:

```bash
python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01 && python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json >/dev/null && git diff --check
```

Scenario entrypoint:

```bash
python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01
```

Scenario must prove in an isolated state directory:

- Backend and frontend start without reusing the long-running developer
  services.
- API can create a channel, attach a source, write a synthetic test secret,
  run a probe, and return probe history.
- UI can view the channel, replace the synthetic secret without echoing it,
  create a source, and show latest probe status.
- A source run still produces raw evidence and queue continuity where the
  fixture expects it.
- Artifact hygiene either redacts or omits any logs that could contain access
  diagnostics.

### Evaluator Scenario Draft

Each scenario file must follow the existing `must_simulate` format. The angle
bracket values below are template variables; the Planner must replace them with
the concrete task id, scenario id, and entrypoint before writing a scenario file
or handing the task to a Generator:

```json
{
  "task_id": "<task-id>",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "<task-id>-user-flow",
      "user_goal": "Verify the phase from a workbench user's perspective.",
      "prerequisites": [
        "Repository root is writable.",
        "Scenario uses an isolated state directory.",
        "No real credentials are required."
      ],
      "entrypoint": "<scenario entrypoint command>",
      "steps": [],
      "expected_outcomes": [],
      "failure_signals": [],
      "cleanup": [
        "Remove generated .codex scenario output for a clean rerun."
      ],
      "automation_hint": "shell or playwright+shell"
    }
  ]
}
```

### Artifact Policy

Loop and evaluator artifacts are acceptance evidence, but they must pass
artifact hygiene before commit.

Allowed to commit after hygiene:

- `result.json`, `summary.md`, scenario JSON, redaction manifests, artifact
  manifests, small sanitized API response summaries.

Local-only by default:

- Raw Playwright traces, screenshots containing form fields, raw probe HTTP
  responses, raw stdout/stderr that may include headers, state databases,
  `secrets.key`, cookie files, and any generated secret payload.

If an artifact contains `Authorization`, `Cookie`, token-like strings, secret
input values, or private response bodies, the loop must redact it or omit it
from git and keep only a manifest entry with path, size, and hash.

### Completion Records

Each implementation task must update `progress.md` at the top after verify and
evaluator pass, recording:

- task id and commit hash
- verify commands and outcome
- evaluator bundle path
- loop run path
- whether backend/frontend services were restarted
- any blocked credential/browser/CV follow-up

If verification or evaluator is blocked, `progress.md` must record the blocker
and the task must not be marked `done`.

If a task needs access to real credentials, the loop must stop and request
human input. Generator agents must not invent, inspect, or commit real tokens,
cookies, key files, or state databases.

### Stop Conditions

The loop must stop at `stopped_blocked` or equivalent human gate when:

- Existing dirty paths overlap the planned task outputs and cannot be
  separated from user work.
- A migration would rewrite or delete existing raw evidence.
- A test or evaluator scenario requires real third-party credentials.
- `secrets.key` creation, encryption, or redaction evidence cannot be verified.
- Browser/CV automation becomes necessary for correctness; that is outside the
  first-version non-goals.

Passing evaluator results still end at the human merge gate for
`demand_development`. They do not imply automatic merge to `main`.

## Testing

Backend coverage:

- Schema migration creates `channels`, `channel_secrets`, `channel_probe_runs`, and source channel columns.
- Empty DB imports YAML once; non-empty DB is not overwritten by YAML.
- Existing source URLs are assigned to generated channels.
- Channel CRUD validates base URL, kind, connector, auth mode, and domain.
- Source CRUD requires a channel and preserves existing source behavior.
- Secret write/replace does not expose plaintext through read APIs.
- Probe records `ready`, `needs_auth_config`, `auth_failed`, `needs_browser`, `network_failed`, and `unsupported`.
- `run_source_once` inherits channel auth and records a clear failure when a channel is unavailable.
- Existing source, scheduler, queue, manual ingest, discovery, and accelerator tests continue passing.

Frontend coverage:

- Domain Channels page renders domains, channels, source counts, and selected channel details.
- Channel create/edit flows call the right APIs.
- Secret replacement clears plaintext input and does not render secret values.
- Verify Access shows running state, latest status, and probe history.
- Source create/edit under a selected channel works.
- Existing Sources, Queue, Wiki Browser, and Knowledge pages do not regress.

Verification commands:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build
git diff --check
```

Because this is a new feature touching backend, frontend, schema, and security-sensitive behavior, every implementation task must set `requires_eval=true` under the repository task rules and run the relevant evaluator gate or document the evidence bundle. Loop artifacts under `.codex/loop-runs/<run-id>/` and evaluator bundles under `.codex/evaluations/tasks/<task-id>/` are part of the acceptance evidence.

## Deployment Validation

After implementation:

1. Restart `personal-wiki-crawler-backend` after schema/API changes.
2. Restart `personal-wiki-crawler-frontend` after frontend changes.
3. Verify backend APIs can create a channel, attach a source, store a secret, run a probe, and return probe history.
4. Verify the frontend through Vite proxy or Playwright: create a channel, replace a secret, run a probe, create a source under that channel, and see the source on the page.
5. Confirm source runs still produce raw evidence and queue entries through existing APIs.

Final reports for implementation must include commands or page-level verification results and state whether backend/frontend services were restarted.
