from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from .db import open_db
from .fetch_service import run_source_once
from .settings import Settings


LOG = logging.getLogger("crawler_workbench.scheduler")

_SCHEDULE_INTERVALS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


class Scheduler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_once(self) -> int:
        return await asyncio.to_thread(self._run_once_sync)

    def _run_once_sync(self) -> int:
        now = datetime.now(UTC).replace(tzinfo=None)
        with open_db(self.settings.database_path) as db:
            placeholders = ", ".join("?" for _ in _SCHEDULE_INTERVALS)
            rows = db.execute(
                f"""
                select id, schedule, next_run_at from source_profiles
                where enabled = 1
                  and schedule in ({placeholders})
                  and auth_state = 'ready'
                order by id
                """,
                tuple(_SCHEDULE_INTERVALS),
            ).fetchall()
            due_rows = [row for row in rows if _is_due(row["next_run_at"], now)]

            for row in due_rows:
                source_id = str(row["id"])
                schedule = str(row["schedule"])
                try:
                    run_source_once(self.settings, db, source_id)
                except Exception:
                    LOG.exception("scheduled source run failed: %s", source_id)
                _advance_next_run_at(db, source_id, schedule, now)

        return len(due_rows)

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.scheduler_interval_seconds)
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOG.exception("scheduler run failed")


def _next_run_at(now: datetime, schedule: str) -> datetime | None:
    interval = _SCHEDULE_INTERVALS.get(schedule)
    if interval is None:
        return None
    return now + interval


def _advance_next_run_at(db, source_id: str, schedule: str, now: datetime) -> None:
    next_run_at = _next_run_at(now, schedule)
    if next_run_at is None:
        return
    db.execute(
        """
        update source_profiles
        set next_run_at = ?, updated_at = current_timestamp
        where id = ?
        """,
        (next_run_at.isoformat(timespec="seconds"), source_id),
    )
    db.commit()


def _is_due(next_run_at: str | None, now: datetime) -> bool:
    if next_run_at is None:
        return True
    return datetime.fromisoformat(next_run_at) <= now
