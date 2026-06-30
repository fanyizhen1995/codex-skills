#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TASK_ID = "github-closed-issues-k8s-volcano-kueue-01"
API_ROOT = "https://api.github.com"
RAW_ROOT = Path("personal-wiki/domains/ai_infra/raw/github")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture closed GitHub issue corpora into personal-wiki raw evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repo-root", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--repo", action="append", required=True)
    run_parser.add_argument("--domain", default="ai_infra")
    run_parser.add_argument("--max-pages", type=int, default=0)
    run_parser.add_argument("--max-comment-issues", type=int, default=0)
    run_parser.add_argument("--include-comments", action="store_true", default=True)
    run_parser.add_argument("--no-comments", action="store_true")

    verify_parser = subparsers.add_parser("verify-manifest")
    verify_parser.add_argument("--repo-root", required=True)
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--min-repos", type=int, default=1)

    args = parser.parse_args(argv)
    if args.command == "run":
        manifest = run_capture(
            repo_root=Path(args.repo_root).resolve(),
            output_dir=Path(args.output_dir).resolve(),
            repos=args.repo,
            domain=args.domain,
            max_pages=args.max_pages or None,
            max_comment_issues=args.max_comment_issues or None,
            include_comments=not args.no_comments,
        )
        print(json.dumps({"manifest": str(Path(args.output_dir) / "manifest.json"), "repos": len(manifest["repos"])}))
        return 0

    ok, message = verify_manifest(Path(args.repo_root).resolve(), Path(args.manifest), min_repos=args.min_repos)
    if ok:
        print(message)
        return 0
    print(message, file=sys.stderr)
    return 1


def slug_for_repo(repo: str) -> str:
    normalized = repo.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", normalized):
        raise ValueError(f"invalid GitHub repository slug: {repo}")
    return normalized.replace("/", "-") + "-closed-issues"


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        match = re.match(r"<([^>]+)>", section)
        if match:
            return match.group(1)
    return None


def filter_issue_items(items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if not item.get("pull_request") and "/pull/" not in str(item.get("html_url", ""))]


def summarize_repo(
    repo: str,
    issues: Sequence[dict[str, Any]],
    comments_by_issue: dict[int, list[dict[str, Any]]],
    pages: int,
    comments_pages: int,
    partial: bool,
    partial_reasons: Sequence[str],
) -> dict[str, Any]:
    label_counts: Counter[str] = Counter()
    state_reasons: Counter[str] = Counter()
    closed_at_values: list[str] = []
    for issue in issues:
        state_reason = str(issue.get("state_reason") or "unknown")
        state_reasons[state_reason] += 1
        closed_at = issue.get("closed_at")
        if isinstance(closed_at, str) and closed_at:
            closed_at_values.append(closed_at)
        labels = issue.get("labels")
        if isinstance(labels, list):
            for label in labels:
                if isinstance(label, dict) and label.get("name"):
                    label_counts[str(label["name"])] += 1
                elif label:
                    label_counts[str(label)] += 1
    comment_count = sum(len(comments) for comments in comments_by_issue.values())
    return {
        "repo": repo,
        "issue_count": len(issues),
        "comment_count": comment_count,
        "pages": pages,
        "comments_pages": comments_pages,
        "partial": partial,
        "partial_reasons": list(partial_reasons),
        "state_reasons": dict(sorted(state_reasons.items())),
        "top_labels": [{"name": name, "count": count} for name, count in label_counts.most_common(20)],
        "closed_at_min": min(closed_at_values) if closed_at_values else None,
        "closed_at_max": max(closed_at_values) if closed_at_values else None,
    }


def run_capture(
    repo_root: Path,
    output_dir: Path,
    repos: Sequence[str],
    domain: str,
    max_pages: int | None = None,
    max_comment_issues: int | None = None,
    include_comments: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "repos": [],
    }
    for repo in repos:
        manifest["repos"].append(
            capture_repo(
                repo_root=repo_root,
                repo=repo,
                domain=domain,
                max_pages=max_pages,
                max_comment_issues=max_comment_issues,
                include_comments=include_comments,
            )
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    ok, message = verify_manifest(repo_root, manifest_path, min_repos=len(repos))
    if not ok:
        raise ValueError(message)
    return manifest


def capture_repo(
    repo_root: Path,
    repo: str,
    domain: str,
    max_pages: int | None,
    max_comment_issues: int | None,
    include_comments: bool,
) -> dict[str, Any]:
    slug = slug_for_repo(repo)
    raw_dir = repo_root / RAW_ROOT / slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    issue_pages, rate_limits, partial = fetch_paginated(
        f"{API_ROOT}/repos/{repo}/issues",
        {"state": "closed", "sort": "updated", "direction": "desc", "per_page": "100"},
        max_pages=max_pages,
    )
    issues = filter_issue_items([item for page in issue_pages for item in page])
    partial_reasons: list[str] = []
    if partial:
        partial_reasons.append(f"max_pages={max_pages}" if max_pages is not None else "rate_limit_near_empty")

    comment_pages: list[dict[str, Any]] = []
    comments_by_issue: dict[int, list[dict[str, Any]]] = {}
    if include_comments:
        comment_issues = list(issues)
        if max_comment_issues is not None and len(comment_issues) > max_comment_issues:
            comment_issues = comment_issues[:max_comment_issues]
            partial = True
            partial_reasons.append(f"max_comment_issues={max_comment_issues}")
        for issue in comment_issues:
            number = int(issue.get("number") or 0)
            if number <= 0:
                continue
            pages, comment_rate_limits, comment_partial = fetch_paginated(
                f"{API_ROOT}/repos/{repo}/issues/{number}/comments",
                {"per_page": "100"},
                max_pages=None,
            )
            rate_limits.extend(comment_rate_limits)
            partial = partial or comment_partial
            if comment_partial:
                partial_reasons.append(f"comments_partial_issue={number}")
            comments = [comment for page in pages for comment in page]
            comments_by_issue[number] = comments
            if pages:
                comment_pages.append({"issue_number": number, "pages": pages})
    else:
        partial = True
        partial_reasons.append("comments_disabled")

    joined = []
    for issue in issues:
        number = int(issue.get("number") or 0)
        joined.append({"issue": issue, "comments": comments_by_issue.get(number, [])})

    summary = summarize_repo(
        repo,
        issues,
        comments_by_issue,
        pages=len(issue_pages),
        comments_pages=sum(len(item["pages"]) for item in comment_pages),
        partial=partial,
        partial_reasons=dedupe(partial_reasons),
    )
    paths = corpus_paths(raw_dir, slug)
    issue_pages_path = paths["issue_pages"]
    comments_pages_path = paths["comments_pages"]
    joined_path = paths["joined"]
    summary_path = paths["summary"]
    index_path = paths["index"]
    ingest_plan_path = paths["ingest_plan"]

    index = {
        "repo": repo,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": joined_path.name,
        "issues": [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "html_url": issue.get("html_url"),
                "state_reason": issue.get("state_reason"),
                "closed_at": issue.get("closed_at"),
                "labels": label_names(issue.get("labels")),
                "comment_count": len(comments_by_issue.get(int(issue.get("number") or 0), [])),
            }
            for issue in issues
        ],
    }

    write_json_gz(issue_pages_path, issue_pages)
    write_json_gz(comments_pages_path, comment_pages)
    write_json_gz(joined_path, joined)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    ingest_plan_path.write_text(ingest_plan(repo, slug, domain, summary), encoding="utf-8")

    raw_paths = [
        relative(repo_root, issue_pages_path),
        relative(repo_root, comments_pages_path),
        relative(repo_root, joined_path),
        relative(repo_root, summary_path),
        relative(repo_root, index_path),
        relative(repo_root, ingest_plan_path),
    ]
    return {
        "repo": repo,
        "slug": slug,
        "raw_paths": raw_paths,
        "summary_path": relative(repo_root, summary_path),
        "issue_count": summary["issue_count"],
        "comment_count": summary["comment_count"],
        "partial": partial,
        "partial_reasons": summary["partial_reasons"],
        "rate_limits": rate_limits[-10:],
    }


def corpus_paths(raw_dir: Path, slug: str) -> dict[str, Path]:
    repo_prefix = slug.removesuffix("-closed-issues")
    return {
        "issue_pages": raw_dir / f"{repo_prefix}-closed-issues-api-pages.json.gz",
        "comments_pages": raw_dir / f"{repo_prefix}-issue-comments-api-pages.json.gz",
        "joined": raw_dir / f"{repo_prefix}-closed-issues-with-comments.json.gz",
        "summary": raw_dir / f"{repo_prefix}-closed-issues-summary.json",
        "index": raw_dir / f"{repo_prefix}-closed-issues-index.json",
        "ingest_plan": raw_dir / f"{repo_prefix}-closed-issues.ingest-plan.md",
    }


def dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def fetch_paginated(
    url: str,
    params: dict[str, str],
    max_pages: int | None,
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]], bool]:
    pages: list[list[dict[str, Any]]] = []
    rate_limits: list[dict[str, Any]] = []
    next_url: str | None = f"{url}?{urlencode(params)}"
    page_count = 0
    partial = False
    while next_url:
        if max_pages is not None and page_count >= max_pages:
            partial = True
            break
        payload, headers = github_get_json(next_url)
        if not isinstance(payload, list):
            raise ValueError(f"GitHub API returned non-list payload for {next_url}")
        pages.append(payload)
        page_count += 1
        rate_limits.append(rate_limit_metadata(headers))
        next_url = parse_next_link(headers.get("link"))
        remaining = int(headers.get("x-ratelimit-remaining", "1"))
        if remaining <= 1 and next_url:
            partial = True
            break
    return pages, rate_limits, partial


def github_get_json(url: str) -> tuple[Any, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "personal-wiki-crawler",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload, {key.lower(): value for key, value in response.headers.items()}


def rate_limit_metadata(headers: dict[str, str]) -> dict[str, Any]:
    return {
        "limit": headers.get("x-ratelimit-limit"),
        "remaining": headers.get("x-ratelimit-remaining"),
        "reset": headers.get("x-ratelimit-reset"),
    }


def label_names(labels: object) -> list[str]:
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict) and label.get("name"):
            names.append(str(label["name"]))
        elif label:
            names.append(str(label))
    return names


def write_json_gz(path: Path, payload: Any) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def ingest_plan(repo: str, slug: str, domain: str, summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Ingest Plan",
            "",
            f"Source: GitHub closed issues for `{repo}`",
            f"Domain: `{domain}`",
            f"Joined corpus: `{slug}-with-comments.json.gz`",
            f"Summary: `{slug}-summary.json`",
            "",
            "## Proposed Wiki Updates",
            "",
            "- Update the project page for this repository.",
            "- Link the shared Kubernetes/Volcano/Kueue closed issue corpus reference page.",
            "- Preserve the raw corpus as the fact source; do not mirror individual issues into wiki pages.",
            "",
            "## Capture Summary",
            "",
            f"- Issues: {summary['issue_count']}",
            f"- Comments: {summary['comment_count']}",
            f"- Partial: {summary['partial']}",
            "",
        ]
    )


def verify_manifest(repo_root: Path, manifest_path: Path, min_repos: int) -> tuple[bool, str]:
    if not manifest_path.exists():
        return False, f"missing manifest: {manifest_path}"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"manifest is not valid JSON: {exc}"
    if not isinstance(manifest, dict):
        return False, "manifest must be a JSON object"
    repos = manifest.get("repos")
    if not isinstance(repos, list):
        return False, "manifest repos must be a list"
    if len(repos) < min_repos:
        return False, f"manifest has {len(repos)} repos, expected at least {min_repos}"
    for repo in repos:
        if not isinstance(repo, dict):
            return False, "repo manifest entry must be an object"
        raw_paths = repo.get("raw_paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            return False, f"repo {repo.get('repo')} has no raw paths"
        decoded_payloads: dict[str, Any] = {}
        for raw_path in raw_paths:
            path = repo_root / str(raw_path)
            if not path.exists():
                return False, f"missing raw path: {raw_path}"
            if path.suffix == ".gz" and path.stat().st_size == 0:
                return False, f"empty gzip raw path: {raw_path}"
            if path.suffix == ".gz":
                try:
                    with gzip.open(path, "rt", encoding="utf-8") as handle:
                        decoded_payloads[str(raw_path)] = json.load(handle)
                except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    return False, f"invalid gzip JSON raw path: {raw_path}: {exc}"
        summary_path = repo.get("summary_path")
        if not summary_path or not (repo_root / str(summary_path)).exists():
            return False, f"missing summary path: {summary_path}"
        try:
            summary_payload = json.loads((repo_root / str(summary_path)).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return False, f"invalid summary JSON path: {summary_path}: {exc}"
        if int(repo.get("issue_count") or 0) <= 0:
            return False, f"repo {repo.get('repo')} has no captured issues"
        ok, message = verify_repo_corpus(repo_root, repo, raw_paths, decoded_payloads, summary_payload)
        if not ok:
            return False, message
    return True, "manifest verified"


def verify_repo_corpus(
    repo_root: Path,
    repo: dict[str, Any],
    raw_paths: Sequence[object],
    decoded_payloads: dict[str, Any],
    summary_payload: Any,
) -> tuple[bool, str]:
    repo_name = str(repo.get("repo") or "unknown")
    if not isinstance(summary_payload, dict):
        return False, f"repo {repo_name} summary must be a JSON object"
    summary_issue_count = int(summary_payload.get("issue_count") or 0)
    summary_comment_count = int(summary_payload.get("comment_count") or 0)
    if int(repo.get("issue_count") or 0) != summary_issue_count:
        return False, f"repo {repo_name} manifest issue count mismatch with summary"
    if int(repo.get("comment_count") or 0) != summary_comment_count:
        return False, f"repo {repo_name} manifest comment count mismatch with summary"

    joined_path = find_raw_path(raw_paths, "-closed-issues-with-comments.json.gz")
    index_path = find_raw_path(raw_paths, "-closed-issues-index.json")
    if joined_path is None or index_path is None:
        return True, "corpus detail verification skipped for legacy manifest"

    joined_payload = decoded_payloads.get(joined_path)
    if not isinstance(joined_payload, list):
        return False, f"repo {repo_name} joined corpus must be a JSON list"

    for item in joined_payload:
        if not isinstance(item, dict):
            return False, f"repo {repo_name} joined corpus item must be an object"
        issue = item.get("issue")
        if not isinstance(issue, dict):
            return False, f"repo {repo_name} joined corpus item missing issue object"
        if issue.get("pull_request") or "/pull/" in str(issue.get("html_url", "")):
            return False, f"repo {repo_name} joined corpus contains pull request item"
        if issue.get("state") != "closed":
            return False, f"repo {repo_name} joined corpus contains non-closed issue"

    joined_comment_count = sum(
        len(item.get("comments") or [])
        for item in joined_payload
        if isinstance(item, dict) and isinstance(item.get("comments") or [], list)
    )
    if len(joined_payload) != summary_issue_count:
        return False, f"repo {repo_name} joined issue count mismatch with summary"
    if joined_comment_count != summary_comment_count:
        return False, f"repo {repo_name} joined comment count mismatch with summary"

    try:
        index_payload = json.loads((repo_root / index_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"invalid index JSON path: {index_path}: {exc}"
    index_issues = index_payload.get("issues") if isinstance(index_payload, dict) else None
    if not isinstance(index_issues, list):
        return False, f"repo {repo_name} index issues must be a list"
    if len(index_issues) != summary_issue_count:
        return False, f"repo {repo_name} index issue count mismatch with summary"

    return True, "repo corpus verified"


def find_raw_path(raw_paths: Sequence[object], suffix: str) -> str | None:
    for raw_path in raw_paths:
        value = str(raw_path)
        if value.endswith(suffix):
            return value
    return None


def relative(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


if __name__ == "__main__":
    raise SystemExit(main())
