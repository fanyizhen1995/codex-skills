from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    return connection


@contextmanager
def open_db(path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
    finally:
        connection.close()


def migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _ensure_column(connection, "source_profiles", "baseline_on_first_run", "integer not null default 0")
    _ensure_column(connection, "source_profiles", "run_policy", "text not null default 'scheduled'")
    _ensure_column(connection, "source_profiles", "config_json", "text not null default '{}'")
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"pragma table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"alter table {table} add column {column} {definition}")


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
