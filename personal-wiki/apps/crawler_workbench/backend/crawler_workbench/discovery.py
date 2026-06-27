from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any

import yaml

from .fetchers.base import FetchResult
from .profiles import load_profiles_from_yaml, validate_accelerator_metadata, validate_profile_source_id


MODEL_PATTERNS = [
    re.compile(r"\b(H|B|GB|MI|TPU|Trainium|Inferentia|Gaudi|Atlas|MLU|R|C|S|TG|ZK)\s?-?\d{2,4}[A-Za-z0-9-]*\b", re.I),
]

EVIDENCE_KEYWORDS = {
    "accelerator",
    "gpu",
    "npu",
    "tpu",
    "dpu",
    "ipu",
    "fpga",
    "asic",
    "training",
    "inference",
}


@dataclass
class AcceleratorCandidate:
    vendor: str
    model_name: str
    normalized_model: str
    scope: str
    source_url: str
    evidence_url: str | None
    evidence_text: str
    confidence: float


def extract_accelerator_candidates(profile: dict[str, Any], results: list[FetchResult]) -> list[AcceleratorCandidate]:
    if profile.get("discovery_mode") != "accelerator_models":
        return []
    vendor = str(profile.get("vendor_hint") or "").strip().lower() or "unknown"
    scope = _scope_from_profile(profile)
    candidates: dict[tuple[str, str], AcceleratorCandidate] = {}
    for result in results:
        source_url = str(result.metadata.get("source_url") or result.canonical_url)
        for match in _model_matches(result.content, profile):
            model = _clean_model(match.group(0))
            normalized = normalize_model(model)
            evidence = _evidence_window(result.content, match.start(), match.end())
            key = (normalized, source_url)
            confidence = _confidence(evidence, profile)
            candidate = AcceleratorCandidate(
                vendor=vendor,
                model_name=model,
                normalized_model=normalized,
                scope=scope,
                source_url=source_url,
                evidence_url=source_url,
                evidence_text=evidence,
                confidence=confidence,
            )
            previous = candidates.get(key)
            if previous is None or candidate.confidence > previous.confidence:
                candidates[key] = candidate
    return list(candidates.values())


def upsert_candidates(
    db: sqlite3.Connection,
    profile: dict[str, Any],
    candidates: list[AcceleratorCandidate],
) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for candidate in candidates:
        row = db.execute(
            """
            select * from accelerator_candidates
            where vendor = ? and normalized_model = ? and coalesce(evidence_url, source_url) = ?
            """,
            (candidate.vendor, candidate.normalized_model, candidate.evidence_url or candidate.source_url),
        ).fetchone()
        if row is None:
            db.execute(
                """
                insert into accelerator_candidates (
                  vendor, model_name, normalized_model, scope, source_profile_id, source_url,
                  evidence_url, evidence_text, confidence, status
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    candidate.vendor,
                    candidate.model_name,
                    candidate.normalized_model,
                    candidate.scope,
                    profile["id"],
                    candidate.source_url,
                    candidate.evidence_url,
                    candidate.evidence_text,
                    candidate.confidence,
                ),
            )
            counts["created"] += 1
            continue
        if row["status"] == "pending" and (
            float(row["confidence"]) < candidate.confidence or row["evidence_text"] != candidate.evidence_text
        ):
            db.execute(
                """
                update accelerator_candidates
                set model_name = ?, scope = ?, source_url = ?, evidence_url = ?,
                    evidence_text = ?, confidence = ?, updated_at = current_timestamp
                where id = ?
                """,
                (
                    candidate.model_name,
                    candidate.scope,
                    candidate.source_url,
                    candidate.evidence_url,
                    candidate.evidence_text,
                    candidate.confidence,
                    row["id"],
                ),
            )
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
    return counts


def list_candidates(db: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    if status is None:
        rows = db.execute("select * from accelerator_candidates order by id").fetchall()
    else:
        rows = db.execute(
            "select * from accelerator_candidates where status = ? order by id",
            (status,),
        ).fetchall()
    return [dict(row) for row in rows]


def reject_candidate(db: sqlite3.Connection, candidate_id: int) -> dict[str, Any]:
    candidate = _candidate_by_id(db, candidate_id)
    _require_pending(candidate)
    db.execute(
        """
        update accelerator_candidates
        set status = 'rejected', updated_at = current_timestamp
        where id = ?
        """,
        (candidate["id"],),
    )
    db.commit()
    return _candidate_by_id(db, candidate_id)


def accept_candidate(db: sqlite3.Connection, candidate_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    candidate = _candidate_by_id(db, candidate_id)
    _require_pending(candidate)
    source_id = str(payload["source_id"])
    source_profile = _accepted_source_profile(candidate, payload, source_id)
    validate_profile_source_id(source_profile)
    validate_accelerator_metadata(source_profile)
    config_json = _accepted_source_config_json(source_profile)
    sources_yaml_path = payload.get("sources_yaml_path")
    if sources_yaml_path is not None:
        _persist_accepted_source(Path(sources_yaml_path), source_profile)
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, run_policy, auth_state, config_json, topic, enabled
        )
        values (?, ?, 'web', 'ai_infra', ?, 'trusted', 'monthly', 0, 0, 'once', 'ready', ?, ?, 1)
        on conflict(id) do update set
          name = excluded.name,
          type = excluded.type,
          target_domain = excluded.target_domain,
          url = excluded.url,
          trust_level = excluded.trust_level,
          schedule = excluded.schedule,
          auto_ingest = excluded.auto_ingest,
          auth_required = excluded.auth_required,
          run_policy = excluded.run_policy,
          auth_state = excluded.auth_state,
          config_json = excluded.config_json,
          topic = excluded.topic,
          enabled = excluded.enabled,
          updated_at = current_timestamp
        """,
        (
            source_profile["id"],
            source_profile["name"],
            source_profile["url"],
            config_json,
            source_profile["topic"],
        ),
    )
    db.execute(
        """
        update accelerator_candidates
        set status = 'accepted',
            accepted_source_id = ?,
            updated_at = current_timestamp
        where id = ?
        """,
        (source_id, candidate["id"]),
    )
    db.commit()
    return _candidate_by_id(db, candidate_id)


def normalize_model(model: str) -> str:
    return re.sub(r"[\s-]+", "", model).upper()


def _candidate_by_id(db: sqlite3.Connection, candidate_id: int) -> dict[str, Any]:
    row = db.execute("select * from accelerator_candidates where id = ?", (candidate_id,)).fetchone()
    if row is None:
        raise ValueError(f"candidate not found: {candidate_id}")
    return dict(row)


def _require_pending(candidate: dict[str, Any]) -> None:
    if candidate["status"] != "pending":
        raise ValueError(f"candidate {candidate['id']} must be pending")


def _accepted_source_profile(candidate: dict[str, Any], payload: dict[str, Any], source_id: str) -> dict[str, Any]:
    return {
        "id": source_id,
        "name": payload["name"],
        "type": "web",
        "target_domain": "ai_infra",
        "url": payload["url"],
        "trust_level": "trusted",
        "schedule": "monthly",
        "auto_ingest": False,
        "auth_required": False,
        "run_policy": "once",
        "topic": f"{candidate['vendor']} {candidate['model_name']} accelerator specs",
        "source_rank": payload.get("source_rank", "S1"),
        "accelerator_scope": payload["scope"],
        "extract_mode": "specs_candidate",
        "vendor_hint": candidate["vendor"],
        "auto_resolve": False,
    }


def _accepted_source_config_json(source_profile: dict[str, Any]) -> str:
    return json.dumps(
        {
            "source_rank": source_profile["source_rank"],
            "accelerator_scope": source_profile["accelerator_scope"],
            "extract_mode": source_profile["extract_mode"],
            "vendor_hint": source_profile["vendor_hint"],
            "auto_resolve": source_profile["auto_resolve"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _persist_accepted_source(path: Path, source_profile: dict[str, Any]) -> None:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        data = {}
    sources = data.get("sources")
    if sources is None:
        sources = []
        data["sources"] = sources
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")

    yaml_source = _accepted_source_yaml(source_profile)
    for index, source in enumerate(sources):
        if isinstance(source, dict) and source.get("id") == source_profile["id"]:
            sources[index] = yaml_source
            break
    else:
        sources.append(yaml_source)

    rendered = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    _validate_profiles_yaml_text(rendered)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def _accepted_source_yaml(source_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": source_profile["id"],
        "name": source_profile["name"],
        "type": source_profile["type"],
        "target_domain": source_profile["target_domain"],
        "url": source_profile["url"],
        "trust_level": source_profile["trust_level"],
        "schedule": source_profile["schedule"],
        "run_policy": source_profile["run_policy"],
        "auto_ingest": source_profile["auto_ingest"],
        "auth_required": source_profile["auth_required"],
        "baseline_on_first_run": False,
        "topic": source_profile["topic"],
        "source_rank": source_profile["source_rank"],
        "accelerator_scope": source_profile["accelerator_scope"],
        "extract_mode": source_profile["extract_mode"],
        "vendor_hint": source_profile["vendor_hint"],
        "auto_resolve": source_profile["auto_resolve"],
    }


def _validate_profiles_yaml_text(rendered: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml") as handle:
        handle.write(rendered)
        handle.flush()
        load_profiles_from_yaml(Path(handle.name))


def _model_matches(text: str, profile: dict[str, Any]) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    for pattern in _model_patterns_for_profile(profile):
        matches.extend(pattern.finditer(text))
    unique: dict[tuple[int, int, str], re.Match[str]] = {}
    for match in matches:
        unique.setdefault((match.start(), match.end(), match.group(0)), match)
    return sorted(unique.values(), key=lambda match: match.start())


def _model_patterns_for_profile(profile: dict[str, Any]) -> list[re.Pattern[str]]:
    patterns = list(MODEL_PATTERNS)
    seen = {(pattern.pattern, pattern.flags) for pattern in patterns}
    for pattern_text in profile.get("include_patterns", []):
        if not isinstance(pattern_text, str):
            continue
        try:
            pattern = re.compile(pattern_text, re.I)
        except re.error:
            continue
        key = (pattern.pattern, pattern.flags)
        if key not in seen:
            patterns.append(pattern)
            seen.add(key)
    return patterns


def _clean_model(model: str) -> str:
    cleaned = re.sub(r"\s+", "", model.strip())
    return cleaned.upper()


def _evidence_window(text: str, start: int, end: int, radius: int = 90) -> str:
    window_start = max(0, start - radius)
    window_end = min(len(text), end + radius)
    return " ".join(text[window_start:window_end].split())


def _scope_from_profile(profile: dict[str, Any]) -> str:
    scopes = profile.get("accelerator_scope")
    if isinstance(scopes, list) and scopes:
        return str(scopes[0])
    return "gpu"


def _confidence(evidence: str, profile: dict[str, Any]) -> float:
    lowered = evidence.lower()
    score = 0.55
    if str(profile.get("vendor_hint") or "").lower() in lowered:
        score += 0.1
    if any(keyword in lowered for keyword in EVIDENCE_KEYWORDS):
        score += 0.2
    if any(str(scope).lower() in lowered for scope in profile.get("accelerator_scope", [])):
        score += 0.05
    return min(score, 0.95)
