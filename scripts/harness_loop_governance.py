import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit


AI_INFRA_GOVERNANCE_RUN_ID = "ai-infra-loop-governance-dev"
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "dclid",
    "gbraid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "wbraid",
    "yclid",
}
PASS_STATUSES = frozenset({"ok", "pass", "passed", "reachable", "success"})
REQUIRED_HARD_GATES = (
    "has_gap_proof",
    "has_two_source_types_for_deep_dive",
    "has_evaluator_scenario",
    "has_domain_channel_plan",
    "has_depth_acquisition_proof",
    "identity_key_is_canonical",
)
NETWORK_FAILURE_TYPES = frozenset(
    {"dns", "tls", "timeout", "connection", "network", "http_5xx", "http_429"}
)
AUTH_FAILURE_TYPES = frozenset(
    {"http_403", "403", "auth", "authentication", "authorization", "robots", "captcha", "rate_limit"}
)
SEED_FAILURE_TYPES = frozenset({"seed_url", "missing_seed_url", "no_seed_url"})
HUMAN_FAILURE_TYPES = frozenset({"human_judgement", "manual", "ambiguous", "denylist"})
SENSITIVE_SNAPSHOT_KEYS = frozenset(
    {
        "authorization",
        "client_secret",
        "cookie",
        "cookies",
        "encrypted_secret",
        "header",
        "headers",
        "key_path",
        "local_key_path",
        "nonce",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)
SENSITIVE_SNAPSHOT_KEY_FRAGMENTS = frozenset(
    {
        "apikey",
        "api_key",
        "authorization",
        "cookie",
        "header",
        "password",
        "secret",
        "token",
    }
)
GOVERNANCE_P0_ARTIFACTS = (
    "egress-proof.json",
    "identity-key-audit.json",
    "depth-acquisition-smoke.json",
)
GOVERNANCE_CANDIDATE_SCORING_GLOB = "candidate-scoring/*.json"
SLUG_RE = re.compile(r"[^a-z0-9]+")
DOMAIN_RE = re.compile(r"[^a-z0-9_-]+")
DEFAULT_PROBE_TIME = datetime(1970, 1, 1, tzinfo=timezone.utc)
FORMAL_SUSPICION_RESULTS = frozenset({"confirmed_bug", "disproved", "inconclusive"})
FORMAL_SUSPICION_RISKS = frozenset({"low", "medium", "high"})
FORMAL_COUNTEREXAMPLE_TYPES = frozenset(
    {"unit_test", "cli_probe", "api_probe", "playwright", "schema_validation", "fixture_replay"}
)


def canonical_identity_key(candidate: Mapping[str, Any]) -> str:
    """Return the deterministic governance identity key for a candidate payload."""

    if not isinstance(candidate, Mapping):
        return ""

    doi = _normalized_doi(_first_string(candidate, "doi"))
    if doi:
        return f"doi:{doi}"

    arxiv_id = _normalized_arxiv(_first_string(candidate, "arxiv_id", "arxiv"))
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    source_type = _source_type(candidate)
    if source_type in {"hardware", "hardware_model"}:
        return _hardware_identity_key(candidate)
    if source_type in {"channel", "crawler_channel", "domain_channel"}:
        target_domain = _domain_slug(_first_string(candidate, "target_domain", "domain"))
        base_url = _canonical_url_without_prefix(_first_string(candidate, "base_url", "url"))
        return f"channel:{target_domain}:{base_url}" if target_domain and base_url else ""
    if source_type in {"source_profile", "source-profile", "crawler_source"}:
        source_id = _first_string(candidate, "source_id", "id")
        return f"source-profile:{source_id}" if source_id else ""
    if source_type in {"github_repo", "github-repo"}:
        return _github_repo_key_from_fields(candidate) or _github_key_from_url(
            _first_string(candidate, "url", "canonical_url", "html_url")
        )
    if source_type in {"github_issue", "github-issue"}:
        return _github_issue_or_pr_key_from_fields(candidate, "github-issue") or _github_key_from_url(
            _first_string(candidate, "url", "canonical_url", "html_url")
        )
    if source_type in {"github_pr", "github-pr", "github_pull_request"}:
        return _github_issue_or_pr_key_from_fields(candidate, "github-pr") or _github_key_from_url(
            _first_string(candidate, "url", "canonical_url", "html_url")
        )
    if source_type in {"github_release", "github-release"}:
        return _github_release_key_from_fields(candidate) or _github_key_from_url(
            _first_string(candidate, "url", "canonical_url", "html_url")
        )

    url = _first_string(candidate, "url", "canonical_url", "html_url")
    github_key = _github_key_from_url(url)
    if github_key:
        return github_key

    doi = _normalized_doi_from_url(url)
    if doi:
        return f"doi:{doi}"

    arxiv_id = _normalized_arxiv_from_url(url)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    canonical_url = _canonical_url_without_prefix(url)
    if canonical_url:
        return f"url:{canonical_url}"

    raw_sha256 = _first_string(candidate, "raw_sha256", "sha256")
    if (
        raw_sha256
        and _source_type(candidate) in {"", "raw", "raw_sha256", "raw-sha256"}
        and _is_hex_digest(raw_sha256)
    ):
        return f"raw-sha256:{raw_sha256.lower()}"

    existing_identity = _first_string(candidate, "identity_key")
    if _is_canonical_identity_key(existing_identity):
        return existing_identity

    title = _slug(_first_string(candidate, "title", "candidate_id"))
    if title:
        return f"candidate:{title}"
    return ""


def classify_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a candidate without allowing advisory priority_score to override hard gates."""

    source = candidate if isinstance(candidate, Mapping) else {}
    decision_inputs = _mapping(source.get("decision_inputs"))
    hard_gates = _mapping(source.get("hard_gates"))

    identity_key = canonical_identity_key(source)
    source_type_count = _int(decision_inputs.get("source_type_count", source.get("source_type_count")), 0)
    local_gap_level = str(decision_inputs.get("local_gap_level", source.get("local_gap_level", "none"))).strip().lower()
    duplicate_status = str(
        decision_inputs.get("duplicate_status", source.get("duplicate_status", "none"))
    ).strip().lower()
    acquisition_path = str(
        decision_inputs.get("acquisition_path", source.get("acquisition_path", "none"))
    ).strip().lower()
    priority_score = _int(source.get("priority_score"), 0)

    missing_hard_gates = [gate for gate in REQUIRED_HARD_GATES if hard_gates.get(gate) is not True]
    hard_gate_passed = not missing_hard_gates

    missing_inputs: list[str] = []
    if source_type_count < 2:
        missing_inputs.append("source_type_count>=2")
    if local_gap_level == "none":
        missing_inputs.append("local_gap_level!=none")
    if duplicate_status == "duplicate":
        missing_inputs.append("duplicate_status!=duplicate")
    if acquisition_path == "none":
        missing_inputs.append("acquisition_path!=none")
    identity_key_is_canonical = _is_canonical_identity_key(identity_key)
    if not identity_key_is_canonical:
        missing_inputs.append("identity_key")

    if _has_blocked_marker(source, decision_inputs):
        classification = "blocked"
    elif duplicate_status == "duplicate":
        classification = "low_value"
    elif hard_gate_passed and not missing_inputs:
        classification = "high_value"
    elif local_gap_level == "none":
        classification = "low_value"
    elif missing_hard_gates or acquisition_path == "none":
        classification = "needs_more_evidence"
    elif source_type_count < 2:
        classification = "medium_value"
    else:
        classification = "medium_value"

    return {
        "candidate_id": _first_string(source, "candidate_id", "id"),
        "identity_key": identity_key,
        "classification": classification,
        "priority_score": priority_score,
        "hard_gate_passed": hard_gate_passed,
        "identity_key_is_canonical": identity_key_is_canonical,
        "missing_hard_gates": missing_hard_gates,
        "missing_inputs": missing_inputs,
        "decision_inputs": {
            "source_type_count": source_type_count,
            "local_gap_level": local_gap_level,
            "duplicate_status": duplicate_status,
            "acquisition_path": acquisition_path,
        },
        "high_value_eligible": classification == "high_value",
        "rationale": _classification_rationale(classification, missing_hard_gates, missing_inputs),
    }


def record_needs_transition(item: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
    """Return the next governance state for a blocked/actionable item and probe payload."""

    current = deepcopy(dict(item)) if isinstance(item, Mapping) else {}
    current_probe = dict(probe) if isinstance(probe, Mapping) else {}
    now = _probe_time(current_probe)
    failure_type = _failure_type(current_probe)
    identity_key = _first_string(current_probe, "identity_key") or _first_string(current, "identity_key")

    if current.get("status") == "needs_network":
        due = _is_reprobe_due(current, now)
        changed_findings = _network_state_change_findings(current, current_probe)
        if (
            current_probe.get("network_state_changed") is True
            and due
            and _probe_http_reachable(current_probe)
            and not changed_findings
        ):
            result = deepcopy(current)
            result.update(
                {
                    "status": "actionable",
                    "needs_queue": "",
                    "wait_condition": "",
                    "reprobe_due": True,
                    "network_state_changed": True,
                    "last_probe": current_probe,
                    "findings": [],
                }
            )
            return result

        result = deepcopy(current)
        result.update(
            {
                "status": "needs_network",
                "needs_queue": "needs_network",
                "reprobe_due": due,
                "network_state_changed": False,
                "last_probe": current_probe if due else current.get("last_probe", {}),
                "findings": changed_findings if current_probe.get("network_state_changed") is True else [],
            }
        )
        return result

    history = list(current.get("failure_history", [])) if isinstance(current.get("failure_history"), list) else []
    current_probe_entry = {
        "identity_key": identity_key,
        "source_boundary": _first_string(current_probe, "source_boundary")
        or _first_string(current, "source_boundary"),
        "failure_type": failure_type,
        "status": str(current_probe.get("status", "")).strip().lower(),
        "finished_at": _first_string(current_probe, "finished_at"),
        "probe_url": _first_string(current_probe, "probe_url"),
        "error_class": _first_string(current_probe, "error_class"),
        "summary": _first_string(current_probe, "summary"),
    }

    if _probe_http_reachable(current_probe):
        result = deepcopy(current)
        result.update(
            {
                "identity_key": identity_key,
                "status": "actionable",
                "needs_queue": "",
                "wait_condition": "",
                "reprobe_due": False,
                "last_probe": current_probe,
                "failure_history": history,
            }
        )
        return result

    history.append(current_probe_entry)
    consecutive = _has_consecutive_same_failure(history, current_probe_entry)
    needs_queue = _needs_queue_for_failure(failure_type)

    result = deepcopy(current)
    result.update(
        {
            "identity_key": identity_key,
            "status": "blocked",
            "failure_type": failure_type,
            "failure_history": history,
            "last_probe": current_probe,
            "reprobe_due": False,
        }
    )
    if consecutive and needs_queue:
        result["status"] = needs_queue
        result["needs_queue"] = needs_queue
        result["wait_condition"] = _wait_condition_for_queue(needs_queue)
        if needs_queue == "needs_network":
            result["next_probe_at"] = _format_time(now + timedelta(days=7))
    return result


def validate_egress_proof(payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    probes = payload.get("probes") if isinstance(payload, Mapping) else None
    if not isinstance(probes, list) or not probes:
        return ["egress proof must contain a non-empty probes list"]

    has_success = False
    for index, probe in enumerate(probes):
        if not isinstance(probe, Mapping):
            findings.append(f"probes[{index}] must be an object")
            continue
        findings.extend(_missing_probe_fields(probe, f"probes[{index}]"))
        if _is_successful_external_egress_probe(probe):
            has_success = True

    if not has_success:
        findings.append("no successful external HTTP egress probe found")
    return findings


def validate_depth_acquisition_smoke(payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    source = payload if isinstance(payload, Mapping) else {}
    status = str(source.get("status", source.get("smoke_status", ""))).strip().lower()
    if status != "pass":
        findings.append("depth acquisition smoke status must be pass")
    if not _first_string(source, "identity_key"):
        findings.append("depth acquisition smoke missing identity_key")
    acquisition_path = _first_string(source, "acquisition_path")
    if not acquisition_path or acquisition_path == "none":
        findings.append("depth acquisition smoke missing acquisition_path")
    if source.get("bounded") is not True:
        findings.append("depth acquisition smoke must set bounded=true")
    if _int(source.get("max_items"), 0) <= 0:
        findings.append("depth acquisition smoke must record positive max_items")

    items = source.get("items", source.get("evidence", []))
    if not isinstance(items, list) or not items:
        findings.append("depth acquisition smoke must contain non-empty items")
        items = []

    source_types = _source_types_for_smoke(source, items)
    page_count = _page_count_for_smoke(source, items)
    if len(source_types) < 2 and page_count < 2:
        findings.append("depth acquisition smoke must include at least two source types or multiple pages")

    if acquisition_path in {"raw_links", "raw/links"} and page_count <= 1 and source_types <= {"raw_links"}:
        findings.append("single-page raw/links smoke cannot support high value deep dive")
    return findings


def validate_source_profile_snapshot(payload: Mapping[str, Any], db_rows: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    snapshot = payload if isinstance(payload, Mapping) else {}
    findings.extend(_sensitive_key_findings(snapshot, ""))

    for key in ("schema_version", "captured_at"):
        if key not in snapshot or snapshot.get(key) in ("", None):
            findings.append(f"source profile snapshot missing {key}")

    channels = snapshot.get("channels")
    sources = snapshot.get("sources")
    if not isinstance(channels, list):
        findings.append("source profile snapshot channels must be a list")
        channels = []
    if not isinstance(sources, list):
        findings.append("source profile snapshot sources must be a list")
        sources = []

    record_counts = snapshot.get("record_counts")
    if not isinstance(record_counts, Mapping):
        findings.append("source profile snapshot missing record_counts")
        record_counts = {}
    else:
        if record_counts.get("channels") != len(channels):
            findings.append(
                f"record_counts.channels {record_counts.get('channels')} does not match {len(channels)} channels"
            )
        if record_counts.get("sources") != len(sources):
            findings.append(
                f"record_counts.sources {record_counts.get('sources')} does not match {len(sources)} sources"
            )

    db_channels = _rows_by_id(db_rows.get("channels") if isinstance(db_rows, Mapping) else None, "channel_id")
    db_sources = _rows_by_id(db_rows.get("sources") if isinstance(db_rows, Mapping) else None, "source_id")
    if isinstance(record_counts, Mapping):
        if record_counts.get("channels") != len(db_channels):
            findings.append(
                f"record_counts.channels {record_counts.get('channels')} does not match current DB count {len(db_channels)}"
            )
        if record_counts.get("sources") != len(db_sources):
            findings.append(
                f"record_counts.sources {record_counts.get('sources')} does not match current DB count {len(db_sources)}"
            )
    captured_at_text = _first_string(snapshot, "captured_at")
    if captured_at_text and _parse_time(captured_at_text) is None:
        findings.append("source profile snapshot captured_at must be a valid timestamp")
    snapshot_channel_ids = {
        str(channel.get("channel_id", "")).strip()
        for channel in channels
        if isinstance(channel, Mapping)
    }

    for index, channel in enumerate(channels):
        if not isinstance(channel, Mapping):
            findings.append(f"channels[{index}] must be an object")
            continue
        expected_identity_key = canonical_identity_key(
            {
                "source_type": "channel",
                "target_domain": _first_string(channel, "target_domain"),
                "base_url": _first_string(channel, "base_url", "canonical_url"),
            }
        )
        observed_identity_key = _first_string(channel, "identity_key")
        if expected_identity_key and observed_identity_key != expected_identity_key:
            findings.append(
                f"channels[{index}].identity_key {observed_identity_key or '<missing>'} "
                f"does not match canonical {expected_identity_key}"
            )
        findings.extend(
            _validate_snapshot_entry(
                entry=channel,
                db_entries=db_channels,
                id_key="channel_id",
                path=f"channels[{index}]",
                required_keys=(
                    "channel_id",
                    "target_domain",
                    "base_url",
                    "trust_level",
                    "auth_state",
                    "canonical_url",
                    "identity_key",
                    "updated_at_watermark",
                ),
                compared_keys=(
                    "target_domain",
                    "base_url",
                    "trust_level",
                    "auth_state",
                    "canonical_url",
                    "identity_key",
                ),
            )
        )

    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            findings.append(f"sources[{index}] must be an object")
            continue
        channel_id = _first_string(source, "channel_id")
        if channel_id and channel_id not in snapshot_channel_ids:
            findings.append(f"sources[{index}].channel_id {channel_id} is not present in snapshot channels")
        findings.extend(
            _validate_snapshot_entry(
                entry=source,
                db_entries=db_sources,
                id_key="source_id",
                path=f"sources[{index}]",
                required_keys=(
                    "source_id",
                    "channel_id",
                    "base_url",
                    "fetcher_type",
                    "schedule",
                    "probe_summary",
                    "canonical_url",
                    "identity_key",
                    "updated_at_watermark",
                ),
                compared_keys=(
                    "channel_id",
                    "base_url",
                    "fetcher_type",
                    "schedule",
                    "canonical_url",
                    "identity_key",
                ),
            )
        )

    return findings


def validate_formal_verification_artifact(
    payload: Mapping[str, Any],
    *,
    run_dir: Path | str | None = None,
) -> list[str]:
    findings: list[str] = []
    source = payload if isinstance(payload, Mapping) else {}
    run_path = Path(run_dir) if run_dir is not None else None
    if _first_string(source, "phase") != "formal_suspicion_pass":
        findings.append("formal verification phase must be formal_suspicion_pass")
    suspicions = source.get("suspicions")
    if not isinstance(suspicions, list):
        return [*findings, "formal verification suspicions must be a list"]

    for index, suspicion in enumerate(suspicions):
        path = f"suspicions[{index}]"
        if not isinstance(suspicion, Mapping):
            findings.append(f"{path} must be an object")
            continue
        suspicion_id = _first_string(suspicion, "id")
        if not suspicion_id:
            findings.append(f"{path}.id is required")
        risk = _first_string(suspicion, "risk").lower()
        if risk not in FORMAL_SUSPICION_RISKS:
            findings.append(f"{path}.risk must be one of {sorted(FORMAL_SUSPICION_RISKS)}")
        if not _first_string(suspicion, "hypothesis"):
            findings.append(f"{path}.hypothesis is required")
        result = _first_string(suspicion, "result").lower()
        if result not in FORMAL_SUSPICION_RESULTS:
            findings.append(f"{path}.result must be one of {sorted(FORMAL_SUSPICION_RESULTS)}")
        if not isinstance(suspicion.get("repair_required"), bool):
            findings.append(f"{path}.repair_required must be a boolean")

        counterexample = suspicion.get("counterexample")
        if not isinstance(counterexample, Mapping):
            findings.append(f"{path}.counterexample must be an object")
            continue
        counterexample_type = _first_string(counterexample, "type")
        if counterexample_type not in FORMAL_COUNTEREXAMPLE_TYPES:
            findings.append(f"{path}.counterexample.type must be one of {sorted(FORMAL_COUNTEREXAMPLE_TYPES)}")
        artifact_path = _first_string(counterexample, "artifact_path")
        if not artifact_path:
            findings.append(f"{path}.counterexample.artifact_path is required")
        command = _first_string(counterexample, "command")
        if result in {"confirmed_bug", "disproved"} and not command:
            findings.append(f"{path}.counterexample.command is required for {result}")
        if run_path is not None and artifact_path:
            findings.extend(_validate_counterexample_artifact(run_path, suspicion, path))
        if result == "confirmed_bug" and suspicion.get("repair_required") is not True:
            findings.append(f"{path}.repair_required must be true for confirmed_bug")
        if result == "disproved" and suspicion.get("repair_required") is not False:
            findings.append(f"{path}.repair_required must be false for disproved")
    return findings


def summarize_formal_verification(
    run_dir: Path | str,
    *,
    required_counterexample_reruns: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    run_id = run_path.name
    formal_dir = run_path / "formal-verification"
    artifact_paths: list[str] = []
    findings: list[str] = []
    suspicions: list[Mapping[str, Any]] = []
    missing_reruns: list[dict[str, str]] = []

    if formal_dir.exists():
        for artifact_path in sorted(formal_dir.glob("*.json")):
            payload = _read_governance_json(artifact_path, f"formal-verification/{artifact_path.name}", findings, [])
            if payload is None:
                continue
            artifact_paths.append(_run_artifact_path(run_id, f"formal-verification/{artifact_path.name}"))
            findings.extend(
                f"formal-verification/{artifact_path.name} {finding}"
                for finding in validate_formal_verification_artifact(payload, run_dir=run_path)
            )
            raw_suspicions = payload.get("suspicions")
            if isinstance(raw_suspicions, list):
                suspicions.extend(item for item in raw_suspicions if isinstance(item, Mapping))

    if findings:
        return {
            "status": "blocked",
            "next_action": "collect_formal_verification_evidence",
            "artifact_paths": artifact_paths,
            "findings": findings,
            "required_counterexample_reruns": [],
        }

    required_reruns = [_normalize_counterexample_requirement(item) for item in (required_counterexample_reruns or [])]
    required_reruns = [item for item in required_reruns if item]
    latest_by_key: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    unkeyed_inconclusive_high_risk: list[str] = []
    for suspicion in suspicions:
        requirement = _counterexample_requirement_from_suspicion(suspicion)
        if requirement:
            latest_by_key[(requirement["id"], requirement["command"], requirement["artifact_path"])] = suspicion
        elif _first_string(suspicion, "result").lower() == "inconclusive" and _first_string(
            suspicion, "risk"
        ).lower() == "high":
            unkeyed_inconclusive_high_risk.append(_first_string(suspicion, "id") or "<unknown>")

    lifecycle_findings: list[str] = []
    observed_reruns: set[tuple[str, str, str]] = set()
    confirmed: list[dict[str, str]] = []
    inconclusive_high_risk: list[str] = list(unkeyed_inconclusive_high_risk)
    for key, suspicion in latest_by_key.items():
        result = _first_string(suspicion, "result").lower()
        risk = _first_string(suspicion, "risk").lower()
        requirement = _counterexample_requirement_from_suspicion(suspicion)
        if result == "disproved":
            if _counterexample_artifact_status(run_path, requirement) == "pass":
                observed_reruns.add(key)
            else:
                lifecycle_findings.append(
                    f"counterexample rerun artifact must record pass for {requirement['id']}"
                )
        elif result == "confirmed_bug":
            if _counterexample_artifact_status(run_path, requirement) == "fail":
                confirmed.append(requirement)
            else:
                lifecycle_findings.append(
                    f"confirmed counterexample artifact must record fail for {requirement['id']}"
                )
        elif result == "inconclusive" and risk == "high":
            inconclusive_high_risk.append(_first_string(suspicion, "id") or "<unknown>")

    if lifecycle_findings:
        return {
            "status": "blocked",
            "next_action": "collect_formal_verification_evidence",
            "artifact_paths": artifact_paths,
            "findings": lifecycle_findings,
            "required_counterexample_reruns": [],
        }

    for requirement in required_reruns:
        key = (requirement["id"], requirement["command"], requirement["artifact_path"])
        if key not in observed_reruns:
            missing_reruns.append(requirement)

    if confirmed:
        return {
            "status": "fail",
            "next_action": "repair_and_reevaluate",
            "artifact_paths": artifact_paths,
            "findings": [],
            "required_counterexample_reruns": confirmed,
        }
    if missing_reruns:
        findings = [
            "original counterexample rerun is still required: "
            + ", ".join(requirement["id"] for requirement in missing_reruns)
        ]
        return {
            "status": "fail",
            "next_action": "repair_and_reevaluate",
            "artifact_paths": artifact_paths,
            "findings": findings,
            "required_counterexample_reruns": required_reruns,
        }
    if inconclusive_high_risk:
        findings = [f"high-risk suspicion remains inconclusive: {suspicion_id}" for suspicion_id in inconclusive_high_risk]
        return {
            "status": "blocked",
            "next_action": "needs_human_judgement",
            "artifact_paths": artifact_paths,
            "findings": findings,
            "required_counterexample_reruns": [],
        }
    return {
        "status": "pass",
        "next_action": "",
        "artifact_paths": artifact_paths,
        "findings": [],
        "required_counterexample_reruns": [],
    }


def governance_preflight_artifact_paths(run_id: str, *, candidate_scoring_paths: list[str] | None = None) -> list[str]:
    base = f".codex/loop-runs/{run_id}"
    paths = [f"{base}/{name}" for name in GOVERNANCE_P0_ARTIFACTS]
    if candidate_scoring_paths:
        paths.extend(candidate_scoring_paths)
    else:
        paths.append(f"{base}/{GOVERNANCE_CANDIDATE_SCORING_GLOB}")
    return paths


def validate_governance_preflight_evidence(run_dir: Path | str) -> dict[str, Any]:
    """Validate run-local AI infra governance P0 artifacts before implementation children."""

    run_path = Path(run_dir)
    run_id = run_path.name
    findings: list[str] = []
    missing_artifacts: list[str] = []
    artifact_paths: list[str] = []

    egress = _read_governance_json(run_path / "egress-proof.json", "egress-proof.json", findings, missing_artifacts)
    if egress is not None:
        artifact_paths.append(_run_artifact_path(run_id, "egress-proof.json"))
        findings.extend(f"egress-proof.json {finding}" for finding in validate_egress_proof(egress))

    identity = _read_governance_json(
        run_path / "identity-key-audit.json", "identity-key-audit.json", findings, missing_artifacts
    )
    if identity is not None:
        artifact_paths.append(_run_artifact_path(run_id, "identity-key-audit.json"))
        findings.extend(validate_identity_key_audit(identity, artifact_label="identity-key-audit.json"))

    depth = _read_governance_json(
        run_path / "depth-acquisition-smoke.json", "depth-acquisition-smoke.json", findings, missing_artifacts
    )
    if depth is not None:
        artifact_paths.append(_run_artifact_path(run_id, "depth-acquisition-smoke.json"))
        findings.extend(
            f"depth-acquisition-smoke.json {finding}" for finding in validate_depth_acquisition_smoke(depth)
        )

    scoring_paths = sorted((run_path / "candidate-scoring").glob("*.json"))
    if not scoring_paths:
        missing_artifacts.append(_run_artifact_path(run_id, GOVERNANCE_CANDIDATE_SCORING_GLOB))
    for scoring_path in scoring_paths:
        relative = f"candidate-scoring/{scoring_path.name}"
        payload = _read_governance_json(scoring_path, relative, findings, missing_artifacts)
        if payload is None:
            continue
        artifact_path = _run_artifact_path(run_id, relative)
        artifact_paths.append(artifact_path)
        findings.extend(validate_candidate_scoring_artifact(payload, artifact_label=relative))

    status = "blocked" if findings or missing_artifacts else "pass"
    return {
        "status": status,
        "run_id": run_id,
        "required_artifacts": governance_preflight_artifact_paths(run_id),
        "missing_artifacts": missing_artifacts,
        "artifact_paths": artifact_paths,
        "findings": findings,
        "next_action": "run_parent_planner" if status == "pass" else "collect_governance_preflight_evidence",
        "reader_summary": _governance_preflight_reader_summary(status, findings, missing_artifacts),
    }


def validate_identity_key_audit(payload: Mapping[str, Any], *, artifact_label: str = "identity-key-audit") -> list[str]:
    findings: list[str] = []
    source = payload if isinstance(payload, Mapping) else {}
    if str(source.get("status", "")).strip().lower() != "pass":
        findings.append(f"{artifact_label} status must be pass")
    candidates = source.get("candidates", source.get("items", []))
    if not isinstance(candidates, list) or not candidates:
        findings.append(f"{artifact_label} must contain a non-empty candidates list")
        return findings
    for index, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            findings.append(f"{artifact_label} candidates[{index}] must be an object")
            continue
        candidate = item.get("candidate", item)
        if not isinstance(candidate, Mapping):
            findings.append(f"{artifact_label} candidates[{index}].candidate must be an object")
            continue
        expected = canonical_identity_key(candidate)
        observed = _first_string(item, "identity_key") or _first_string(candidate, "identity_key")
        if not expected:
            findings.append(f"{artifact_label} candidates[{index}] has no canonical identity key")
        elif observed != expected:
            findings.append(
                f"{artifact_label} candidates[{index}] identity_key {observed or '<missing>'} does not match canonical {expected}"
            )
    return findings


def validate_candidate_scoring_artifact(
    payload: Mapping[str, Any], *, artifact_label: str = "candidate-scoring"
) -> list[str]:
    findings: list[str] = []
    source = payload if isinstance(payload, Mapping) else {}
    if str(source.get("status", "")).strip().lower() != "pass":
        findings.append(f"{artifact_label} status must be pass")
    candidate = source.get("candidate", source)
    if not isinstance(candidate, Mapping):
        return [*findings, f"{artifact_label} candidate must be an object"]

    computed = classify_candidate(candidate)
    expected_identity = str(computed["identity_key"])
    observed_identity = _first_string(source, "identity_key") or _first_string(candidate, "identity_key")
    if not expected_identity:
        findings.append(f"{artifact_label} candidate has no canonical identity key")
    elif observed_identity != expected_identity:
        findings.append(
            f"{artifact_label} identity_key {observed_identity or '<missing>'} does not match computed {expected_identity}"
        )

    declared_classification = _first_string(source, "classification")
    if declared_classification and declared_classification != computed["classification"]:
        findings.append(
            f"{artifact_label} classification {declared_classification} does not match computed {computed['classification']}"
        )

    if "high_value_eligible" in source and bool(source.get("high_value_eligible")) is not computed["high_value_eligible"]:
        findings.append(
            f"{artifact_label} high_value_eligible {source.get('high_value_eligible')} does not match computed "
            f"{computed['high_value_eligible']}"
        )

    return findings


def _run_artifact_path(run_id: str, relative_path: str) -> str:
    return f".codex/loop-runs/{run_id}/{relative_path}"


def _counterexample_requirement_from_suspicion(suspicion: Mapping[str, Any]) -> dict[str, str]:
    counterexample = _mapping(suspicion.get("counterexample"))
    normalized = _normalize_counterexample_requirement(
        {
            "id": _first_string(suspicion, "id"),
            "command": _first_string(counterexample, "command"),
            "artifact_path": _first_string(counterexample, "artifact_path"),
        }
    )
    return normalized


def _normalize_counterexample_requirement(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    suspicion_id = _first_string(value, "id")
    command = _first_string(value, "command")
    artifact_path = _first_string(value, "artifact_path")
    if not (suspicion_id and command and artifact_path):
        return {}
    return {"id": suspicion_id, "command": command, "artifact_path": artifact_path}


def _validate_counterexample_artifact(
    run_path: Path,
    suspicion: Mapping[str, Any],
    path_label: str,
) -> list[str]:
    findings: list[str] = []
    requirement = _counterexample_requirement_from_suspicion(suspicion)
    artifact_path = _first_string(_mapping(suspicion.get("counterexample")), "artifact_path")
    resolved_path = _resolve_counterexample_artifact_path(run_path, artifact_path)
    if not resolved_path.exists():
        return [f"{path_label}.counterexample artifact does not exist: {artifact_path}"]
    if resolved_path.suffix.lower() != ".json":
        return findings
    payload = _read_counterexample_artifact_payload(resolved_path)
    if not isinstance(payload, Mapping):
        return [f"{path_label}.counterexample artifact must be a JSON object: {artifact_path}"]
    observed_id = _first_string(payload, "id", "suspicion_id")
    if observed_id != _first_string(suspicion, "id"):
        findings.append(f"{path_label}.counterexample artifact id does not match suspicion id")
    expected_command = requirement.get("command", "")
    observed_command = _first_string(payload, "command")
    if expected_command and observed_command != expected_command:
        findings.append(f"{path_label}.counterexample artifact command does not match")
    observed_status = _first_string(payload, "status", "result").lower()
    if observed_status not in {"pass", "fail", "failed", "inconclusive", "blocked"}:
        findings.append(f"{path_label}.counterexample artifact status is required")
    return findings


def _counterexample_artifact_status(run_path: Path, requirement: Mapping[str, str]) -> str:
    artifact_path = _first_string(requirement, "artifact_path")
    resolved_path = _resolve_counterexample_artifact_path(run_path, artifact_path)
    payload = _read_counterexample_artifact_payload(resolved_path)
    if not isinstance(payload, Mapping):
        return "missing"
    status = _first_string(payload, "status", "result").lower()
    returncode = payload.get("returncode", payload.get("exit_code"))
    if status in {"pass", "passed"} or returncode == 0:
        return "pass"
    if status in {"fail", "failed"} or (isinstance(returncode, int) and returncode != 0):
        return "fail"
    return status or "missing"


def _read_counterexample_artifact_payload(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_counterexample_artifact_path(run_path: Path, artifact_path: str) -> Path:
    value = Path(artifact_path)
    if value.is_absolute():
        return value
    if artifact_path.startswith(".codex/"):
        return _repo_root_for_run_path(run_path) / value
    return run_path / value


def _repo_root_for_run_path(run_path: Path) -> Path:
    if run_path.parent.name == "loop-runs" and run_path.parent.parent.name == ".codex":
        return run_path.parent.parent.parent
    return run_path


def _read_governance_json(
    path: Path,
    artifact_label: str,
    findings: list[str],
    missing_artifacts: list[str],
) -> dict[str, Any] | None:
    run_id = path.parent.name if path.parent.name != "candidate-scoring" else path.parent.parent.name
    relative = artifact_label if artifact_label.startswith("candidate-scoring/") else path.name
    if not path.exists():
        missing_artifacts.append(_run_artifact_path(run_id, relative))
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        findings.append(f"{artifact_label} invalid JSON: {exc.msg}")
        return None
    if not isinstance(payload, dict):
        findings.append(f"{artifact_label} must be a JSON object")
        return None
    return payload


def _governance_preflight_reader_summary(
    status: str, findings: list[str], missing_artifacts: list[str]
) -> dict[str, str]:
    if status == "pass":
        return {
            "purpose": "AI infra loop governance preflight",
            "current_progress": "P0 governance preflight artifacts validated",
            "next_step": "Run parent planner",
            "decision_needed": "No",
        }
    issue_count = len(findings) + len(missing_artifacts)
    return {
        "purpose": "AI infra loop governance preflight",
        "current_progress": f"Blocked on {issue_count} P0 evidence issue(s)",
        "next_step": "Collect P0 governance preflight artifacts before implementation children",
        "decision_needed": "Yes",
    }


def _canonical_url_without_prefix(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return ""

    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not host:
        return ""

    try:
        port = parts.port
    except ValueError:
        port = None
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    netloc = host if port is None or default_port else f"{host}:{port}"

    path = parts.path or ""
    if path != "/":
        path = path.rstrip("/")
    else:
        path = ""

    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        normalized_key = key.strip()
        key_lc = normalized_key.lower()
        if key_lc.startswith("utm_") or key_lc in TRACKING_QUERY_KEYS:
            continue
        query_pairs.append((normalized_key, value))
    query_pairs.sort(key=lambda item: (item[0].lower(), item[1]))
    query = "&".join(f"{key}={value}" if value != "" else key for key, value in query_pairs)

    return urlunsplit((scheme, netloc, path, query, ""))


def _github_key_from_url(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if host == "www.github.com":
        host = "github.com"
    if host != "github.com":
        return ""
    segments = [unquote(segment) for segment in parts.path.split("/") if segment]
    if len(segments) < 2:
        return ""

    owner = segments[0].lower()
    repo = _strip_git_suffix(segments[1]).lower()
    if len(segments) == 2:
        return f"github-repo:{owner}/{repo}"
    if len(segments) >= 4 and segments[2] == "issues" and segments[3].isdigit():
        return f"github-issue:{owner}/{repo}#{segments[3]}"
    if len(segments) >= 4 and segments[2] in {"pull", "pulls"} and segments[3].isdigit():
        return f"github-pr:{owner}/{repo}#{segments[3]}"
    if len(segments) >= 5 and segments[2] == "releases" and segments[3] == "tag":
        tag = "/".join(segments[4:])
        return f"github-release:{owner}/{repo}@{tag}"
    return f"github-repo:{owner}/{repo}"


def _github_repo_key_from_fields(candidate: Mapping[str, Any]) -> str:
    owner = _first_string(candidate, "owner", "github_owner").lower()
    repo = _strip_git_suffix(_first_string(candidate, "repo", "repository", "github_repo")).lower()
    return f"github-repo:{owner}/{repo}" if owner and repo else ""


def _github_issue_or_pr_key_from_fields(candidate: Mapping[str, Any], prefix: str) -> str:
    owner = _first_string(candidate, "owner", "github_owner").lower()
    repo = _strip_git_suffix(_first_string(candidate, "repo", "repository", "github_repo")).lower()
    number = _first_string(candidate, "number", "issue_number", "pr_number")
    return f"{prefix}:{owner}/{repo}#{number}" if owner and repo and number.isdigit() else ""


def _github_release_key_from_fields(candidate: Mapping[str, Any]) -> str:
    owner = _first_string(candidate, "owner", "github_owner").lower()
    repo = _strip_git_suffix(_first_string(candidate, "repo", "repository", "github_repo")).lower()
    tag = _first_string(candidate, "tag", "release_tag")
    return f"github-release:{owner}/{repo}@{tag}" if owner and repo and tag else ""


def _hardware_identity_key(candidate: Mapping[str, Any]) -> str:
    vendor = _slug(_first_string(candidate, "vendor"))
    model = _slug(_first_string(candidate, "model"))
    variant = _slug(_first_string(candidate, "variant", "sku_or_memory_variant", "sku", "memory_variant"))
    return f"hardware:{vendor}:{model}:{variant}" if vendor and model and variant else ""


def _normalized_doi(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    return text.lower()


def _normalized_doi_from_url(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    host = (parts.hostname or "").lower()
    if host in {"doi.org", "dx.doi.org"} and parts.path.strip("/"):
        return _normalized_doi(parts.path.strip("/"))
    return ""


def _normalized_arxiv(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^arxiv:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", text, flags=re.IGNORECASE)
    text = text.removesuffix(".pdf")
    return text.lower()


def _normalized_arxiv_from_url(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    if (parts.hostname or "").lower() != "arxiv.org":
        return ""
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) >= 2 and segments[0] in {"abs", "pdf"}:
        return _normalized_arxiv(segments[1])
    return ""


def _source_type(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("source_type", candidate.get("kind", ""))).strip().lower().replace("-", "_")


def _first_string(mapping: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _slug(value: str) -> str:
    return SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")


def _domain_slug(value: str) -> str:
    return DOMAIN_RE.sub("-", str(value or "").strip().lower()).strip("-")


def _strip_git_suffix(value: str) -> str:
    return str(value or "").removesuffix(".git")


def _is_canonical_identity_key(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("url:"):
        return bool(_canonical_url_without_prefix(text.removeprefix("url:")))
    if text.startswith("github-repo:"):
        return bool(re.fullmatch(r"github-repo:[^/\s]+/[^#@\s]+", text))
    if text.startswith(("github-issue:", "github-pr:")):
        return bool(re.fullmatch(r"github-(issue|pr):[^/\s]+/[^#@\s]+#[0-9]+", text))
    if text.startswith("github-release:"):
        return bool(re.fullmatch(r"github-release:[^/\s]+/[^@\s]+@.+", text))
    if text.startswith("doi:"):
        return bool(text.removeprefix("doi:"))
    if text.startswith("arxiv:"):
        return bool(text.removeprefix("arxiv:"))
    if text.startswith("hardware:"):
        return bool(re.fullmatch(r"hardware:[^:]+:[^:]+:[^:]+", text))
    if text.startswith("channel:"):
        return bool(re.fullmatch(r"channel:[^:]+:https?://.+", text))
    if text.startswith("source-profile:"):
        return bool(text.removeprefix("source-profile:"))
    if text.startswith("raw-sha256:"):
        return bool(re.fullmatch(r"raw-sha256:[0-9a-fA-F]+", text))
    return False


def _is_hex_digest(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]+", str(value or "").strip()))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _has_blocked_marker(source: Mapping[str, Any], decision_inputs: Mapping[str, Any]) -> bool:
    if str(source.get("classification", "")).strip().lower() == "blocked":
        return True
    for key in ("blocked_reason", "needs_queue", "wait_condition"):
        if _first_string(source, key) or _first_string(decision_inputs, key):
            return True
    return False


def _classification_rationale(
    classification: str, missing_hard_gates: list[str], missing_inputs: list[str]
) -> str:
    if classification == "high_value":
        return "hard gates and decision inputs satisfy high value deep dive criteria"
    if classification == "blocked":
        return "candidate is blocked by an explicit wait condition"
    if missing_hard_gates:
        return f"missing hard gates: {', '.join(missing_hard_gates)}"
    if missing_inputs:
        return f"missing decision inputs: {', '.join(missing_inputs)}"
    return "candidate does not satisfy high value criteria"


def _probe_time(probe: Mapping[str, Any]) -> datetime:
    return _parse_time(_first_string(probe, "finished_at", "started_at")) or DEFAULT_PROBE_TIME


def _parse_time(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _failure_type(probe: Mapping[str, Any]) -> str:
    explicit = _first_string(probe, "failure_type", "error_class").lower()
    if explicit:
        return explicit
    status = probe.get("http_status")
    if isinstance(status, int):
        if status == 403:
            return "http_403"
        if status == 429:
            return "http_429"
        if status >= 500:
            return "http_5xx"
    return ""


def _is_reprobe_due(item: Mapping[str, Any], now: datetime) -> bool:
    next_probe_at = _parse_time(_first_string(item, "next_probe_at"))
    if next_probe_at is None:
        return True
    return now >= next_probe_at


def _network_state_change_findings(item: Mapping[str, Any], probe: Mapping[str, Any]) -> list[str]:
    findings = _missing_probe_fields(probe, "network_state_changed probe")
    if not _probe_http_reachable(probe):
        findings.append("network_state_changed probe must be HTTP reachable")
    if not _probe_matches_waiting_network_scope(item, probe):
        findings.append("network_state_changed probe must use the same identity_key or canonical host as the waiting item")
    return findings


def _probe_matches_waiting_network_scope(item: Mapping[str, Any], probe: Mapping[str, Any]) -> bool:
    waiting_identity = _first_string(item, "identity_key")
    probe_identity = _first_string(probe, "identity_key")
    if waiting_identity and probe_identity and waiting_identity == probe_identity:
        return True

    last_probe = item.get("last_probe")
    last_probe_mapping = last_probe if isinstance(last_probe, Mapping) else {}
    waiting_urls = [
        _first_string(item, "probe_url"),
        _first_string(last_probe_mapping, "probe_url"),
        _url_from_identity_key(waiting_identity),
    ]
    probe_urls = [
        _first_string(probe, "probe_url"),
        _first_string(probe, "final_url"),
        _url_from_identity_key(probe_identity),
    ]
    waiting_canonicals = {_canonical_url_without_prefix(url) for url in waiting_urls if url}
    probe_canonicals = {_canonical_url_without_prefix(url) for url in probe_urls if url}
    if waiting_canonicals and probe_canonicals and waiting_canonicals.intersection(probe_canonicals):
        return True

    waiting_hosts = {_host_from_url(url) for url in waiting_urls if url}
    probe_hosts = {_host_from_url(url) for url in probe_urls if url}
    source_boundary = _first_string(item, "source_boundary") or _first_string(last_probe_mapping, "source_boundary")
    if source_boundary.startswith("host:"):
        waiting_hosts.add(source_boundary.removeprefix("host:").lower())
    waiting_hosts.discard("")
    probe_hosts.discard("")
    return bool(waiting_hosts and probe_hosts and waiting_hosts.intersection(probe_hosts))


def _missing_probe_fields(probe: Mapping[str, Any], prefix: str) -> list[str]:
    findings: list[str] = []
    for key in (
        "probe_url",
        "started_at",
        "finished_at",
        "dns_status",
        "tls_status",
        "http_status",
        "final_url",
        "error_class",
        "summary",
    ):
        if key not in probe:
            findings.append(f"{prefix}.{key} is required")
            continue
        if key not in {"http_status", "error_class"} and probe.get(key) in ("", None):
            findings.append(f"{prefix}.{key} is required")
    return findings


def _probe_http_reachable(probe: Mapping[str, Any]) -> bool:
    status = probe.get("http_status")
    return (
        str(probe.get("dns_status", "")).strip().lower() in PASS_STATUSES
        and str(probe.get("tls_status", "")).strip().lower() in PASS_STATUSES
        and isinstance(status, int)
        and 200 <= status < 400
    )


def _has_consecutive_same_failure(history: list[Any], current_probe_entry: Mapping[str, Any]) -> bool:
    comparable_history = [entry for entry in history if isinstance(entry, Mapping)]
    if len(comparable_history) < 2:
        return False
    previous = comparable_history[-2]
    return (
        _first_string(previous, "identity_key") == _first_string(current_probe_entry, "identity_key")
        and _first_string(previous, "failure_type") == _first_string(current_probe_entry, "failure_type")
        and _first_string(previous, "source_boundary")
        == _first_string(current_probe_entry, "source_boundary")
        and _first_string(previous, "status") == "blocked"
        and _first_string(current_probe_entry, "status") == "blocked"
    )


def _needs_queue_for_failure(failure_type: str) -> str:
    normalized = str(failure_type or "").strip().lower()
    if normalized in NETWORK_FAILURE_TYPES:
        return "needs_network"
    if normalized in AUTH_FAILURE_TYPES:
        return "needs_auth"
    if normalized in SEED_FAILURE_TYPES:
        return "needs_seed_url"
    if normalized in HUMAN_FAILURE_TYPES:
        return "needs_human_judgement"
    return ""


def _wait_condition_for_queue(queue: str) -> str:
    return {
        "needs_network": "network_state_changed",
        "needs_auth": "auth_configured",
        "needs_seed_url": "seed_url_added",
        "needs_human_judgement": "user_requested_retry",
    }.get(queue, "")


def _is_successful_external_egress_probe(probe: Mapping[str, Any]) -> bool:
    return _is_external_url(_first_string(probe, "probe_url")) and _probe_http_reachable(probe)


def _is_external_url(url: str) -> bool:
    parts = urlsplit(str(url or "").strip())
    host = parts.hostname
    if not host:
        return False
    host_lc = host.lower()
    if host_lc in {"localhost", "127.0.0.1", "::1"} or host_lc.endswith(".local"):
        return False
    try:
        address = ip_address(host_lc)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local)


def _url_from_identity_key(identity_key: str) -> str:
    value = str(identity_key or "").strip()
    return value.removeprefix("url:") if value.startswith("url:") else ""


def _host_from_url(url: str) -> str:
    try:
        return (urlsplit(str(url or "").strip()).hostname or "").lower()
    except ValueError:
        return ""


def _source_types_for_smoke(source: Mapping[str, Any], items: list[Any]) -> set[str]:
    explicit = source.get("source_types", [])
    source_types: set[str] = set()
    if isinstance(explicit, list):
        source_types.update(str(item).strip().lower() for item in explicit if str(item).strip())
    for item in items:
        if isinstance(item, Mapping):
            source_type = _first_string(item, "source_type", "kind").lower()
            if source_type:
                source_types.add(source_type)
    return source_types


def _page_count_for_smoke(source: Mapping[str, Any], items: list[Any]) -> int:
    explicit = _int(source.get("page_count"), 0)
    if explicit > 0:
        return explicit
    urls = {
        _first_string(item, "url", "canonical_url")
        for item in items
        if isinstance(item, Mapping) and _first_string(item, "url", "canonical_url")
    }
    return len(urls) if urls else len(items)


def _sensitive_key_findings(value: Any, path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            normalized = key_text.lower()
            child_path = f"{path}.{key_text}" if path else key_text
            if (
                normalized in SENSITIVE_SNAPSHOT_KEYS
                or normalized.endswith("_token")
                or normalized.endswith("_secret")
                or _contains_sensitive_snapshot_fragment(normalized)
            ):
                findings.append(f"sensitive key {child_path} must not be present in source profile snapshot")
            findings.extend(_sensitive_key_findings(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_sensitive_key_findings(item, f"{path}[{index}]"))
    return findings


def _contains_sensitive_snapshot_fragment(normalized_key: str) -> bool:
    compact = re.sub(r"[^a-z0-9]+", "", normalized_key)
    snake_like = re.sub(r"[^a-z0-9_]+", "_", normalized_key)
    for fragment in SENSITIVE_SNAPSHOT_KEY_FRAGMENTS:
        compact_fragment = fragment.replace("_", "")
        if fragment in snake_like or compact_fragment in compact:
            return True
    return False


def _rows_by_id(rows: Any, id_key: str) -> dict[str, Mapping[str, Any]]:
    if isinstance(rows, Mapping):
        result: dict[str, Mapping[str, Any]] = {}
        for key, value in rows.items():
            if isinstance(value, Mapping):
                result[str(key)] = value
        return result
    if isinstance(rows, list):
        return {
            _first_string(row, id_key): row
            for row in rows
            if isinstance(row, Mapping) and _first_string(row, id_key)
        }
    return {}


def _validate_snapshot_entry(
    *,
    entry: Mapping[str, Any],
    db_entries: Mapping[str, Mapping[str, Any]],
    id_key: str,
    path: str,
    required_keys: tuple[str, ...],
    compared_keys: tuple[str, ...],
) -> list[str]:
    findings: list[str] = []
    for key in required_keys:
        if key not in entry or entry.get(key) in ("", None):
            findings.append(f"{path}.{key} is required")

    entry_id = _first_string(entry, id_key)
    if not entry_id:
        return findings
    db_entry = db_entries.get(entry_id)
    if not isinstance(db_entry, Mapping):
        findings.append(f"{path} id {entry_id} is missing from current SQLite rows")
        return findings

    for key in compared_keys:
        snapshot_value = entry.get(key)
        db_value = db_entry.get(key)
        if db_value != snapshot_value:
            findings.append(
                f"{path}.{key} snapshot value {snapshot_value!r} does not match current DB value {db_value!r}"
            )

    watermark_text = _first_string(entry, "updated_at_watermark")
    watermark = _parse_time(watermark_text)
    if watermark_text and watermark is None:
        findings.append(f"{path}.updated_at_watermark must be a valid timestamp")
    db_updated_at_text = _first_string(db_entry, "updated_at")
    db_updated_at = _parse_time(db_updated_at_text)
    if db_updated_at_text and db_updated_at is None:
        findings.append(f"{path} current DB updated_at must be a valid timestamp")
    if watermark is not None and db_updated_at is not None and db_updated_at > watermark:
        findings.append(
            f"{entry_id} updated_at {db_updated_at_text} is newer than snapshot watermark "
            f"{watermark_text}"
        )
    return findings
