from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CATALOG_RELATIVE = Path("domains/ai_infra/data/compute_accelerators")
ALLOWED_FIELD_VALUE_TYPES = {"number", "string", "boolean"}
S2_OBSERVATION_KINDS = {"cloud_offering"}
S3_OBSERVATION_KINDS = {"benchmark_result", "registry", "standard"}
S4_OBSERVATION_KINDS = {"observed_runtime", "runtime_probe"}


@dataclass(frozen=True)
class CatalogIssue:
    code: str
    path: Path
    message: str


def validate_catalog(root: Path) -> list[CatalogIssue]:
    root = Path(root)
    base = root / CATALOG_RELATIVE
    issues: list[CatalogIssue] = []

    source_ranks_path = base / "schema/source-ranks.yaml"
    scopes_path = base / "schema/accelerator-scopes.yaml"
    fields_path = base / "schema/spec-fields.yaml"
    sources_path = base / "sources/source-registry.yaml"

    source_ranks = _load_mapping(source_ranks_path, "source_ranks", issues)
    scopes = _load_mapping(scopes_path, "accelerator_scopes", issues)
    fields = _load_mapping(fields_path, "spec_fields", issues)
    sources_payload = _load_list(sources_path, "sources", issues)
    skus_payload = _load_catalog_directory(base / "skus", "skus", issues)
    observations_payload = _load_catalog_directory(
        base / "observations", "observations", issues
    )
    resolved_payload = _load_catalog_directory(base / "resolved", "resolved_specs", issues)

    if issues:
        return issues

    _validate_source_ranks(source_ranks, source_ranks_path, issues)
    _validate_scopes(scopes, scopes_path, issues)
    _validate_fields(fields, scopes, fields_path, issues)

    source_ids = _index_by_id(sources_payload, "source_id", sources_path, issues)
    sku_ids = _index_by_id_with_row_path(skus_payload, "sku_id", issues)
    observation_ids = _index_by_id(
        observations_payload,
        "observation_id",
        base / "observations",
        issues,
    )

    for source in sources_payload:
        rank = source.get("source_rank")
        if rank not in source_ranks:
            issues.append(
                CatalogIssue(
                    "unknown_source_rank",
                    sources_path,
                    f"source {source.get('source_id')} uses unknown source_rank {rank}",
                )
            )

    for sku in skus_payload:
        _validate_sku(sku, scopes, source_ids, _row_path(sku), issues)

    for observation in observations_payload:
        _validate_observation(
            observation,
            sku_ids,
            fields,
            source_ids,
            _row_path(observation),
            issues,
        )

    seen_resolved_fields: set[tuple[str, str]] = set()
    for resolved in resolved_payload:
        _validate_resolved_spec(
            resolved,
            sku_ids,
            fields,
            source_ids,
            observation_ids,
            seen_resolved_fields,
            _row_path(resolved),
            issues,
        )

    return issues


def _validate_source_ranks(
    source_ranks: dict[str, Any],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    for rank, payload in source_ranks.items():
        if not isinstance(payload, dict):
            issues.append(CatalogIssue("invalid_catalog_shape", path, f"{rank} must be a mapping"))
            continue
        if not _has_value(payload.get("auto_resolve_allowed")):
            issues.append(
                CatalogIssue(
                    "missing_source_rank_field",
                    path,
                    f"source rank {rank} missing required field auto_resolve_allowed",
                )
            )


def _validate_scopes(
    scopes: dict[str, Any],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    for scope, payload in scopes.items():
        if not isinstance(payload, dict):
            issues.append(CatalogIssue("invalid_catalog_shape", path, f"{scope} must be a mapping"))


def _validate_fields(
    fields: dict[str, Any],
    scopes: dict[str, Any],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    for field, payload in fields.items():
        if not isinstance(payload, dict):
            issues.append(CatalogIssue("invalid_catalog_shape", path, f"{field} must be a mapping"))
            continue
        for key in ("value_type", "canonical_unit", "allowed_units", "applies_to"):
            if not _has_value(payload.get(key)):
                issues.append(
                    CatalogIssue(
                        "missing_field_definition",
                        path,
                        f"field {field} missing required field {key}",
                    )
                )
        value_type = payload.get("value_type")
        if _has_value(value_type) and value_type not in ALLOWED_FIELD_VALUE_TYPES:
            issues.append(
                CatalogIssue(
                    "invalid_field_value_type",
                    path,
                    f"field {field} uses invalid value_type {value_type}",
                )
            )
        canonical_unit = payload.get("canonical_unit")
        allowed_units = _list_value(payload.get("allowed_units"))
        if _has_value(canonical_unit) and str(canonical_unit) not in allowed_units:
            issues.append(
                CatalogIssue(
                    "canonical_unit_not_allowed",
                    path,
                    f"field {field} canonical_unit {canonical_unit} is not in allowed_units",
                )
            )
        for scope in _list_value(payload.get("applies_to")):
            if scope not in scopes:
                issues.append(
                    CatalogIssue(
                        "unknown_field_scope",
                        path,
                        f"field {field} applies to unknown scope {scope}",
                    )
                )


def _validate_sku(
    sku: dict[str, Any],
    scopes: dict[str, Any],
    source_ids: dict[str, dict[str, Any]],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    sku_id = sku.get("sku_id")
    for key in ("vendor_id", "scope", "canonical_name", "source_refs"):
        if not _has_value(sku.get(key)):
            issues.append(
                CatalogIssue(
                    "missing_sku_field",
                    path,
                    f"sku {sku_id or '<unknown>'} missing required field {key}",
                )
            )
    scope = sku.get("scope")
    if scope not in scopes:
        issues.append(
            CatalogIssue(
                "unknown_scope",
                path,
                f"sku {sku_id or '<unknown>'} uses unknown scope {scope}",
            )
        )
    for source_ref in _list_value(sku.get("source_refs")):
        if source_ref not in source_ids:
            issues.append(
                CatalogIssue(
                    "missing_source_ref",
                    path,
                    f"sku {sku_id or '<unknown>'} references unknown source {source_ref}",
                )
            )


def _validate_observation(
    observation: dict[str, Any],
    sku_ids: dict[str, dict[str, Any]],
    fields: dict[str, Any],
    source_ids: dict[str, dict[str, Any]],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    observation_id = observation.get("observation_id")
    sku_id = observation.get("sku_id")
    field = observation.get("field")
    unit = observation.get("unit")
    source_id = observation.get("source_id")
    source_rank = observation.get("source_rank")
    for key in (
        "observation_id",
        "sku_id",
        "field",
        "value",
        "unit",
        "source_id",
        "source_rank",
        "captured_at",
        "source_locator",
        "is_official",
        "is_inferred",
        "confidence",
    ):
        if not _has_value(observation.get(key)):
            issues.append(
                CatalogIssue(
                    "missing_observation_field",
                    path,
                    f"observation {observation_id or '<unknown>'} missing required field {key}",
                )
            )
    if sku_id not in sku_ids:
        issues.append(
            CatalogIssue(
                "unknown_observation_sku",
                path,
                f"observation {observation_id or '<unknown>'} references unknown sku {sku_id}",
            )
        )
    field_definition = _mapping_value(fields.get(str(field)))
    if field not in fields:
        issues.append(
            CatalogIssue(
                "unknown_field",
                path,
                f"observation {observation_id or '<unknown>'} uses unknown field {field}",
            )
        )
    elif field_definition is None:
        return
    elif unit not in _list_value(field_definition.get("allowed_units")):
        issues.append(
            CatalogIssue(
                "invalid_unit",
                path,
                f"observation {observation_id or '<unknown>'} field {field} uses invalid unit {unit}",
            )
        )
    if field_definition is not None and not _value_matches_type(
        observation.get("value"),
        field_definition.get("value_type"),
    ):
        issues.append(
            CatalogIssue(
                "invalid_value_type",
                path,
                f"observation {observation_id or '<unknown>'} field {field} value does not match value_type {field_definition.get('value_type')}",
            )
        )
    if source_id not in source_ids:
        issues.append(
            CatalogIssue(
                "unknown_observation_source",
                path,
                f"observation {observation_id or '<unknown>'} references unknown source {source_id}",
            )
        )
    elif source_rank != source_ids[source_id].get("source_rank"):
        issues.append(
            CatalogIssue(
                "source_rank_mismatch",
                path,
                f"observation {observation_id or '<unknown>'} source_rank {source_rank} does not match source {source_id}",
            )
        )
    if sku_id in sku_ids and field_definition is not None:
        scope = sku_ids[sku_id].get("scope")
        if scope not in _list_value(field_definition.get("applies_to")):
            issues.append(
                CatalogIssue(
                    "field_not_applicable",
                    path,
                    f"field {field} does not apply to sku {sku_id} scope {scope}",
                )
            )


def _validate_resolved_spec(
    resolved: dict[str, Any],
    sku_ids: dict[str, dict[str, Any]],
    fields: dict[str, Any],
    source_ids: dict[str, dict[str, Any]],
    observation_ids: dict[str, dict[str, Any]],
    seen_resolved_fields: set[tuple[str, str]],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    sku_id = resolved.get("sku_id")
    if sku_id not in sku_ids:
        issues.append(
            CatalogIssue(
                "unknown_resolved_sku",
                path,
                f"resolved spec references unknown sku {sku_id}",
            )
        )
    resolved_fields = resolved.get("resolved_fields")
    if not isinstance(resolved_fields, dict) or not resolved_fields:
        issues.append(
            CatalogIssue(
                "missing_resolved_fields",
                path,
                f"resolved spec {sku_id or '<unknown>'} has no resolved_fields mapping",
            )
        )
        return
    for field, value in resolved_fields.items():
        if not isinstance(value, dict):
            issues.append(
                CatalogIssue(
                    "invalid_catalog_shape",
                    path,
                    f"resolved spec {sku_id or '<unknown>'} field {field} must be a mapping",
                )
            )
            continue
        resolved_key = (str(sku_id), str(field))
        if resolved_key in seen_resolved_fields:
            issues.append(
                CatalogIssue(
                    "duplicate_resolved_field",
                    path,
                    f"resolved spec {sku_id or '<unknown>'} repeats field {field}",
                )
            )
        else:
            seen_resolved_fields.add(resolved_key)
        _validate_resolved_field(
            sku_id,
            field,
            value,
            sku_ids,
            fields,
            source_ids,
            observation_ids,
            path,
            issues,
        )


def _validate_resolved_field(
    sku_id: object,
    field: str,
    value: dict[str, Any],
    sku_ids: dict[str, dict[str, Any]],
    fields: dict[str, Any],
    source_ids: dict[str, dict[str, Any]],
    observation_ids: dict[str, dict[str, Any]],
    path: Path,
    issues: list[CatalogIssue],
) -> None:
    for key in (
        "value",
        "unit",
        "source_observation_id",
        "resolved_by",
        "confidence",
        "conflict_status",
        "updated_at",
    ):
        if not _has_value(value.get(key)):
            issues.append(
                CatalogIssue(
                    "missing_resolved_field",
                    path,
                    f"resolved spec {sku_id or '<unknown>'} field {field} missing required field {key}",
                )
            )
    if field not in fields:
        issues.append(
            CatalogIssue(
                "unknown_resolved_field",
                path,
                f"resolved spec {sku_id or '<unknown>'} uses unknown field {field}",
            )
        )
        return
    field_definition = _mapping_value(fields[field])
    if field_definition is None:
        return
    if sku_id in sku_ids:
        scope = sku_ids[sku_id].get("scope")
        if scope not in _list_value(field_definition.get("applies_to")):
            issues.append(
                CatalogIssue(
                    "field_not_applicable",
                    path,
                    f"resolved field {field} does not apply to sku {sku_id} scope {scope}",
                )
            )
    unit = value.get("unit")
    if unit not in _list_value(field_definition.get("allowed_units")):
        issues.append(
            CatalogIssue(
                "invalid_resolved_unit",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} uses invalid unit {unit}",
            )
        )
    if not _value_matches_type(value.get("value"), field_definition.get("value_type")):
        issues.append(
            CatalogIssue(
                "invalid_value_type",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} value does not match value_type {field_definition.get('value_type')}",
            )
        )
    observation_id = value.get("source_observation_id")
    if observation_id not in observation_ids:
        issues.append(
            CatalogIssue(
                "missing_observation",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} references missing observation {observation_id}",
            )
        )
        return
    observation = observation_ids[observation_id]
    if observation.get("sku_id") != sku_id or observation.get("field") != field:
        issues.append(
            CatalogIssue(
                "observation_field_mismatch",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} points to incompatible observation {observation_id}",
            )
        )
    if observation.get("value") != value.get("value") or observation.get("unit") != unit:
        issues.append(
            CatalogIssue(
                "resolved_observation_mismatch",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} value/unit does not match observation {observation_id}",
            )
        )
    effective_rank = _effective_source_rank(observation, source_ids)
    if effective_rank == "S5" and not observation.get("reviewed_by"):
        issues.append(
            CatalogIssue(
                "s5_resolved_without_review",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} uses S5 observation {observation_id} without reviewed_by",
            )
        )
    policy_issue = _source_rank_policy_issue(effective_rank, field_definition)
    if policy_issue is not None:
        issues.append(
            CatalogIssue(
                "source_rank_policy_violation",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} uses {effective_rank} observation {observation_id}: {policy_issue}",
            )
        )


def _load_catalog_directory(
    directory: Path,
    key: str,
    issues: list[CatalogIssue],
) -> list[dict[str, Any]]:
    if not directory.exists():
        issues.append(CatalogIssue("missing_file", directory, f"missing catalog directory {directory}"))
        return []
    rows: list[dict[str, Any]] = []
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        issues.append(CatalogIssue("missing_file", directory, f"no {key} YAML files found"))
        return []
    for path in paths:
        for row in _load_list(path, key, issues):
            row["__catalog_path"] = path
            rows.append(row)
    return rows


def _load_yaml(path: Path, issues: list[CatalogIssue]) -> Any:
    if not path.exists():
        issues.append(CatalogIssue("missing_file", path, f"missing catalog file {path}"))
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        issues.append(CatalogIssue("invalid_yaml", path, f"invalid YAML: {error}"))
        return {}


def _load_mapping(path: Path, key: str, issues: list[CatalogIssue]) -> dict[str, Any]:
    payload = _load_yaml(path, issues)
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, dict):
        issues.append(CatalogIssue("invalid_catalog_shape", path, f"{key} must be a mapping"))
        return {}
    return value


def _load_list(path: Path, key: str, issues: list[CatalogIssue]) -> list[dict[str, Any]]:
    payload = _load_yaml(path, issues)
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, list):
        issues.append(CatalogIssue("invalid_catalog_shape", path, f"{key} must be a list"))
        return []
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(
                CatalogIssue(
                    "invalid_catalog_shape",
                    path,
                    f"{key}[{index}] must be a mapping",
                )
            )
        else:
            objects.append(item)
    return objects


def _index_by_id_with_row_path(
    rows: list[dict[str, Any]],
    key: str,
    issues: list[CatalogIssue],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        path = _row_path(row)
        if not _has_value(value):
            issues.append(
                CatalogIssue("missing_id", path, f"row missing required identifier {key}")
            )
            continue
        text = str(value)
        if text in indexed:
            issues.append(CatalogIssue("duplicate_id", path, f"duplicate {key}: {text}"))
            continue
        indexed[text] = row
    return indexed


def _index_by_id(
    rows: list[dict[str, Any]],
    key: str,
    path: Path,
    issues: list[CatalogIssue],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not _has_value(value):
            issues.append(
                CatalogIssue("missing_id", path, f"row missing required identifier {key}")
            )
            continue
        text = str(value)
        if text in indexed:
            issues.append(CatalogIssue("duplicate_id", path, f"duplicate {key}: {text}"))
            continue
        indexed[text] = row
    return indexed


def _row_path(row: dict[str, Any]) -> Path:
    path = row.get("__catalog_path")
    if isinstance(path, Path):
        return path
    return Path("<catalog>")


def _mapping_value(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _effective_source_rank(
    observation: dict[str, Any],
    source_ids: dict[str, dict[str, Any]],
) -> object:
    source_id = observation.get("source_id")
    if source_id in source_ids:
        return source_ids[source_id].get("source_rank")
    return observation.get("source_rank")


def _source_rank_policy_issue(
    source_rank: object,
    field_definition: dict[str, Any],
) -> str | None:
    observation_kind = str(field_definition.get("observation_kind", "")).strip()
    if source_rank == "S2" and observation_kind not in S2_OBSERVATION_KINDS:
        return f"field observation_kind {observation_kind or '<missing>'} is not cloud_offering"
    if source_rank == "S3" and observation_kind not in S3_OBSERVATION_KINDS:
        return f"field observation_kind {observation_kind or '<missing>'} is not benchmark or registry"
    if source_rank == "S4" and observation_kind not in S4_OBSERVATION_KINDS:
        return f"field observation_kind {observation_kind or '<missing>'} is not observed runtime"
    return None


def _value_matches_type(value: object, value_type: object) -> bool:
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "boolean":
        return isinstance(value, bool)
    return True


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_value(item) for item in value)
    return True


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
