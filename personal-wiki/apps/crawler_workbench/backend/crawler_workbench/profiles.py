from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any
from urllib.parse import urlparse

import yaml

from .channels import get_channel, normalize_base_url, upsert_channel
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
    "run_policy",
    "fetcher_type",
    "channel_id",
}

SOURCE_TYPES = {"web", "rss", "github", "arxiv"}

RUN_POLICIES = {"scheduled", "once"}
ACCELERATOR_SOURCE_RANKS = {"S1", "S2", "S3", "S4", "S5"}
ACCELERATOR_SCOPES = {"gpu", "npu", "tpu", "dpu", "ipu", "fpga", "dsa", "ai_asic"}
ACCELERATOR_EXTRACT_MODES = {"specs_candidate", "snapshot_only", "manual_probe", "discovery_index"}
DISCOVERY_MODES = {"accelerator_models"}
DISCOVERY_OPTIONAL_LIST_KEYS = {"include_patterns", "exclude_patterns", "candidate_url_patterns"}


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
        validate_profile_source_id(profile)
        validate_profile_booleans(profile)
        validate_run_policy(profile)
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
        validate_profile_source_id(profile)
        booleans = validate_profile_booleans(profile)
        run_policy = validate_run_policy(profile)
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
              auto_ingest, auth_required, baseline_on_first_run, run_policy,
              auth_state, auth_method, auth_ref, channel_id, fetcher_type,
              config_json, topic, enabled, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
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
              run_policy = excluded.run_policy,
              auth_state = excluded.auth_state,
              auth_method = excluded.auth_method,
              auth_ref = excluded.auth_ref,
              channel_id = excluded.channel_id,
              fetcher_type = excluded.fetcher_type,
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
                run_policy,
                auth_state,
                auth_method,
                auth_ref,
                None,
                profile.get("fetcher_type") or infer_fetcher_type(profile),
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
    ensure_source_channels(connection)


def initialize_profiles_from_seed(connection: sqlite3.Connection, yaml_path: Path) -> None:
    row = connection.execute("select count(*) as count from source_profiles").fetchone()
    if int(row["count"]) == 0:
        mirror_profiles(connection, load_profiles_from_yaml(yaml_path))
    else:
        ensure_source_channels(connection)
    connection.commit()


def ensure_source_channels(connection: sqlite3.Connection) -> None:
    rows = connection.execute("select * from source_profiles order by id").fetchall()
    for row in rows:
        profile = dict(row)
        updates: dict[str, Any] = {}
        if not profile.get("fetcher_type"):
            updates["fetcher_type"] = infer_fetcher_type(profile)
        if not profile.get("channel_id"):
            updates["channel_id"] = upsert_channel(connection, derive_channel_seed(profile))
        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            connection.execute(
                f"update source_profiles set {assignments}, updated_at = current_timestamp where id = ?",
                (*updates.values(), profile["id"]),
            )


def list_profiles(
    connection: sqlite3.Connection,
    *,
    domain: str | None = None,
    channel_id: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if domain:
        filters.append("source_profiles.target_domain = ?")
        params.append(domain)
    if channel_id:
        filters.append("source_profiles.channel_id = ?")
        params.append(channel_id)
    where = f"where {' and '.join(filters)}" if filters else ""
    rows = connection.execute(
        f"""
        select
          source_profiles.*,
          channels.name as channel_name,
          channels.base_url as channel_base_url,
          channels.auth_state as channel_auth_state,
          latest_run.finished_at as latest_run_finished_at,
          latest_run.started_at as latest_run_started_at,
          latest_run.status as latest_run_status
        from source_profiles
        left join channels on channels.id = source_profiles.channel_id
        left join fetch_runs latest_run on latest_run.id = (
          select fetch_runs.id
          from fetch_runs
          where fetch_runs.source_id = source_profiles.id
          order by coalesce(fetch_runs.finished_at, fetch_runs.started_at) desc, fetch_runs.id desc
          limit 1
        )
        {where}
        order by source_profiles.id
        """,
        tuple(params),
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


def get_profile(connection: sqlite3.Connection, source_id: str) -> dict[str, Any]:
    rows = list_profiles(connection)
    for row in rows:
        if row["id"] == source_id:
            return row
    raise ValueError(f"source not found: {source_id}")


def create_profile(connection: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    source = _normalize_profile_payload(payload, creating=True)
    validate_profile_source_id(source)
    validate_profile_domain(source)
    booleans = validate_profile_booleans(source)
    run_policy = validate_run_policy(source)
    validate_accelerator_metadata(source)
    channel_id = _channel_id_for_source(connection, source)
    auth_required = booleans["auth_required"]
    auth_state = (
        AuthState.READY.value
        if not auth_required or source.get("auth_method") and source.get("auth_ref")
        else AuthState.NEEDS_AUTH_CONFIG.value
    )
    connection.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, baseline_on_first_run, run_policy,
          auth_state, auth_method, auth_ref, channel_id, fetcher_type,
          config_json, topic, enabled, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        """,
        (
            source["id"],
            source["name"],
            source["type"],
            source["target_domain"],
            source["url"],
            source["trust_level"],
            source["schedule"],
            int(booleans["auto_ingest"]),
            int(auth_required),
            int(booleans.get("baseline_on_first_run", False)),
            run_policy,
            source.get("auth_state") or auth_state,
            source.get("auth_method"),
            source.get("auth_ref"),
            channel_id,
            source.get("fetcher_type") or infer_fetcher_type({**source, "channel_id": channel_id}),
            _profile_config_json(source),
            source["topic"],
            int(booleans["enabled"]),
        ),
    )
    connection.commit()
    return get_profile(connection, str(source["id"]))


def update_profile(connection: sqlite3.Connection, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = get_profile(connection, source_id)
    merged = {**existing, **{key: value for key, value in payload.items() if value is not None}}
    merged["id"] = source_id
    source = _normalize_profile_payload(merged, creating=False)
    validate_profile_source_id(source)
    validate_profile_domain(source)
    booleans = validate_profile_booleans(source)
    run_policy = validate_run_policy(source)
    validate_accelerator_metadata(source)
    channel_id = _channel_id_for_source(connection, source)
    connection.execute(
        """
        update source_profiles
        set name = ?,
            type = ?,
            target_domain = ?,
            url = ?,
            trust_level = ?,
            schedule = ?,
            auto_ingest = ?,
            auth_required = ?,
            baseline_on_first_run = ?,
            run_policy = ?,
            auth_state = ?,
            auth_method = ?,
            auth_ref = ?,
            channel_id = ?,
            fetcher_type = ?,
            config_json = ?,
            topic = ?,
            enabled = ?,
            updated_at = current_timestamp
        where id = ?
        """,
        (
            source["name"],
            source["type"],
            source["target_domain"],
            source["url"],
            source["trust_level"],
            source["schedule"],
            int(booleans["auto_ingest"]),
            int(booleans["auth_required"]),
            int(booleans.get("baseline_on_first_run", False)),
            run_policy,
            source.get("auth_state") or existing.get("auth_state") or AuthState.READY.value,
            source.get("auth_method"),
            source.get("auth_ref"),
            channel_id,
            source.get("fetcher_type") or infer_fetcher_type({**source, "channel_id": channel_id}),
            _profile_config_json(source),
            source["topic"],
            int(booleans["enabled"]),
            source_id,
        ),
    )
    connection.commit()
    return get_profile(connection, source_id)


def delete_profile(connection: sqlite3.Connection, source_id: str) -> dict[str, Any]:
    get_profile(connection, source_id)
    row = connection.execute(
        """
        select
          (select count(*) from raw_items where source_id = ?) as raw_count,
          (select count(*) from fetch_runs where source_id = ?) as run_count,
          (select count(*) from ingest_tasks where source_id = ?) as task_count
        """,
        (source_id, source_id, source_id),
    ).fetchone()
    if int(row["raw_count"]) or int(row["run_count"]) or int(row["task_count"]):
        connection.execute(
            "update source_profiles set enabled = 0, updated_at = current_timestamp where id = ?",
            (source_id,),
        )
        connection.commit()
        return {"id": source_id, "deleted": False, "disabled": True}
    connection.execute("delete from source_profiles where id = ?", (source_id,))
    connection.commit()
    return {"id": source_id, "deleted": True, "disabled": False}


def derive_channel_seed(profile: dict[str, Any]) -> dict[str, Any]:
    base_url = _base_url_for_profile(profile)
    connector = _connector_for_profile(profile, base_url)
    kind = _kind_for_profile(profile, base_url)
    auth_required = bool(profile.get("auth_required", False))
    auth_mode = _auth_mode_for_profile(profile)
    return {
        "target_domain": profile["target_domain"],
        "id": profile.get("channel_id"),
        "name": _channel_name(base_url),
        "base_url": base_url,
        "base_url_normalized": normalize_base_url(base_url),
        "kind": kind,
        "connector": connector,
        "trust_level": profile.get("trust_level", "untrusted"),
        "enabled": True,
        "auth_required": auth_required,
        "auth_mode": auth_mode,
        "auth_state": AuthState.NEEDS_AUTH_CONFIG.value if auth_required else AuthState.READY.value,
    }


def infer_fetcher_type(profile: dict[str, Any]) -> str:
    configured = profile.get("fetcher_type")
    if configured:
        return str(configured)
    source_type = str(profile.get("type", "web"))
    url = str(profile.get("url", ""))
    config_json = profile.get("config_json")
    config = _parse_config_json(config_json)
    if source_type == "web":
        return "web_page"
    if source_type == "rss":
        return "rss_feed"
    if source_type == "arxiv":
        return "arxiv_query"
    if source_type == "github":
        if "releases" in url or url.endswith(".atom") or "/releases" in url:
            return "github_releases"
        if "/issues" in url or "issues" in config.get("endpoint", ""):
            return "github_issues"
        return "github_repo"
    return source_type


def _base_url_for_profile(profile: dict[str, Any]) -> str:
    url = str(profile.get("url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    return url.rstrip("/")


def _connector_for_profile(profile: dict[str, Any], base_url: str) -> str:
    source_type = str(profile.get("type", "web"))
    host = urlparse(base_url).netloc.lower()
    if source_type == "github" or host.endswith("github.com"):
        return "github"
    if source_type == "arxiv" or "arxiv.org" in host:
        return "arxiv"
    if source_type == "rss":
        return "rss"
    return "generic"


def _kind_for_profile(profile: dict[str, Any], base_url: str) -> str:
    source_type = str(profile.get("type", "web"))
    host = urlparse(base_url).netloc.lower()
    if source_type in {"github", "arxiv"} or host.startswith("api.") or host == "api.github.com":
        return "api"
    return "web"


def _auth_mode_for_profile(profile: dict[str, Any]) -> str:
    if not bool(profile.get("auth_required", False)):
        return "none"
    auth_method = str(profile.get("auth_method") or "")
    if "token" in auth_method:
        return "token"
    if "cookie" in auth_method:
        return "cookie"
    if "header" in auth_method:
        return "header"
    if "basic" in auth_method:
        return "basic"
    return "token"


def _channel_name(base_url: str) -> str:
    parsed = urlparse(base_url)
    return parsed.netloc or base_url


def _parse_config_json(config_json: object) -> dict[str, Any]:
    if not config_json or not isinstance(config_json, str):
        return {}
    parsed = json.loads(config_json)
    return parsed if isinstance(parsed, dict) else {}


def _normalize_profile_payload(payload: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    source = dict(payload)
    if creating:
        missing = sorted(REQUIRED_PROFILE_KEYS - set(source))
        if missing:
            raise ValueError(f"profile {source.get('id', '<unknown>')} missing keys: {', '.join(missing)}")
    for key in ("id", "name", "type", "target_domain", "url", "trust_level", "schedule", "topic"):
        if key in source and source[key] is not None:
            source[key] = str(source[key]).strip()
    if source.get("type") not in SOURCE_TYPES:
        raise ValueError(f"profile {source.get('id', '<unknown>')} invalid type: {source.get('type')}")
    if source.get("trust_level") not in {"trusted", "untrusted"}:
        raise ValueError(f"profile {source.get('id', '<unknown>')} invalid trust_level: {source.get('trust_level')}")
    source.setdefault("baseline_on_first_run", False)
    source.setdefault("run_policy", "scheduled")
    source.setdefault("enabled", True)
    for key in ("auto_ingest", "auth_required", "baseline_on_first_run", "enabled"):
        if key in source and isinstance(source[key], int):
            source[key] = bool(source[key])
    return source


def _channel_id_for_source(connection: sqlite3.Connection, source: dict[str, Any]) -> str:
    channel_id = source.get("channel_id")
    if channel_id:
        channel = get_channel(connection, str(channel_id))
        if channel["target_domain"] != source["target_domain"]:
            raise ValueError(f"channel domain mismatch: {channel_id}")
        return str(channel_id)
    return upsert_channel(connection, derive_channel_seed(source))


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


def validate_run_policy(profile: dict[str, Any]) -> str:
    profile_id = profile.get("id", "<unknown>")
    run_policy = str(profile.get("run_policy", "scheduled"))
    if run_policy not in RUN_POLICIES:
        raise ValueError(f"profile {profile_id} invalid run_policy: {run_policy}")
    return run_policy


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


def validate_profile_source_id(profile: dict[str, Any]) -> None:
    source_id = str(profile.get("id", ""))
    source_path = Path(source_id)
    if (
        not source_id
        or source_path.is_absolute()
        or len(source_path.parts) != 1
        or "/" in source_id
        or "\\" in source_id
        or ".." in source_path.parts
    ):
        raise ValueError(f"Invalid source id path: {source_id}")


def validate_accelerator_metadata(profile: dict[str, Any]) -> None:
    profile_id = profile.get("id", "<unknown>")
    if profile.get("discovery_mode") is not None:
        if profile.get("run_policy", "scheduled") != "scheduled":
            raise ValueError(f"profile {profile_id} discovery profiles require run_policy: scheduled")
        if profile["discovery_mode"] not in DISCOVERY_MODES:
            raise ValueError(f"profile {profile_id} invalid discovery_mode: {profile['discovery_mode']}")
        if profile.get("extract_mode") != "discovery_index":
            raise ValueError(f"profile {profile_id} discovery profiles require extract_mode: discovery_index")
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
        for key in DISCOVERY_OPTIONAL_LIST_KEYS:
            if key in profile and (
                not isinstance(profile[key], list) or not all(isinstance(item, str) for item in profile[key])
            ):
                raise ValueError(f"profile {profile_id} {key} must be a list of strings")
        return

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
