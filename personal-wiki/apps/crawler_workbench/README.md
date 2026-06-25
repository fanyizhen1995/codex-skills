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
npm run dev -- --host 0.0.0.0
```

By default, the frontend uses the Vite `/api` proxy to reach the backend at `http://localhost:8765`, so remote browsers only need to open the frontend address.

## Source Profiles

Copy `config/sources.example.yaml` to `.personal-wiki-workbench/sources.yaml`, then edit source ids, domains, URLs, schedules, and trust levels.

The bundled example tracks the current `ai_infra` watch set daily:

- NCCL release notes: `https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html`
- NCCL closed GitHub issues: `https://api.github.com/repos/NVIDIA/nccl`
- SGLang closed GitHub issues and pull requests: `https://api.github.com/repos/sgl-project/sglang`

The scheduler fetches due `daily`, `hourly`, and `weekly` sources. Trusted
`auto_ingest: true` captures become approved ingest tasks, and the scheduler
then runs approved tasks through ingest-plan, Codex wiki curation, index,
backlinks, validation, and auto-commit. Pending tasks remain visible in the
queue for manual review.

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
npm run test:ui

cd /home/fyz/codex-skills
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
git diff --check
```
