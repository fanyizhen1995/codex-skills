from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any

import yaml

from .models import AuthState


REQUIRED_PROFILE_KEYS = {
    "id",
    "name",
    "type",
    "target_domain",
    "url",
    "trust_level",
    "schedule",
    "auto_ingest",
    "auth_required",
    "topic",
}

PROFILE_STORAGE_KEYS = REQUIRED_PROFILE_KEYS | {
    "baseline_on_first_run",
    "enabled",
    "auth_method",
    "auth_ref",
}

ACCELERATOR_SOURCE_RANKS = {"S1", "S2", "S3", "S4", "S5"}
ACCELERATOR_SCOPES = {"gpu", "npu", "tpu", "dpu", "ipu", "fpga", "dsa", "ai_asic"}
ACCELERATOR_EXTRACT_MODES = {"specs_candidate", "snapshot_only", "manual_probe"}


def load_profiles_from_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("sources", [])
    if not isinstance(profiles, list):
        raise ValueError("sources must be a list")
    seen_ids: set[str] = set()
    for profile in profiles:
        missing = sorted(REQUIRED_PROFILE_KEYS - set(profile))
        if missing:
            raise ValueError(f"profile {profile.get('id', '<unknown>')} missing keys: {', '.join(missing)}")
        if profile["id"] in seen_ids:
            raise ValueError(f"duplicate source id: {profile['id']}")
        seen_ids.add(profile["id"])
        validate_profile_booleans(profile)
        validate_profile_domain(profile)
        validate_accelerator_metadata(profile)
    return profiles


def mirror_profiles(connection: sqlite3.Connection, profiles: list[dict[str, Any]]) -> None:
    active_ids = {profile["id"] for profile in profiles}
    if active_ids:
        placeholders = ", ".join("?" for _ in active_ids)
        connection.execute(
            f"update source_profiles set enabled = 0, updated_at = current_timestamp where id not in ({placeholders})",
            tuple(active_ids),
        )
    else:
        connection.execute("update source_profiles set enabled = 0, updated_at = current_timestamp")

    for profile in profiles:
        booleans = validate_profile_booleans(profile)
        validate_profile_domain(profile)
        validate_accelerator_metadata(profile)
        auto_ingest = booleans["auto_ingest"]
        auth_required = booleans["auth_required"]
        enabled = booleans["enabled"]
        existing = connection.execute(
            "select auth_required, auth_state, auth_method, auth_ref from source_profiles where id = ?",
            (profile["id"],),
        ).fetchone()
        auth_method = profile.get("auth_method")
        auth_ref = profile.get("auth_ref")
        auth_changed = (
            existing is None
            or bool(existing["auth_required"]) != auth_required
            or existing["auth_method"] != auth_method
            or existing["auth_ref"] != auth_ref
        )
        if not auth_required:
            auth_state = AuthState.READY.value
        elif existing is not None and not auth_changed:
            auth_state = existing["auth_state"]
        else:
            auth_state = AuthState.NEEDS_AUTH_CONFIG.value
        connection.execute(
            """
            insert into source_profiles (
              id, name, type, target_domain, url, trust_level, schedule,
              auto_ingest, auth_required, baseline_on_first_run, auth_state, auth_method, auth_ref, config_json, topic, enabled, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
            on conflict(id) do update set
              name = excluded.name,
              type = excluded.type,
              target_domain = excluded.target_domain,
              url = excluded.url,
              trust_level = excluded.trust_level,
              schedule = excluded.schedule,
              auto_ingest = excluded.auto_ingest,
              auth_required = excluded.auth_required,
              baseline_on_first_run = excluded.baseline_on_first_run,
              auth_state = excluded.auth_state,
              auth_method = excluded.auth_method,
              auth_ref = excluded.auth_ref,
              config_json = excluded.config_json,
              topic = excluded.topic,
              enabled = excluded.enabled,
              updated_at = current_timestamp
            """,
            (
                profile["id"],
                profile["name"],
                profile["type"],
                profile["target_domain"],
                profile["url"],
                profile["trust_level"],
                profile["schedule"],
                int(auto_ingest),
                int(auth_required),
                int(bool(profile.get("baseline_on_first_run", False))),
                auth_state,
                auth_method,
                auth_ref,
                _profile_config_json(profile),
                profile["topic"],
                int(enabled),
            ),
        )
        if auth_required and auth_method and auth_ref:
            connection.execute(
                """
                insert into source_auth_refs (source_id, auth_method, auth_ref, state, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                on conflict(source_id) do update set
                  auth_method = excluded.auth_method,
                  auth_ref = excluded.auth_ref,
                  state = excluded.state,
                  updated_at = current_timestamp
                """,
                (profile["id"], auth_method, auth_ref, auth_state),
            )
        else:
            connection.execute("delete from source_auth_refs where source_id = ?", (profile["id"],))


def list_profiles(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        select
          source_profiles.*,
          latest_run.finished_at as latest_run_finished_at,
          latest_run.started_at as latest_run_started_at,
          latest_run.status as latest_run_status
        from source_profiles
        left join fetch_runs latest_run on latest_run.id = (
          select fetch_runs.id
          from fetch_runs
          where fetch_runs.source_id = source_profiles.id
          order by coalesce(fetch_runs.finished_at, fetch_runs.started_at) desc, fetch_runs.id desc
          limit 1
        )
        order by source_profiles.id
        """
    ).fetchall()
    profiles: list[dict[str, Any]] = []
    for row in rows:
        profile = dict(row)
        latest_run_finished_at = profile.pop("latest_run_finished_at")
        latest_run_started_at = profile.pop("latest_run_started_at")
        profile["last_run_status"] = profile.pop("latest_run_status")
        profile["last_run_at"] = latest_run_finished_at or latest_run_started_at
        profiles.append(profile)
    return profiles


def validate_profile_booleans(profile: dict[str, Any]) -> dict[str, bool]:
    profile_id = profile.get("id", "<unknown>")
    values = {
        "auto_ingest": _require_bool(profile, "auto_ingest", profile_id),
        "auth_required": _require_bool(profile, "auth_required", profile_id),
    }
    if "baseline_on_first_run" in profile:
        values["baseline_on_first_run"] = _require_bool(profile, "baseline_on_first_run", profile_id)
    values["enabled"] = _require_bool(profile, "enabled", profile_id) if "enabled" in profile else True
    return values


def validate_profile_domain(profile: dict[str, Any]) -> None:
    profile_id = profile.get("id", "<unknown>")
    domain = str(profile.get("target_domain", ""))
    domain_path = Path(domain)
    if (
        not domain
        or domain_path.is_absolute()
        or len(domain_path.parts) != 1
        or "/" in domain
        or "\\" in domain
        or ".." in domain_path.parts
    ):
        raise ValueError(f"Invalid domain path for profile {profile_id}: {domain}")


def validate_accelerator_metadata(profile: dict[str, Any]) -> None:
    profile_id = profile.get("id", "<unknown>")
    has_accelerator_metadata = any(
        key in profile
        for key in (
            "source_rank",
            "accelerator_scope",
            "extract_mode",
            "vendor_hint",
            "auto_resolve",
        )
    )
    if not has_accelerator_metadata:
        return

    source_rank = profile.get("source_rank")
    if source_rank not in ACCELERATOR_SOURCE_RANKS:
        raise ValueError(f"profile {profile_id} invalid source_rank: {source_rank}")

    scopes = profile.get("accelerator_scope")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError(f"profile {profile_id} accelerator_scope must be a non-empty list")
    if not all(isinstance(scope, str) for scope in scopes):
        raise ValueError(f"profile {profile_id} accelerator_scope entries must be strings")
    invalid_scopes = sorted(str(scope) for scope in scopes if scope not in ACCELERATOR_SCOPES)
    if invalid_scopes:
        raise ValueError(
            f"profile {profile_id} invalid accelerator_scope: {', '.join(invalid_scopes)}"
        )

    extract_mode = profile.get("extract_mode")
    if extract_mode not in ACCELERATOR_EXTRACT_MODES:
        raise ValueError(f"profile {profile_id} invalid extract_mode: {extract_mode}")

    auto_resolve = profile.get("auto_resolve")
    if not isinstance(auto_resolve, bool):
        raise ValueError(f"profile {profile_id} key auto_resolve must be a boolean")
    if source_rank == "S5" and auto_resolve:
        raise ValueError(f"profile {profile_id} S5 profiles cannot auto_resolve")


def _require_bool(profile: dict[str, Any], key: str, profile_id: object) -> bool:
    value = profile.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"profile {profile_id} key {key} must be a boolean")
    return value


def _profile_config_json(profile: dict[str, Any]) -> str:
    config = {
        key: value
        for key, value in sorted(profile.items())
        if key not in PROFILE_STORAGE_KEYS
    }
    return json.dumps(config, ensure_ascii=False, sort_keys=True)
