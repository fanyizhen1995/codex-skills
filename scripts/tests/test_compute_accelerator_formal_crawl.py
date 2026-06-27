import json
from pathlib import Path
import sys
import hashlib


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import compute_accelerator_formal_crawl as crawl


def test_select_profiles_returns_enabled_accelerators_and_skipped_disabled() -> None:
    profiles = [
        {
            "id": "plain-source",
            "enabled": True,
            "baseline_on_first_run": True,
        },
        {
            "id": "enabled-accelerator",
            "enabled": True,
            "source_rank": "S1",
            "baseline_on_first_run": True,
        },
        {
            "id": "disabled-accelerator",
            "enabled": False,
            "accelerator_scope": ["gpu"],
            "baseline_on_first_run": False,
        },
    ]

    selected, skipped = crawl.select_run_profiles(profiles, source_ids=[])

    assert [profile["id"] for profile in selected] == ["enabled-accelerator"]
    assert skipped == [{"source_id": "disabled-accelerator", "reason": "disabled"}]


def test_prepare_run_profiles_forces_baseline_false_without_mutating_original() -> None:
    original = [
        {
            "id": "enabled-accelerator",
            "enabled": True,
            "source_rank": "S1",
            "baseline_on_first_run": True,
        }
    ]

    prepared = crawl.prepare_run_profiles(original)

    assert prepared[0]["baseline_on_first_run"] is False
    assert original[0]["baseline_on_first_run"] is True


def test_verify_manifest_fails_when_succeeded_raw_path_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest_path = tmp_path / "manifest.json"
    missing_raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/missing.md"
    manifest_path.write_text(json.dumps(full_manifest(repo_root, missing_raw_path)), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "missing raw path" in message


def test_verify_manifest_fails_when_succeeded_count_has_no_succeeded_entries(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md"
    manifest = full_manifest(repo_root, raw_path)
    manifest["succeeded"] = []
    manifest["raw_paths"] = []
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "succeeded entries" in message


def test_verify_manifest_fails_when_required_top_level_key_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# raw\n", encoding="utf-8")
    manifest = full_manifest(repo_root, raw_path)
    del manifest["task_id"]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "missing required manifest key: task_id" in message


def test_verify_manifest_passes_for_minimal_valid_manifest_and_raw_file(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# raw\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(full_manifest(repo_root, raw_path)), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is True
    assert message == "manifest verified"


def test_verify_manifest_fails_when_declared_pdf_attachment_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        """---
source_id: source-a
title: PDF capture
canonical_url: https://example.com/report.pdf
captured_at: '2026-06-27T00:00:00+00:00'
content_hash: abc
attachment_filename: capture.pdf
attachment_sha256: deadbeef
attachment_content_type: application/pdf
---
# PDF capture
""",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(full_manifest(repo_root, raw_path)), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "missing raw attachment" in message


def test_verify_manifest_rejects_raw_paths_that_escape_raw_prefix_with_parent_segments(tmp_path: Path) -> None:
    repo_root = tmp_path
    escaped_path = repo_root / "personal-wiki/domains/ai_infra/wiki/projects/fake.md"
    escaped_path.parent.mkdir(parents=True)
    escaped_path.write_text("# not raw\n", encoding="utf-8")
    (repo_root / "personal-wiki/domains/ai_infra/raw/crawler").mkdir(parents=True)
    escaped_manifest_path = "personal-wiki/domains/ai_infra/raw/crawler/../../wiki/projects/fake.md"
    manifest = full_manifest(repo_root, repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md")
    manifest["succeeded"] = [{"source_id": "source-a", "raw_paths": [escaped_manifest_path]}]
    manifest["raw_paths"] = [escaped_manifest_path]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "raw path is outside accelerator crawler raw area" in message


def test_run_formal_crawl_fails_self_verification_when_no_raw_captures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    source_path = repo_root / "personal-wiki/apps/crawler_workbench/config/sources.example.yaml"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        """
sources:
  - id: accelerator-source
    enabled: true
    source_rank: S1
""".lstrip(),
        encoding="utf-8",
    )

    def fake_mirror_profiles_and_run(repo_root, state_dir, run_profiles, manifest):
        manifest["ran_source_ids"].append("accelerator-source")
        manifest["succeeded"].append(
            {
                "source_id": "accelerator-source",
                "fetch_run": {"fetch_run_id": 123},
                "raw_paths": [],
                "ingest_task_ids": [],
            }
        )

    monkeypatch.setattr(crawl, "_mirror_profiles_and_run", fake_mirror_profiles_and_run)

    try:
        crawl.run_formal_crawl(repo_root=repo_root, output_dir=tmp_path / "out", source_ids=[])
    except ValueError as exc:
        assert "generated manifest failed verification" in str(exc)
    else:
        raise AssertionError("run_formal_crawl should fail when its manifest has no raw captures")


def test_run_formal_crawl_accepts_custom_task_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    source_path = repo_root / "personal-wiki/apps/crawler_workbench/config/sources.example.yaml"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        """
sources:
  - id: accelerator-source
    enabled: true
    source_rank: S1
""".lstrip(),
        encoding="utf-8",
    )
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/accelerator-source/capture.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# raw\n", encoding="utf-8")

    def fake_mirror_profiles_and_run(repo_root, state_dir, run_profiles, manifest):
        relative_raw_path = raw_path.relative_to(repo_root).as_posix()
        manifest["ran_source_ids"].append("accelerator-source")
        manifest["raw_paths"].append(relative_raw_path)
        manifest["succeeded"].append(
            {
                "source_id": "accelerator-source",
                "fetch_run": {"fetch_run_id": 123},
                "raw_paths": [relative_raw_path],
                "ingest_task_ids": [],
            }
        )

    monkeypatch.setattr(crawl, "_mirror_profiles_and_run", fake_mirror_profiles_and_run)

    manifest = crawl.run_formal_crawl(
        repo_root=repo_root,
        output_dir=tmp_path / "out",
        source_ids=[],
        task_id="compute-accelerator-domestic-crawl-01",
    )

    assert manifest["task_id"] == "compute-accelerator-domestic-crawl-01"


def test_mirror_profiles_records_no_raw_captures_as_failed(monkeypatch, tmp_path: Path) -> None:
    class FakeTransaction:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeDb:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=()):
            class Rows:
                def fetchall(self):
                    return []

            return Rows()

    monkeypatch.setitem(sys.modules, "crawler_workbench", type(sys)("crawler_workbench"))
    for module_name in [
        "crawler_workbench.db",
        "crawler_workbench.fetch_service",
        "crawler_workbench.profiles",
        "crawler_workbench.settings",
    ]:
        monkeypatch.setitem(sys.modules, module_name, type(sys)(module_name))

    sys.modules["crawler_workbench.db"].migrate = lambda db: None
    sys.modules["crawler_workbench.db"].open_db = lambda database_path: FakeDb()
    sys.modules["crawler_workbench.db"].transaction = lambda db: FakeTransaction()
    sys.modules["crawler_workbench.fetch_service"].run_source_once = lambda settings, db, source_id: {
        "fetch_run_id": 123
    }
    sys.modules["crawler_workbench.profiles"].load_profiles_from_yaml = lambda path: []
    sys.modules["crawler_workbench.profiles"].mirror_profiles = lambda db, profiles: None

    class Settings:
        def __init__(self, repo_root, state_dir, bind_host):
            self.repo_root = repo_root
            self.state_dir = state_dir
            self.bind_host = bind_host
            self.database_path = state_dir / "crawler.db"
            self.sources_yaml_path = state_dir / "sources.yaml"

    sys.modules["crawler_workbench.settings"].Settings = Settings

    manifest = {
        "ran_source_ids": [],
        "succeeded": [],
        "failed": [],
        "raw_paths": [],
        "ingest_tasks": [],
    }

    crawl._mirror_profiles_and_run(
        repo_root=tmp_path,
        state_dir=tmp_path / "state",
        run_profiles=[{"id": "accelerator-source"}],
        manifest=manifest,
    )

    assert manifest["succeeded"] == []
    assert manifest["failed"] == [
        {"source_id": "accelerator-source", "error": "no raw captures produced"}
    ]


def test_raw_paths_for_fetch_run_includes_pdf_attachment_from_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_dir = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "capture.md"
    attachment_path = raw_dir / "capture.pdf"
    raw_path.write_text("# capture\n", encoding="utf-8")
    attachment_path.write_bytes(b"%PDF-1.4\n%%EOF")

    class FakeDb:
        def execute(self, query, params=()):
            class Rows:
                def fetchall(self):
                    return [
                        {
                            "raw_path": str(raw_path),
                            "metadata_json": json.dumps({"attachment_filename": "capture.pdf"}),
                        }
                    ]

            return Rows()

    paths = crawl._raw_paths_for_fetch_run(repo_root, FakeDb(), fetch_run_id=1)

    assert paths == [
        "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md",
        "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.pdf",
    ]


def test_verify_manifest_accepts_pdf_attachment_raw_path_without_utf8_frontmatter(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_dir = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "capture.md"
    attachment_path = raw_dir / "capture.pdf"
    attachment_bytes = b"%PDF-1.4\n\xb5\n%%EOF"
    raw_path.write_text(
        f"""---
source_id: source-a
title: PDF capture
canonical_url: https://example.com/report.pdf
captured_at: '2026-06-27T00:00:00+00:00'
content_hash: abc
attachment_filename: capture.pdf
attachment_sha256: {hashlib.sha256(attachment_bytes).hexdigest()}
attachment_content_type: application/pdf
---
# PDF capture
""",
        encoding="utf-8",
    )
    attachment_path.write_bytes(attachment_bytes)
    manifest = full_manifest(repo_root, raw_path)
    attachment_relative_path = str(attachment_path.relative_to(repo_root))
    manifest["succeeded"][0]["raw_paths"].append(attachment_relative_path)
    manifest["raw_paths"].append(attachment_relative_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is True
    assert message == "manifest verified"


def test_verify_manifest_rejects_pdf_attachment_sha_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_dir = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "capture.md"
    attachment_path = raw_dir / "capture.pdf"
    raw_path.write_text(
        """---
source_id: source-a
title: PDF capture
canonical_url: https://example.com/report.pdf
captured_at: '2026-06-27T00:00:00+00:00'
content_hash: abc
attachment_filename: capture.pdf
attachment_sha256: deadbeef
attachment_content_type: application/pdf
---
# PDF capture
""",
        encoding="utf-8",
    )
    attachment_path.write_bytes(b"%PDF-1.4\nchanged\n%%EOF")
    manifest = full_manifest(repo_root, raw_path)
    attachment_relative_path = str(attachment_path.relative_to(repo_root))
    manifest["succeeded"][0]["raw_paths"].append(attachment_relative_path)
    manifest["raw_paths"].append(attachment_relative_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "attachment sha256 mismatch" in message


def full_manifest(repo_root: Path, raw_path: Path) -> dict[str, object]:
    raw_relative_path = str(raw_path.relative_to(repo_root))
    return {
        "task_id": crawl.TASK_ID,
        "generated_at": "2026-06-27T00:00:00+00:00",
        "repo_root": str(repo_root),
        "sources_yaml": str(repo_root / ".codex/state/sources.yaml"),
        "ran_source_ids": ["source-a"],
        "succeeded": [{"source_id": "source-a", "raw_paths": [raw_relative_path]}],
        "failed": [{"source_id": "source-b", "error": "fetch failed"}],
        "skipped_disabled": [{"source_id": "source-c", "reason": "disabled"}],
        "raw_paths": [raw_relative_path],
        "ingest_tasks": [{"id": 1, "source_id": "source-a", "status": "pending"}],
        "summary": {
            "selected_count": 1,
            "attempted_count": 1,
            "succeeded_count": 1,
            "failed_count": 1,
            "skipped_disabled_count": 1,
        },
    }
