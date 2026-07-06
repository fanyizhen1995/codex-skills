import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit, urlunsplit
from urllib.request import urlopen


TRACKING_QUERY_KEYS = {"fbclid", "gclid"}
ARXIV_VERSION_RE = re.compile(r"v\d+$", re.IGNORECASE)
SLUG_RE = re.compile(r"[^a-z0-9]+")
EVIDENCE_TOKEN_RE = re.compile(r"[a-z0-9]+")
EVIDENCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "before",
    "by",
    "during",
    "each",
    "evidence",
    "for",
    "from",
    "in",
    "is",
    "new",
    "of",
    "or",
    "result",
    "the",
    "to",
    "when",
    "with",
}


def canonicalize_url(url: str) -> str:
    value = str(url).strip()
    if not value:
        return ""
    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    query_pairs = [
        (key, item_value)
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = "&".join(
        f"{key}={item_value}" if item_value else key
        for key, item_value in query_pairs
    )
    return urlunsplit((scheme, netloc, parts.path or "", query, parts.fragment))


def _slugify(value: Any) -> str:
    text = str(value).strip().lower()
    return SLUG_RE.sub("-", text).strip("-")


def identity_key_for_candidate(candidate: Mapping[str, Any]) -> str:
    source_type = str(candidate.get("source_type", "")).strip().lower()
    if source_type == "github_issue":
        owner = _slugify(candidate.get("owner", ""))
        repo = _slugify(candidate.get("repo", ""))
        number = str(candidate.get("number", "")).strip()
        return f"github:{owner}/{repo}#{number}"
    if source_type == "paper":
        arxiv_id = ARXIV_VERSION_RE.sub("", str(candidate.get("arxiv_id", "")).strip().lower())
        return f"arxiv:{arxiv_id}"
    if source_type == "hardware":
        vendor = _slugify(candidate.get("vendor", ""))
        model = _slugify(candidate.get("model", ""))
        variant = _slugify(candidate.get("sku_or_memory_variant", ""))
        return f"hardware:{vendor}:{model}:{variant}"
    canonical_url = canonicalize_url(str(candidate.get("url", "")).strip())
    if canonical_url:
        return f"url:{canonical_url}"
    title = _slugify(candidate.get("title", ""))
    return f"{source_type}:{title}".strip(":")


def validate_gap_proof_payload(payload: Mapping[str, Any], expected_task_id: str | None = None) -> list[str]:
    findings: list[str] = []

    payload_task_id = str(payload.get("task_id", "")).strip()
    if not payload_task_id:
        findings.append("missing task_id")
    elif expected_task_id is not None and payload_task_id != expected_task_id:
        findings.append(
            f"gap proof payload task_id {payload_task_id} does not match expected task {expected_task_id}"
        )
    if not str(payload.get("layer", "")).strip():
        findings.append("missing layer")

    candidate = payload.get("candidate")
    if not isinstance(candidate, Mapping):
        candidate = {}
    if not str(candidate.get("title", "")).strip():
        findings.append("missing candidate.title")
    if not str(candidate.get("source_type", "")).strip():
        findings.append("missing candidate.source_type")
    if not str(candidate.get("identity_key", "")).strip():
        findings.append("missing candidate.identity_key")

    local_checks = payload.get("local_checks")
    if not isinstance(local_checks, Mapping):
        local_checks = {}
    for key in ("raw_manifest_scan", "wiki_search", "domain_index_scan"):
        if not str(local_checks.get(key, "")).strip():
            findings.append(f"missing local_checks.{key}")

    if not str(payload.get("gap_reason", "")).strip():
        findings.append("missing gap_reason")

    planned_outputs = payload.get("planned_outputs")
    if not isinstance(planned_outputs, list) or not any(str(item).strip() for item in planned_outputs):
        findings.append("planned_outputs must be a non-empty list")

    return findings


def validate_gap_proof_file(path: Path | str, expected_task_id: str | None = None) -> list[str]:
    gap_proof_path = Path(path)
    with gap_proof_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"gap proof payload must be an object: {gap_proof_path}")
    return validate_gap_proof_payload(payload, expected_task_id=expected_task_id)


def _keyword_tokens(value: Any) -> set[str]:
    tokens = {
        token
        for token in EVIDENCE_TOKEN_RE.findall(str(value).lower())
        if len(token) >= 3 and token not in EVIDENCE_STOPWORDS
    }
    return tokens


def _manifest_items(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    entries = payload.get("items")
    if entries is None:
        entries = payload.get("evidence")
    if not isinstance(entries, list):
        return [], ["required-evidence-manifest.json must contain an items list"]
    return [entry for entry in entries if isinstance(entry, dict)], []


def _resolve_manifest_artifact_path(raw_path: str, repo_root: Path, run_dir: Path) -> Path | None:
    candidate = Path(raw_path)
    roots = [run_dir.resolve(), repo_root.resolve()]
    if candidate.is_absolute():
        resolved = candidate.resolve()
        for root in roots:
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            return resolved
        return None
    matched_nonexistent: Path | None = None
    for root in roots:
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.exists():
            return resolved
        if matched_nonexistent is None:
            matched_nonexistent = resolved
    return matched_nonexistent


def validate_required_evidence_manifest(
    policy_required: Sequence[str],
    manifest: Mapping[str, Any],
    repo_root: Path,
    run_dir: Path,
) -> list[str]:
    findings: list[str] = []
    items, item_findings = _manifest_items(manifest)
    findings.extend(item_findings)
    if item_findings:
        return findings

    indexed_items: list[tuple[dict[str, Any], set[str]]] = []
    for item in items:
        status = str(item.get("status", "")).strip().lower()
        if status not in {"pass", "blocked"}:
            evidence_id = str(item.get("evidence_id", "")).strip() or "<unknown>"
            findings.append(f"required evidence item {evidence_id} has invalid status {status or '<missing>'}")
        artifacts = item.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            evidence_id = str(item.get("evidence_id", "")).strip() or "<unknown>"
            findings.append(f"required evidence item {evidence_id} must list at least one artifact")
            artifact_values: list[str] = []
        else:
            artifact_values = [str(value).strip() for value in artifacts if str(value).strip()]
            if not artifact_values:
                evidence_id = str(item.get("evidence_id", "")).strip() or "<unknown>"
                findings.append(f"required evidence item {evidence_id} must list at least one artifact")
        for artifact_path in artifact_values:
            resolved = _resolve_manifest_artifact_path(artifact_path, repo_root, run_dir)
            if resolved is None:
                findings.append(f"required evidence artifact escapes repo or run dir: {artifact_path}")
                continue
            if not resolved.exists():
                findings.append(f"missing required evidence artifact file: {artifact_path}")
        evidence_text = " ".join(
            str(item.get(key, "")).strip() for key in ("evidence_id", "summary") if str(item.get(key, "")).strip()
        )
        indexed_items.append((item, _keyword_tokens(evidence_text)))

    for requirement in policy_required:
        requirement_text = str(requirement).strip()
        if not requirement_text:
            continue
        requirement_tokens = _keyword_tokens(requirement_text)
        if not requirement_tokens:
            continue
        if not any(requirement_tokens.issubset(item_tokens) for _, item_tokens in indexed_items):
            findings.append(f"missing required evidence manifest item for: {requirement_text}")

    return findings


def check_service_availability(
    services: Sequence[Mapping[str, str]],
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    overall_status = "pass"
    for service in services:
        name = str(service.get("service", "")).strip()
        url = str(service.get("url", "")).strip()
        entry = {
            "service": name,
            "url": url,
            "status": "fail",
            "http_status": None,
            "error": "",
        }
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                http_status = int(getattr(response, "status", 0) or 0)
                entry["http_status"] = http_status
                entry["status"] = "pass" if 200 <= http_status < 400 else "fail"
                if entry["status"] != "pass":
                    entry["error"] = f"unexpected HTTP status {http_status}"
        except HTTPError as exc:
            entry["http_status"] = int(exc.code)
            entry["error"] = str(exc)
        except URLError as exc:
            entry["error"] = str(exc.reason)
        except OSError as exc:
            entry["error"] = str(exc)
        if entry["status"] != "pass":
            overall_status = "fail"
        results.append(entry)
    return {"overall_status": overall_status, "services": results}
