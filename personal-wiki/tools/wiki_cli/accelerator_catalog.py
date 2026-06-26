from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CATALOG_RELATIVE = Path("domains/ai_infra/data/compute_accelerators")


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
    skus_path = base / "skus/sample-skus.yaml"
    observations_path = base / "observations/sample-observations.yaml"
    resolved_path = base / "resolved/sample-resolved-specs.yaml"

    source_ranks = _load_mapping(source_ranks_path, "source_ranks", issues)
    scopes = _load_mapping(scopes_path, "accelerator_scopes", issues)
    fields = _load_mapping(fields_path, "spec_fields", issues)
    sources_payload = _load_list(sources_path, "sources", issues)
    skus_payload = _load_list(skus_path, "skus", issues)
    observations_payload = _load_list(observations_path, "observations", issues)
    resolved_payload = _load_list(resolved_path, "resolved_specs", issues)

    if issues:
        return issues

    _validate_source_ranks(source_ranks, source_ranks_path, issues)
    _validate_scopes(scopes, scopes_path, issues)
    _validate_fields(fields, scopes, fields_path, issues)

    source_ids = _index_by_id(sources_payload, "source_id", sources_path, issues)
    sku_ids = _index_by_id(skus_payload, "sku_id", skus_path, issues)
    observation_ids = _index_by_id(
        observations_payload, "observation_id", observations_path, issues
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
        _validate_sku(sku, scopes, source_ids, skus_path, issues)

    for observation in observations_payload:
        _validate_observation(
            observation,
            sku_ids,
            fields,
            source_ids,
            observations_path,
            issues,
        )

    for resolved in resolved_payload:
        _validate_resolved_spec(
            resolved,
            sku_ids,
            fields,
            observation_ids,
            resolved_path,
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
        for key in ("canonical_unit", "allowed_units", "applies_to"):
            if not _has_value(payload.get(key)):
                issues.append(
                    CatalogIssue(
                        "missing_field_definition",
                        path,
                        f"field {field} missing required field {key}",
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
    if field not in fields:
        issues.append(
            CatalogIssue(
                "unknown_field",
                path,
                f"observation {observation_id or '<unknown>'} uses unknown field {field}",
            )
        )
    elif unit not in _list_value(fields[field].get("allowed_units")):
        issues.append(
            CatalogIssue(
                "invalid_unit",
                path,
                f"observation {observation_id or '<unknown>'} field {field} uses invalid unit {unit}",
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
    if sku_id in sku_ids and field in fields:
        scope = sku_ids[sku_id].get("scope")
        if scope not in _list_value(fields[field].get("applies_to")):
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
    observation_ids: dict[str, dict[str, Any]],
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
        _validate_resolved_field(
            sku_id,
            field,
            value,
            sku_ids,
            fields,
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
    if sku_id in sku_ids:
        scope = sku_ids[sku_id].get("scope")
        if scope not in _list_value(fields[field].get("applies_to")):
            issues.append(
                CatalogIssue(
                    "field_not_applicable",
                    path,
                    f"resolved field {field} does not apply to sku {sku_id} scope {scope}",
                )
            )
    unit = value.get("unit")
    if unit not in _list_value(fields[field].get("allowed_units")):
        issues.append(
            CatalogIssue(
                "invalid_resolved_unit",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} uses invalid unit {unit}",
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
    if observation.get("source_rank") == "S5" and not observation.get("reviewed_by"):
        issues.append(
            CatalogIssue(
                "s5_resolved_without_review",
                path,
                f"resolved spec {sku_id or '<unknown>'} field {field} uses S5 observation {observation_id} without reviewed_by",
            )
        )


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
