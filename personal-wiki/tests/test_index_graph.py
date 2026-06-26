import json
from pathlib import Path

from personal_wiki_test_loader import load_cli_module


indexer = load_cli_module("indexer")
graph = load_cli_module("graph")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_wiki_page(
    root: Path,
    relative_path: str,
    *,
    wiki_type: str,
    title: str,
    description: str,
    tags: str = "[]",
    body: str = "",
) -> Path:
    path = root / "domains/ai-infra/wiki" / relative_path
    write(
        path,
        "\n".join(
            [
                "---",
                f"type: {wiki_type}",
                f"title: {title}",
                f"description: {description}",
                "domain: ai-infra",
                "status: draft",
                f"tags: {tags}",
                "source_refs: []",
                "---",
                "",
                body,
            ]
        ),
    )
    return path


def build_graph_fixture(root: Path) -> None:
    write_wiki_page(
        root,
        "concepts/attention.md",
        wiki_type="Concept",
        title="Attention",
        description="Mechanism for weighting context.",
        tags="[transformer, mechanism]",
        body=(
            "See [KV Cache](kv-cache.md), [Flash Attention](../papers/flash-attention.md), "
            "[Missing](missing.md), and [External](https://example.com).\n"
        ),
    )
    write_wiki_page(
        root,
        "concepts/kv-cache.md",
        wiki_type="Concept",
        title="KV Cache",
        description="Cache for transformer key/value states.",
        body="Back to [Attention](attention.md).\n",
    )
    write_wiki_page(
        root,
        "papers/flash-attention.md",
        wiki_type="Paper",
        title="Flash Attention",
        description="IO-aware attention algorithm.",
        tags="[paper]",
        body="Builds on [Attention](../concepts/attention.md#summary).\n",
    )
    write_wiki_page(
        root,
        "projects/inference-stack.md",
        wiki_type="Project",
        title="Inference Stack",
        description="Serving stack notes.",
    )
    write_wiki_page(
        root,
        "decisions/batching.md",
        wiki_type="Decision",
        title="Batching Policy",
        description="Decision about batching requests.",
    )
    write_wiki_page(
        root,
        "references/glossary.md",
        wiki_type="Reference",
        title="Glossary",
        description="Reference definitions.",
    )
    write(
        root / "domains/ai-infra/wiki/index.md",
        "# Existing Index\n\nThis page is overwritten by build_index.\n",
    )


def test_init_domain_creates_domain_skeleton(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    created = indexer.init_domain(root, "ai-infra")

    expected = [
        "domains/ai-infra/DOMAIN.md",
        "domains/ai-infra/ingest.md",
        "domains/ai-infra/raw/inbox",
        "domains/ai-infra/raw/links",
        "domains/ai-infra/raw/notes",
        "domains/ai-infra/raw/papers",
        "domains/ai-infra/raw/images",
        "domains/ai-infra/raw/snapshots",
        "domains/ai-infra/wiki/index.md",
        "domains/ai-infra/wiki/assets/images",
        "domains/ai-infra/wiki/concepts",
        "domains/ai-infra/wiki/papers",
        "domains/ai-infra/wiki/projects",
        "domains/ai-infra/wiki/decisions",
        "domains/ai-infra/wiki/references",
    ]
    assert [path.relative_to(root).as_posix() for path in created] == expected
    for relative_path in expected:
        assert (root / relative_path).exists(), relative_path


def test_build_index_groups_pages_by_type_with_title_description_and_stable_sort(
    tmp_path: Path,
):
    root = tmp_path / "personal-wiki"
    build_graph_fixture(root)
    write_wiki_page(
        root,
        "concepts/activation.md",
        wiki_type="Concept",
        title="Activation Function",
        description="Non-linear transform.",
    )

    index_path = indexer.build_index(root, "ai-infra")

    assert index_path == root / "domains/ai-infra/wiki/index.md"
    text = index_path.read_text(encoding="utf-8")
    assert "## Concepts" in text
    assert "## Papers" in text
    assert "## Projects" in text
    assert "## Decisions" in text
    assert "## References" in text
    assert (
        "- [Activation Function](concepts/activation.md) - Non-linear transform.\n"
        "- [Attention](concepts/attention.md) - Mechanism for weighting context.\n"
        "- [KV Cache](concepts/kv-cache.md) - Cache for transformer key/value states."
    ) in text
    assert "- [Flash Attention](papers/flash-attention.md) - IO-aware attention algorithm." in text
    assert "- [Inference Stack](projects/inference-stack.md) - Serving stack notes." in text
    assert "- [Batching Policy](decisions/batching.md) - Decision about batching requests." in text
    assert "- [Glossary](references/glossary.md) - Reference definitions." in text


def test_collect_backlinks_maps_targets_to_sources_for_relative_markdown_links(
    tmp_path: Path,
):
    root = tmp_path / "personal-wiki"
    build_graph_fixture(root)

    backlinks = graph.collect_backlinks(root, "ai-infra")

    assert backlinks == {
        "domains/ai-infra/wiki/concepts/attention": [
            "domains/ai-infra/wiki/concepts/kv-cache",
            "domains/ai-infra/wiki/papers/flash-attention",
        ],
        "domains/ai-infra/wiki/concepts/kv-cache": [
            "domains/ai-infra/wiki/concepts/attention"
        ],
        "domains/ai-infra/wiki/papers/flash-attention": [
            "domains/ai-infra/wiki/concepts/attention"
        ],
    }


def test_build_graph_returns_serializable_nodes_and_edges(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_graph_fixture(root)

    payload = graph.build_graph(root, "ai-infra")

    json.dumps(payload)
    assert {
        "id": "domains/ai-infra/wiki/concepts/attention",
        "path": "domains/ai-infra/wiki/concepts/attention.md",
        "title": "Attention",
        "type": "Concept",
        "tags": ["transformer", "mechanism"],
        "description": "Mechanism for weighting context.",
    } in payload["nodes"]
    assert {
        "source": "domains/ai-infra/wiki/concepts/attention",
        "target": "domains/ai-infra/wiki/concepts/kv-cache",
    } in payload["edges"]
    assert {
        "source": "domains/ai-infra/wiki/concepts/attention",
        "target": "domains/ai-infra/wiki/papers/flash-attention",
    } in payload["edges"]
    assert all("missing" not in edge["target"] for edge in payload["edges"])
