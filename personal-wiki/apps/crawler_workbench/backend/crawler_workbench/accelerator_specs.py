from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .settings import Settings


SOURCE_ID_PREFIX = "compute-accelerators-"


@dataclass(frozen=True)
class ExtractedObservation:
    field: str
    value: str | int | float
    unit: str
    evidence_text: str
    confidence: float


def extract_observations_from_text(
    profile: dict[str, Any],
    raw_item: dict[str, Any],
    text: str,
) -> list[ExtractedObservation]:
    del profile, raw_item

    observations: list[ExtractedObservation] = []
    seen: set[tuple[str, str, str]] = set()

    for observation in [
        *_extract_tdp(text),
        *_extract_memory_capacity(text),
        *_extract_memory_bandwidth(text),
        *_extract_network_bandwidth(text),
        *_extract_form_factor(text),
        *_extract_host_interface(text),
    ]:
        key = (observation.field, _value_text(observation.value), observation.unit)
        if key not in seen:
            observations.append(observation)
            seen.add(key)

    return observations


def upsert_extracted_specs_for_raw_item(
    settings: Settings,
    db: sqlite3.Connection,
    raw_item_id: int,
) -> dict[str, int]:
    row = db.execute(
        """
        select
          raw_items.*,
          source_profiles.name as source_name,
          source_profiles.url as source_url,
          source_profiles.config_json as profile_config_json
        from raw_items
        join source_profiles on source_profiles.id = raw_items.source_id
        where raw_items.id = ?
        """,
        (raw_item_id,),
    ).fetchone()
    if row is None:
        return {"skus": 0, "observations": 0, "resolved": 0}

    raw_item = dict(row)
    profile = _profile_from_raw_item(raw_item)
    if profile.get("extract_mode") != "specs_candidate":
        return {"skus": 0, "observations": 0, "resolved": 0}

    raw_path = str(raw_item["raw_path"])
    text_path = _raw_path(settings, raw_path)
    text = text_path.read_text(encoding="utf-8")
    observations = extract_observations_from_text(profile, raw_item, text)
    if not observations:
        return {"skus": 0, "observations": 0, "resolved": 0}

    sku_id = _sku_id(str(raw_item["source_id"]))
    _upsert_sku(db, profile, raw_item, sku_id)
    observation_ids = _upsert_observations(db, profile, raw_item, sku_id, observations)
    resolved_count = _resolve_observations(db, profile, sku_id, observations, observation_ids)
    return {"skus": 1, "observations": len(observation_ids), "resolved": resolved_count}


def extract_specs_for_all_raw_items(settings: Settings, db: sqlite3.Connection) -> dict[str, int]:
    rows = db.execute(
        """
        select raw_items.id
        from raw_items
        join source_profiles on source_profiles.id = raw_items.source_id
        order by raw_items.id
        """
    ).fetchall()
    totals = {"skus": 0, "observations": 0, "resolved": 0}
    for row in rows:
        counts = upsert_extracted_specs_for_raw_item(settings, db, int(row["id"]))
        totals["skus"] += counts["skus"]
        totals["observations"] += counts["observations"]
        totals["resolved"] += counts["resolved"]
    return totals


def list_accelerator_specs(db: sqlite3.Connection) -> list[dict[str, object]]:
    sku_rows = db.execute(
        """
        select sku_id, vendor, model_name, normalized_model, scope, source_profile_id,
               source_url, raw_item_id, raw_path
        from accelerator_skus
        order by sku_id
        """
    ).fetchall()
    specs: list[dict[str, object]] = []
    for row in sku_rows:
        sku = dict(row)
        sku["observations"] = [
            dict(observation)
            for observation in db.execute(
                """
                select id, field, value_text, value_number, unit, source_profile_id, source_rank,
                       raw_item_id, raw_path, evidence_text, confidence
                from accelerator_observations
                where sku_id = ?
                order by field, id
                """,
                (row["sku_id"],),
            ).fetchall()
        ]
        sku["resolved_specs"] = [
            dict(resolved)
            for resolved in db.execute(
                """
                select field, value_text, value_number, unit, source_observation_id,
                       resolved_by, confidence, conflict_status
                from accelerator_resolved_specs
                where sku_id = ?
                order by field
                """,
                (row["sku_id"],),
            ).fetchall()
        ]
        specs.append(sku)
    return specs


def _extract_tdp(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(r"(峰值功耗\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?)\s*W)", re.I),
        re.compile(r"\b(TDP\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?)\s*W)\b", re.I),
    ]
    return [
        ExtractedObservation("tdp", _number(match.group("value")), "W", _clean_evidence(match.group(1)), 0.9)
        for pattern in patterns
        for match in pattern.finditer(text)
    ]


def _extract_memory_capacity(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(
            r"((?:memory|显存|内存|存储容量|HBM(?:\d\w*)?)\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>GB|GiB|TB|TiB)\s*(?:HBM\d\w*)?)",
            re.I,
        ),
        re.compile(
            r"((?P<value>\d+(?:\.\d+)?)\s*(?P<unit>GB|GiB|TB|TiB)\s+HBM\d\w*)",
            re.I,
        ),
    ]
    return [
        ExtractedObservation(
            "memory_capacity",
            _number(match.group("value")),
            _unit(match.group("unit")),
            _clean_evidence(match.group(1)),
            0.85,
        )
        for pattern in patterns
        for match in pattern.finditer(text)
    ]


def _extract_memory_bandwidth(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(
            r"((?:memory\s+bandwidth|显存带宽|内存带宽)\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>TB/s|GB/s|TByte/s|GByte/s))",
            re.I,
        ),
    ]
    return [
        ExtractedObservation(
            "memory_bandwidth",
            _number(match.group("value")),
            _unit(match.group("unit")),
            _clean_evidence(match.group(1)),
            0.85,
        )
        for pattern in patterns
        for match in pattern.finditer(text)
    ]


def _extract_network_bandwidth(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(
            r"((?:network\s+bandwidth|网络带宽|互联带宽|端口带宽)\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>Gb/s|Gbit/s|Gbps|GB/s|TB/s))",
            re.I,
        ),
        re.compile(
            r"((?P<value>\d+(?:\.\d+)?)\s*(?P<unit>Gb/s|Gbit/s|Gbps)\s*(?:network|Ethernet|以太网|网络))",
            re.I,
        ),
    ]
    return [
        ExtractedObservation(
            "network_bandwidth",
            _number(match.group("value")),
            _unit(match.group("unit")),
            _clean_evidence(match.group(1)),
            0.85,
        )
        for pattern in patterns
        for match in pattern.finditer(text)
    ]


def _extract_form_factor(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(r"(产品形态为(?P<value>[^。\n\r，,；;]{2,80}))"),
        re.compile(r"((?:form\s+factor|形态)\s*[:：]\s*(?P<value>[^。\n\r，,；;]{2,80}))", re.I),
    ]
    observations: list[ExtractedObservation] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = _clean_phrase(match.group("value"))
            if value:
                observations.append(
                    ExtractedObservation("form_factor", value, "none", _clean_evidence(match.group(1)), 0.85)
                )
    return observations


def _extract_host_interface(text: str) -> list[ExtractedObservation]:
    patterns = [
        re.compile(r"\b(?P<value>PCIe\s+Gen\s*\d(?:\.\d)?\s*x\s*\d{1,2})\b", re.I),
        re.compile(r"\b(?P<value>PCIe\s*\d(?:\.\d)?\s*x\s*\d{1,2})\b", re.I),
    ]
    observations: list[ExtractedObservation] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = _normalize_pcie(match.group("value"))
            observations.append(ExtractedObservation("host_interface", value, "none", value, 0.9))
    return observations


def _profile_from_raw_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    config = _profile_config(raw_item.get("profile_config_json"))
    profile = {
        "id": raw_item["source_id"],
        "name": raw_item.get("source_name") or raw_item["source_id"],
        "url": raw_item.get("source_url") or raw_item["canonical_url"],
    }
    profile.update(config)
    return profile


def _profile_config(config_json: object) -> dict[str, Any]:
    if not isinstance(config_json, str) or not config_json:
        return {}
    parsed = json.loads(config_json)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _upsert_sku(
    db: sqlite3.Connection,
    profile: dict[str, Any],
    raw_item: dict[str, Any],
    sku_id: str,
) -> None:
    model_name = _model_name(sku_id)
    db.execute(
        """
        insert into accelerator_skus (
          sku_id, vendor, model_name, normalized_model, scope, source_profile_id,
          source_url, raw_item_id, raw_path, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        on conflict(sku_id) do update set
          vendor = excluded.vendor,
          model_name = excluded.model_name,
          normalized_model = excluded.normalized_model,
          scope = excluded.scope,
          source_profile_id = excluded.source_profile_id,
          source_url = excluded.source_url,
          raw_item_id = excluded.raw_item_id,
          raw_path = excluded.raw_path,
          updated_at = current_timestamp
        """,
        (
            sku_id,
            _vendor(profile),
            model_name,
            _normalized_model(model_name),
            _scope(profile),
            profile["id"],
            profile.get("url") or raw_item["canonical_url"],
            raw_item["id"],
            raw_item["raw_path"],
        ),
    )


def _upsert_observations(
    db: sqlite3.Connection,
    profile: dict[str, Any],
    raw_item: dict[str, Any],
    sku_id: str,
    observations: list[ExtractedObservation],
) -> list[int]:
    observation_ids: list[int] = []
    for observation in observations:
        value_text = _value_text(observation.value)
        value_number = _value_number(observation.value)
        db.execute(
            """
            insert into accelerator_observations (
              sku_id, field, value_text, value_number, unit, source_profile_id, source_rank,
              raw_item_id, raw_path, evidence_text, confidence, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
            on conflict(sku_id, field, value_text, unit, raw_path) do update set
              value_number = excluded.value_number,
              source_profile_id = excluded.source_profile_id,
              source_rank = excluded.source_rank,
              raw_item_id = excluded.raw_item_id,
              evidence_text = excluded.evidence_text,
              confidence = excluded.confidence,
              updated_at = current_timestamp
            """,
            (
                sku_id,
                observation.field,
                value_text,
                value_number,
                observation.unit,
                profile["id"],
                _source_rank(profile),
                raw_item["id"],
                raw_item["raw_path"],
                observation.evidence_text,
                observation.confidence,
            ),
        )
        row = db.execute(
            """
            select id from accelerator_observations
            where sku_id = ? and field = ? and value_text = ? and unit = ? and raw_path = ?
            """,
            (sku_id, observation.field, value_text, observation.unit, raw_item["raw_path"]),
        ).fetchone()
        observation_ids.append(int(row["id"]))
    return observation_ids


def _resolve_observations(
    db: sqlite3.Connection,
    profile: dict[str, Any],
    sku_id: str,
    observations: list[ExtractedObservation],
    observation_ids: list[int],
) -> int:
    if _source_rank(profile) == "S5":
        return 0

    resolved_count = 0
    grouped: dict[str, list[tuple[ExtractedObservation, int]]] = {}
    for observation, observation_id in zip(observations, observation_ids, strict=True):
        grouped.setdefault(observation.field, []).append((observation, observation_id))

    for field, field_observations in grouped.items():
        distinct_values = {
            (_value_text(observation.value), observation.unit)
            for observation, _observation_id in field_observations
        }
        if len(distinct_values) != 1:
            continue

        observation, observation_id = field_observations[0]
        value_text = _value_text(observation.value)
        existing = db.execute(
            "select value_text, unit from accelerator_resolved_specs where sku_id = ? and field = ?",
            (sku_id, field),
        ).fetchone()
        if existing is not None:
            if existing["value_text"] == value_text and existing["unit"] == observation.unit:
                continue
            continue

        db.execute(
            """
            insert into accelerator_resolved_specs (
              sku_id, field, value_text, value_number, unit, source_observation_id,
              resolved_by, confidence, conflict_status, updated_at
            )
            values (?, ?, ?, ?, ?, ?, 'rule', ?, 'clean', current_timestamp)
            """,
            (
                sku_id,
                field,
                value_text,
                _value_number(observation.value),
                observation.unit,
                observation_id,
                str(observation.confidence),
            ),
        )
        resolved_count += 1
    return resolved_count


def _raw_path(settings: Settings, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return settings.repo_root / path


def _sku_id(source_id: str) -> str:
    if source_id.startswith(SOURCE_ID_PREFIX):
        return source_id[len(SOURCE_ID_PREFIX) :]
    return source_id


def _vendor(profile: dict[str, Any]) -> str:
    vendor = str(profile.get("vendor_hint") or "").strip().lower()
    if vendor:
        return vendor
    source_id = _sku_id(str(profile["id"]))
    return source_id.split("-", 1)[0]


def _scope(profile: dict[str, Any]) -> str:
    scopes = profile.get("accelerator_scope")
    if isinstance(scopes, list) and scopes:
        return str(scopes[0])
    if isinstance(scopes, str) and scopes:
        return scopes
    return "unknown"


def _source_rank(profile: dict[str, Any]) -> str:
    return str(profile.get("source_rank") or "S5")


def _model_name(sku_id: str) -> str:
    vendor_prefix = f"{sku_id.split('-', 1)[0]}-"
    if sku_id.startswith(vendor_prefix):
        return sku_id[len(vendor_prefix) :]
    return sku_id


def _normalized_model(model_name: str) -> str:
    return re.sub(r"[\s-]+", "", model_name).upper()


def _number(value: str) -> int | float:
    parsed = float(value)
    if parsed.is_integer():
        return int(parsed)
    return parsed


def _value_text(value: str | int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _value_number(value: str | int | float) -> float | int | None:
    if isinstance(value, int | float):
        return value
    return None


def _unit(unit: str) -> str:
    normalized = unit.strip()
    replacements = {
        "gbps": "Gb/s",
        "gbit/s": "Gb/s",
        "tbyte/s": "TB/s",
        "gbyte/s": "GB/s",
    }
    return replacements.get(normalized.lower(), normalized)


def _clean_evidence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" 。.;；，,")


def _clean_phrase(value: str) -> str:
    cleaned = _clean_evidence(value)
    cleaned = re.split(
        r"\s+(?=峰值功耗|TDP\b|memory\b|显存|内存|存储容量|带宽|网络带宽|互联带宽|端口带宽|PCIe\b)",
        cleaned,
        maxsplit=1,
        flags=re.I,
    )[0]
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _normalize_pcie(value: str) -> str:
    match = re.search(r"PCIe\s*(?:Gen\s*)?(?P<gen>\d(?:\.\d)?)\s*x\s*(?P<lanes>\d{1,2})", value, re.I)
    if match is None:
        return _clean_evidence(value)
    return f"PCIe Gen{match.group('gen')} x{match.group('lanes')}"
