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
    assert doc.body == "\n# Summary\nBody\n"


def test_parse_markdown_without_frontmatter():
    doc = document.parse_markdown("# Plain\n")
    assert doc.frontmatter == {}
    assert doc.body == "# Plain\n"


def test_parse_frontmatter_preserves_body_after_delimiter_line():
    doc = document.parse_markdown("---\na: b\n---\n\n# H\n")
    assert doc.frontmatter == {"a": "b"}
    assert doc.body == "\n# H\n"


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


def test_repo_root_from_returns_personal_wiki_root(tmp_path: Path):
    outer = tmp_path / "repo"
    root = outer / "personal-wiki"
    root.mkdir(parents=True)
    (root / "WIKI.md").write_text("# Wiki\n", encoding="utf-8")
    (root / "domains").mkdir()

    assert paths.repo_root_from(outer) == root
    assert paths.repo_root_from(root / "domains") == root
