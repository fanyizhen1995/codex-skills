import json

import pytest
import yaml

from crawler_workbench.hashing import canonicalize_url, content_hash, slugify_url
from crawler_workbench.raw_store import write_raw_item
from crawler_workbench.settings import Settings


def test_canonicalize_url_and_hash_are_stable():
    assert canonicalize_url("HTTPS://Example.com:443/a/../b?utm_source=x&z=1") == "https://example.com/b?z=1"
    assert canonicalize_url("example.com/a") == "https://example.com/a"
    assert canonicalize_url("https://example.com/%7Euser") == canonicalize_url("https://example.com/~user")
    assert content_hash(" hello\nworld ") == content_hash("hello\nworld")
    assert slugify_url("https://example.com/a/b?z=1").startswith("example-com-a-b")


def test_write_raw_item_creates_domain_raw_file(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw = write_raw_item(
        settings=settings,
        source_id="nccl-release-notes",
        target_domain="ai_infra",
        canonical_url="https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        title="NCCL release notes",
        content="# NCCL\ncontent",
        metadata={"kind": "web"},
    )
    assert raw.path.exists()
    assert raw.path.as_posix().endswith(".md")
    text = raw.path.read_text(encoding="utf-8")
    assert "source_id: nccl-release-notes" in text
    assert "canonical_url: https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html" in text
    assert "# NCCL" in text
    metadata = json.loads(raw.metadata_json)
    assert metadata["kind"] == "web"


def test_write_raw_item_creates_distinct_files_for_duplicate_content(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    first = write_raw_item(
        settings=settings,
        source_id="nccl-release-notes",
        target_domain="ai_infra",
        canonical_url="https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        title="NCCL release notes",
        content="# NCCL\ncontent",
        metadata={"kind": "web"},
    )
    second = write_raw_item(
        settings=settings,
        source_id="nccl-release-notes",
        target_domain="ai_infra",
        canonical_url="https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        title="NCCL release notes",
        content="# NCCL\ncontent",
        metadata={"kind": "web"},
    )

    assert first.path != second.path
    assert first.path.exists()
    assert second.path.exists()
    assert len(list(first.path.parent.glob("*.md"))) == 2
    assert first.path.read_text(encoding="utf-8").endswith("# NCCL\ncontent\n")
    assert second.path.read_text(encoding="utf-8").endswith("# NCCL\ncontent\n")


def test_write_raw_item_frontmatter_is_valid_yaml(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw = write_raw_item(
        settings=settings,
        source_id="quoted-title",
        target_domain="ai_infra",
        canonical_url="https://example.com/release-notes",
        title='Release notes: "NCCL"',
        content="# Heading\n\nBody",
        metadata={"kind": "web"},
    )
    text = raw.path.read_text(encoding="utf-8")
    frontmatter_text, markdown = text.split("---\n", 2)[1:]
    frontmatter = yaml.safe_load(frontmatter_text)

    assert frontmatter["source_id"] == "quoted-title"
    assert frontmatter["title"] == 'Release notes: "NCCL"'
    assert frontmatter["canonical_url"] == "https://example.com/release-notes"
    assert frontmatter["content_hash"] == raw.content_hash
    assert markdown == "# Heading\n\nBody\n"


def test_write_raw_item_rejects_non_json_metadata(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    with pytest.raises(TypeError, match="metadata must be JSON serializable"):
        write_raw_item(
            settings=settings,
            source_id="bad-metadata",
            target_domain="ai_infra",
            canonical_url="https://example.com/release-notes",
            title="Bad metadata",
            content="# Heading",
            metadata={"bad": object()},
        )
