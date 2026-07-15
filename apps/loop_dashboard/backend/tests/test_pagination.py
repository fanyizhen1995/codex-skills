from __future__ import annotations

import base64
import json

import pytest

from loop_dashboard.pagination import (
    CursorCodec,
    CursorError,
    PageSizeError,
    paginate_items,
)


def _items(count: int) -> list[dict[str, str]]:
    return [
        {
            "item_id": f"item-{index:03d}",
            "updated_at": f"2026-07-15T00:{index:02d}:00Z",
        }
        for index in range(count)
    ]


def test_cursor_carries_the_bound_collection_and_snapshot_contract() -> None:
    codec = CursorCodec(b"test-secret")

    page = paginate_items(
        _items(25),
        endpoint="runs",
        page_size=20,
        cursor=None,
        filters={"status": "active"},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )

    payload = codec.decode(page.next_cursor or "")
    assert payload.version == 1
    assert payload.endpoint == "runs"
    assert payload.filter_fingerprint == codec.filter_fingerprint(
        {"status": "active"}
    )
    assert payload.direction == "next"
    assert payload.timestamp == "2026-07-15T00:05:00Z"
    assert payload.primary_key == "item-005"
    assert payload.snapshot_timestamp == "2026-07-15T00:24:00Z"
    assert payload.snapshot_primary_key == "item-024"


def test_keyset_pages_are_stable_when_a_newer_item_arrives() -> None:
    codec = CursorCodec(b"test-secret")
    original = _items(25)
    first = paginate_items(
        original,
        endpoint="runs",
        page_size=20,
        cursor=None,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )

    second = paginate_items(
        [
            *original,
            {"item_id": "item-new", "updated_at": "2026-07-15T01:00:00Z"},
        ],
        endpoint="runs",
        page_size=20,
        cursor=first.next_cursor,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )

    assert {item["item_id"] for item in first.items}.isdisjoint(
        item["item_id"] for item in second.items
    )
    assert second.total == 25
    assert second.previous_cursor is not None

    previous = paginate_items(
        original,
        endpoint="runs",
        page_size=20,
        cursor=second.previous_cursor,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    assert previous.items == first.items


def test_cursor_rejects_tampering_collection_filter_and_page_size_mismatch() -> None:
    codec = CursorCodec(b"test-secret")
    first = paginate_items(
        _items(25),
        endpoint="runs",
        page_size=20,
        cursor=None,
        filters={"status": "active"},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    assert first.next_cursor is not None
    raw = base64.urlsafe_b64decode(first.next_cursor + "=" * (-len(first.next_cursor) % 4))
    envelope = json.loads(raw)
    envelope["payload"]["endpoint"] = "actions"
    tampered = base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")

    with pytest.raises(CursorError, match="signature"):
        codec.decode(tampered)
    with pytest.raises(CursorError, match="endpoint"):
        paginate_items(
            _items(25),
            endpoint="actions",
            page_size=20,
            cursor=first.next_cursor,
            filters={"status": "active"},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )
    with pytest.raises(CursorError, match="filter"):
        paginate_items(
            _items(25),
            endpoint="runs",
            page_size=20,
            cursor=first.next_cursor,
            filters={"status": "done"},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )
    with pytest.raises(CursorError, match="page size"):
        paginate_items(
            _items(25),
            endpoint="runs",
            page_size=50,
            cursor=first.next_cursor,
            filters={"status": "active"},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )


@pytest.mark.parametrize("page_size", [0, 19, 21, 101, True])
def test_page_size_only_allows_20_50_or_100(page_size: object) -> None:
    with pytest.raises(PageSizeError):
        paginate_items(
            [],
            endpoint="runs",
            page_size=page_size,  # type: ignore[arg-type]
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=CursorCodec(b"test-secret"),
        )
