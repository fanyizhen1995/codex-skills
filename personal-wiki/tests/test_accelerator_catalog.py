import subprocess
import sys
from pathlib import Path

import yaml

from personal_wiki_test_loader import load_cli_module


accelerator_catalog = load_cli_module("accelerator_catalog")


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_catalog(root: Path) -> Path:
    base = root / "domains/ai_infra/data/compute_accelerators"
    write_yaml(
        base / "schema/source-ranks.yaml",
        {
            "source_ranks": {
                "S1": {"auto_resolve_allowed": "conditional"},
                "S5": {"auto_resolve_allowed": "reviewed_only"},
            }
        },
    )
    write_yaml(
        base / "schema/accelerator-scopes.yaml",
        {"accelerator_scopes": {"gpu": {}, "dpu": {}}},
    )
    write_yaml(
        base / "schema/spec-fields.yaml",
        {
            "spec_fields": {
                "memory_capacity": {
                    "canonical_unit": "GB",
                    "allowed_units": ["GB"],
                    "applies_to": ["gpu"],
                },
                "network_bandwidth": {
                    "canonical_unit": "Gb/s",
                    "allowed_units": ["Gb/s"],
                    "applies_to": ["dpu"],
                },
            }
        },
    )
    write_yaml(
        base / "sources/source-registry.yaml",
        {
            "sources": [
                {"source_id": "official-source", "source_rank": "S1"},
                {"source_id": "third-party-source", "source_rank": "S5"},
            ]
        },
    )
    write_yaml(
        base / "skus/sample-skus.yaml",
        {
            "skus": [
                {
                    "sku_id": "gpu-sku",
                    "vendor_id": "vendor",
                    "canonical_name": "GPU SKU",
                    "scope": "gpu",
                    "source_refs": ["official-source"],
                }
            ]
        },
    )
    write_yaml(
        base / "observations/sample-observations.yaml",
        {
            "observations": [
                {
                    "observation_id": "obs-memory",
                    "sku_id": "gpu-sku",
                    "field": "memory_capacity",
                    "value": 141,
                    "unit": "GB",
                    "source_id": "official-source",
                    "source_rank": "S1",
                    "captured_at": "2026-06-27",
                    "source_locator": "fixture",
                    "is_official": True,
                    "is_inferred": False,
                    "confidence": "high",
                }
            ]
        },
    )
    write_yaml(
        base / "resolved/sample-resolved-specs.yaml",
        {
            "resolved_specs": [
                {
                    "sku_id": "gpu-sku",
                    "resolved_fields": {
                        "memory_capacity": {
                            "value": 141,
                            "unit": "GB",
                            "source_observation_id": "obs-memory",
                            "resolved_by": "rule",
                            "confidence": "high",
                            "conflict_status": "clean",
                            "updated_at": "2026-06-27",
                        }
                    },
                }
            ]
        },
    )
    return base


def test_validate_catalog_accepts_consistent_fixture(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_catalog(root)

    issues = accelerator_catalog.validate_catalog(root)

    assert issues == []


def test_validate_catalog_rejects_unknown_scope(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    sku_path = base / "skus/sample-skus.yaml"
    payload = yaml.safe_load(sku_path.read_text(encoding="utf-8"))
    payload["skus"][0]["scope"] = "quantum"
    write_yaml(sku_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "unknown_scope" for issue in issues)


def test_validate_catalog_rejects_resolved_field_without_observation(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    resolved_path = base / "resolved/sample-resolved-specs.yaml"
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    payload["resolved_specs"][0]["resolved_fields"]["memory_capacity"][
        "source_observation_id"
    ] = "missing-observation"
    write_yaml(resolved_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "missing_observation" for issue in issues)


def test_validate_catalog_rejects_s5_auto_resolve_without_review(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["source_id"] = "third-party-source"
    payload["observations"][0]["source_rank"] = "S5"
    payload["observations"][0].pop("reviewed_by", None)
    write_yaml(observations_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "s5_resolved_without_review" for issue in issues)


def test_validate_catalog_accepts_s5_resolved_value_with_review(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["source_id"] = "third-party-source"
    payload["observations"][0]["source_rank"] = "S5"
    payload["observations"][0]["reviewed_by"] = "catalog-reviewer"
    write_yaml(observations_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert issues == []


def test_validate_catalog_rejects_field_not_applicable_to_scope(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["field"] = "network_bandwidth"
    payload["observations"][0]["unit"] = "Gb/s"
    write_yaml(observations_path, payload)
    resolved_path = base / "resolved/sample-resolved-specs.yaml"
    resolved = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    field_payload = resolved["resolved_specs"][0]["resolved_fields"].pop("memory_capacity")
    field_payload["unit"] = "Gb/s"
    resolved["resolved_specs"][0]["resolved_fields"]["network_bandwidth"] = field_payload
    write_yaml(resolved_path, resolved)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "field_not_applicable" for issue in issues)


def test_validate_catalog_reports_malformed_field_definition_without_crashing(
    tmp_path: Path,
):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    fields_path = base / "schema/spec-fields.yaml"
    payload = yaml.safe_load(fields_path.read_text(encoding="utf-8"))
    payload["spec_fields"]["memory_capacity"] = "bad"
    write_yaml(fields_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "invalid_catalog_shape" for issue in issues)


def test_validate_catalog_rejects_resolved_value_mismatch(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    resolved_path = base / "resolved/sample-resolved-specs.yaml"
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    payload["resolved_specs"][0]["resolved_fields"]["memory_capacity"]["value"] = 999
    write_yaml(resolved_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "resolved_observation_mismatch" for issue in issues)


def test_validate_catalog_uses_registry_rank_for_s5_review_policy(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    observations_path = base / "observations/sample-observations.yaml"
    payload = yaml.safe_load(observations_path.read_text(encoding="utf-8"))
    payload["observations"][0]["source_id"] = "third-party-source"
    payload["observations"][0]["source_rank"] = "S1"
    payload["observations"][0].pop("reviewed_by", None)
    write_yaml(observations_path, payload)

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "source_rank_mismatch" for issue in issues)
    assert any(issue.code == "s5_resolved_without_review" for issue in issues)


def test_validate_catalog_loads_additional_data_files(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    base = build_catalog(root)
    write_yaml(
        base / "skus/extra-skus.yaml",
        {
            "skus": [
                {
                    "sku_id": "extra-gpu-sku",
                    "vendor_id": "vendor",
                    "canonical_name": "Extra GPU SKU",
                    "scope": "gpu",
                    "source_refs": ["official-source"],
                }
            ]
        },
    )
    write_yaml(
        base / "observations/extra-observations.yaml",
        {
            "observations": [
                {
                    "observation_id": "obs-extra-memory",
                    "sku_id": "extra-gpu-sku",
                    "field": "memory_capacity",
                    "value": 80,
                    "unit": "GB",
                    "source_id": "official-source",
                    "source_rank": "S1",
                    "captured_at": "2026-06-27",
                    "source_locator": "fixture",
                    "is_official": True,
                    "is_inferred": False,
                    "confidence": "high",
                }
            ]
        },
    )
    write_yaml(
        base / "resolved/extra-resolved-specs.yaml",
        {
            "resolved_specs": [
                {
                    "sku_id": "extra-gpu-sku",
                    "resolved_fields": {
                        "memory_capacity": {
                            "value": 999,
                            "unit": "GB",
                            "source_observation_id": "obs-extra-memory",
                            "resolved_by": "rule",
                            "confidence": "high",
                            "conflict_status": "clean",
                            "updated_at": "2026-06-27",
                        }
                    },
                }
            ]
        },
    )

    issues = accelerator_catalog.validate_catalog(root)

    assert any(issue.code == "resolved_observation_mismatch" for issue in issues)


def test_validate_accelerators_cli_reports_success_for_repo_catalog():
    cli = Path(__file__).resolve().parents[1] / "tools/wiki_cli/cli.py"

    result = subprocess.run(
        [
            sys.executable,
            str(cli),
            "--root",
            str(Path(__file__).resolve().parents[1]),
            "validate-accelerators",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "No accelerator catalog validation issues" in result.stdout
