from __future__ import annotations

import re
import sqlite3
from typing import Any
from urllib.parse import urlparse

CHANNEL_KINDS = {"web", "api", "mcp", "browser", "command"}
CHANNEL_CONNECTORS = {"generic", "github", "arxiv", "rss"}
CHANNEL_AUTH_MODES = {"none", "token", "cookie", "header", "basic", "command", "oauth_placeholder"}


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
          count(source_profiles.id) as source_count
        from channels
        left join source_profiles on source_profiles.channel_id = channels.id
        {where}
        group by channels.id
        order by channels.target_domain, channels.base_url_normalized
        """,
        params,
    ).fetchall()
    return [_channel_row(row) for row in rows]


def _channel_row(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    for key in ("enabled", "auth_required"):
        record[key] = bool(record[key])
    record["source_count"] = int(record.get("source_count") or 0)
    return record


def _allowed(value: str, allowed: set[str], fallback: str) -> str:
    return value if value in allowed else fallback
