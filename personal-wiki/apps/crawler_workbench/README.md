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
- NCCL closed GitHub issues: `https://api.github.com/repos/NVIDIA/nccl/issues?sort=updated&direction=desc`
- SGLang closed GitHub issues and pull requests: `https://api.github.com/repos/sgl-project/sglang?sort=updated&direction=desc`

The scheduler fetches due `hourly`, `daily`, `weekly`, and `monthly` sources;
`manual` sources are fetched only when triggered. Trusted `auto_ingest: true`
captures become approved ingest tasks, and the scheduler then runs approved
tasks through ingest-plan, Codex wiki curation, index, backlinks, validation,
and auto-commit. Pending tasks remain visible in the queue for manual review.
From the queue, the `信源` action can mark the pending item's site as a trusted
source and choose either on-demand (`manual`) or scheduled daily/weekly/monthly
tracking; matching same-site pending items are approved together.

Auth-required profiles store only references:

- `auth_method: env_token` with `auth_ref: GITHUB_TOKEN`
- `auth_method: command` with `auth_ref: local-token-command`
- `auth_method: header_template` with `auth_ref: local-header-template-name`
- `auth_method: cookie_file` with `auth_ref: /local/path/cookies.txt`

Do not store token values in wiki files or Git.

## Crawl Methods

Use the cheapest reliable capture method first, and keep the original capture in
`raw/` as evidence. For broad sources, filter by topic before ingesting into
curated wiki pages.

### RSS Article Body Capture

RSS and Atom feeds should be treated as discovery indexes. The preferred flow is:

1. Fetch the RSS or Atom feed.
2. Parse entries and use each entry `link` as the canonical article URL.
3. Fetch the article body over normal HTTP.
4. Extract `article`, then `main`, then `body` text.
5. If HTTP content is empty, blocked, or clearly JS-rendered, retry the same URL
   with Playwright.
6. Store feed metadata and article metadata with the raw item, including
   `feed_url`, `feed_title`, `entry_id`, `entry_url`, `published`, `updated`,
   `rss_summary`, `article_fetch_method`, `article_fetch_status`, and
   `article_content_type`.

For broad feeds, apply `include_keywords` before article body capture. For NCCL
tracking, useful keywords include `NCCL`, `GPUDirect`, `RDMA`, `collective
communication`, `all-reduce`, `NVLink`, and `InfiniBand`.

The current smoke-tested NCCL RSS source is:

```text
https://developer.nvidia.com/blog/tag/nccl/feed/
```

The tested entry was:

```text
https://developer.nvidia.com/blog/real-time-performance-monitoring-and-faster-debugging-with-nccl-inspector-and-prometheus/
```

Smoke result from 2026-06-25:

| Method | Status | HTML bytes | Extracted text | NCCL hits |
| --- | ---: | ---: | ---: | ---: |
| RSS feed | 200 | 232984 | 32 entries | n/a |
| HTTP article fetch | 200 | 329191 | 12962 chars | 45 |
| Playwright article fetch | 200 | 491460 | 13062 chars | 45 |

Local smoke artifacts were written under:

```text
/tmp/personal-wiki-rss-body-smoke/
```

### HTTP First, Playwright Fallback

Use HTTP as the default article fetcher because it is cheaper, deterministic,
and sufficient for many technical blogs. Use Playwright only when one of these
conditions is true:

- HTTP returns a login, bot check, or shell page instead of article text.
- HTTP text extraction is empty or much shorter than the RSS summary.
- The page requires client-side rendering to expose the article body.

When Playwright is used, launch Chromium with the same explicit proxy as HTTP
capture. On the tested machine, Chromium failed through the inherited
`all_proxy=socks5://127.0.0.1:7898`, while explicit
`proxy: { server: "http://127.0.0.1:7897" }` worked. Prefer explicit proxy
configuration and disable ambient proxy inheritance for reproducibility.

Minimal Playwright body capture pattern:

```javascript
const { chromium } = require("playwright");

const browser = await chromium.launch({
  headless: true,
  proxy: { server: "http://127.0.0.1:7897" },
});
const page = await browser.newPage({
  userAgent: "Mozilla/5.0 personal-wiki-crawler",
});
const response = await page.goto(articleUrl, {
  waitUntil: "domcontentloaded",
  timeout: 90000,
});
await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
const text = await page
  .locator("article, main, body")
  .first()
  .innerText({ timeout: 10000 });
await browser.close();
```

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

After every knowledge ingest or curation update, verify the long-running app
reflects the new data on both sides:

- Backend: query `/api/wiki/pages`, `/api/wiki/page`, or the relevant API for
  the new item. If search is involved, use normal `/api/search` to confirm the
  FTS index refreshes automatically; do not rely only on manual
  `/api/search/rebuild`.
- Services: restart `personal-wiki-crawler-backend` after backend code, schema,
  index, or runtime config changes; restart `personal-wiki-crawler-frontend`
  after frontend or Vite config changes.
- Frontend: verify through the Vite `/api` proxy or Playwright user actions.
  For Knowledge Workbench, search a keyword from the new material. For Wiki
  Browser, confirm the new page title or body is visible.
