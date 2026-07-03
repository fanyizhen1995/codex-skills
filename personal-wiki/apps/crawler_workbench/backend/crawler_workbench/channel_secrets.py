from __future__ import annotations

import os
import sqlite3
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .channels import get_channel, update_channel_auth_state
from .settings import Settings


class SecretError(RuntimeError):
    pass


class SecretKeyUnavailableError(SecretError):
    pass


class SecretDecryptError(SecretError):
    pass


def set_channel_secret(
    settings: Settings,
    connection: sqlite3.Connection,
    channel_id: str,
    *,
    secret_kind: str,
    secret: str,
) -> dict[str, Any]:
    channel = get_channel(connection, channel_id)
    fernet = _fernet_for_write(settings)
    ciphertext = fernet.encrypt(secret.encode("utf-8"))
    connection.execute(
        """
        insert into channel_secrets (id, channel_id, secret_kind, ciphertext, nonce, updated_at)
        values (?, ?, ?, ?, ?, current_timestamp)
        on conflict(channel_id) do update set
          secret_kind = excluded.secret_kind,
          ciphertext = excluded.ciphertext,
          nonce = excluded.nonce,
          updated_at = current_timestamp
        """,
        (channel_id, channel_id, secret_kind, ciphertext, b"fernet-v1"),
    )
    if channel["auth_required"]:
        update_channel_auth_state(connection, channel_id, "ready")
    connection.commit()
    return secret_status(connection, channel_id)


def delete_channel_secret(settings: Settings, connection: sqlite3.Connection, channel_id: str) -> dict[str, Any]:
    channel = get_channel(connection, channel_id)
    connection.execute("delete from channel_secrets where channel_id = ?", (channel_id,))
    if channel["auth_required"]:
        update_channel_auth_state(connection, channel_id, "needs_auth_config")
    connection.commit()
    return secret_status(connection, channel_id)


def secret_status(connection: sqlite3.Connection, channel_id: str) -> dict[str, Any]:
    channel = get_channel(connection, channel_id)
    row = connection.execute(
        "select secret_kind from channel_secrets where channel_id = ?",
        (channel_id,),
    ).fetchone()
    return {
        "channel_id": channel_id,
        "secret_kind": row["secret_kind"] if row is not None else None,
        "secret_configured": row is not None,
        "auth_state": channel["auth_state"],
    }


def get_channel_secret(
    settings: Settings,
    connection: sqlite3.Connection,
    channel_id: str,
) -> dict[str, str] | None:
    row = connection.execute(
        "select secret_kind, ciphertext from channel_secrets where channel_id = ?",
        (channel_id,),
    ).fetchone()
    if row is None:
        return None
    fernet = _fernet_for_read(settings)
    try:
        plaintext = fernet.decrypt(bytes(row["ciphertext"])).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise SecretDecryptError("unable to decrypt channel secret") from exc
    return {"secret_kind": str(row["secret_kind"]), "secret": plaintext}


def has_channel_secret(connection: sqlite3.Connection, channel_id: str) -> bool:
    row = connection.execute(
        "select 1 from channel_secrets where channel_id = ?",
        (channel_id,),
    ).fetchone()
    return row is not None


def _fernet_for_write(settings: Settings) -> Fernet:
    key_path = settings.secrets_key_path
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    return _fernet_for_read(settings)


def _fernet_for_read(settings: Settings) -> Fernet:
    key_path = settings.secrets_key_path
    if not key_path.exists():
        raise SecretKeyUnavailableError(f"secret key file is missing: {key_path}")
    try:
        return Fernet(key_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise SecretKeyUnavailableError(f"secret key file is unavailable: {key_path}") from exc

