from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_required_scaffold_files_exist():
    required = [
        "README.md",
        "WIKI.md",
        "ROADMAP.md",
        "docs/design.md",
        "schemas/frontmatter.md",
        "templates/domain/DOMAIN.md",
        "templates/domain/ingest.md",
        "templates/domain/wiki/index.md",
        "templates/wiki/concept.md",
        "templates/wiki/paper.md",
        "templates/wiki/project.md",
        "templates/wiki/decision.md",
        "templates/wiki/reference.md",
        "templates/raw/source.md",
        "templates/raw/image-source.md",
        "global/wiki/index.md",
        "global/wiki/concepts/.gitkeep",
        "global/wiki/people/.gitkeep",
        "global/wiki/organizations/.gitkeep",
        "global/wiki/references/.gitkeep",
        "domains/.gitkeep",
        "tools/README.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_global_llm_protocol_contains_core_rules():
    text = read("WIKI.md")
    assert "Read Order" in text
    assert "raw/ is the fact source" in text
    assert "wiki/ is the curated knowledge layer" in text
    assert "Do not promote a page to reviewed unless the user explicitly asks" in text
    assert "Avoid full-repository scans" in text


def test_frontmatter_schema_documents_required_fields():
    text = read("schemas/frontmatter.md")
    assert "Required wiki fields" in text
    assert "`type`" in text
    assert "`title`" in text
    assert "`description`" in text
    assert "`domain`" in text
    assert "RawSource" in text


def test_page_templates_include_source_refs_and_status():
    for path in [
        "templates/wiki/concept.md",
        "templates/wiki/paper.md",
        "templates/wiki/project.md",
        "templates/wiki/decision.md",
        "templates/wiki/reference.md",
    ]:
        text = read(path)
        assert "source_refs:" in text, path
        assert "status: draft" in text, path
        assert "# Citations" in text, path


def test_image_rules_are_represented_in_reference_template():
    text = read("templates/wiki/reference.md")
    assert "wiki/assets/images/" in text
    assert "raw/images/" in text
    assert "Image Meaning" in text
    assert "Image Source" in text


def test_roadmap_preserves_later_phases():
    text = read("ROADMAP.md")
    for phrase in [
        "Phase 2: Validation tooling",
        "Phase 3: Index and graph tooling",
        "Phase 4: Ingest assistance",
        "Phase 5: Codex skill",
        "Phase 6: Optional publication and visualization",
    ]:
        assert phrase in text
