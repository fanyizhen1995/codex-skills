from __future__ import annotations

import re
import sqlite3
from typing import Any
from urllib.parse import urlparse

CHANNEL_KINDS = {"web", "api", "mcp", "browser", "command"}
CHANNEL_CONNECTORS = {"generic", "github", "arxiv", "rss"}
CHANNEL_AUTH_MODES = {"none", "token", "cookie", "header", "basic", "command", "oauth_placeholder"}
CHANNEL_AUTH_STATES = {"ready", "needs_auth_config", "auth_failed", "needs_browser", "network_failed", "unsupported"}
TRUST_LEVELS = {"trusted", "untrusted"}


class ChannelError(ValueError):
    pass


class ChannelNotFoundError(ChannelError):
    pass


class ChannelInUseError(ChannelError):
    pass


class ChannelNotReadyError(ChannelError):
    pass


def normalize_base_url(value: str) -> str:
    stripped = value.strip().rstrip("/")
    parsed = urlparse(stripped)
    if parsed.scheme and parsed.netloc:
        scheme = parsed.scheme.lower()
        host = parsed.netloc.lower()
        return f"{scheme}://{host}"
    return stripped.lower()


def channel_id_for(target_domain: str, base_url: str) -> str:
    normalized = normalize_base_url(base_url)
    parsed = urlparse(normalized)
    if parsed.scheme and parsed.netloc:
        stem = parsed.netloc
    else:
        stem = normalized
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return f"{target_domain}-{slug or 'channel'}"


def get_channel(connection: sqlite3.Connection, channel_id: str) -> dict[str, Any]:
    row = connection.execute(
        """
        select
          channels.*,
          count(distinct source_profiles.id) as source_count,
          channel_secrets.secret_kind as secret_kind,
          channel_secrets.id is not null as secret_configured
        from channels
        left join source_profiles on source_profiles.channel_id = channels.id
        left join channel_secrets on channel_secrets.channel_id = channels.id
        where channels.id = ?
        group by channels.id
        """,
        (channel_id,),
    ).fetchone()
    if row is None:
        raise ChannelNotFoundError(f"channel not found: {channel_id}")
    return _channel_row(row)


def upsert_channel(connection: sqlite3.Connection, seed: dict[str, Any]) -> str:
    base_url = normalize_base_url(str(seed["base_url"]))
    base_url_normalized = normalize_base_url(str(seed.get("base_url_normalized") or base_url))
    target_domain = str(seed["target_domain"])
    channel_id = str(seed.get("id") or channel_id_for(target_domain, base_url_normalized))
    auth_required = bool(seed.get("auth_required", False))
    auth_state = str(seed.get("auth_state") or ("needs_auth_config" if auth_required else "ready"))
    connection.execute(
        """
        insert into channels (
          id, target_domain, name, base_url, base_url_normalized, probe_url,
          probe_method, probe_config_json, kind, connector, trust_level, enabled,
          auth_required, auth_mode, auth_state, notes, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        on conflict(target_domain, base_url_normalized) do update set
          name = excluded.name,
          base_url = excluded.base_url,
          probe_url = coalesce(channels.probe_url, excluded.probe_url),
          probe_method = excluded.probe_method,
          probe_config_json = excluded.probe_config_json,
          kind = excluded.kind,
          connector = excluded.connector,
          trust_level = excluded.trust_level,
          enabled = excluded.enabled,
          auth_required = excluded.auth_required,
          auth_mode = excluded.auth_mode,
          auth_state = case
            when channels.auth_state = 'ready' and excluded.auth_required = 1 then channels.auth_state
            else excluded.auth_state
          end,
          updated_at = current_timestamp
        """,
        (
            channel_id,
            target_domain,
            str(seed["name"]),
            base_url,
            base_url_normalized,
            seed.get("probe_url"),
            str(seed.get("probe_method") or "GET"),
            str(seed.get("probe_config_json") or "{}"),
            _allowed(str(seed.get("kind") or "web"), CHANNEL_KINDS, "web"),
            _allowed(str(seed.get("connector") or "generic"), CHANNEL_CONNECTORS, "generic"),
            str(seed.get("trust_level") or "untrusted"),
            int(bool(seed.get("enabled", True))),
            int(auth_required),
            _allowed(str(seed.get("auth_mode") or "none"), CHANNEL_AUTH_MODES, "none"),
            auth_state,
            str(seed.get("notes") or ""),
        ),
    )
    row = connection.execute(
        "select id from channels where target_domain = ? and base_url_normalized = ?",
        (target_domain, base_url_normalized),
    ).fetchone()
    return str(row["id"])


def list_channels(connection: sqlite3.Connection, *, domain: str | None = None) -> list[dict[str, Any]]:
    where = ""
    params: tuple[Any, ...] = ()
    if domain:
        where = "where channels.target_domain = ?"
        params = (domain,)
    rows = connection.execute(
        f"""
        select
          channels.*,
          count(source_profiles.id) as source_count,
          channel_secrets.secret_kind as secret_kind,
          channel_secrets.id is not null as secret_configured
        from channels
        left join source_profiles on source_profiles.channel_id = channels.id
        left join channel_secrets on channel_secrets.channel_id = channels.id
        {where}
        group by channels.id
        order by channels.target_domain, channels.base_url_normalized
        """,
        params,
    ).fetchall()
    return [_channel_row(row) for row in rows]


def create_channel(connection: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    channel_id = upsert_channel(connection, _channel_seed_from_payload(payload))
    connection.commit()
    return get_channel(connection, channel_id)


def update_channel(connection: sqlite3.Connection, channel_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = get_channel(connection, channel_id)
    merged = {**existing, **{key: value for key, value in payload.items() if value is not None}}
    base_url = normalize_base_url(str(merged["base_url"]))
    base_url_normalized = normalize_base_url(str(merged.get("base_url_normalized") or base_url))
    connection.execute(
        """
        update channels
        set name = ?,
            base_url = ?,
            base_url_normalized = ?,
            probe_url = ?,
            probe_method = ?,
            probe_config_json = ?,
            kind = ?,
            connector = ?,
            trust_level = ?,
            enabled = ?,
            auth_required = ?,
            auth_mode = ?,
            auth_state = ?,
            notes = ?,
            updated_at = current_timestamp
        where id = ?
        """,
        (
            str(merged["name"]).strip(),
            base_url,
            base_url_normalized,
            _optional_text(merged.get("probe_url")),
            str(merged.get("probe_method") or "GET").upper(),
            str(merged.get("probe_config_json") or "{}"),
            _allowed(str(merged.get("kind") or "web"), CHANNEL_KINDS, "web"),
            _allowed(str(merged.get("connector") or "generic"), CHANNEL_CONNECTORS, "generic"),
            _allowed(str(merged.get("trust_level") or "untrusted"), TRUST_LEVELS, "untrusted"),
            int(bool(merged.get("enabled", True))),
            int(bool(merged.get("auth_required", False))),
            _allowed(str(merged.get("auth_mode") or "none"), CHANNEL_AUTH_MODES, "none"),
            _allowed(str(merged.get("auth_state") or "ready"), CHANNEL_AUTH_STATES, "ready"),
            str(merged.get("notes") or ""),
            channel_id,
        ),
    )
    connection.commit()
    return get_channel(connection, channel_id)


def delete_channel(connection: sqlite3.Connection, channel_id: str) -> dict[str, Any]:
    get_channel(connection, channel_id)
    row = connection.execute(
        "select count(*) as count from source_profiles where channel_id = ?",
        (channel_id,),
    ).fetchone()
    if int(row["count"]):
        raise ChannelInUseError(f"channel has attached sources: {channel_id}")
    connection.execute("delete from channels where id = ?", (channel_id,))
    connection.commit()
    return {"id": channel_id, "deleted": True}


def update_channel_auth_state(
    connection: sqlite3.Connection,
    channel_id: str,
    auth_state: str,
    *,
    last_probe_status: str | None = None,
    last_probe_summary: str | None = None,
) -> None:
    state = _allowed(auth_state, CHANNEL_AUTH_STATES, "needs_auth_config")
    connection.execute(
        """
        update channels
        set auth_state = ?,
            last_probe_status = coalesce(?, last_probe_status),
            last_probe_summary = coalesce(?, last_probe_summary),
            last_probe_at = case when ? is null then last_probe_at else current_timestamp end,
            updated_at = current_timestamp
        where id = ?
        """,
        (state, last_probe_status, last_probe_summary, last_probe_status, channel_id),
    )


def assert_channel_ready_for_source(connection: sqlite3.Connection, profile: dict[str, Any]) -> None:
    channel_id = profile.get("channel_id")
    if not channel_id:
        return
    channel = get_channel(connection, str(channel_id))
    if not channel["enabled"]:
        raise ChannelNotReadyError(f"channel disabled: {channel_id}")
    auth_state = str(channel["auth_state"])
    if auth_state != "ready":
        raise ChannelNotReadyError(f"channel not ready: {auth_state}")


def _channel_seed_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    target_domain = str(payload["target_domain"]).strip()
    base_url = normalize_base_url(str(payload["base_url"]))
    auth_required = bool(payload.get("auth_required", False))
    auth_state = str(payload.get("auth_state") or ("needs_auth_config" if auth_required else "ready"))
    return {
        "id": payload.get("id"),
        "target_domain": target_domain,
        "name": str(payload.get("name") or _name_from_base_url(base_url)),
        "base_url": base_url,
        "base_url_normalized": normalize_base_url(base_url),
        "probe_url": _optional_text(payload.get("probe_url")),
        "probe_method": str(payload.get("probe_method") or "GET").upper(),
        "probe_config_json": str(payload.get("probe_config_json") or "{}"),
        "kind": _allowed(str(payload.get("kind") or "web"), CHANNEL_KINDS, "web"),
        "connector": _allowed(str(payload.get("connector") or "generic"), CHANNEL_CONNECTORS, "generic"),
        "trust_level": _allowed(str(payload.get("trust_level") or "untrusted"), TRUST_LEVELS, "untrusted"),
        "enabled": bool(payload.get("enabled", True)),
        "auth_required": auth_required,
        "auth_mode": _allowed(str(payload.get("auth_mode") or "none"), CHANNEL_AUTH_MODES, "none"),
        "auth_state": _allowed(auth_state, CHANNEL_AUTH_STATES, "needs_auth_config" if auth_required else "ready"),
        "notes": str(payload.get("notes") or ""),
    }


def _name_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return parsed.netloc or base_url


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _channel_row(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    for key in ("enabled", "auth_required"):
        record[key] = bool(record[key])
    record["source_count"] = int(record.get("source_count") or 0)
    record["secret_configured"] = bool(record.get("secret_configured", False))
    return record


def _allowed(value: str, allowed: set[str], fallback: str) -> str:
    return value if value in allowed else fallback
