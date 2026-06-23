from pathlib import Path

from personal_wiki_test_loader import load_cli_module


document = load_cli_module("document")
ingest = load_cli_module("ingest")


def test_snapshot_url_without_fetch_creates_pending_raw_source(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    path = ingest.snapshot_url(root, "ai-infra", "https://example.com/a", fetch=False)

    assert path == root / "domains/ai-infra/raw/links/example-com-a.md"
    doc = document.load_document(path)
    assert doc.frontmatter["type"] == "RawSource"
    assert doc.frontmatter["source_kind"] == "web"
    assert doc.frontmatter["url"] == "https://example.com/a"
    assert doc.frontmatter["captured"]
    assert doc.frontmatter["status"] == "pending"
    assert "Live fetching was not requested." in doc.body


def test_image_note_creates_reference_note_for_raw_image(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    path = ingest.image_note(root, "ai-infra", "raw/images/diagram.png")

    assert path == root / "domains/ai-infra/wiki/references/diagram-image.md"
    doc = document.load_document(path)
    assert doc.frontmatter["type"] == "Reference"
    assert doc.frontmatter["status"] == "draft"
    assert doc.frontmatter["source_refs"] == ["raw/images/diagram.png"]
    assert "# Image Meaning" in doc.body
    assert "# Image Source" in doc.body


def test_ingest_plan_writes_plan_next_to_raw_source_without_wiki_page(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    raw = root / "domains/ai-infra/raw/inbox/source.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("# Source\n", encoding="utf-8")

    path = ingest.ingest_plan(root, "ai-infra", "raw/inbox/source.md")

    assert path == root / "domains/ai-infra/raw/inbox/source.ingest-plan.md"
    body = path.read_text(encoding="utf-8")
    assert "Source path: raw/inbox/source.md" in body
    assert "Candidate page types" in body
    assert "Concept" in body
    assert "Next steps" in body
    assert not (root / "domains/ai-infra/wiki/concepts/source.md").exists()
    assert raw.exists()


def test_update_ingest_log_appends_pending_entry_once(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    first = ingest.update_ingest_log(
        root,
        "ai-infra",
        "raw/inbox/source.md",
        "raw/inbox/source.ingest-plan.md",
    )
    second = ingest.update_ingest_log(
        root,
        "ai-infra",
        "raw/inbox/source.md",
        "raw/inbox/source.ingest-plan.md",
    )

    assert first == root / "domains/ai-infra/ingest.md"
    assert second == first
    text = first.read_text(encoding="utf-8")
    entry = "- [ ] raw/inbox/source.md -> raw/inbox/source.ingest-plan.md (pending)"
    assert text.count(entry) == 1
