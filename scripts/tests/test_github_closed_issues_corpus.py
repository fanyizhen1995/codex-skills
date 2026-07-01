import gzip
from http.client import IncompleteRead
import json
from pathlib import Path
import sys
from urllib.error import URLError


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import github_closed_issues_corpus as corpus


def test_slug_for_repo_normalizes_owner_and_name() -> None:
    assert corpus.slug_for_repo("Kubernetes/Kubernetes") == "kubernetes-kubernetes-closed-issues"
    assert corpus.slug_for_repo("kubernetes-sigs/kueue") == "kubernetes-sigs-kueue-closed-issues"


def test_parse_repo_closed_since_normalizes_repo_keys_and_dates() -> None:
    mapping = corpus.parse_repo_closed_since(["Kubernetes/Kubernetes=2023-07-01"])

    assert mapping == {"kubernetes/kubernetes": "2023-07-01T00:00:00+00:00"}


def test_parse_rate_limit_policy_rejects_unknown_values() -> None:
    assert corpus.parse_rate_limit_policy("wait") == "wait"
    try:
        corpus.parse_rate_limit_policy("retry")
    except ValueError as exc:
        assert "invalid rate-limit policy" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_comment_fetch_mode_rejects_unknown_values() -> None:
    assert corpus.parse_comment_fetch_mode("repository") == "repository"
    try:
        corpus.parse_comment_fetch_mode("all")
    except ValueError as exc:
        assert "invalid comment fetch mode" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_issue_discovery_mode_rejects_unknown_values() -> None:
    assert corpus.parse_issue_discovery_mode("search-monthly") == "search-monthly"
    try:
        corpus.parse_issue_discovery_mode("graphql")
    except ValueError as exc:
        assert "invalid issue discovery mode" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_extract_comment_issue_number_reads_issue_url() -> None:
    comment = {"issue_url": "https://api.github.com/repos/kubernetes/kubernetes/issues/123"}

    assert corpus.extract_comment_issue_number(comment) == 123


def test_transient_github_read_errors_are_retryable() -> None:
    assert corpus.is_retryable_github_error(IncompleteRead(b"partial", 10)) is True
    assert corpus.is_retryable_github_error(URLError("timed out")) is True
    assert corpus.is_retryable_github_error(ValueError("bad payload")) is False


def test_retry_delay_caps_attempts(monkeypatch) -> None:
    sleeps = []
    monkeypatch.setattr(corpus.time, "sleep", lambda seconds: sleeps.append(seconds))

    corpus.sleep_before_retry(3)

    assert sleeps == [8]


def test_month_ranges_cover_closed_since_to_now(monkeypatch) -> None:
    class FixedDateTime(corpus.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2023, 9, 15, tzinfo=tz)

    monkeypatch.setattr(corpus, "datetime", FixedDateTime)

    assert corpus.month_ranges("2023-07-01") == [
        ("2023-07-01", "2023-07-31"),
        ("2023-08-01", "2023-08-31"),
        ("2023-09-01", "2023-09-15"),
    ]


def test_parse_next_link_extracts_next_url() -> None:
    header = '<https://api.github.com/repos/o/r/issues?page=2>; rel="next", <https://api.github.com/repos/o/r/issues?page=9>; rel="last"'
    assert corpus.parse_next_link(header) == "https://api.github.com/repos/o/r/issues?page=2"


def test_filter_closed_issues_excludes_pull_requests() -> None:
    payload = [
        {"number": 1, "title": "issue", "state": "closed", "html_url": "https://github.com/o/r/issues/1"},
        {"number": 2, "title": "pr", "state": "closed", "pull_request": {}, "html_url": "https://github.com/o/r/pull/2"},
    ]

    assert [item["number"] for item in corpus.filter_issue_items(payload)] == [1]


def test_filter_issue_items_applies_closed_since_window() -> None:
    payload = [
        {
            "number": 1,
            "title": "old issue",
            "state": "closed",
            "closed_at": "2023-06-30T23:59:59Z",
            "html_url": "https://github.com/o/r/issues/1",
        },
        {
            "number": 2,
            "title": "window issue",
            "state": "closed",
            "closed_at": "2023-07-01T00:00:00Z",
            "html_url": "https://github.com/o/r/issues/2",
        },
        {
            "number": 3,
            "title": "pr",
            "state": "closed",
            "closed_at": "2024-01-01T00:00:00Z",
            "pull_request": {},
            "html_url": "https://github.com/o/r/pull/3",
        },
    ]

    issues = corpus.filter_issue_items(payload, closed_since="2023-07-01")

    assert [item["number"] for item in issues] == [2]


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


def test_summarize_repo_records_closed_window() -> None:
    summary = corpus.summarize_repo(
        "kubernetes/kubernetes",
        [{"number": 1, "state_reason": "completed", "closed_at": "2026-01-02T00:00:00Z"}],
        {},
        pages=1,
        comments_pages=0,
        partial=False,
        partial_reasons=[],
        closed_since="2023-07-01",
    )

    assert summary["closed_since"] == "2023-07-01T00:00:00+00:00"


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


def test_run_capture_applies_repo_specific_closed_since(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_capture_repo(
        repo_root,
        repo,
        domain,
        max_pages,
        max_comment_issues,
        max_comment_pages,
        include_comments,
        closed_since=None,
        rate_limit_policy="partial",
        comment_fetch_mode="auto",
        issue_discovery_mode="issues",
        verbose=False,
    ):
        calls.append((repo, max_comment_pages, closed_since, rate_limit_policy, comment_fetch_mode, issue_discovery_mode))
        return {
            "repo": repo,
            "slug": corpus.slug_for_repo(repo),
            "raw_paths": ["placeholder"],
            "summary_path": "placeholder-summary.json",
            "issue_count": 1,
            "comment_count": 0,
            "partial": False,
            "partial_reasons": [],
            "rate_limits": [],
        }

    monkeypatch.setattr(corpus, "capture_repo", fake_capture_repo)
    monkeypatch.setattr(corpus, "verify_manifest", lambda repo_root, manifest_path, min_repos: (True, "ok"))

    corpus.run_capture(
        repo_root=tmp_path,
        output_dir=tmp_path / "out",
        repos=["kubernetes/kubernetes", "volcano-sh/volcano"],
        domain="ai_infra",
        max_comment_pages=2,
        repo_closed_since={"kubernetes/kubernetes": "2023-07-01T00:00:00+00:00"},
        rate_limit_policy="wait",
        comment_fetch_mode="repository",
        issue_discovery_mode="search-monthly",
    )

    assert calls == [
        ("kubernetes/kubernetes", 2, "2023-07-01T00:00:00+00:00", "wait", "repository", "search-monthly"),
        ("volcano-sh/volcano", 2, None, "wait", "repository", "search-monthly"),
    ]


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
    def fake_fetch_paginated(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
        if url.endswith("/issues"):
            return (
                [
                    [
                        {
                            "number": 6,
                            "title": "old scheduler issue",
                            "state": "closed",
                            "state_reason": "completed",
                            "html_url": "https://github.com/kubernetes/kubernetes/issues/6",
                            "closed_at": "2023-06-30T00:00:00Z",
                            "labels": [{"name": "kind/bug"}],
                        },
                        {
                            "number": 7,
                            "title": "closed scheduler issue",
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 1,
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
            max_comment_pages=None,
            include_comments=True,
        closed_since="2023-07-01",
        comment_fetch_mode="per-issue",
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
    assert manifest_entry["closed_since"] == "2023-07-01T00:00:00+00:00"


def test_capture_repo_marks_comment_issue_limit_partial(tmp_path: Path, monkeypatch) -> None:
    def fake_fetch_paginated(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
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
            max_comment_pages=None,
            include_comments=True,
        closed_since=None,
        comment_fetch_mode="per-issue",
    )

    assert manifest_entry["partial"] is True
    assert manifest_entry["partial_reasons"] == ["max_comment_issues=1"]


def test_capture_repo_skips_comment_endpoint_when_issue_has_no_comments(tmp_path: Path, monkeypatch) -> None:
    requested_urls = []

    def fake_fetch_paginated(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
        requested_urls.append(url)
        if url.endswith("/issues"):
            return (
                [
                    [
                        {
                            "number": 1,
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 0,
                            "html_url": "https://github.com/o/r/issues/1",
                        },
                        {
                            "number": 2,
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 1,
                            "html_url": "https://github.com/o/r/issues/2",
                        },
                    ]
                ],
                [{"limit": "5000", "remaining": "4999", "reset": "0"}],
                False,
            )
        if url.endswith("/issues/2/comments"):
            return ([[{"id": 20, "body": "fixed"}]], [{"limit": "5000", "remaining": "4998", "reset": "0"}], False)
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(corpus, "fetch_paginated", fake_fetch_paginated)

    manifest_entry = corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
            max_pages=None,
            max_comment_issues=None,
            max_comment_pages=None,
            include_comments=True,
        comment_fetch_mode="per-issue",
    )

    assert manifest_entry["issue_count"] == 2
    assert manifest_entry["comment_count"] == 1
    assert requested_urls == [
        "https://api.github.com/repos/kubernetes/kubernetes/issues",
        "https://api.github.com/repos/kubernetes/kubernetes/issues/2/comments",
    ]


def test_capture_repo_joins_repository_comment_pages_by_issue_number(tmp_path: Path, monkeypatch) -> None:
    requested_urls = []

    def fake_fetch_paginated(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
        requested_urls.append(url)
        if url.endswith("/issues"):
            return (
                [
                    [
                        {
                            "number": 1,
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 1,
                            "html_url": "https://github.com/o/r/issues/1",
                        },
                        {
                            "number": 2,
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 1,
                            "html_url": "https://github.com/o/r/issues/2",
                        },
                    ]
                ],
                [{"limit": "5000", "remaining": "4999", "reset": "0"}],
                False,
            )
        if url.endswith("/issues/comments"):
            return (
                [
                    [
                        {"id": 10, "issue_url": "https://api.github.com/repos/o/r/issues/1", "body": "fixed"},
                        {"id": 20, "issue_url": "https://api.github.com/repos/o/r/issues/2", "body": "also fixed"},
                        {"id": 990, "issue_url": "https://api.github.com/repos/o/r/issues/99", "body": "ignored"},
                    ]
                ],
                [{"limit": "5000", "remaining": "4998", "reset": "0"}],
                max_pages == 1,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(corpus, "fetch_paginated", fake_fetch_paginated)

    manifest_entry = corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
        max_pages=None,
        max_comment_issues=None,
        max_comment_pages=1,
        include_comments=True,
        comment_fetch_mode="repository",
    )

    raw_dir = tmp_path / "personal-wiki/domains/ai_infra/raw/github/kubernetes-kubernetes-closed-issues"
    joined_path = raw_dir / "kubernetes-kubernetes-closed-issues-with-comments.json.gz"
    with gzip.open(joined_path, "rt", encoding="utf-8") as handle:
        joined = json.load(handle)

    assert manifest_entry["comment_count"] == 2
    assert [len(item["comments"]) for item in joined] == [1, 1]
    assert requested_urls == [
        "https://api.github.com/repos/kubernetes/kubernetes/issues",
        "https://api.github.com/repos/kubernetes/kubernetes/issues/comments",
    ]
    assert manifest_entry["partial"] is True
    assert manifest_entry["partial_reasons"] == ["max_comment_pages=1"]


def test_capture_repo_uses_closed_since_for_repository_comment_window(tmp_path: Path, monkeypatch) -> None:
    comment_params = []

    def fake_fetch_paginated(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
        if url.endswith("/issues"):
            return (
                [
                    [
                        {
                            "number": 1,
                            "state": "closed",
                            "state_reason": "completed",
                            "comments": 1,
                            "closed_at": "2024-01-02T00:00:00Z",
                            "html_url": "https://github.com/o/r/issues/1",
                        }
                    ]
                ],
                [{"limit": "5000", "remaining": "4999", "reset": "0"}],
                False,
            )
        if url.endswith("/issues/comments"):
            comment_params.append(params)
            return (
                [[{"id": 10, "issue_url": "https://api.github.com/repos/o/r/issues/1", "body": "fixed"}]],
                [{"limit": "5000", "remaining": "4998", "reset": "0"}],
                False,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(corpus, "fetch_paginated", fake_fetch_paginated)

    corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
        max_pages=None,
        max_comment_issues=None,
        max_comment_pages=None,
        include_comments=True,
        closed_since="2023-07-01",
        comment_fetch_mode="repository",
    )

    assert comment_params == [
        {
            "sort": "updated",
            "direction": "asc",
            "since": "2023-07-01T00:00:00Z",
            "per_page": "100",
        }
    ]


def test_capture_repo_can_discover_issues_with_monthly_search(tmp_path: Path, monkeypatch) -> None:
    requested = []

    def fake_month_ranges(closed_since):
        return [("2023-07-01", "2023-07-31")]

    def fake_fetch_search(url, params, max_pages, rate_limit_policy="partial", progress_label=None):
        requested.append((url, params))
        return (
            [
                [
                    {
                        "number": 1,
                        "state": "closed",
                        "state_reason": "completed",
                        "comments": 0,
                        "closed_at": "2023-07-15T00:00:00Z",
                        "html_url": "https://github.com/kubernetes/kubernetes/issues/1",
                    }
                ]
            ],
            [{"limit": "30", "remaining": "29", "reset": "0"}],
            False,
        )

    monkeypatch.setattr(corpus, "month_ranges", fake_month_ranges)
    monkeypatch.setattr(corpus, "fetch_search_issue_pages", fake_fetch_search)

    manifest_entry = corpus.capture_repo(
        repo_root=tmp_path,
        repo="kubernetes/kubernetes",
        domain="ai_infra",
        max_pages=None,
        max_comment_issues=None,
        max_comment_pages=None,
        include_comments=False,
        closed_since="2023-07-01",
        issue_discovery_mode="search-monthly",
    )

    assert manifest_entry["issue_count"] == 1
    assert requested == [
        (
            "https://api.github.com/search/issues",
            {
                "q": "repo:kubernetes/kubernetes is:issue is:closed closed:2023-07-01..2023-07-31",
                "sort": "updated",
                "order": "desc",
                "per_page": "100",
            },
        )
    ]


def test_fetch_search_issue_pages_extracts_items_from_search_payload(monkeypatch) -> None:
    def fake_github_get_json(url):
        return (
            {
                "total_count": 1,
                "incomplete_results": False,
                "items": [{"number": 1, "state": "closed"}],
            },
            {"x-ratelimit-limit": "30", "x-ratelimit-remaining": "29", "x-ratelimit-reset": "0"},
        )

    monkeypatch.setattr(corpus, "github_get_json", fake_github_get_json)

    pages, rate_limits, partial = corpus.fetch_search_issue_pages(
        "https://api.github.com/search/issues",
        {"q": "repo:o/r is:issue is:closed closed:2023-07-01..2023-07-31", "per_page": "100"},
        max_pages=None,
    )

    assert pages == [[{"number": 1, "state": "closed"}]]
    assert rate_limits == [{"limit": "30", "remaining": "29", "reset": "0"}]
    assert partial is False


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
