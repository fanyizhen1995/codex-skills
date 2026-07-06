import json
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit, urlunsplit


TRACKING_QUERY_KEYS = {"fbclid", "gclid"}
ARXIV_VERSION_RE = re.compile(r"v\d+$", re.IGNORECASE)
SLUG_RE = re.compile(r"[^a-z0-9]+")


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


def validate_gap_proof_payload(payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []

    if not str(payload.get("task_id", "")).strip():
        findings.append("missing task_id")
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


def validate_gap_proof_file(path: Path | str) -> list[str]:
    gap_proof_path = Path(path)
    with gap_proof_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"gap proof payload must be an object: {gap_proof_path}")
    return validate_gap_proof_payload(payload)
