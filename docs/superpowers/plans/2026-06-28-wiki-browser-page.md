# Wiki Browser Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a crawler workbench frontend page for browsing existing curated Personal Wiki Markdown pages.

**Architecture:** Add a small backend wiki-page reader module and API endpoints that list/read only `personal-wiki/domains/<domain>/wiki/**/*.md`. Add a dedicated React page that loads domains, lists pages by type, and renders selected Markdown with metadata and source references.

**Tech Stack:** FastAPI, sqlite-backed existing backend app, React, TypeScript, Vitest, Testing Library, pytest.

---

### Task 1: Backend Wiki Page API

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/wiki_pages.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`

- [ ] **Step 1: Write failing backend API tests**

Add tests to `test_api.py`:

```python
def test_wiki_pages_endpoint_lists_curated_pages(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "projects" / "nccl.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        "---\n"
        "type: Project\n"
        "title: NCCL\n"
        "description: Collective communication library.\n"
        "status: reviewed\n"
        "tags:\n"
        "  - nccl\n"
        "source_refs:\n"
        "  - ../../raw/nccl.md\n"
        "---\n"
        "# Summary\n\nNCCL content.\n",
        encoding="utf-8",
    )
    (settings.wiki_root / "domains" / "ai_infra" / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/pages?domain=ai_infra")

    assert response.status_code == 200
    assert response.json() == [
        {
            "domain": "ai_infra",
            "path": "projects/nccl.md",
            "full_path": "domains/ai_infra/wiki/projects/nccl.md",
            "type": "Project",
            "title": "NCCL",
            "description": "Collective communication library.",
            "status": "reviewed",
            "tags": ["nccl"],
            "source_refs": ["../../raw/nccl.md"],
        }
    ]


def test_wiki_page_endpoint_reads_curated_page_body(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "projects" / "nccl.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("---\ntitle: NCCL\n---\n# Summary\n\nNCCL content.\n", encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/page?domain=ai_infra&path=projects/nccl.md")

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "ai_infra"
    assert data["path"] == "projects/nccl.md"
    assert data["title"] == "NCCL"
    assert data["body"] == "# Summary\n\nNCCL content.\n"
    assert data["content"].startswith("---\ntitle: NCCL")


def test_wiki_page_endpoint_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/wiki/page?domain=ai_infra&path=../raw/secret.md")

    assert response.status_code == 400
```

- [ ] **Step 2: Run backend API tests and verify failure**

Run:

```bash
pytest personal-wiki/apps/crawler_workbench/backend/tests/test_api.py -k "wiki_pages_endpoint or wiki_page_endpoint" -q
```

Expected: FAIL because `/api/wiki/pages` and `/api/wiki/page` are not implemented.

- [ ] **Step 3: Implement backend page reader**

Create `wiki_pages.py` with:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .settings import Settings


class WikiPageError(ValueError):
    pass


def list_wiki_pages(settings: Settings, domain: str) -> list[dict[str, object]]:
    wiki_root = _domain_wiki_root(settings, domain)
    if not wiki_root.exists():
        return []
    pages = [page for page in wiki_root.rglob("*.md") if page.name != "index.md"]
    return [_page_summary(settings, domain, page) for page in sorted(pages)]


def read_wiki_page(settings: Settings, domain: str, page_path: str) -> dict[str, object]:
    wiki_root = _domain_wiki_root(settings, domain)
    page = _resolve_page_path(wiki_root, page_path)
    if not page.exists() or not page.is_file():
        raise FileNotFoundError(page_path)
    text = page.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(text)
    summary = _page_summary(settings, domain, page, frontmatter=frontmatter)
    return {**summary, "content": text, "body": body}
```

Include helpers for `_validate_domain`, `_resolve_page_path`, `_parse_frontmatter`, `_string_list`, and `_page_summary`. `_resolve_page_path` must reject absolute paths, `..`, non-Markdown paths, and resolved paths outside the domain wiki root.

- [ ] **Step 4: Add FastAPI endpoints**

Modify `api.py`:

```python
from .wiki_pages import WikiPageError, list_wiki_pages, read_wiki_page


@router.get("/wiki/pages")
def wiki_pages(domain: str, request: Request) -> list[dict[str, object]]:
    try:
        return list_wiki_pages(request.app.state.settings, domain)
    except WikiPageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wiki/page")
def wiki_page(domain: str, path: str, request: Request) -> dict[str, object]:
    try:
        return read_wiki_page(request.app.state.settings, domain, path)
    except WikiPageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Wiki page not found") from exc
```

- [ ] **Step 5: Run backend tests and verify pass**

Run:

```bash
pytest personal-wiki/apps/crawler_workbench/backend/tests/test_api.py -k "wiki_pages_endpoint or wiki_page_endpoint" -q
```

Expected: PASS.

### Task 2: Frontend API Types And Wiki Browser Page

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/WikiBrowserPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`
- Test: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

Update the API mock in `App.test.tsx` to include:

```typescript
getWikiPages: vi.fn().mockResolvedValue([
  {
    domain: "ai_infra",
    path: "projects/nccl.md",
    full_path: "domains/ai_infra/wiki/projects/nccl.md",
    type: "Project",
    title: "NCCL",
    description: "Collective communication library.",
    status: "reviewed",
    tags: ["nccl"],
    source_refs: ["../../raw/nccl.md"]
  }
]),
getWikiPage: vi.fn().mockResolvedValue({
  domain: "ai_infra",
  path: "projects/nccl.md",
  full_path: "domains/ai_infra/wiki/projects/nccl.md",
  type: "Project",
  title: "NCCL",
  description: "Collective communication library.",
  status: "reviewed",
  tags: ["nccl"],
  source_refs: ["../../raw/nccl.md"],
  content: "---\ntitle: NCCL\n---\n# Summary\n\nNCCL content.",
  body: "# Summary\n\nNCCL content."
})
```

Add a test:

```typescript
it("opens the wiki browser and renders a selected markdown page", async () => {
  render(<App />);

  fireEvent.click(screen.getAllByText("Wiki 浏览")[0]);

  expect(await screen.findByText("NCCL")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("NCCL content.")).toBeInTheDocument());
  expect(screen.getByText("projects/nccl.md")).toBeInTheDocument();
  expect(screen.getByText("../../raw/nccl.md")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run frontend test and verify failure**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test -- App.test.tsx --runInBand
```

Expected: FAIL because `Wiki 浏览` and API functions do not exist.

- [ ] **Step 3: Add types and API functions**

Add to `types.ts`:

```typescript
export interface WikiPageSummary {
  domain: string;
  path: string;
  full_path: string;
  type: string;
  title: string;
  description: string;
  status: string;
  tags: string[];
  source_refs: string[];
}

export interface WikiPageDetail extends WikiPageSummary {
  content: string;
  body: string;
}
```

Add to `api.ts`:

```typescript
export async function getWikiPages(domain: string): Promise<WikiPageSummary[]> {
  return request<WikiPageSummary[]>(withQuery("/wiki/pages", { domain }));
}

export async function getWikiPage(domain: string, path: string): Promise<WikiPageDetail> {
  return request<WikiPageDetail>(withQuery("/wiki/page", { domain, path }));
}
```

Add these to exported `api`.

- [ ] **Step 4: Implement WikiBrowserPage**

Create a page that:

- loads domains with `getDomains()`
- loads page summaries with `getWikiPages(domain)`
- auto-selects the first page
- loads selected page with `getWikiPage(domain, path)`
- groups page list by `type`
- renders metadata and source refs
- renders Markdown body with a small local renderer supporting headings, paragraphs, unordered lists, code fences, simple tables, and links as text anchors

- [ ] **Step 5: Wire navigation**

Modify `App.tsx`:

- import `FileText` from lucide-react
- import `WikiBrowserPage`
- extend `PageKey` to include `wikiBrowser`
- add navigation item `{ key: "wikiBrowser", label: "Wiki 浏览", icon: FileText }`
- render `<WikiBrowserPage />` when active

- [ ] **Step 6: Add CSS**

Add classes for:

- `.wiki-browser-grid`
- `.wiki-page-list`
- `.wiki-page-button`
- `.wiki-page-button.active`
- `.wiki-reader`
- `.wiki-metadata`
- `.markdown-body`

Keep the layout dense and operational, consistent with the existing workbench.

- [ ] **Step 7: Run frontend tests and verify pass**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test -- App.test.tsx
```

Expected: PASS.

### Task 3: Integration Verification

**Files:**
- Verify: backend tests, frontend tests, build, running local backend/frontend behavior

- [ ] **Step 1: Run full backend tests**

Run:

```bash
pytest personal-wiki/apps/crawler_workbench/backend/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm run build
```

Expected: PASS.

- [ ] **Step 4: Restart backend if needed**

If backend is running, restart `personal-wiki-crawler-backend` so new API endpoints are loaded.

- [ ] **Step 5: Smoke test live API**

Run:

```bash
curl -sS "http://127.0.0.1:8765/api/wiki/pages?domain=ai_infra"
curl -sS "http://127.0.0.1:8765/api/wiki/page?domain=ai_infra&path=projects/nccl.md"
```

Expected: first response contains `projects/nccl.md`; second response contains `NCCL`.

- [ ] **Step 6: Final diff review**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; changed files match the feature and existing uncommitted GitHub fallback fix remains visible.
