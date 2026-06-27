import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
import yaml

from crawler_workbench.db import connect, migrate
from crawler_workbench.fetch_service import run_source_once
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.hashing import canonicalize_url, content_hash, slugify_url
from crawler_workbench.profiles import mirror_profiles
from crawler_workbench import raw_store
from crawler_workbench.raw_store import write_raw_item
from crawler_workbench.settings import Settings


class StaticFetcher:
    def __init__(self, results):
        self.results = results

    def fetch(self, profile):
        return self.results


def profile():
    return {
        "id": "src",
        "name": "Source",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com/report.pdf",
        "trust_level": "trusted",
        "schedule": "manual",
        "auto_ingest": True,
        "auth_required": False,
        "baseline_on_first_run": False,
        "topic": "topic",
        "enabled": True,
    }


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


def test_write_raw_item_rejects_path_traversal_source_id(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    with pytest.raises(ValueError, match="Invalid source id"):
        write_raw_item(
            settings=settings,
            source_id="../escaped",
            target_domain="ai_infra",
            canonical_url="https://example.com/release-notes",
            title="Escaped source",
            content="# Heading",
            metadata={"kind": "web"},
        )

    assert not (settings.wiki_root / "domains" / "ai_infra" / "raw" / "escaped").exists()


def test_write_raw_item_saves_pdf_attachment_next_to_markdown(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    pdf_bytes = b"%PDF-1.4\nbinary pdf\n%%EOF"

    raw = write_raw_item(
        settings=settings,
        source_id="pdf-source",
        target_domain="ai_infra",
        canonical_url="https://example.com/report.pdf",
        title="GPU Report",
        content="# GPU Report\n\nExtracted PDF text",
        metadata={"kind": "web", "pdf_extract_error": "pdftotext failed"},
        attachment_bytes=pdf_bytes,
        attachment_extension=".pdf",
        attachment_content_type="application/pdf",
    )

    attachment_path = raw.path.with_suffix(".pdf")
    attachment_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    assert raw.path.exists()
    assert attachment_path.exists()
    assert attachment_path.read_bytes() == pdf_bytes

    text = raw.path.read_text(encoding="utf-8")
    frontmatter_text, markdown = text.split("---\n", 2)[1:]
    frontmatter = yaml.safe_load(frontmatter_text)
    metadata = json.loads(raw.metadata_json)

    assert frontmatter["attachment_filename"] == attachment_path.name
    assert frontmatter["attachment_sha256"] == attachment_sha256
    assert frontmatter["attachment_content_type"] == "application/pdf"
    assert metadata["attachment_filename"] == attachment_path.name
    assert metadata["attachment_sha256"] == attachment_sha256
    assert metadata["attachment_content_type"] == "application/pdf"
    assert metadata["pdf_extract_error"] == "pdftotext failed"
    assert markdown == "# GPU Report\n\nExtracted PDF text\n"


def test_run_source_once_keeps_raw_path_on_markdown_and_metadata_on_pdf_attachment(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    pdf_bytes = b"%PDF-1.4\nbinary pdf\n%%EOF"
    result = FetchResult(
        canonical_url="https://example.com/report.pdf",
        title="GPU Report",
        content="# GPU Report\n\nExtracted PDF text",
        content_type="application/pdf",
        metadata={"kind": "web"},
        attachment_bytes=pdf_bytes,
        attachment_extension=".pdf",
        attachment_content_type="application/pdf",
    )

    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
        row = db.execute("select raw_path, metadata_json from raw_items").fetchone()

    metadata = json.loads(row["metadata_json"])
    raw_path = Path(row["raw_path"])
    assert str(row["raw_path"]).endswith(".md")
    assert metadata["attachment_filename"].endswith(".pdf")
    assert metadata["attachment_content_type"] == "application/pdf"
    assert metadata["attachment_sha256"] == hashlib.sha256(pdf_bytes).hexdigest()
    assert raw_path.with_name(metadata["attachment_filename"]).read_bytes() == pdf_bytes


def test_run_source_once_treats_changed_pdf_bytes_as_changed_content(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    first = FetchResult(
        canonical_url="https://example.com/report.pdf",
        title="GPU Report",
        content="# GPU Report\n\nExtracted PDF text",
        content_type="application/pdf",
        metadata={"kind": "web"},
        attachment_bytes=b"%PDF-1.4\nfirst\n%%EOF",
        attachment_extension=".pdf",
        attachment_content_type="application/pdf",
    )
    second = FetchResult(
        canonical_url="https://example.com/report.pdf",
        title="GPU Report",
        content="# GPU Report\n\nExtracted PDF text",
        content_type="application/pdf",
        metadata={"kind": "web"},
        attachment_bytes=b"%PDF-1.4\nsecond\n%%EOF",
        attachment_extension=".pdf",
        attachment_content_type="application/pdf",
    )

    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        run_source_once(settings, db, "src", fetcher=StaticFetcher([first]))
        summary = run_source_once(settings, db, "src", fetcher=StaticFetcher([second]))
        rows = db.execute("select content_hash, metadata_json from raw_items order by id").fetchall()

    assert summary["changed_count"] == 1
    assert len(rows) == 2
    assert rows[0]["content_hash"] != rows[1]["content_hash"]
    assert json.loads(rows[0]["metadata_json"])["attachment_sha256"] != json.loads(rows[1]["metadata_json"])["attachment_sha256"]


def test_run_source_once_cleans_pdf_attachment_after_insert_failure(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    pdf_bytes = b"%PDF-1.4\nbinary pdf\n%%EOF"
    results = [
        FetchResult(
            canonical_url="https://example.com/report.pdf",
            title="GPU Report",
            content="# GPU Report\n\nExtracted PDF text",
            content_type="application/pdf",
            metadata={"kind": "web"},
            attachment_bytes=pdf_bytes,
            attachment_extension=".pdf",
            attachment_content_type="application/pdf",
        ),
        FetchResult("https://example.com/broken", None, "broken", "text/markdown"),
    ]

    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        with pytest.raises(sqlite3.IntegrityError):
            run_source_once(settings, db, "src", fetcher=StaticFetcher(results))

    raw_dir = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src"
    assert list(raw_dir.glob("*.md")) == []
    assert list(raw_dir.glob("*.pdf")) == []


def test_write_raw_item_removes_markdown_when_attachment_write_fails(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    original_write_bytes = raw_store._exclusive_write_bytes

    def failing_write_bytes(path, body):
        raise OSError("disk full")

    monkeypatch.setattr(raw_store, "_exclusive_write_bytes", failing_write_bytes)

    with pytest.raises(OSError, match="disk full"):
        write_raw_item(
            settings=settings,
            source_id="pdf-source",
            target_domain="ai_infra",
            canonical_url="https://example.com/report.pdf",
            title="GPU Report",
            content="# GPU Report\n\nExtracted PDF text",
            metadata={"kind": "web"},
            attachment_bytes=b"%PDF-1.4\n%%EOF",
            attachment_extension=".pdf",
            attachment_content_type="application/pdf",
        )

    raw_dir = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "pdf-source"
    assert list(raw_dir.glob("*.md")) == []
    assert list(raw_dir.glob("*.pdf")) == []
    monkeypatch.setattr(raw_store, "_exclusive_write_bytes", original_write_bytes)
