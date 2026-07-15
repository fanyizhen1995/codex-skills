from __future__ import annotations

import base64
from collections import OrderedDict
import copy
from dataclasses import asdict, dataclass, field
import hashlib
import hmac
import json
import secrets
from threading import RLock
import time
from typing import Any, Generic, Mapping, Sequence, TypeVar


CURSOR_VERSION = 1
ALLOWED_PAGE_SIZES = frozenset({20, 50, 100})
MAX_CURSOR_CHARS = 4096
MAX_CURSOR_DECODED_BYTES = 2048
DEFAULT_SNAPSHOT_TTL_SECONDS = 300
DEFAULT_MAX_SNAPSHOTS = 128
DEFAULT_MAX_SNAPSHOT_ITEMS = 10_000
DEFAULT_MAX_SNAPSHOT_ROW_BYTES = 256 * 1024
DEFAULT_MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


class CursorError(ValueError):
    """Raised when an opaque cursor is malformed or belongs to another query."""


class PageSizeError(ValueError):
    """Raised when a collection page size is outside the API contract."""


class SnapshotCapacityError(RuntimeError):
    """Raised when a bounded server-side snapshot cannot be retained safely."""


@dataclass(frozen=True)
class CursorPayload:
    version: int
    endpoint: str
    filter_fingerprint: str
    page_size: int
    timestamp: str
    primary_key: str
    direction: str
    snapshot_timestamp: str
    snapshot_primary_key: str
    snapshot_total: int
    snapshot_id: str
    snapshot_sequence: int | None = None
    occurrence: int = 0
    snapshot_occurrence: int = 0


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None
    page_size: int
    total: int
    has_more: bool
    private_items: list[Any] = field(default_factory=list, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "next_cursor": self.next_cursor,
            "previous_cursor": self.previous_cursor,
            "page_size": self.page_size,
            "total": self.total,
            "has_more": self.has_more,
        }


@dataclass(frozen=True)
class SnapshotRow:
    item: dict[str, Any]
    timestamp: str
    source_id: str
    occurrence: int
    private_item: Any = None


@dataclass(frozen=True)
class CollectionSnapshot:
    snapshot_id: str
    endpoint: str
    filter_fingerprint: str
    rows: tuple[SnapshotRow, ...]
    created_at: float
    expires_at: float


class CursorCodec:
    def __init__(
        self,
        secret: bytes,
        *,
        snapshot_ttl_seconds: int = DEFAULT_SNAPSHOT_TTL_SECONDS,
        max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
        max_snapshot_items: int = DEFAULT_MAX_SNAPSHOT_ITEMS,
        max_snapshot_row_bytes: int = DEFAULT_MAX_SNAPSHOT_ROW_BYTES,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        if not isinstance(secret, bytes) or not secret:
            raise ValueError("cursor secret must be non-empty bytes")
        if any(
            value <= 0
            for value in (
                snapshot_ttl_seconds,
                max_snapshots,
                max_snapshot_items,
                max_snapshot_row_bytes,
                max_snapshot_bytes,
            )
        ):
            raise ValueError("snapshot bounds must be positive")
        self._secret = secret
        self._snapshot_ttl_seconds = snapshot_ttl_seconds
        self._max_snapshots = max_snapshots
        self._max_snapshot_items = max_snapshot_items
        self._max_snapshot_row_bytes = max_snapshot_row_bytes
        self._max_snapshot_bytes = max_snapshot_bytes
        self._snapshots: OrderedDict[str, CollectionSnapshot] = OrderedDict()
        self._snapshot_lock = RLock()

    @property
    def namespace(self) -> str:
        return hashlib.sha256(self._secret).hexdigest()

    def encode(self, payload: CursorPayload) -> str:
        payload_data = asdict(payload)
        serialized = self._serialize(payload_data)
        signature = hmac.new(self._secret, serialized, hashlib.sha256).hexdigest()
        envelope = self._serialize({"payload": payload_data, "signature": signature})
        cursor = base64.urlsafe_b64encode(envelope).decode().rstrip("=")
        if (
            len(envelope) > MAX_CURSOR_DECODED_BYTES
            or len(cursor) > MAX_CURSOR_CHARS
        ):
            raise SnapshotCapacityError("encoded cursor size limit exceeded")
        return cursor

    def decode(self, cursor: str) -> CursorPayload:
        if not isinstance(cursor, str) or not cursor:
            raise CursorError("cursor is malformed")
        if len(cursor) > MAX_CURSOR_CHARS:
            raise CursorError("cursor is too large")
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
            if len(raw) > MAX_CURSOR_DECODED_BYTES:
                raise CursorError("decoded cursor size limit exceeded")
            envelope = json.loads(raw)
            payload = envelope["payload"]
            signature = envelope["signature"]
            if not isinstance(payload, dict) or not isinstance(signature, str):
                raise TypeError
            expected = hmac.new(
                self._secret,
                self._serialize(payload),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise CursorError("cursor signature is invalid")
            decoded = CursorPayload(**payload)
            self._validate_payload(decoded)
            return decoded
        except CursorError:
            raise
        except (
            TypeError,
            ValueError,
            KeyError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise CursorError("cursor is malformed") from exc

    def filter_fingerprint(self, filters: Mapping[str, Any]) -> str:
        return hashlib.sha256(self._serialize(dict(filters))).hexdigest()

    def create_snapshot(
        self,
        endpoint: str,
        filter_fingerprint: str,
        items: Sequence[dict[str, Any]],
        *,
        timestamp_key: str,
        primary_key: str,
        private_items: Sequence[Any] | None = None,
    ) -> CollectionSnapshot:
        if len(items) > self._max_snapshot_items:
            raise SnapshotCapacityError("snapshot item limit exceeded")
        copied_items = copy.deepcopy(list(items))
        copied_private = (
            copy.deepcopy(list(private_items))
            if private_items is not None
            else [None] * len(copied_items)
        )
        if len(copied_private) != len(copied_items):
            raise ValueError("private snapshot items must align with public items")
        total_bytes = 0
        for item, private_item in zip(
            copied_items, copied_private, strict=True
        ):
            row_bytes = len(self._serialize(item))
            if private_item is not None:
                row_bytes += len(self._serialize(private_item))
            if row_bytes > self._max_snapshot_row_bytes:
                raise SnapshotCapacityError("snapshot row byte budget exceeded")
            total_bytes += row_bytes
            if total_bytes > self._max_snapshot_bytes:
                raise SnapshotCapacityError("snapshot total byte budget exceeded")
        source_positions = [
            _position(item, timestamp_key, primary_key) for item in copied_items
        ]
        occurrences: dict[tuple[str, str], int] = {}
        rows: list[SnapshotRow] = []
        for item, private_item, position in zip(
            copied_items,
            copied_private,
            source_positions,
            strict=True,
        ):
            occurrence = occurrences.get(position, 0)
            occurrences[position] = occurrence + 1
            rows.append(
                SnapshotRow(
                    item,
                    position[0],
                    position[1],
                    occurrence,
                    private_item,
                )
            )
        rows.sort(key=_row_position, reverse=True)
        now = time.monotonic()
        snapshot = CollectionSnapshot(
            snapshot_id=secrets.token_urlsafe(18),
            endpoint=endpoint,
            filter_fingerprint=filter_fingerprint,
            rows=tuple(rows),
            created_at=now,
            expires_at=now + self._snapshot_ttl_seconds,
        )
        with self._snapshot_lock:
            self._prune_snapshots(now)
            if len(self._snapshots) >= self._max_snapshots:
                raise SnapshotCapacityError("snapshot capacity exhausted")
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._snapshots.move_to_end(snapshot.snapshot_id)
        return snapshot

    def get_snapshot(self, payload: CursorPayload) -> CollectionSnapshot:
        now = time.monotonic()
        with self._snapshot_lock:
            self._prune_snapshots(now)
            snapshot = self._snapshots.get(payload.snapshot_id)
            if snapshot is None:
                raise CursorError("cursor snapshot is unavailable or expired")
            if (
                snapshot.endpoint != payload.endpoint
                or snapshot.filter_fingerprint != payload.filter_fingerprint
            ):
                raise CursorError("cursor snapshot collection mismatch")
            self._snapshots.move_to_end(payload.snapshot_id)
            return snapshot

    def discard_snapshot(self, snapshot_id: str) -> None:
        with self._snapshot_lock:
            self._snapshots.pop(snapshot_id, None)

    def reap_expired(self) -> None:
        with self._snapshot_lock:
            self._prune_snapshots(time.monotonic())

    def _prune_snapshots(self, now: float) -> None:
        expired = [
            snapshot_id
            for snapshot_id, snapshot in self._snapshots.items()
            if snapshot.expires_at <= now
        ]
        for snapshot_id in expired:
            self._snapshots.pop(snapshot_id, None)

    @staticmethod
    def _serialize(value: object) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()

    @staticmethod
    def _validate_payload(payload: CursorPayload) -> None:
        if payload.version != CURSOR_VERSION:
            raise CursorError("cursor version is invalid")
        if not payload.endpoint:
            raise CursorError("cursor endpoint is invalid")
        if not payload.filter_fingerprint:
            raise CursorError("cursor filter fingerprint is invalid")
        validate_page_size(payload.page_size)
        if not payload.timestamp or not payload.primary_key:
            raise CursorError("cursor position is invalid")
        if payload.direction not in {"next", "previous"}:
            raise CursorError("cursor direction is invalid")
        if not payload.snapshot_timestamp or not payload.snapshot_primary_key:
            raise CursorError("cursor snapshot is invalid")
        if not isinstance(payload.snapshot_id, str) or not payload.snapshot_id:
            raise CursorError("cursor snapshot id is invalid")
        if (
            not isinstance(payload.snapshot_total, int)
            or isinstance(payload.snapshot_total, bool)
            or payload.snapshot_total < 0
        ):
            raise CursorError("cursor snapshot total is invalid")
        if payload.snapshot_sequence is not None and (
            not isinstance(payload.snapshot_sequence, int)
            or isinstance(payload.snapshot_sequence, bool)
            or payload.snapshot_sequence < 0
        ):
            raise CursorError("cursor snapshot sequence is invalid")
        for occurrence in (payload.occurrence, payload.snapshot_occurrence):
            if (
                not isinstance(occurrence, int)
                or isinstance(occurrence, bool)
                or occurrence < 0
            ):
                raise CursorError("cursor occurrence is invalid")


def validate_page_size(page_size: int) -> None:
    if (
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
        or page_size not in ALLOWED_PAGE_SIZES
    ):
        raise PageSizeError(
            f"page_size must be one of {sorted(ALLOWED_PAGE_SIZES)}"
        )


def paginate_items(
    items: Sequence[dict[str, Any]],
    *,
    endpoint: str,
    page_size: int,
    cursor: str | None,
    filters: Mapping[str, Any],
    timestamp_key: str,
    primary_key: str,
    codec: CursorCodec,
    private_items: Sequence[Any] | None = None,
) -> Page[dict[str, Any]]:
    validate_page_size(page_size)
    fingerprint = codec.filter_fingerprint(filters)
    payload: CursorPayload | None = None
    if cursor:
        payload = codec.decode(cursor)
        _validate_collection_cursor(
            payload,
            endpoint=endpoint,
            page_size=page_size,
            fingerprint=fingerprint,
        )

    if payload is None:
        if not items:
            return Page([], None, None, page_size, 0, False)
        collection_snapshot = codec.create_snapshot(
            endpoint,
            fingerprint,
            items,
            timestamp_key=timestamp_key,
            primary_key=primary_key,
            private_items=private_items,
        )
        ordered = list(collection_snapshot.rows)
        snapshot = _row_position(ordered[0])
        total = len(ordered)
        snapshot_id = collection_snapshot.snapshot_id
        direction = "next"
        boundary: tuple[str, str, int] | None = None
    else:
        collection_snapshot = codec.get_snapshot(payload)
        ordered = list(collection_snapshot.rows)
        snapshot = (
            payload.snapshot_timestamp,
            payload.snapshot_primary_key,
            payload.snapshot_occurrence,
        )
        total = payload.snapshot_total
        snapshot_id = payload.snapshot_id
        if total != len(ordered):
            raise CursorError("cursor snapshot total mismatch")
        direction = payload.direction
        boundary = (payload.timestamp, payload.primary_key, payload.occurrence)

    eligible = [
        row for row in ordered if _row_position(row) <= snapshot
    ]
    if boundary is None:
        candidates = eligible
    elif direction == "next":
        candidates = [
            row for row in eligible if _row_position(row) < boundary
        ]
    else:
        candidates = sorted(
            (
                row for row in eligible if _row_position(row) > boundary
            ),
            key=_row_position,
        )

    selected = list(candidates[: page_size + 1])[:page_size]
    if direction == "previous":
        selected.reverse()
    if not selected:
        return Page([], None, None, page_size, total, False)

    first_position = _row_position(selected[0])
    last_position = _row_position(selected[-1])
    next_cursor = None
    previous_cursor = None

    def encode_page_cursor(cursor_payload: CursorPayload) -> str:
        try:
            return codec.encode(cursor_payload)
        except Exception:
            if payload is None:
                codec.discard_snapshot(snapshot_id)
            raise

    if any(
        _row_position(row) < last_position for row in eligible
    ):
        next_cursor = encode_page_cursor(
            _cursor_payload(
                endpoint,
                fingerprint,
                page_size,
                "next",
                last_position,
                snapshot,
                total,
                snapshot_id,
            )
        )
    if any(
        _row_position(row) > first_position for row in eligible
    ):
        previous_cursor = encode_page_cursor(
            _cursor_payload(
                endpoint,
                fingerprint,
                page_size,
                "previous",
                first_position,
                snapshot,
                total,
                snapshot_id,
            )
        )
    page = Page(
        [copy.deepcopy(row.item) for row in selected],
        next_cursor,
        previous_cursor,
        page_size,
        total,
        next_cursor is not None,
        [copy.deepcopy(row.private_item) for row in selected],
    )
    if page.next_cursor is None and page.previous_cursor is None:
        codec.discard_snapshot(snapshot_id)
    return page


def _cursor_payload(
    endpoint: str,
    fingerprint: str,
    page_size: int,
    direction: str,
    position: tuple[str, str] | tuple[str, str, int],
    snapshot: tuple[str, str] | tuple[str, str, int],
    total: int,
    snapshot_id: str,
    snapshot_sequence: int | None = None,
) -> CursorPayload:
    position_timestamp, position_key, occurrence = _structural_position(position)
    snapshot_timestamp, snapshot_key, snapshot_occurrence = _structural_position(
        snapshot
    )
    return CursorPayload(
        version=CURSOR_VERSION,
        endpoint=endpoint,
        filter_fingerprint=fingerprint,
        page_size=page_size,
        timestamp=position_timestamp,
        primary_key=position_key,
        direction=direction,
        snapshot_timestamp=snapshot_timestamp,
        snapshot_primary_key=snapshot_key,
        snapshot_total=total,
        snapshot_id=snapshot_id,
        snapshot_sequence=snapshot_sequence,
        occurrence=occurrence,
        snapshot_occurrence=snapshot_occurrence,
    )


def _validate_collection_cursor(
    payload: CursorPayload,
    *,
    endpoint: str,
    page_size: int,
    fingerprint: str,
) -> None:
    if payload.endpoint != endpoint:
        raise CursorError("cursor endpoint mismatch")
    if payload.page_size != page_size:
        raise CursorError("cursor page size mismatch")
    if payload.filter_fingerprint != fingerprint:
        raise CursorError("cursor filter mismatch")


def _position(
    item: Mapping[str, Any],
    timestamp_key: str,
    primary_key: str,
) -> tuple[str, str]:
    timestamp = item.get(timestamp_key)
    key = item.get(primary_key)
    if not isinstance(timestamp, str) or not isinstance(key, str):
        raise ValueError(
            f"paged items require string {timestamp_key} and {primary_key}"
        )
    return timestamp, key


def _row_position(row: SnapshotRow) -> tuple[str, str, int]:
    return row.timestamp, row.source_id, row.occurrence


def _structural_position(
    position: tuple[str, str] | tuple[str, str, int],
) -> tuple[str, str, int]:
    if len(position) == 2:
        return position[0], position[1], 0
    return position
