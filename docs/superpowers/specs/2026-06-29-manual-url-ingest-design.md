# Manual URL Ingest Design

## Goal

Allow a user to paste an ad hoc URL into Crawler Workbench and have the system fetch it, store raw evidence, run the existing wiki ingest flow, validate, and optionally create a git commit.

## Architecture

Add a narrow backend orchestration service that creates or reuses a temporary trusted web source for the URL, runs the normal fetcher, approves the generated ingest task, and delegates execution to the existing queue runner. The queue runner remains responsible for `ingest-plan`, Codex curation, `index`, `backlinks`, `validate`, and auto-commit policy. The API and frontend only expose the orchestration result.

## Behavior

- Endpoint: `POST /api/manual-ingests`
- Request fields:
  - `url`: required URL or host/path string accepted by current URL canonicalization.
  - `domain`: optional, defaults to `ai_infra`.
  - `auto_commit_enabled`: optional, defaults to `true`.
- The backend creates source ids like `manual-url-<slug>-<hash>` and stores them in SQLite only.
- Manual URL sources are `type=web`, `trust_level=trusted`, `schedule=manual`, `run_policy=once`, `auto_ingest=true`, `baseline_on_first_run=false`.
- If fetch creates no changed raw item, return a clear result with `status=skipped`.
- If ingest/validation/commit fails, return the task state and reason instead of hiding the failure.
- If the git workspace has unrelated dirty paths, the existing queue runner defers/fails according to its current baseline checks; the UI shows that reason.

## Frontend

Add a compact form to the Sources page. It accepts URL, domain, and an auto-commit checkbox. On submit, it calls the new API and displays a status message with task id and commit sha when available. The form refreshes sources after the request.

## Testing

- Backend unit/API test for the orchestration happy path with an injected static fetcher and fake Codex runner.
- Backend API validation test for empty URL/domain.
- Frontend test that submits a URL and shows the resulting status.
- Existing backend/frontend/evaluator commands remain the final gate.
