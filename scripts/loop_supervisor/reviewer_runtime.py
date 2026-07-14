"""Lease heartbeat and loss checkpoints for Supervisor Reviewer actions."""

from __future__ import annotations

from threading import Event, Thread
from types import TracebackType
from typing import Self

from .store import LeaseError, SupervisorStore


class ActionLeaseGuard:
    """Renew one action lease in the background and gate every side effect."""

    def __init__(
        self,
        store: SupervisorStore,
        *,
        action_id: str,
        owner_id: str,
        lease_seconds: int,
        heartbeat_seconds: float,
    ) -> None:
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        self._store = store
        self._action_id = action_id
        self._owner_id = owner_id
        self._lease_seconds = lease_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._finished = Event()
        self._lost = Event()
        self._error: BaseException | None = None
        self._thread = Thread(
            target=self._heartbeat,
            name=f"reviewer-lease-{action_id}",
            daemon=True,
        )

    @property
    def lease_lost(self) -> bool:
        return self._lost.is_set()

    def __enter__(self) -> Self:
        self.checkpoint()
        self._thread.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._finished.set()
        if self._thread.ident is not None:
            self._thread.join()

    def checkpoint(self) -> None:
        if self._lost.is_set():
            detail = f": {self._error}" if self._error is not None else ""
            raise LeaseError(f"Reviewer action lease lost{detail}")
        try:
            renewed = self._store.renew_lease(
                self._action_id,
                self._owner_id,
                lease_seconds=self._lease_seconds,
            )
        except BaseException as exc:
            self._error = exc
            self._lost.set()
            raise LeaseError(f"Reviewer action lease lost: {exc}") from exc
        if not renewed:
            self._lost.set()
            raise LeaseError("Reviewer action lease lost")

    def _heartbeat(self) -> None:
        while not self._finished.wait(self._heartbeat_seconds):
            try:
                renewed = self._store.renew_lease(
                    self._action_id,
                    self._owner_id,
                    lease_seconds=self._lease_seconds,
                )
            except BaseException as exc:
                self._error = exc
                self._lost.set()
                return
            if not renewed:
                self._lost.set()
                return
