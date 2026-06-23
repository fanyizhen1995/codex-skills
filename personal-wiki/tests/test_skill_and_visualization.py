from pathlib import Path

from personal_wiki_test_loader import load_cli_module


ROOT = Path(__file__).resolve().parents[1]
html = load_cli_module("html")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_linked_wiki_fixture(root: Path) -> None:
    write(
        root / "domains/ai-infra/wiki/concepts/vector-db.md",
        "---\ntype: Concept\ntitle: Vector Database\ndescription: Stores embeddings for retrieval.\ndomain: ai-infra\nstatus: draft\nsource_refs: []\n---\n\nSee [Retrieval](retrieval.md).\n",
    )
    write(
        root / "domains/ai-infra/wiki/concepts/retrieval.md",
        "---\ntype: Concept\ntitle: Retrieval\ndescription: Finds relevant context.\ndomain: ai-infra\nstatus: draft\nsource_refs: []\n---\n\nRelated to [Vector Database](vector-db.md).\n",
    )


def test_generate_html_embeds_static_graph_without_external_assets(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_linked_wiki_fixture(root)
    out = tmp_path / "graph.html"

    path = html.generate_html(root, "ai-infra", out)

    assert path == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Personal Wiki Graph" in text
    assert 'const graphData = {"edges":' in text
    assert "Vector Database" in text
    assert "Retrieval" in text
    assert "https://" not in text
    assert "http://" not in text
    assert "cdn" not in text.lower()


def test_generate_html_escapes_script_sensitive_graph_json(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(
        root / "domains/ai-infra/wiki/concepts/script-title.md",
        "---\ntype: Concept\ntitle: Break </script><h1>Injected</h1>\ndescription: Safe description.\ndomain: ai-infra\nstatus: draft\nsource_refs: []\n---\n\nBody.\n",
    )
    out = tmp_path / "graph.html"

    html.generate_html(root, "ai-infra", out)

    text = out.read_text(encoding="utf-8")
    payload = text.split("const graphData = ", 1)[1].split(";\n", 1)[0]
    assert "</script>" not in payload.lower()
    assert "\\u003c/script\\u003e" in payload.lower()


def test_personal_wiki_manager_skill_exists_with_required_routing():
    path = ROOT / "skills/personal-wiki-manager/SKILL.md"

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter = text.split("---\n", 2)[1]
    body = text.split("---\n", 2)[2]

    assert "name: personal-wiki-manager" in frontmatter
    description = next(
        line.split(":", 1)[1].strip()
        for line in frontmatter.splitlines()
        if line.startswith("description:")
    )
    for phrase in [
        "query",
        "ingest",
        "validate",
        "refactor",
        "create-domain",
        "image-note",
    ]:
        assert phrase in description

    body_lower = body.lower()
    for phrase in [
        "read order",
        "mode routing",
        "python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate",
        "domain boundary",
        "image-note workflow",
    ]:
        assert phrase in body_lower
