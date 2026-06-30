import gzip
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import github_closed_issues_corpus as corpus


def test_slug_for_repo_normalizes_owner_and_name() -> None:
    assert corpus.slug_for_repo("Kubernetes/Kubernetes") == "kubernetes-kubernetes-closed-issues"
    assert corpus.slug_for_repo("kubernetes-sigs/kueue") == "kubernetes-sigs-kueue-closed-issues"


def test_parse_next_link_extracts_next_url() -> None:
    header = '<https://api.github.com/repos/o/r/issues?page=2>; rel="next", <https://api.github.com/repos/o/r/issues?page=9>; rel="last"'
    assert corpus.parse_next_link(header) == "https://api.github.com/repos/o/r/issues?page=2"


def test_filter_closed_issues_excludes_pull_requests() -> None:
    payload = [
        {"number": 1, "title": "issue", "state": "closed", "html_url": "https://github.com/o/r/issues/1"},
        {"number": 2, "title": "pr", "state": "closed", "pull_request": {}, "html_url": "https://github.com/o/r/pull/2"},
    ]

    assert [item["number"] for item in corpus.filter_issue_items(payload)] == [1]


def test_summarize_repo_counts_state_reasons_labels_and_comments() -> None:
    issues = [
        {
            "number": 1,
            "state_reason": "completed",
            "labels": [{"name": "kind/bug"}],
            "comments": 2,
            "closed_at": "2026-01-02T00:00:00Z",
        },
        {
            "number": 2,
            "state_reason": "not_planned",
            "labels": [{"name": "triage/accepted"}],
            "comments": 0,
            "closed_at": "2026-01-03T00:00:00Z",
        },
    ]
    comments = {1: [{"id": 10}, {"id": 11}], 2: []}

    summary = corpus.summarize_repo(
        "kubernetes/kubernetes",
        issues,
        comments,
        pages=3,
        comments_pages=1,
        partial=False,
        partial_reasons=[],
    )

    assert summary["repo"] == "kubernetes/kubernetes"
    assert summary["issue_count"] == 2
    assert summary["comment_count"] == 2
    assert summary["state_reasons"] == {"completed": 1, "not_planned": 1}
    assert summary["top_labels"][0] == {"name": "kind/bug", "count": 1}
    assert summary["closed_at_min"] == "2026-01-02T00:00:00Z"
    assert summary["closed_at_max"] == "2026-01-03T00:00:00Z"
    assert summary["partial_reasons"] == []


def test_summarize_repo_records_partial_reasons() -> None:
    summary = corpus.summarize_repo(
        "kubernetes-sigs/kueue",
        [{"number": 1, "state_reason": "completed", "closed_at": "2026-01-02T00:00:00Z"}],
        {},
        pages=1,
        comments_pages=0,
        partial=True,
        partial_reasons=["max_pages=1", "max_comment_issues=0"],
    )

    assert summary["partial"] is True
    assert summary["partial_reasons"] == ["max_pages=1", "max_comment_issues=0"]


def test_corpus_paths_use_closed_issue_file_names(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    paths = corpus.corpus_paths(raw_dir, "kubernetes-kubernetes-closed-issues")

    assert paths["issue_pages"].name == "kubernetes-kubernetes-closed-issues-api-pages.json.gz"
    assert paths["comments_pages"].name == "kubernetes-kubernetes-issue-comments-api-pages.json.gz"
    assert paths["joined"].name == "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    assert paths["summary"].name == "kubernetes-kubernetes-closed-issues-summary.json"
    assert paths["index"].name == "kubernetes-kubernetes-closed-issues-index.json"
    assert paths["ingest_plan"].name == "kubernetes-kubernetes-closed-issues.ingest-plan.md"


def test_ingest_plan_uses_closed_issue_file_names() -> None:
    plan = corpus.ingest_plan(
        "kubernetes/kubernetes",
        "kubernetes-kubernetes-closed-issues",
        "ai_infra",
        {"issue_count": 1, "comment_count": 0, "partial": True},
    )

    assert "kubernetes-kubernetes-closed-issues-with-comments.json.gz" in plan
    assert "kubernetes-kubernetes-closed-issues-summary.json" in plan


def test_capture_repo_writes_closed_issue_contract_files(tmp_path: Path, monkeypatch) -> None:
    def fake_fetch_paginated(url, params, max_pages):
        if url.endswith("/issues"):
            return (
                [
                    [
                        {
                            "number": 7,
                            "title": "closed scheduler issue",
                            "state": "closed",
                            "state_reason": "completed",
                            "html_url": "https://github.com/kubernetes/kubernetes/issues/7",
                            "closed_at": "2026-01-02T00:00:00Z",
                            "labels": [{"name": "kind/bug"}],
                        }
                    ]
                ],
                [{"limit": "60", "remaining": "59", "reset": "0"}],
                False,
            )
        if url.endswith("/issues/7/comments"):
            return (
                [[{"id": 70, "body": "fixed"}]],
                [{"limit": "60", "remaining": "58", "reset": "0"}],
                False,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(corpus, "fetch_paginated", fake_fetch_paginated)

    manifest_entry = corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
        max_pages=None,
        max_comment_issues=None,
        include_comments=True,
    )

    raw_dir = tmp_path / "personal-wiki/domains/ai_infra/raw/github/kubernetes-kubernetes-closed-issues"
    expected_names = {
        "kubernetes-kubernetes-closed-issues-api-pages.json.gz",
        "kubernetes-kubernetes-issue-comments-api-pages.json.gz",
        "kubernetes-kubernetes-closed-issues-with-comments.json.gz",
        "kubernetes-kubernetes-closed-issues-summary.json",
        "kubernetes-kubernetes-closed-issues-index.json",
        "kubernetes-kubernetes-closed-issues.ingest-plan.md",
    }

    assert {path.name for path in raw_dir.iterdir()} == expected_names
    index = json.loads((raw_dir / "kubernetes-kubernetes-closed-issues-index.json").read_text(encoding="utf-8"))
    assert index["source"] == "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    assert manifest_entry["issue_count"] == 1
    assert manifest_entry["comment_count"] == 1
    assert manifest_entry["partial_reasons"] == []


def test_capture_repo_marks_comment_issue_limit_partial(tmp_path: Path, monkeypatch) -> None:
    def fake_fetch_paginated(url, params, max_pages):
        if url.endswith("/issues"):
            return (
                [
                    [
                        {"number": 1, "state_reason": "completed", "html_url": "https://github.com/o/r/issues/1"},
                        {"number": 2, "state_reason": "completed", "html_url": "https://github.com/o/r/issues/2"},
                    ]
                ],
                [{"limit": "60", "remaining": "59", "reset": "0"}],
                False,
            )
        if url.endswith("/issues/1/comments"):
            return ([[]], [{"limit": "60", "remaining": "58", "reset": "0"}], False)
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(corpus, "fetch_paginated", fake_fetch_paginated)

    manifest_entry = corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
        max_pages=None,
        max_comment_issues=1,
        include_comments=True,
    )

    assert manifest_entry["partial"] is True
    assert manifest_entry["partial_reasons"] == ["max_comment_issues=1"]


def test_verify_manifest_rejects_missing_raw_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": corpus.TASK_ID,
                "generated_at": "2026-07-01T00:00:00+00:00",
                "domain": "ai_infra",
                "repos": [
                    {
                        "repo": "kubernetes/kubernetes",
                        "raw_paths": ["personal-wiki/domains/ai_infra/raw/github/missing.json.gz"],
                        "summary_path": "personal-wiki/domains/ai_infra/raw/github/missing-summary.json",
                        "issue_count": 1,
                        "comment_count": 0,
                        "partial": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is False
    assert "missing raw path" in message


def test_verify_manifest_rejects_invalid_gzip_json(tmp_path: Path) -> None:
    raw_path = tmp_path / "personal-wiki/domains/ai_infra/raw/github/repo/repo.json.gz"
    summary_path = tmp_path / "personal-wiki/domains/ai_infra/raw/github/repo/repo-summary.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(b"not gzip json")
    summary_path.write_text(json.dumps({"issue_count": 1}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": corpus.TASK_ID,
                "generated_at": "2026-07-01T00:00:00+00:00",
                "domain": "ai_infra",
                "repos": [
                    {
                        "repo": "kubernetes/kubernetes",
                        "raw_paths": [str(raw_path.relative_to(tmp_path)), str(summary_path.relative_to(tmp_path))],
                        "summary_path": str(summary_path.relative_to(tmp_path)),
                        "issue_count": 1,
                        "comment_count": 0,
                        "partial": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is False
    assert "invalid gzip JSON raw path" in message


def test_verify_manifest_accepts_existing_raw_and_summary(tmp_path: Path) -> None:
    raw_path = tmp_path / "personal-wiki/domains/ai_infra/raw/github/repo/repo.json.gz"
    summary_path = tmp_path / "personal-wiki/domains/ai_infra/raw/github/repo/repo-summary.json"
    raw_path.parent.mkdir(parents=True)
    with gzip.open(raw_path, "wt", encoding="utf-8") as handle:
        json.dump([{"number": 1}], handle)
    summary_path.write_text(json.dumps({"issue_count": 1}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": corpus.TASK_ID,
                "generated_at": "2026-07-01T00:00:00+00:00",
                "domain": "ai_infra",
                "repos": [
                    {
                        "repo": "kubernetes/kubernetes",
                        "raw_paths": [str(raw_path.relative_to(tmp_path))],
                        "summary_path": str(summary_path.relative_to(tmp_path)),
                        "issue_count": 1,
                        "comment_count": 0,
                        "partial": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is True
    assert message == "manifest verified"


def test_verify_manifest_rejects_joined_corpus_with_pull_request(tmp_path: Path) -> None:
    raw_dir = tmp_path / "personal-wiki/domains/ai_infra/raw/github/kubernetes-kubernetes-closed-issues"
    raw_dir.mkdir(parents=True)
    joined_path = raw_dir / "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    index_path = raw_dir / "kubernetes-kubernetes-closed-issues-index.json"
    summary_path = raw_dir / "kubernetes-kubernetes-closed-issues-summary.json"
    with gzip.open(joined_path, "wt", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "issue": {
                        "number": 1,
                        "state": "closed",
                        "html_url": "https://github.com/kubernetes/kubernetes/pull/1",
                        "pull_request": {},
                    },
                    "comments": [],
                }
            ],
            handle,
        )
    index_path.write_text(json.dumps({"issues": [{"number": 1}]}), encoding="utf-8")
    summary_path.write_text(json.dumps({"issue_count": 1, "comment_count": 0}), encoding="utf-8")
    manifest_path = _write_manifest(tmp_path, joined_path, index_path, summary_path, issue_count=1, comment_count=0)

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is False
    assert "contains pull request item" in message


def test_verify_manifest_rejects_joined_corpus_with_open_issue(tmp_path: Path) -> None:
    raw_dir = tmp_path / "personal-wiki/domains/ai_infra/raw/github/kubernetes-kubernetes-closed-issues"
    raw_dir.mkdir(parents=True)
    joined_path = raw_dir / "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    index_path = raw_dir / "kubernetes-kubernetes-closed-issues-index.json"
    summary_path = raw_dir / "kubernetes-kubernetes-closed-issues-summary.json"
    with gzip.open(joined_path, "wt", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "issue": {
                        "number": 1,
                        "state": "open",
                        "html_url": "https://github.com/kubernetes/kubernetes/issues/1",
                    },
                    "comments": [],
                }
            ],
            handle,
        )
    index_path.write_text(json.dumps({"issues": [{"number": 1}]}), encoding="utf-8")
    summary_path.write_text(json.dumps({"issue_count": 1, "comment_count": 0}), encoding="utf-8")
    manifest_path = _write_manifest(tmp_path, joined_path, index_path, summary_path, issue_count=1, comment_count=0)

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is False
    assert "contains non-closed issue" in message


def test_verify_manifest_rejects_summary_index_joined_count_mismatch(tmp_path: Path) -> None:
    raw_dir = tmp_path / "personal-wiki/domains/ai_infra/raw/github/kubernetes-kubernetes-closed-issues"
    raw_dir.mkdir(parents=True)
    joined_path = raw_dir / "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    index_path = raw_dir / "kubernetes-kubernetes-closed-issues-index.json"
    summary_path = raw_dir / "kubernetes-kubernetes-closed-issues-summary.json"
    with gzip.open(joined_path, "wt", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "issue": {
                        "number": 1,
                        "state": "closed",
                        "html_url": "https://github.com/kubernetes/kubernetes/issues/1",
                    },
                    "comments": [],
                }
            ],
            handle,
        )
    index_path.write_text(json.dumps({"issues": [{"number": 1}, {"number": 2}]}), encoding="utf-8")
    summary_path.write_text(json.dumps({"issue_count": 1, "comment_count": 0}), encoding="utf-8")
    manifest_path = _write_manifest(tmp_path, joined_path, index_path, summary_path, issue_count=1, comment_count=0)

    ok, message = corpus.verify_manifest(tmp_path, manifest_path, min_repos=1)

    assert ok is False
    assert "index issue count mismatch" in message


def _write_manifest(
    repo_root: Path,
    joined_path: Path,
    index_path: Path,
    summary_path: Path,
    *,
    issue_count: int,
    comment_count: int,
) -> Path:
    manifest_path = repo_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": corpus.TASK_ID,
                "generated_at": "2026-07-01T00:00:00+00:00",
                "domain": "ai_infra",
                "repos": [
                    {
                        "repo": "kubernetes/kubernetes",
                        "raw_paths": [
                            str(joined_path.relative_to(repo_root)),
                            str(index_path.relative_to(repo_root)),
                            str(summary_path.relative_to(repo_root)),
                        ],
                        "summary_path": str(summary_path.relative_to(repo_root)),
                        "issue_count": issue_count,
                        "comment_count": comment_count,
                        "partial": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path
