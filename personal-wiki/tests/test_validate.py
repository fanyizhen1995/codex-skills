from pathlib import Path

from personal_wiki_test_loader import load_cli_module


validate = load_cli_module("validate")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def issue_codes(root: Path, domain: str = "ai-infra") -> list[str]:
    return [issue.code for issue in validate.validate(root, domain=domain)]


def build_valid_domain(root: Path) -> None:
    write(
        root / "domains/ai-infra/raw/notes/source.md",
        "---\ntype: RawSource\ntitle: Source\nsource_kind: note\ncaptured: 2026-06-23\nstatus: pending\n---\n\n# Raw Content\n",
    )
    write(root / "domains/ai-infra/wiki/concepts/diagram.png", "image")
    write(
        root / "domains/ai-infra/wiki/concepts/related.md",
        "---\ntype: Reference\ntitle: Related\ndescription: Related note.\ndomain: ai-infra\nstatus: draft\n---\n\n# Summary\nRelated.\n",
    )
    write(
        root / "domains/ai-infra/wiki/concepts/kv-cache.md",
        "---\ntype: Concept\ntitle: KV Cache\ndescription: Cache for transformer key/value states.\ndomain: ai-infra\nstatus: reviewed\nsource_refs:\n  - ../../raw/notes/source.md\n---\n\n# Summary\nSee [related](related.md).\n\n![Diagram](diagram.png)\n\n# Citations\n- ../../raw/notes/source.md\n",
    )


def test_validate_accepts_well_formed_domain(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_domain(root)

    assert validate.validate(root, domain="ai-infra") == []


def test_validate_reports_missing_required_frontmatter(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/foo.md",
        "---\ntype: Concept\ntitle: Foo\ndomain: ai-infra\n---\n\n# Summary\nMissing description.\n",
    )

    issues = validate.validate(root, domain="ai-infra")

    assert [issue.code for issue in issues] == ["missing_required"]
    assert issues[0].path.as_posix().endswith("wiki/concepts/foo.md")
    assert "description" in issues[0].message


def test_validate_reports_bad_type_and_status(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/bad.md",
        "---\ntype: Note\ntitle: Bad\ndescription: Bad page.\ndomain: ai-infra\nstatus: pending\n---\n\n# Summary\nBad.\n",
    )

    assert issue_codes(root) == ["invalid_type", "invalid_status"]


def test_validate_reports_missing_source_ref_and_broken_link(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/broken.md",
        "---\ntype: Concept\ntitle: Broken\ndescription: Broken references.\ndomain: ai-infra\nstatus: draft\nsource_refs:\n  - ../../raw/notes/missing.md\n---\n\n# Summary\nSee [missing](missing.md), [section](#local), and [external](https://example.com/page.md).\n",
    )

    assert issue_codes(root) == ["missing_source_ref", "broken_link"]


def test_validate_reports_absolute_source_ref_outside_root(tmp_path: Path):
    outside = tmp_path / "outside.md"
    write(outside, "# Outside\n")
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/escaped-source.md",
        f"---\ntype: Concept\ntitle: Escaped Source\ndescription: Escaped source ref.\ndomain: ai-infra\nstatus: draft\nsource_refs: [{outside}]\n---\n\n# Summary\nEscaped.\n",
    )

    assert issue_codes(root) == ["missing_source_ref"]


def test_validate_reports_markdown_link_outside_root(tmp_path: Path):
    write(tmp_path / "outside.md", "# Outside\n")
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/escaped-link.md",
        "---\ntype: Concept\ntitle: Escaped Link\ndescription: Escaped markdown link.\ndomain: ai-infra\nstatus: draft\n---\n\n# Summary\n[outside](../../../../../outside.md)\n",
    )

    assert issue_codes(root) == ["broken_link"]


def test_validate_reports_missing_image(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/image.md",
        "---\ntype: Concept\ntitle: Image\ndescription: Image page.\ndomain: ai-infra\nstatus: draft\n---\n\n# Summary\n![Missing](assets/missing.png)\n",
    )

    assert issue_codes(root) == ["missing_image"]


def test_validate_reports_image_outside_root(tmp_path: Path):
    write(tmp_path / "outside.png", "image")
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/escaped-image.md",
        "---\ntype: Concept\ntitle: Escaped Image\ndescription: Escaped image.\ndomain: ai-infra\nstatus: draft\n---\n\n# Summary\n![x](../../../../../outside.png)\n",
    )

    assert issue_codes(root) == ["missing_image"]


def test_validate_reports_duplicate_titles_and_aliases(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/first.md",
        "---\ntype: Concept\ntitle: Duplicate\ndescription: First.\ndomain: ai-infra\nstatus: draft\naliases: [Shared Alias]\n---\n\n# Summary\nFirst.\n",
    )
    write(
        root / "domains/ai-infra/wiki/concepts/second.md",
        "---\ntype: Concept\ntitle: Duplicate\ndescription: Second.\ndomain: ai-infra\nstatus: draft\naliases:\n  - Shared Alias\n---\n\n# Summary\nSecond.\n",
    )

    assert issue_codes(root) == ["duplicate_title", "duplicate_alias"]


def test_validate_reviewed_page_requires_sources(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/reviewed.md",
        "---\ntype: Concept\ntitle: Reviewed\ndescription: Reviewed without evidence.\ndomain: ai-infra\nstatus: reviewed\n---\n\n# Summary\nReviewed.\n\n# Citations\n\n",
    )

    assert issue_codes(root) == ["reviewed_without_sources"]
