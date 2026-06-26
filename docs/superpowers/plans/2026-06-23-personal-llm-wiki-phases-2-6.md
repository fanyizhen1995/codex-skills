# Personal LLM Wiki Phases 2-6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining personal wiki phases by adding validation, indexing, graph export, ingest helper commands, a Codex skill, and optional static visualization.

**Architecture:** Keep the wiki file-first and standard-library-only. Add a Python CLI package under `personal-wiki/tools/wiki_cli/` with focused modules for documents, validation, indexing, graphing, ingest helpers, and HTML visualization. Keep generated skill instructions in `personal-wiki/skills/personal-wiki-manager/SKILL.md` and verify all behavior through pytest tests under `personal-wiki/tests/`.

**Tech Stack:** Python 3.12 standard library, pytest, Markdown/YAML-like frontmatter parsing implemented locally, static HTML/JSON output.

---

## Scope

This plan implements Phases 2-6 from:

- `docs/superpowers/specs/2026-06-23-personal-llm-wiki-design.md`
- `personal-wiki/ROADMAP.md`

The implementation remains local and deterministic:

- No database.
- No network dependency in tests.
- No third-party Python packages beyond pytest already used in this repo.
- URL snapshot support stores a metadata stub by default and only performs live fetching when explicitly requested with a CLI flag.

## File Map

Core CLI package:

- Create: `personal-wiki/tools/wiki_cli/__init__.py`
- Create: `personal-wiki/tools/wiki_cli/__main__.py`
- Create: `personal-wiki/tools/wiki_cli/cli.py`
- Create: `personal-wiki/tools/wiki_cli/document.py`
- Create: `personal-wiki/tools/wiki_cli/paths.py`
- Create: `personal-wiki/tools/wiki_cli/validate.py`
- Create: `personal-wiki/tools/wiki_cli/indexer.py`
- Create: `personal-wiki/tools/wiki_cli/graph.py`
- Create: `personal-wiki/tools/wiki_cli/ingest.py`
- Create: `personal-wiki/tools/wiki_cli/html.py`

Tests and fixtures:

- Modify: `personal-wiki/tests/test_scaffold.py`
- Create: `personal-wiki/tests/test_document.py`
- Create: `personal-wiki/tests/test_validate.py`
- Create: `personal-wiki/tests/test_index_graph.py`
- Create: `personal-wiki/tests/test_ingest_helpers.py`
- Create: `personal-wiki/tests/test_cli.py`
- Create: `personal-wiki/tests/test_skill_and_visualization.py`

Docs and generated skill:

- Modify: `personal-wiki/tools/README.md`
- Modify: `personal-wiki/ROADMAP.md`
- Create: `personal-wiki/skills/personal-wiki-manager/SKILL.md`
- Create: `personal-wiki/docs/cli.md`

## CLI Contract

All commands run from the repository root. Because `personal-wiki` contains a
hyphen and cannot be imported as a normal package name, the supported invocation
is the script path:

```bash
python personal-wiki/tools/wiki_cli/cli.py <command> ...
```

Add the executable module files under:

```text
personal-wiki/tools/wiki_cli/
```

The CLI must accept `--root personal-wiki` for tests and scripted use.

Required commands:

```text
init-domain <name>
validate [--domain <name>] [--json]
index <domain>
backlinks [--domain <name>] [--write-json]
graph [--domain <name>] [--out graph.json]
visualize [--domain <name>] [--out graph.html]
snapshot-url <domain> <url> [--fetch]
image-note <domain> <image-path>
ingest-plan <domain> <raw-path>
```

Exit code contract:

- `0`: command completed and no validation errors.
- `1`: validation found issues or user input is invalid.
- `2`: unexpected internal error caught by CLI boundary.

## Task 1: Document Parser And Path Utilities

**Files:**
- Create: `personal-wiki/tools/wiki_cli/document.py`
- Create: `personal-wiki/tools/wiki_cli/paths.py`
- Create: `personal-wiki/tools/wiki_cli/__init__.py`
- Test: `personal-wiki/tests/test_document.py`

- [ ] **Step 1: Write failing parser tests**

Create `personal-wiki/tests/test_document.py` with tests for:

```python
from pathlib import Path

from personal_wiki_test_loader import load_cli_module


document = load_cli_module("document")
paths = load_cli_module("paths")


def test_parse_frontmatter_and_body():
    text = "---\ntype: Concept\ntitle: KV Cache\ntags: [llm, inference]\nsource_refs:\n  - ../../raw/papers/a.md\n---\n\n# Summary\nBody\n"
    doc = document.parse_markdown(text)
    assert doc.frontmatter["type"] == "Concept"
    assert doc.frontmatter["title"] == "KV Cache"
    assert doc.frontmatter["tags"] == ["llm", "inference"]
    assert doc.frontmatter["source_refs"] == ["../../raw/papers/a.md"]
    assert doc.body.startswith("# Summary")


def test_parse_markdown_without_frontmatter():
    doc = document.parse_markdown("# Plain\n")
    assert doc.frontmatter == {}
    assert doc.body == "# Plain\n"


def test_serialize_frontmatter_round_trip():
    original = document.MarkdownDocument(
        frontmatter={
            "type": "Concept",
            "title": "KV Cache",
            "tags": ["llm", "inference"],
            "source_refs": ["../../raw/a.md"],
        },
        body="# Summary\nBody\n",
    )
    reparsed = document.parse_markdown(document.serialize_markdown(original))
    assert reparsed.frontmatter == original.frontmatter
    assert reparsed.body == original.body


def test_domain_paths_are_resolved(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    domain = paths.domain_root(root, "ai-infra")
    assert domain == root / "domains" / "ai-infra"
    assert paths.domain_wiki(root, "ai-infra") == domain / "wiki"
```

Also create `personal-wiki/tests/personal_wiki_test_loader.py` if it does not
exist yet:

```python
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = ROOT / "tools" / "wiki_cli"


def load_cli_module(name: str):
    path = CLI_ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"wiki_cli_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 2: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_document.py -q
```

Expected: FAIL because `document.py` and `paths.py` do not exist.

- [ ] **Step 3: Implement parser and path helpers**

Implement:

```python
@dataclass
class MarkdownDocument:
    frontmatter: dict[str, Any]
    body: str

def parse_markdown(text: str) -> MarkdownDocument
def serialize_markdown(doc: MarkdownDocument) -> str
def load_document(path: Path) -> MarkdownDocument
def write_document(path: Path, doc: MarkdownDocument) -> None
```

Parser requirements:

- Frontmatter is delimited by `---` at the start of a file.
- Support scalar strings, empty values, inline lists like `[a, b]`, and indented list values.
- Preserve body text after the closing delimiter.
- Serialization writes stable key order using insertion order, list values as YAML-style lists when non-empty, and empty lists as `[]`.

Implement path helpers:

```python
def repo_root_from(start: Path) -> Path
def domain_root(root: Path, domain: str) -> Path
def domain_wiki(root: Path, domain: str) -> Path
def wiki_pages(root: Path, domain: str | None = None) -> list[Path]
def raw_pages(root: Path, domain: str | None = None) -> list[Path]
```

- [ ] **Step 4: Run green tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_document.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add personal-wiki/tools/wiki_cli/__init__.py personal-wiki/tools/wiki_cli/document.py personal-wiki/tools/wiki_cli/paths.py personal-wiki/tests/personal_wiki_test_loader.py personal-wiki/tests/test_document.py
git commit -m "feat: add personal wiki document parser"
```

## Task 2: Validation Engine And CLI Command

**Files:**
- Create: `personal-wiki/tools/wiki_cli/validate.py`
- Create: `personal-wiki/tools/wiki_cli/cli.py`
- Test: `personal-wiki/tests/test_validate.py`
- Test: `personal-wiki/tests/test_cli.py`

- [ ] **Step 1: Write failing validation tests**

Create `personal-wiki/tests/test_validate.py` with fixtures that build a small
domain under `tmp_path/personal-wiki/domains/ai-infra/`.

Required tests:

- `test_validate_accepts_well_formed_domain`: valid Concept page, raw source,
  local image asset, and citation returns no issues.
- `test_validate_reports_missing_required_frontmatter`: missing `description`
  reports issue code `missing_required`.
- `test_validate_reports_bad_type_and_status`: invalid `type` and `status`
  report `invalid_type` and `invalid_status`.
- `test_validate_reports_missing_source_ref_and_broken_link`: nonexistent
  local `source_refs` and Markdown link report `missing_source_ref` and
  `broken_link`.
- `test_validate_reports_missing_image`: Markdown image pointing to a missing
  asset reports `missing_image`.
- `test_validate_reports_duplicate_titles_and_aliases`: duplicate page titles
  or aliases report `duplicate_title` or `duplicate_alias`.
- `test_validate_reviewed_page_requires_sources`: `status: reviewed` without
  citations or source refs reports `reviewed_without_sources`.

Expected API:

```python
issues = validate.validate(root, domain="ai-infra")
assert [issue.code for issue in issues] == ["missing_required"]
assert issue.path.as_posix().endswith("wiki/concepts/foo.md")
```

- [ ] **Step 2: Write failing CLI tests**

Create `personal-wiki/tests/test_cli.py` with:

```python
import subprocess
import sys
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "tools" / "wiki_cli" / "cli.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_valid_fixture(root: Path) -> None:
    write(root / "domains/ai-infra/raw/notes/source.md", "---\ntype: RawSource\ntitle: Source\nsource_kind: note\ncaptured: 2026-06-23\nstatus: pending\n---\n\n# Raw Content\n")
    write(root / "domains/ai-infra/wiki/concepts/kv-cache.md", "---\ntype: Concept\ntitle: KV Cache\ndescription: Cache for transformer key/value states.\ndomain: ai-infra\nstatus: draft\nsource_refs:\n  - ../../raw/notes/source.md\n---\n\n# Summary\nBody.\n\n# Citations\n- ../../raw/notes/source.md\n")


def build_invalid_fixture(root: Path) -> None:
    write(root / "domains/ai-infra/wiki/concepts/bad.md", "---\ntype: Concept\ntitle: Bad\ndomain: ai-infra\n---\n\n# Summary\nMissing description.\n")


def test_validate_cli_exits_zero_for_valid_fixture(tmp_path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "validate", "--domain", "ai-infra"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "No validation issues" in result.stdout


def test_validate_cli_exits_one_for_invalid_fixture(tmp_path):
    root = tmp_path / "personal-wiki"
    build_invalid_fixture(root)
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "validate", "--domain", "ai-infra"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "missing_required" in result.stdout
```

Use local fixture helper functions in the test file rather than shared mutable
state.

- [ ] **Step 3: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_validate.py personal-wiki/tests/test_cli.py -q
```

Expected: FAIL because validation and CLI modules do not exist.

- [ ] **Step 4: Implement validation**

Implement `ValidationIssue` dataclass:

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: Path
    message: str
```

Validation requirements:

- Required wiki fields: `type`, `title`, `description`, `domain`.
- Accepted wiki types: `Concept`, `Paper`, `Project`, `Decision`, `Reference`.
- Accepted statuses: `draft`, `reviewed`, `stale`, `deprecated`.
- Local `source_refs` are resolved relative to the wiki page path.
- Markdown links with `.md` are resolved relative to the page path, ignoring
  external URLs and anchors.
- Markdown images are resolved relative to the page path.
- Duplicate titles and aliases are reported within the validation scope.
- Reviewed pages require non-empty `source_refs` or at least one non-empty line
  under `# Citations`.

- [ ] **Step 5: Implement CLI validate command**

`cli.py` requirements:

- Uses `argparse`.
- Global option `--root`, default current directory.
- Command `validate [--domain <name>] [--json]`.
- Text output lists `code path message` per issue.
- JSON output is a list of objects with `code`, `path`, and `message`.
- Exit code `0` when no issues, `1` for validation issues.

- [ ] **Step 6: Run green tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_validate.py personal-wiki/tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add personal-wiki/tools/wiki_cli/validate.py personal-wiki/tools/wiki_cli/cli.py personal-wiki/tests/test_validate.py personal-wiki/tests/test_cli.py
git commit -m "feat: add personal wiki validation CLI"
```

## Task 3: Domain Initialization, Indexing, Backlinks, And Graph Export

**Files:**
- Create: `personal-wiki/tools/wiki_cli/indexer.py`
- Create: `personal-wiki/tools/wiki_cli/graph.py`
- Modify: `personal-wiki/tools/wiki_cli/cli.py`
- Test: `personal-wiki/tests/test_index_graph.py`
- Test: `personal-wiki/tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `personal-wiki/tests/test_index_graph.py` covering:

- `init_domain(root, "ai-infra")` creates:
  - `DOMAIN.md`
  - `ingest.md`
  - `raw/inbox`, `raw/links`, `raw/notes`, `raw/papers`, `raw/images`,
    `raw/snapshots`
  - `wiki/index.md`, `wiki/assets/images`, `wiki/concepts`, `wiki/papers`,
    `wiki/projects`, `wiki/decisions`, `wiki/references`
- `build_index(root, "ai-infra")` writes sections for Concepts, Papers,
  Projects, Decisions, References using page frontmatter title and description.
- `collect_backlinks(root, "ai-infra")` maps target pages to source pages for
  relative Markdown links.
- `build_graph(root, "ai-infra")` returns JSON-serializable dict with `nodes`
  and `edges`; nodes include id, path, title, type, tags, description; edges
  include source and target ids.

Add CLI tests for:

- `init-domain ai-infra`
- `index ai-infra`
- `backlinks --domain ai-infra --write-json`
- `graph --domain ai-infra --out graph.json`

- [ ] **Step 2: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_index_graph.py personal-wiki/tests/test_cli.py -q
```

Expected: FAIL because commands/modules are missing.

- [ ] **Step 3: Implement indexing and graph modules**

Required APIs:

```python
def init_domain(root: Path, domain: str) -> list[Path]
def build_index(root: Path, domain: str) -> Path
def collect_backlinks(root: Path, domain: str | None = None) -> dict[str, list[str]]
def build_graph(root: Path, domain: str | None = None) -> dict[str, Any]
def write_graph(root: Path, domain: str | None, out: Path) -> Path
```

Indexing rules:

- Scan `domains/<domain>/wiki/**/*.md`, excluding `index.md`.
- Group by page `type`.
- Include `title`, relative link, and `description`.
- Stable sort by title.

Graph rules:

- Node id is path relative to root without `.md`.
- Edge source/target ids use resolved relative wiki links.
- Ignore external links and missing local links.

- [ ] **Step 4: Add CLI commands**

Add `init-domain`, `index`, `backlinks`, and `graph` subcommands to `cli.py`.

- [ ] **Step 5: Run green tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_index_graph.py personal-wiki/tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add personal-wiki/tools/wiki_cli/indexer.py personal-wiki/tools/wiki_cli/graph.py personal-wiki/tools/wiki_cli/cli.py personal-wiki/tests/test_index_graph.py personal-wiki/tests/test_cli.py
git commit -m "feat: add personal wiki index and graph commands"
```

## Task 4: Ingest Helper Commands

**Files:**
- Create: `personal-wiki/tools/wiki_cli/ingest.py`
- Modify: `personal-wiki/tools/wiki_cli/cli.py`
- Test: `personal-wiki/tests/test_ingest_helpers.py`
- Test: `personal-wiki/tests/test_cli.py`

- [ ] **Step 1: Write failing ingest tests**

Create `personal-wiki/tests/test_ingest_helpers.py` covering:

- `snapshot_url(root, "ai-infra", "https://example.com/a", fetch=False)`
  creates a raw source under `raw/links/` with `type: RawSource`,
  `source_kind: web`, URL, captured date, `status: pending`, and content noting
  live fetching was not requested.
- `image_note(root, "ai-infra", "raw/images/diagram.png")` creates
  `wiki/references/diagram-image.md` with `type: Reference`, `status: draft`,
  `source_refs` containing the raw image path, and sections `# Image Meaning`
  and `# Image Source`.
- `ingest_plan(root, "ai-infra", "raw/inbox/source.md")` writes a deterministic
  plan under `raw/inbox/source.ingest-plan.md` listing candidate page types,
  source path, and next steps. It must not create wiki concept pages.
- `update_ingest_log(root, "ai-infra", raw_path, output_path)` appends a pending
  entry if none exists.

Add CLI tests for `snapshot-url`, `image-note`, and `ingest-plan`.

- [ ] **Step 2: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_ingest_helpers.py personal-wiki/tests/test_cli.py -q
```

Expected: FAIL because ingest helpers are missing.

- [ ] **Step 3: Implement ingest helpers**

Required APIs:

```python
def slugify(value: str) -> str
def snapshot_url(root: Path, domain: str, url: str, *, fetch: bool = False) -> Path
def image_note(root: Path, domain: str, image_path: str) -> Path
def ingest_plan(root: Path, domain: str, raw_path: str) -> Path
def update_ingest_log(root: Path, domain: str, raw_path: str, output_path: str) -> Path
```

Constraints:

- `fetch=False` must not perform network I/O.
- `fetch=True` may use `urllib.request.urlopen` with timeout and store fetched
  text best-effort; tests only cover `fetch=False`.
- Helpers create parent directories as needed.
- Helpers never delete raw sources.
- Helpers do not create polished wiki concept pages; `ingest-plan` only drafts a
  plan.

- [ ] **Step 4: Add CLI commands**

Add `snapshot-url`, `image-note`, and `ingest-plan` subcommands.

- [ ] **Step 5: Run green tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_ingest_helpers.py personal-wiki/tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add personal-wiki/tools/wiki_cli/ingest.py personal-wiki/tools/wiki_cli/cli.py personal-wiki/tests/test_ingest_helpers.py personal-wiki/tests/test_cli.py
git commit -m "feat: add personal wiki ingest helpers"
```

## Task 5: Static Visualization

**Files:**
- Create: `personal-wiki/tools/wiki_cli/html.py`
- Modify: `personal-wiki/tools/wiki_cli/cli.py`
- Test: `personal-wiki/tests/test_skill_and_visualization.py`

- [ ] **Step 1: Write failing visualization tests**

Add tests that:

- Build a small domain with two linked wiki pages.
- Run `html.generate_html(root, "ai-infra", out)`.
- Assert output file exists.
- Assert output contains:
  - `Personal Wiki Graph`
  - embedded graph JSON
  - concept titles from the fixture
  - no external CDN references.

Add CLI test for:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root <root> visualize --domain ai-infra --out graph.html
```

- [ ] **Step 2: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_cli.py -q
```

Expected: FAIL because `html.py` and command are missing.

- [ ] **Step 3: Implement HTML generator**

Required API:

```python
def generate_html(root: Path, domain: str | None, out: Path) -> Path
```

Requirements:

- Embed graph JSON from `graph.build_graph`.
- Use inline CSS and JS only.
- Render a simple node list and edge list.
- No external network assets.

- [ ] **Step 4: Add CLI command**

Add `visualize [--domain <name>] [--out <path>]`.

- [ ] **Step 5: Run green tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add personal-wiki/tools/wiki_cli/html.py personal-wiki/tools/wiki_cli/cli.py personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_cli.py
git commit -m "feat: add personal wiki static visualization"
```

## Task 6: Codex Skill And Documentation

**Files:**
- Create: `personal-wiki/skills/personal-wiki-manager/SKILL.md`
- Create: `personal-wiki/docs/cli.md`
- Modify: `personal-wiki/tools/README.md`
- Modify: `personal-wiki/README.md`
- Modify: `personal-wiki/ROADMAP.md`
- Test: `personal-wiki/tests/test_skill_and_visualization.py`
- Test: `personal-wiki/tests/test_scaffold.py`

- [ ] **Step 1: Write failing docs/skill tests**

Extend `personal-wiki/tests/test_skill_and_visualization.py`:

- Assert `skills/personal-wiki-manager/SKILL.md` exists.
- Assert skill frontmatter has:
  - `name: personal-wiki-manager`
  - description mentioning query, ingest, validate, refactor, create-domain, and image-note.
- Assert skill body includes read order, mode routing, validation command, domain boundary, and image-note workflow.

Extend `personal-wiki/tests/test_scaffold.py`:

- Add required files:
  - `skills/personal-wiki-manager/SKILL.md`
  - `docs/cli.md`
  - `tools/wiki_cli/cli.py`

- [ ] **Step 2: Run red tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_scaffold.py -q
```

Expected: FAIL because skill/docs updates are missing.

- [ ] **Step 3: Add `personal-wiki/skills/personal-wiki-manager/SKILL.md`**

Skill requirements:

- Valid skill frontmatter with `name` and `description`.
- Sections:
  - Purpose
  - Read Order
  - Modes
  - Query Mode
  - Ingest Mode
  - Validate Mode
  - Refactor Mode
  - Create-Domain Mode
  - Image-Note Mode
  - Safety Rules
  - Commands
- Explicitly says raw is fact source, wiki is curated layer, default scope is
  one domain, and reviewed promotion needs user approval.

- [ ] **Step 4: Add CLI docs and update roadmap**

`personal-wiki/docs/cli.md` documents every implemented command with examples.

Update `personal-wiki/tools/README.md` from roadmap-only wording to state that
local tools now exist and point to `docs/cli.md`.

Update `personal-wiki/README.md` to mention the CLI and skill.

Update `personal-wiki/ROADMAP.md` to mark Phases 2-6 as implemented and list
remaining future ideas separately. Do not remove acceptance criteria.

- [ ] **Step 5: Run green docs/skill tests**

Run:

```bash
python -m pytest personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add personal-wiki/skills personal-wiki/docs/cli.md personal-wiki/tools/README.md personal-wiki/README.md personal-wiki/ROADMAP.md personal-wiki/tests/test_skill_and_visualization.py personal-wiki/tests/test_scaffold.py
git commit -m "docs: add personal wiki manager skill"
```

## Task 7: End-To-End CLI Verification

**Files:**
- Modify: `personal-wiki/tests/test_cli.py`
- Modify: implementation files only if the new end-to-end tests expose defects.

- [ ] **Step 1: Add failing end-to-end CLI test**

Extend `personal-wiki/tests/test_cli.py` with a single test that:

1. Runs `init-domain ai-infra`.
2. Writes one valid raw source and one Concept page.
3. Runs `validate --domain ai-infra` and expects exit 0.
4. Runs `index ai-infra`.
5. Runs `backlinks --domain ai-infra --write-json`.
6. Runs `graph --domain ai-infra --out graph.json`.
7. Runs `visualize --domain ai-infra --out graph.html`.
8. Runs `snapshot-url ai-infra https://example.com/source`.
9. Runs `image-note ai-infra raw/images/diagram.png`.
10. Runs `ingest-plan ai-infra raw/links/example-com-source.md`.

Assert all expected output files exist.

- [ ] **Step 2: Run red or green check**

Run:

```bash
python -m pytest personal-wiki/tests/test_cli.py -q
```

Expected: If this passes immediately, the prior tasks already satisfy the
end-to-end workflow. If it fails, confirm the failure identifies a real
integration defect.

- [ ] **Step 3: Fix integration defects if needed**

Only change the relevant implementation files. Keep behavior within the CLI
contract in this plan.

- [ ] **Step 4: Run full personal wiki test suite**

Run:

```bash
python -m pytest personal-wiki/tests -q
```

Expected: PASS.

- [ ] **Step 5: Run unfinished-marker and whitespace checks**

Run:

```bash
rg -n "TBD|TODO|FIXME|REPLACE_ME" personal-wiki
git diff --check
```

Expected:

- `rg` exits 1 with no output.
- `git diff --check` exits 0 with no output.

- [ ] **Step 6: Commit**

If Step 3 changed files or Step 1 added a test, run:

```bash
git add personal-wiki/tests/test_cli.py personal-wiki/tools/wiki_cli
git commit -m "test: add personal wiki end-to-end workflow"
```

If no implementation changed after adding the test, still commit the test.

## Final Verification

Run:

```bash
python -m pytest personal-wiki/tests -q
rg -n "TBD|TODO|FIXME|REPLACE_ME" personal-wiki
git diff --check
git status --short
```

Expected:

- All personal wiki tests pass.
- Marker scan has no matches.
- Whitespace check passes.
- No uncommitted files under `personal-wiki/`.

Then perform final code review for the full Phase 2-6 branch before merging.
