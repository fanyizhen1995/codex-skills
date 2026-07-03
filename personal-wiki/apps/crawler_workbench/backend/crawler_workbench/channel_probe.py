from __future__ import annotations

import re
import sqlite3
from typing import Any

import httpx

from .channel_secrets import get_channel_secret, has_channel_secret
from .channels import get_channel
from .settings import Settings


SUPPORTED_HTTP_KINDS = {"web", "api", "browser"}
SECRET_REDACTION = "[redacted]"


def run_channel_probe(
    settings: Settings,
    connection: sqlite3.Connection,
    channel_id: str,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    channel = get_channel(connection, channel_id)
    if channel["kind"] not in SUPPORTED_HTTP_KINDS:
        return _persist_probe(
            connection,
            channel_id,
            status="unsupported",
            summary=f"channel kind {channel['kind']} is not supported by HTTP probe",
        )
    if channel["auth_required"] and not has_channel_secret(connection, channel_id):
        return _persist_probe(
            connection,
            channel_id,
            status="needs_auth_config",
            summary="secret not configured",
        )

    probe_url = channel.get("probe_url") or channel["base_url"]
    headers = _headers_for_probe(settings, connection, channel_id, channel)
    owned_client = client is None
    http_client = client or httpx.Client(follow_redirects=True, timeout=30)
    try:
        response = http_client.request(str(channel.get("probe_method") or "GET"), probe_url, headers=headers, timeout=30)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
        return _persist_probe(
            connection,
            channel_id,
            status="network_failed",
            summary=_safe_summary(str(exc) or exc.__class__.__name__),
            error=exc.__class__.__name__,
        )
    finally:
        if owned_client:
            http_client.close()

    status, summary = _classify_response(response)
    return _persist_probe(
        connection,
        channel_id,
        status=status,
        http_status=response.status_code,
        final_url=str(response.url),
        summary=summary,
    )


def list_probe_runs(connection: sqlite3.Connection, channel_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    get_channel(connection, channel_id)
    rows = connection.execute(
        """
        select *
        from channel_probe_runs
        where channel_id = ?
        order by coalesce(finished_at, started_at) desc, id desc
        limit ?
        """,
        (channel_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _headers_for_probe(
    settings: Settings,
    connection: sqlite3.Connection,
    channel_id: str,
    channel: dict[str, Any],
) -> dict[str, str]:
    if not channel["auth_required"]:
        return {}
    secret = get_channel_secret(settings, connection, channel_id)
    if secret is None:
        return {}
    value = secret["secret"]
    auth_mode = str(channel.get("auth_mode") or "token")
    if auth_mode == "token":
        return {"Authorization": f"Bearer {value}"}
    if auth_mode == "header":
        return {"Authorization": value}
    if auth_mode == "cookie":
        return {"Cookie": value}
    if auth_mode == "basic":
        return {"Authorization": f"Basic {value}"}
    return {}


def _classify_response(response: httpx.Response) -> tuple[str, str]:
    if response.status_code in {401, 403}:
        return "auth_failed", f"HTTP {response.status_code} from {response.url.host or response.url}"
    text = response.text[:4096]
    lowered = text.lower()
    if _looks_like_login(lowered):
        return "needs_browser", "login form detected"
    if "captcha" in lowered or "cf-challenge" in lowered or "cloudflare" in lowered:
        return "needs_browser", "captcha marker detected"
    visible_text = re.sub(r"<(script|style)[^>]*>.*?</\\1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    visible_text = re.sub(r"<[^>]+>", " ", visible_text)
    if "<script" in lowered and len(re.sub(r"\s+", "", visible_text)) < 24:
        return "needs_browser", "JS shell too small; likely browser-rendered"
    if 200 <= response.status_code < 400:
        return "ready", f"HTTP {response.status_code} from {response.url.host or response.url}"
    if response.status_code >= 500:
        return "network_failed", f"HTTP {response.status_code} from {response.url.host or response.url}"
    return "auth_failed", f"HTTP {response.status_code} from {response.url.host or response.url}"


def _looks_like_login(lowered: str) -> bool:
    return (
        "<form" in lowered
        and ("password" in lowered or "login" in lowered or "sign in" in lowered or "signin" in lowered)
    )


def _persist_probe(
    connection: sqlite3.Connection,
    channel_id: str,
    *,
    status: str,
    summary: str,
    http_status: int | None = None,
    final_url: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    safe_summary = _safe_summary(summary)
    row_id = connection.execute(
        """
        insert into channel_probe_runs (
          channel_id, status, finished_at, http_status, final_url, summary, error
        )
        values (?, ?, current_timestamp, ?, ?, ?, ?)
        """,
        (channel_id, status, http_status, final_url, safe_summary, error),
    ).lastrowid
    connection.execute(
        """
        update channels
        set auth_state = ?,
            last_probe_status = ?,
            last_probe_at = current_timestamp,
            last_probe_summary = ?,
            updated_at = current_timestamp
        where id = ?
        """,
        (status, status, safe_summary, channel_id),
    )
    connection.commit()
    row = connection.execute("select * from channel_probe_runs where id = ?", (row_id,)).fetchone()
    return dict(row)


def _safe_summary(value: str) -> str:
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", f"Bearer {SECRET_REDACTION}", value)
    sanitized = re.sub(r"(?i)(token|cookie|authorization|password)=?\\s*[^\\s,;]+", rf"\1={SECRET_REDACTION}", sanitized)
    if len(sanitized) > 240:
        sanitized = sanitized[:237] + "..."
    return sanitized
