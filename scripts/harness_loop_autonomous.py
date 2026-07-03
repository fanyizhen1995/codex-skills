import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

try:
    from scripts.harness_loop_contracts import read_json_file, validate_loop_state_payload, write_json_file
except ModuleNotFoundError:  # pragma: no cover - direct script import fallback
    from harness_loop_contracts import read_json_file, validate_loop_state_payload, write_json_file  # type: ignore[no-redef]


DEPENDENCY_PATH_PATTERNS = (
    "requirements.txt",
    "**/requirements.txt",
    "requirements-*.txt",
    "**/requirements-*.txt",
    "pyproject.toml",
    "**/pyproject.toml",
    "poetry.lock",
    "**/poetry.lock",
    "Pipfile",
    "**/Pipfile",
    "Pipfile.lock",
    "**/Pipfile.lock",
    "package.json",
    "**/package.json",
    "package-lock.json",
    "**/package-lock.json",
    "pnpm-lock.yaml",
    "**/pnpm-lock.yaml",
    "yarn.lock",
    "**/yarn.lock",
)
DOMAIN_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class NoActionDecision:
    no_action: bool
    reasons: list[str]


@dataclass(frozen=True)
class ScopeCheckResult:
    allowed: bool
    allowed_paths: list[str]
    denied_paths: list[str]
    manual_confirm_paths: list[str]
    findings: list[str]


@dataclass(frozen=True)
class SupplyChainCheckResult:
    allowed: bool
    dependency_paths: list[str]
    findings: list[str]


@dataclass(frozen=True)
class GitDirtyRecord:
    path: str
    is_rename: bool = False


def create_default_loop_state(domain: str, domain_goal: str, scan_ttl_days: int = 30) -> dict[str, Any]:
    now = _utc_now_iso()
    state: dict[str, Any] = {
        "policy": "autonomous_knowledge",
        "domain": domain,
        "domain_goal": domain_goal,
        "last_planner_decision": "planned",
        "last_scan_at": now,
        "scan_ttl_days": scan_ttl_days,
        "candidate_backlog": [],
        "coverage_gaps": [],
        "known_sources": [],
        "blocked_items": [],
        "no_action_evidence": [],
    }
    validate_loop_state_payload(state)
    return state


def load_or_create_loop_state(
    repo_root: Path | str,
    domain: str,
    domain_goal: str,
    scan_ttl_days: int = 30,
) -> dict[str, Any]:
    path = _loop_state_path(repo_root, domain)
    if path.exists():
        state = read_json_file(path)
        validate_loop_state_payload(state)
        return state
    return create_default_loop_state(domain, domain_goal, scan_ttl_days=scan_ttl_days)


def write_loop_state(repo_root: Path | str, domain: str, state: Mapping[str, Any]) -> Path:
    payload = dict(state)
    validate_loop_state_payload(payload)
    return write_json_file(_loop_state_path(repo_root, domain), payload)


def decide_no_action(state: Mapping[str, Any], now: datetime | None = None) -> NoActionDecision:
    reasons: list[str] = []
    try:
        validate_loop_state_payload(dict(state))
    except ValueError as exc:
        return NoActionDecision(False, [str(exc)])

    if state["candidate_backlog"]:
        reasons.append("candidate_backlog is not empty")
    if state["coverage_gaps"]:
        reasons.append("coverage_gaps is not empty")
    if not state["known_sources"]:
        reasons.append("known_sources is empty")
    if not state["no_action_evidence"]:
        reasons.append("no_action_evidence is empty")
    if _scan_is_stale(str(state["last_scan_at"]), int(state["scan_ttl_days"]), now=now):
        reasons.append("last_scan_at is stale")
    return NoActionDecision(not reasons, reasons)


def autonomous_allowed_paths() -> list[str]:
    return [
        "personal-wiki/domains/**/wiki/**",
        "personal-wiki/domains/**/raw/**",
        "personal-wiki/domains/**/sources*.yaml",
        "personal-wiki/domains/**/manifest*.json",
    ]


def autonomous_manual_confirm_paths() -> list[str]:
    return [
        "tasks.json",
        "progress.md",
        "docs/**",
        "scripts/**",
    ]


def autonomous_denylist_paths() -> list[str]:
    return [
        ".env",
        ".env.*",
        "**/.env",
        "**/.env.*",
        "**/secrets/**",
        "**/*secret*",
        "**/*token*",
        "**/*credential*",
    ]


def check_autonomous_scope(
    changed_paths: Sequence[str],
    allowed_patterns: Sequence[str],
    deny_patterns: Sequence[str],
    manual_confirm_patterns: Sequence[str] | None = None,
) -> ScopeCheckResult:
    manual_patterns = list(manual_confirm_patterns or [])
    allowed_paths: list[str] = []
    denied_paths: list[str] = []
    manual_confirm_paths: list[str] = []
    findings: list[str] = []

    for changed_path in changed_paths:
        if _matches_any(changed_path, deny_patterns):
            denied_paths.append(changed_path)
            findings.append(f"denylist path: {changed_path}")
            continue
        if _matches_any(changed_path, manual_patterns):
            manual_confirm_paths.append(changed_path)
            findings.append(f"manual confirmation required: {changed_path}")
            continue
        if _matches_any(changed_path, allowed_patterns):
            allowed_paths.append(changed_path)
        else:
            denied_paths.append(changed_path)
            findings.append(f"path outside autonomous allowlist: {changed_path}")

    allowed = not denied_paths and not manual_confirm_paths
    return ScopeCheckResult(allowed, allowed_paths, denied_paths, manual_confirm_paths, findings)


def check_supply_chain(
    changed_paths: Sequence[str],
    explanation: str,
    verification: Sequence[str],
) -> SupplyChainCheckResult:
    dependency_paths = [path for path in changed_paths if _matches_any(path, DEPENDENCY_PATH_PATTERNS)]
    non_empty_verification = [item for item in verification if str(item).strip()]
    findings: list[str] = []
    if dependency_paths and not explanation.strip():
        findings.append(f"missing dependency necessity for: {', '.join(dependency_paths)}")
    if dependency_paths and not non_empty_verification:
        findings.append(f"missing dependency verification for: {', '.join(dependency_paths)}")
    return SupplyChainCheckResult(not findings, dependency_paths, findings)


def run_git_commit(repo_root: Path | str, paths: Sequence[str], message: str) -> str:
    if not paths:
        raise ValueError("paths must not be empty")
    repo = Path(repo_root)
    resolved_paths = _resolve_commit_pathspecs(repo, paths)
    subprocess.run(["git", "add", "--", *resolved_paths], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "commit", "-m", message, "--", *resolved_paths],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _resolve_commit_pathspecs(repo: Path, paths: Sequence[str]) -> list[str]:
    dirty_records = _dirty_files_for_commit(repo)
    resolved: list[str] = []
    for raw_path in paths:
        path = str(raw_path).strip()
        if not path:
            raise ValueError("commit pathspec must not be empty")
        if path.startswith(":") or path.startswith("-") or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError(f"unsafe commit pathspec: {path}")
        candidate = repo / path
        if candidate.exists() and candidate.is_dir():
            normalized = path.rstrip("/")
            matches = sorted(
                (record for record in dirty_records if record.path == normalized or record.path.startswith(f"{normalized}/")),
                key=lambda record: record.path,
            )
            if any(record.is_rename for record in matches):
                raise ValueError(f"directory pathspec cannot expand rename record: {path}")
            if len(matches) != 1:
                raise ValueError(f"directory pathspec must resolve to exactly one dirty file: {path}")
            resolved.append(matches[0].path)
        else:
            resolved.append(path)

    unique: list[str] = []
    seen: set[str] = set()
    for path in resolved:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _dirty_files_for_commit(repo: Path) -> list[GitDirtyRecord]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    dirty: list[GitDirtyRecord] = []
    records = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2]
        path = record[3:]
        is_rename = "R" in status or "C" in status
        if is_rename:
            if index < len(records):
                index += 1
            dirty.append(GitDirtyRecord(path, is_rename=True))
        else:
            dirty.append(GitDirtyRecord(path))
    return dirty


def _loop_state_path(repo_root: Path | str, domain: str) -> Path:
    if not DOMAIN_SLUG_PATTERN.fullmatch(domain):
        raise ValueError("domain must be a safe slug")
    domains_root = Path(repo_root) / "personal-wiki" / "domains"
    path = domains_root / domain / "loop-state.json"
    try:
        path.resolve().relative_to(domains_root.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("domain must stay inside personal-wiki/domains") from exc
    return path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scan_is_stale(last_scan_at: str, scan_ttl_days: int, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    try:
        scan_at = _parse_utc(last_scan_at)
    except ValueError:
        return True
    return current - scan_at > timedelta(days=scan_ttl_days)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _matches_any(path: str, patterns: Sequence[str]) -> bool:
    return any(_matches(path, pattern) for pattern in patterns)


def _matches(path: str, pattern: str) -> bool:
    if fnmatch(path, pattern):
        return True
    if pattern.endswith("/**"):
        return path == pattern[:-3] or path.startswith(pattern[:-2])
    return False
