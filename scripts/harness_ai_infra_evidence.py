import hashlib
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
FRESHNESS_REQUIRED_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "crawler-workbench-freshness": ("sources", "channels", "queue", "wiki", "search"),
    "loop-dashboard-freshness": (
        "current_run",
        "child_tasks",
        "agent_actions",
        "evaluator_scenarios",
        "completed_history",
    ),
}
VISIBILITY_EVIDENCE_IDS = {
    "search-api-visibility",
    "frontend-visibility",
}
SEMANTIC_GATE_EVIDENCE_IDS = FRESHNESS_EVIDENCE_IDS | VISIBILITY_EVIDENCE_IDS | {"service-availability"}
TRUSTED_EVIDENCE_CREATED_BY = "harness_loop_orchestrator"
TRUSTED_LIVE_EVIDENCE_DIR = "trusted-live-evidence"


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
    if bool(payload.get("synthetic_smoke")):
        findings.append(f"{evidence_id} artifact {artifact_path} cannot use synthetic_smoke placeholders")
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
    if bool(payload.get("synthetic_smoke")):
        findings.append(f"{evidence_id} artifact {artifact_path} cannot use synthetic_smoke placeholders")
    details = payload.get("details")
    if not isinstance(details, Mapping) or not details:
        findings.append(f"{evidence_id} artifact {artifact_path} must include meaningful details")
        return findings

    required_dimensions = FRESHNESS_REQUIRED_DIMENSIONS.get(evidence_id, ())
    missing_dimensions = [
        dimension for dimension in required_dimensions if not _freshness_detail_is_pass_like(details.get(dimension))
    ]
    if missing_dimensions:
        findings.append(
            f"{evidence_id} artifact {artifact_path} must include pass details for: {', '.join(missing_dimensions)}"
        )
    if evidence_id == "crawler-workbench-freshness":
        for key in ("wiki", "search"):
            nested = details.get(key)
            if not isinstance(nested, Mapping):
                findings.append(f"{evidence_id} artifact {artifact_path} details.{key} must be a mapping")
                continue
            findings.extend(
                _validate_search_visibility_payload(
                    nested,
                    evidence_id=evidence_id,
                    artifact_path=f"{artifact_path} details.{key}",
                )
            )
    if evidence_id == "loop-dashboard-freshness":
        expected_run_id = str(payload.get("run_id", "")).strip()
        expected_worktree = str(payload.get("worktree", "")).strip()
        if not expected_run_id:
            findings.append(f"{evidence_id} artifact {artifact_path} must include non-empty run_id")
        if not expected_worktree:
            findings.append(f"{evidence_id} artifact {artifact_path} must include non-empty worktree")

        current_run = details.get("current_run")
        child_tasks = details.get("child_tasks")
        agent_actions = details.get("agent_actions")
        evaluator_scenarios = details.get("evaluator_scenarios")
        completed_history = details.get("completed_history")
        project = details.get("project")

        if isinstance(current_run, Mapping):
            current_payload = current_run.get("json")
            if not (
                isinstance(current_payload, Mapping)
                and str(current_payload.get("run_id", "")).strip() == expected_run_id
            ):
                findings.append(f"{evidence_id} artifact {artifact_path} must bind current run_id to details.current_run")
            elif expected_worktree:
                project_root = str(current_payload.get("project_root", "")).strip()
                if project_root and project_root != expected_worktree:
                    findings.append(f"{evidence_id} artifact {artifact_path} current run_id binding must match worktree")
        if isinstance(child_tasks, Mapping):
            child_payload = child_tasks.get("json")
            if not (
                isinstance(child_payload, Mapping)
                and str(child_payload.get("run_id", "")).strip() == expected_run_id
            ):
                findings.append(f"{evidence_id} artifact {artifact_path} must bind current run_id to details.child_tasks")
        if isinstance(agent_actions, Mapping):
            agent_payload = agent_actions.get("json")
            if not (
                isinstance(agent_payload, Mapping)
                and str(agent_payload.get("run_id", "")).strip() == expected_run_id
            ):
                findings.append(f"{evidence_id} artifact {artifact_path} must bind current run_id to details.agent_actions")
        if isinstance(evaluator_scenarios, Mapping):
            evaluator_payload = evaluator_scenarios.get("json")
            if not (
                isinstance(evaluator_payload, Mapping)
                and str(evaluator_payload.get("run_id", "")).strip() == expected_run_id
            ):
                findings.append(
                    f"{evidence_id} artifact {artifact_path} must bind current run_id to details.evaluator_scenarios"
                )
        if isinstance(completed_history, Mapping):
            history_payload = completed_history.get("json")
            if not any(
                isinstance(item, Mapping) and str(item.get("run_id", "")).strip() == expected_run_id
                for item in _json_candidates(history_payload)
            ):
                findings.append(f"{evidence_id} artifact {artifact_path} completed history must contain current run_id")
        if isinstance(project, Mapping):
            project_payload = project.get("json")
            project_root = str(project_payload.get("project_root", "")).strip() if isinstance(project_payload, Mapping) else ""
            if expected_worktree and project_root != expected_worktree:
                findings.append(f"{evidence_id} artifact {artifact_path} project metadata must match current worktree")
    return findings


def _freshness_detail_is_pass_like(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"pass", "passed", "ok", "success", "true"}
    if isinstance(value, Mapping):
        for key in ("status", "check"):
            candidate = value.get(key)
            if candidate is True:
                return True
            if isinstance(candidate, str) and candidate.strip().lower() in {"pass", "passed", "ok", "success", "true"}:
                return True
    return False


def _non_empty_string(value: Any) -> bool:
    return bool(str(value).strip())


def _non_empty_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and any(
        _non_empty_string(item) for item in value
    )


def _normalized_target_ids(targets: Any) -> list[str]:
    if not isinstance(targets, list):
        return []
    return [
        str(item.get("target_id", "")).strip()
        for item in targets
        if isinstance(item, Mapping) and str(item.get("target_id", "")).strip()
    ]


def _validate_visibility_target_consistency(
    payload: Mapping[str, Any],
    *,
    evidence_id: str,
    artifact_path: str,
    prefix: str = "",
) -> list[str]:
    findings: list[str] = []
    expected_targets = payload.get("expected_targets")
    matched_targets = payload.get("matched_targets")
    missing_targets = payload.get("missing_targets")
    if not isinstance(expected_targets, list) or not isinstance(matched_targets, list) or not isinstance(missing_targets, list):
        return findings

    label = f"{prefix} " if prefix else ""
    expected_ids = _normalized_target_ids(expected_targets)
    matched_ids = _normalized_target_ids(matched_targets)
    missing_ids = _normalized_target_ids(missing_targets)
    status = str(payload.get("status", "")).strip().lower()

    if status == "pass":
        if missing_targets or missing_ids:
            findings.append(f"{evidence_id} artifact {artifact_path} {label}pass status requires missing_targets to be empty")
        if len(matched_targets) != len(expected_targets) or set(matched_ids) != set(expected_ids):
            findings.append(
                f"{evidence_id} artifact {artifact_path} {label}pass status requires matched_targets to exactly cover expected target_ids"
            )

    visible_results = payload.get("visible_results")
    if isinstance(visible_results, int) and visible_results != len(matched_targets):
        findings.append(f"{evidence_id} artifact {artifact_path} {label}visible_results must equal len(matched_targets)")

    matched_by_id = {
        str(item.get("target_id", "")).strip(): item
        for item in matched_targets
        if isinstance(item, Mapping) and str(item.get("target_id", "")).strip()
    }
    for expected in expected_targets:
        if not isinstance(expected, Mapping) or str(expected.get("kind", "")).strip() != "wiki_page":
            continue
        expected_id = str(expected.get("target_id", "")).strip()
        expected_terms = {
            str(term).strip().lower()
            for term in expected.get("content_terms", [])
            if str(term).strip()
        }
        if not expected_terms:
            continue
        matched = matched_by_id.get(expected_id)
        if not isinstance(matched, Mapping):
            continue
        matched_terms = {
            str(term).strip().lower()
            for term in matched.get("matched_content_terms", [])
            if str(term).strip()
        }
        if matched_terms != expected_terms:
            findings.append(
                f"{evidence_id} artifact {artifact_path} {label}wiki_page target {expected_id} must prove current content_terms"
            )
    return findings


def _json_candidates(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        return [value]
    return []


def _validate_visibility_target_fields(
    payload: Mapping[str, Any],
    *,
    evidence_id: str,
    artifact_path: str,
) -> list[str]:
    findings: list[str] = []
    for field_name in ("run_id", "task_id", "domain"):
        if not _non_empty_string(payload.get(field_name, "")):
            findings.append(f"{evidence_id} artifact {artifact_path} must include non-empty {field_name}")
    expected_targets = payload.get("expected_targets")
    if not isinstance(expected_targets, list) or not expected_targets:
        findings.append(f"{evidence_id} artifact {artifact_path} must include non-empty expected_targets")
    matched_targets = payload.get("matched_targets")
    if not isinstance(matched_targets, list) or not matched_targets:
        findings.append(f"{evidence_id} artifact {artifact_path} must include non-empty matched_targets")
    missing_targets = payload.get("missing_targets")
    if not isinstance(missing_targets, list):
        findings.append(f"{evidence_id} artifact {artifact_path} must include missing_targets as a list")
    return findings


def _validate_search_visibility_payload(
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
    if bool(payload.get("synthetic_smoke")):
        findings.append(f"{evidence_id} artifact {artifact_path} cannot use synthetic_smoke placeholders")
    if not _non_empty_string(payload.get("query", "")):
        findings.append(f"{evidence_id} artifact {artifact_path} must include a non-empty query")
    visible_results = payload.get("visible_results")
    has_visible_result_count = isinstance(visible_results, int) and visible_results > 0
    has_visible_items = _non_empty_sequence(payload.get("visible_items"))
    if not has_visible_result_count and not has_visible_items:
        findings.append(
            f"{evidence_id} artifact {artifact_path} must include visible_results > 0 or non-empty visible_items"
        )
    findings.extend(
        _validate_visibility_target_fields(
            payload,
            evidence_id=evidence_id,
            artifact_path=artifact_path,
        )
    )
    findings.extend(
        _validate_visibility_target_consistency(
            payload,
            evidence_id=evidence_id,
            artifact_path=artifact_path,
        )
    )
    return findings


def _validate_frontend_visibility_payload(
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
    if bool(payload.get("synthetic_smoke")):
        findings.append(f"{evidence_id} artifact {artifact_path} cannot use synthetic_smoke placeholders")
    if not (_non_empty_string(payload.get("page_url", "")) or _non_empty_string(payload.get("route", ""))):
        findings.append(f"{evidence_id} artifact {artifact_path} must include a non-empty page_url or route")
    has_visible_text = _non_empty_sequence(payload.get("visible_text"))
    has_assertions = _non_empty_sequence(payload.get("assertions"))
    if not has_visible_text and not has_assertions:
        findings.append(
            f"{evidence_id} artifact {artifact_path} must include non-empty visible_text or assertions"
        )
    findings.extend(
        _validate_visibility_target_fields(
            payload,
            evidence_id=evidence_id,
            artifact_path=artifact_path,
        )
    )
    findings.extend(
        _validate_visibility_target_consistency(
            payload,
            evidence_id=evidence_id,
            artifact_path=artifact_path,
        )
    )
    return findings


def _validate_semantic_evidence_artifacts(
    *,
    evidence_id: str,
    item: Mapping[str, Any],
    run_dir: Path,
    resolved_artifacts: Sequence[tuple[str, Path]],
    trusted_live_evidence_state: Mapping[str, Any] | None,
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
            if evidence_id in FRESHNESS_EVIDENCE_IDS
            else _validate_search_visibility_payload(payload, evidence_id=evidence_id, artifact_path=artifact_path)
            if evidence_id == "search-api-visibility"
            else _validate_frontend_visibility_payload(payload, evidence_id=evidence_id, artifact_path=artifact_path)
        )
        provenance_finding = _validate_trusted_live_evidence_provenance(
            payload,
            item=item,
            evidence_id=evidence_id,
            artifact_path=artifact_path,
            run_dir=run_dir,
            resolved=resolved,
            trusted_live_evidence_state=trusted_live_evidence_state,
        )
        if provenance_finding:
            artifact_findings.append(provenance_finding)
        if artifact_findings:
            findings.extend(artifact_findings)
            continue
        semantic_valid = True

    if semantic_valid:
        return []
    return findings


def _validate_trusted_live_evidence_provenance(
    payload: Mapping[str, Any],
    *,
    item: Mapping[str, Any],
    evidence_id: str,
    artifact_path: str,
    run_dir: Path,
    resolved: Path,
    trusted_live_evidence_state: Mapping[str, Any] | None,
) -> str:
    del item, payload
    expected_path = trusted_live_evidence_artifact_path(evidence_id)
    if _normalize_manifest_artifact_path(artifact_path) != expected_path:
        return (
            f"{evidence_id} artifact {artifact_path} must use orchestrator-owned "
            f"{expected_path}"
        )
    expected_resolved = (run_dir / expected_path).resolve()
    if resolved.resolve() != expected_resolved:
        return (
            f"{evidence_id} artifact {artifact_path} must resolve to run-local "
            f"{expected_path}"
        )
    state_entry = _trusted_live_evidence_state_entry(trusted_live_evidence_state, evidence_id)
    if state_entry is None:
        return (
            f"{evidence_id} artifact {artifact_path} is missing trusted live evidence state "
            f"for {expected_path}"
        )
    state_created_by = str(state_entry.get("created_by", "")).strip()
    if state_created_by != TRUSTED_EVIDENCE_CREATED_BY:
        return (
            f"{evidence_id} trusted live evidence state must record created_by "
            f"{TRUSTED_EVIDENCE_CREATED_BY}"
        )
    state_artifact_path = _normalize_manifest_artifact_path(str(state_entry.get("artifact_path", "")))
    if state_artifact_path != expected_path:
        return (
            f"{evidence_id} trusted live evidence state artifact_path {state_artifact_path or '<missing>'} "
            f"does not match {expected_path}"
        )
    if not str(state_entry.get("captured_at", "")).strip():
        return f"{evidence_id} trusted live evidence state must record captured_at"
    expected_sha256 = str(state_entry.get("sha256", "")).strip().lower()
    actual_sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if expected_sha256 != actual_sha256:
        return (
            f"{evidence_id} trusted live evidence state sha256 {expected_sha256 or '<missing>'} "
            f"does not match artifact sha256 {actual_sha256}"
        )
    return ""


def _trusted_live_evidence_state_entry(
    trusted_live_evidence_state: Mapping[str, Any] | None,
    evidence_id: str,
) -> Mapping[str, Any] | None:
    if not isinstance(trusted_live_evidence_state, Mapping):
        return None
    entry = trusted_live_evidence_state.get(evidence_id)
    return entry if isinstance(entry, Mapping) else None


def trusted_live_evidence_artifact_path(evidence_id: str) -> str:
    return f"{TRUSTED_LIVE_EVIDENCE_DIR}/{evidence_id}.json"


def _normalize_manifest_artifact_path(artifact_path: str) -> str:
    return str(artifact_path).strip().replace("\\", "/").lstrip("./")


def validate_required_evidence_manifest(
    policy_required: Sequence[str],
    manifest: Mapping[str, Any],
    repo_root: Path,
    run_dir: Path,
    *,
    trusted_live_evidence_state: Mapping[str, Any] | None = None,
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
            item=item,
            run_dir=run_dir,
            resolved_artifacts=resolved_artifacts,
            trusted_live_evidence_state=trusted_live_evidence_state,
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
            if summary_only_matches:
                findings.append(
                    f"semantic required evidence {inferred_semantic_evidence_id} must use explicit evidence_id"
                )
            summary_only_matches = []
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
    return {
        "overall_status": overall_status,
        "services": results,
        "created_by": TRUSTED_EVIDENCE_CREATED_BY,
    }
