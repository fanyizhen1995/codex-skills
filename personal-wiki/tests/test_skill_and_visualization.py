from pathlib import Path

from personal_wiki_test_loader import load_cli_module


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
