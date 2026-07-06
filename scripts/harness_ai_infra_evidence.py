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
EVIDENCE_REQUIREMENT_ALIAS_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("confirmed-preflight", ("confirmed ai_infra autonomous expansion preflight",)),
    ("policy-run-limits", ("policy_file and expanded limits recorded in run.json",)),
    ("gap-proof", ("gap proof",)),
    ("coverage-map", ("coverage-map",)),
    ("loop-state", ("loop-state.json", "loop state")),
    ("raw-evidence", ("raw evidence", "raw reuse evidence")),
    ("curated-wiki-source-refs", ("source_refs", "source refs")),
    ("wiki-validate", ("wiki validate",)),
    ("search-api-visibility", ("search/api visibility", "search api visibility")),
    ("frontend-visibility", ("frontend visibility",)),
    ("crawler-workbench-freshness", ("crawler workbench api freshness",)),
    ("domain-channels", ("domain channels",)),
    ("loop-dashboard-freshness", ("loop dashboard freshness",)),
    ("service-availability", ("service availability",)),
    ("link-probe", ("link probe", "blocked/auth evidence")),
    ("secret-scan", ("secret scan",)),
    ("code-tests", ("code test",)),
    ("autonomous-scope-result", ("autonomous-scope-result.json",)),
    ("supply-chain-result", ("supply-chain-result.json",)),
    ("commit-result", ("commit-result.json",)),
    ("no-action-evidence", ("no-action evidence",)),
)
SERVICE_AVAILABILITY_REQUIRED_SERVICES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("crawler-backend", ("crawler-backend", "crawler backend")),
    ("crawler-frontend", ("crawler-frontend", "crawler frontend")),
    ("loop-dashboard", ("loop-dashboard", "loop dashboard")),
)
FRESHNESS_EVIDENCE_IDS = {
    "crawler-workbench-freshness",
    "loop-dashboard-freshness",
}
SEMANTIC_GATE_EVIDENCE_IDS = FRESHNESS_EVIDENCE_IDS | {"service-availability"}


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
    findings: list[str] = []
    items: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, dict):
            items.append(entry)
            continue
        findings.append(f"required-evidence-manifest.json items[{index}] must be an object")
    return items, findings


def resolve_manifest_artifact_path(raw_path: str, repo_root: Path, run_dir: Path) -> Path | None:
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


def _normalized_evidence_id(value: Any) -> str:
    return _slugify(value)


def _aliases_for_requirement(requirement: str) -> set[str]:
    normalized = requirement.strip().lower()
    aliases: set[str] = set()
    for evidence_id, markers in EVIDENCE_REQUIREMENT_ALIAS_RULES:
        if any(marker in normalized for marker in markers):
            aliases.add(evidence_id)
    if aliases:
        return aliases
    aliases.add(_normalized_evidence_id(requirement))
    return aliases


def _evidence_id_matches_alias(evidence_id: str, accepted_ids: set[str]) -> bool:
    for accepted_id in accepted_ids:
        if not accepted_id:
            continue
        if evidence_id == accepted_id:
            return True
    return False


def _load_artifact_payload(path: Path, evidence_id: str, artifact_path: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        return None, [f"{evidence_id} artifact {artifact_path} could not be parsed as JSON: {exc.msg}"]
    if not isinstance(payload, dict):
        return None, [f"{evidence_id} artifact {artifact_path} must contain an object payload"]
    return payload, []


def _normalize_service_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")


def _validate_service_availability_payload(
    payload: Mapping[str, Any],
    *,
    evidence_id: str,
    artifact_path: str,
) -> list[str]:
    findings: list[str] = []
    overall_status = str(payload.get("overall_status", "")).strip().lower()
    services = payload.get("services")
    if overall_status not in {"pass", "fail", "blocked"}:
        findings.append(
            f"{evidence_id} artifact {artifact_path} must contain overall_status with pass/fail/blocked"
        )
    if not isinstance(services, list):
        findings.append(f"{evidence_id} artifact {artifact_path} must contain a services list")
        return findings

    services_by_name: dict[str, Mapping[str, Any]] = {}
    for entry in services:
        if not isinstance(entry, Mapping):
            findings.append(f"{evidence_id} artifact {artifact_path} services entries must be objects")
            continue
        normalized = _normalize_service_name(entry.get("service", ""))
        if normalized:
            services_by_name[normalized] = entry

    for canonical_name, aliases in SERVICE_AVAILABILITY_REQUIRED_SERVICES:
        matched = None
        for alias in aliases:
            matched = services_by_name.get(_normalize_service_name(alias))
            if matched is not None:
                break
        if matched is None:
            findings.append(f"{evidence_id} artifact {artifact_path} is missing service {canonical_name}")
            continue
        service_status = str(matched.get("status", "")).strip().lower()
        if service_status != "pass":
            findings.append(
                f"{evidence_id} artifact {artifact_path} must record {canonical_name} as pass"
            )
        http_status = matched.get("http_status")
        if not isinstance(http_status, int) or not 200 <= http_status < 400:
            findings.append(
                f"{evidence_id} artifact {artifact_path} must record HTTP 2xx/3xx for {canonical_name}"
            )

    if overall_status != "pass":
        findings.append(f"{evidence_id} artifact {artifact_path} must report overall_status pass")
    return findings


def _validate_freshness_payload(
    payload: Mapping[str, Any],
    *,
    evidence_id: str,
    artifact_path: str,
) -> list[str]:
    findings: list[str] = []
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"pass", "fail", "blocked"}:
        findings.append(f"{evidence_id} artifact {artifact_path} must contain status pass/fail/blocked")
    elif status != "pass":
        findings.append(f"{evidence_id} artifact {artifact_path} must report status pass")
    summary = str(payload.get("summary", "")).strip()
    if not summary:
        findings.append(f"{evidence_id} artifact {artifact_path} must include a non-empty summary")
    details = payload.get("details")
    if not isinstance(details, Mapping) or not details:
        findings.append(f"{evidence_id} artifact {artifact_path} must include meaningful details")
    return findings


def _validate_semantic_evidence_artifacts(
    *,
    evidence_id: str,
    resolved_artifacts: Sequence[tuple[str, Path]],
) -> list[str]:
    if evidence_id not in SEMANTIC_GATE_EVIDENCE_IDS:
        return []
    if not resolved_artifacts:
        return [f"{evidence_id} must reference at least one artifact"]

    findings: list[str] = []
    semantic_valid = False
    for artifact_path, resolved in resolved_artifacts:
        payload, payload_findings = _load_artifact_payload(resolved, evidence_id, artifact_path)
        if payload_findings:
            findings.extend(payload_findings)
            continue
        artifact_findings = (
            _validate_service_availability_payload(payload, evidence_id=evidence_id, artifact_path=artifact_path)
            if evidence_id == "service-availability"
            else _validate_freshness_payload(payload, evidence_id=evidence_id, artifact_path=artifact_path)
        )
        if artifact_findings:
            findings.extend(artifact_findings)
            continue
        semantic_valid = True

    if semantic_valid:
        return []
    return findings


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

    indexed_items: list[dict[str, Any]] = []
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
        resolved_artifacts: list[tuple[str, Path]] = []
        for artifact_path in artifact_values:
            resolved = resolve_manifest_artifact_path(artifact_path, repo_root, run_dir)
            if resolved is None:
                findings.append(f"required evidence artifact escapes repo or run dir: {artifact_path}")
                continue
            if not resolved.exists():
                findings.append(f"missing required evidence artifact file: {artifact_path}")
                continue
            resolved_artifacts.append((artifact_path, resolved))
        evidence_id = _normalized_evidence_id(item.get("evidence_id", ""))
        semantic_findings = _validate_semantic_evidence_artifacts(
            evidence_id=evidence_id,
            resolved_artifacts=resolved_artifacts,
        )
        findings.extend(semantic_findings)
        evidence_text = " ".join(
            str(item.get(key, "")).strip() for key in ("evidence_id", "summary") if str(item.get(key, "")).strip()
        )
        indexed_items.append(
            {
                "item": item,
                "evidence_id": evidence_id,
                "tokens": _keyword_tokens(evidence_text),
                "status": status,
                "semantic_ok": not semantic_findings,
                "resolved_artifacts": resolved_artifacts,
            }
        )

    for requirement in policy_required:
        requirement_text = str(requirement).strip()
        if not requirement_text:
            continue
        accepted_ids = _aliases_for_requirement(requirement_text)
        inferred_semantic_evidence_id = next(
            (accepted_id for accepted_id in accepted_ids if accepted_id in SEMANTIC_GATE_EVIDENCE_IDS),
            "",
        )
        matching_items = [
            indexed_item
            for indexed_item in indexed_items
            if indexed_item["evidence_id"] and _evidence_id_matches_alias(indexed_item["evidence_id"], accepted_ids)
        ]
        if matching_items:
            if any(item["status"] == "pass" and item["semantic_ok"] for item in matching_items):
                continue
            for indexed_item in matching_items:
                item = indexed_item["item"]
                item_evidence_id = indexed_item["evidence_id"]
                item_status = indexed_item["status"]
                if item_status != "pass":
                    findings.append(
                        f"required evidence item {item_evidence_id or str(item.get('evidence_id', '')).strip() or '<unknown>'} has non-pass status {item_status}"
                    )
            continue
        requirement_tokens = _keyword_tokens(requirement_text)
        if not requirement_tokens:
            continue
        summary_only_matches = [
            indexed_item
            for indexed_item in indexed_items
            if not indexed_item["evidence_id"]
            and indexed_item["status"] == "pass"
            and requirement_tokens.issubset(indexed_item["tokens"])
        ]
        if inferred_semantic_evidence_id:
            validated_summary_matches: list[dict[str, Any]] = []
            for indexed_item in summary_only_matches:
                inferred_findings = _validate_semantic_evidence_artifacts(
                    evidence_id=inferred_semantic_evidence_id,
                    resolved_artifacts=indexed_item["resolved_artifacts"],
                )
                if inferred_findings:
                    findings.extend(inferred_findings)
                    continue
                validated_summary_matches.append(indexed_item)
            summary_only_matches = validated_summary_matches
        if not summary_only_matches:
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
