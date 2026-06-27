import json
from pathlib import Path
import sys


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
    manifest_path.write_text(
        json.dumps(
            {
                "summary": {"succeeded_count": 1},
                "succeeded": [
                    {
                        "source_id": "source-a",
                        "raw_paths": [
                            "personal-wiki/domains/ai_infra/raw/crawler/source-a/missing.md"
                        ],
                    }
                ],
                "failed": [],
                "skipped_disabled": [],
            }
        ),
        encoding="utf-8",
    )

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is False
    assert "missing raw path" in message


def test_verify_manifest_passes_for_minimal_valid_manifest_and_raw_file(tmp_path: Path) -> None:
    repo_root = tmp_path
    raw_path = repo_root / "personal-wiki/domains/ai_infra/raw/crawler/source-a/capture.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# raw\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "summary": {"succeeded_count": 1},
                "succeeded": [
                    {"source_id": "source-a", "raw_paths": [str(raw_path.relative_to(repo_root))]}
                ],
                "failed": [{"source_id": "source-b", "error": "fetch failed"}],
                "skipped_disabled": [{"source_id": "source-c", "reason": "disabled"}],
            }
        ),
        encoding="utf-8",
    )

    ok, message = crawl.verify_manifest(repo_root, manifest_path, min_succeeded=1)

    assert ok is True
    assert message == "manifest verified"
