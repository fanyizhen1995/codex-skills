from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
from typing import Any, Generic, Mapping, Sequence, TypeVar


CURSOR_VERSION = 1
ALLOWED_PAGE_SIZES = frozenset({20, 50, 100})


class CursorError(ValueError):
    """Raised when an opaque cursor is malformed or belongs to another query."""


class PageSizeError(ValueError):
    """Raised when a collection page size is outside the API contract."""


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
    snapshot_sequence: int | None = None


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None
    page_size: int
    total: int
    has_more: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CursorCodec:
    def __init__(self, secret: bytes) -> None:
        if not isinstance(secret, bytes) or not secret:
            raise ValueError("cursor secret must be non-empty bytes")
        self._secret = secret

    def encode(self, payload: CursorPayload) -> str:
        payload_data = asdict(payload)
        serialized = self._serialize(payload_data)
        signature = hmac.new(self._secret, serialized, hashlib.sha256).hexdigest()
        envelope = self._serialize({"payload": payload_data, "signature": signature})
        return base64.urlsafe_b64encode(envelope).decode().rstrip("=")

    def decode(self, cursor: str) -> CursorPayload:
        if not isinstance(cursor, str) or not cursor:
            raise CursorError("cursor is malformed")
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
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
) -> Page[dict[str, Any]]:
    validate_page_size(page_size)
    fingerprint = codec.filter_fingerprint(filters)
    ordered = sorted(
        items,
        key=lambda item: _position(item, timestamp_key, primary_key),
        reverse=True,
    )
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
        if not ordered:
            return Page([], None, None, page_size, 0, False)
        snapshot = _position(ordered[0], timestamp_key, primary_key)
        total = len(ordered)
        direction = "next"
        boundary: tuple[str, str] | None = None
    else:
        snapshot = (
            payload.snapshot_timestamp,
            payload.snapshot_primary_key,
        )
        total = payload.snapshot_total
        direction = payload.direction
        boundary = (payload.timestamp, payload.primary_key)

    eligible = [
        item
        for item in ordered
        if _position(item, timestamp_key, primary_key) <= snapshot
    ]
    if boundary is None:
        candidates = eligible
    elif direction == "next":
        candidates = [
            item
            for item in eligible
            if _position(item, timestamp_key, primary_key) < boundary
        ]
    else:
        candidates = sorted(
            (
                item
                for item in eligible
                if _position(item, timestamp_key, primary_key) > boundary
            ),
            key=lambda item: _position(item, timestamp_key, primary_key),
        )

    selected = list(candidates[: page_size + 1])[:page_size]
    if direction == "previous":
        selected.reverse()
    if not selected:
        return Page([], None, None, page_size, total, False)

    first_position = _position(selected[0], timestamp_key, primary_key)
    last_position = _position(selected[-1], timestamp_key, primary_key)
    next_cursor = None
    previous_cursor = None
    if any(
        _position(item, timestamp_key, primary_key) < last_position
        for item in eligible
    ):
        next_cursor = codec.encode(
            _cursor_payload(
                endpoint,
                fingerprint,
                page_size,
                "next",
                last_position,
                snapshot,
                total,
            )
        )
    if any(
        _position(item, timestamp_key, primary_key) > first_position
        for item in eligible
    ):
        previous_cursor = codec.encode(
            _cursor_payload(
                endpoint,
                fingerprint,
                page_size,
                "previous",
                first_position,
                snapshot,
                total,
            )
        )
    return Page(
        selected,
        next_cursor,
        previous_cursor,
        page_size,
        total,
        next_cursor is not None,
    )


def _cursor_payload(
    endpoint: str,
    fingerprint: str,
    page_size: int,
    direction: str,
    position: tuple[str, str],
    snapshot: tuple[str, str],
    total: int,
    snapshot_sequence: int | None = None,
) -> CursorPayload:
    return CursorPayload(
        version=CURSOR_VERSION,
        endpoint=endpoint,
        filter_fingerprint=fingerprint,
        page_size=page_size,
        timestamp=position[0],
        primary_key=position[1],
        direction=direction,
        snapshot_timestamp=snapshot[0],
        snapshot_primary_key=snapshot[1],
        snapshot_total=total,
        snapshot_sequence=snapshot_sequence,
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
