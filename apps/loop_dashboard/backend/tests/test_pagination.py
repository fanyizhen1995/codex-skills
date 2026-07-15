from __future__ import annotations

import base64
import json

import pytest

from loop_dashboard.pagination import (
    CursorCodec,
    CursorError,
    CursorPayload,
    PageSizeError,
    SnapshotCapacityError,
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


def test_snapshot_survives_backdated_same_timestamp_inserts_and_deletions() -> None:
    codec = CursorCodec(b"test-secret")
    original = _items(45)
    expected_ids = [item["item_id"] for item in reversed(original)]
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
    mutated = [item for item in original if item["item_id"] != "item-015"]
    mutated.extend(
        [
            {
                "item_id": "item-backdated",
                "updated_at": "2026-07-15T00:10:30Z",
            },
            {
                "item_id": "item-010-a",
                "updated_at": "2026-07-15T00:10:00Z",
            },
        ]
    )

    pages = [first]
    while pages[-1].next_cursor:
        pages.append(
            paginate_items(
                mutated,
                endpoint="runs",
                page_size=20,
                cursor=pages[-1].next_cursor,
                filters={},
                timestamp_key="updated_at",
                primary_key="item_id",
                codec=codec,
            )
        )

    assert [
        item["item_id"] for page in pages for item in page.items
    ] == expected_ids
    assert all(page.total == 45 for page in pages)

    reverse_pages = [pages[-1]]
    while reverse_pages[-1].previous_cursor:
        reverse_pages.append(
            paginate_items(
                mutated,
                endpoint="runs",
                page_size=20,
                cursor=reverse_pages[-1].previous_cursor,
                filters={},
                timestamp_key="updated_at",
                primary_key="item_id",
                codec=codec,
            )
        )
    assert reverse_pages[-1].items == first.items


def test_duplicate_source_positions_cross_page_boundaries_without_skips() -> None:
    codec = CursorCodec(b"test-secret")
    items = [
        {
            "item_id": "duplicate-source-id",
            "updated_at": "2026-07-15T00:00:00Z",
            "occurrence": index,
        }
        for index in range(45)
    ]

    pages = []
    cursor = None
    while not pages or cursor:
        page = paginate_items(
            items,
            endpoint="duplicates",
            page_size=20,
            cursor=cursor,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )
        pages.append(page)
        cursor = page.next_cursor

    assert [item["occurrence"] for page in pages for item in page.items] == list(
        reversed(range(45))
    )
    assert all(page.total == 45 for page in pages)

    reverse = paginate_items(
        [],
        endpoint="duplicates",
        page_size=20,
        cursor=pages[-1].previous_cursor,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    assert reverse.items == pages[-2].items


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


def test_cursor_rejects_oversized_input_before_decode() -> None:
    with pytest.raises(CursorError, match="too large"):
        CursorCodec(b"test-secret").decode("A" * 5000)


def test_cursor_rejects_oversized_encoded_and_decoded_envelopes() -> None:
    codec = CursorCodec(b"test-secret")
    payload = CursorPayload(
        version=1,
        endpoint="x" * 5000,
        filter_fingerprint="filters",
        page_size=20,
        timestamp="2026-07-15T00:00:00Z",
        primary_key="item-1",
        direction="next",
        snapshot_timestamp="2026-07-15T00:00:00Z",
        snapshot_primary_key="item-1",
        snapshot_total=1,
        snapshot_id="snapshot-1",
    )

    with pytest.raises(SnapshotCapacityError, match="encoded cursor size"):
        codec.encode(payload)
    with pytest.raises(CursorError, match="decoded cursor size"):
        codec.decode("A" * 3000)


def test_failed_cursor_encoding_releases_new_snapshot_capacity() -> None:
    codec = CursorCodec(b"test-secret", max_snapshots=1)
    oversized_key_items = [
        {
            "item_id": "x" * 3000,
            "updated_at": f"2026-07-15T00:{index:02d}:00Z",
        }
        for index in range(25)
    ]

    with pytest.raises(SnapshotCapacityError, match="encoded cursor size"):
        paginate_items(
            oversized_key_items,
            endpoint="oversized-key",
            page_size=20,
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )

    page = paginate_items(
        _items(25),
        endpoint="normal-after-failure",
        page_size=20,
        cursor=None,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    assert page.next_cursor is not None


def test_snapshot_sessions_have_ttl_and_capacity_bounds(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("loop_dashboard.pagination.time.monotonic", lambda: now[0])
    codec = CursorCodec(
        b"test-secret",
        snapshot_ttl_seconds=1,
        max_snapshots=1,
    )
    first = paginate_items(
        _items(25),
        endpoint="runs-a",
        page_size=20,
        cursor=None,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    with pytest.raises(SnapshotCapacityError, match="snapshot capacity"):
        paginate_items(
            _items(25),
            endpoint="runs-b",
            page_size=20,
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )
    assert paginate_items(
        [],
        endpoint="runs-a",
        page_size=20,
        cursor=first.next_cursor,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    ).items

    now[0] = 102.0
    second = paginate_items(
        _items(25),
        endpoint="runs-b",
        page_size=20,
        cursor=None,
        filters={},
        timestamp_key="updated_at",
        primary_key="item_id",
        codec=codec,
    )
    with pytest.raises(CursorError, match="unavailable or expired"):
        paginate_items(
            [],
            endpoint="runs-a",
            page_size=20,
            cursor=first.next_cursor,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=codec,
        )
    assert second.next_cursor is not None


def test_snapshot_row_count_and_serialized_byte_budgets_are_capacity_errors() -> None:
    with pytest.raises(SnapshotCapacityError, match="item limit"):
        paginate_items(
            _items(2),
            endpoint="item-limit",
            page_size=20,
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=CursorCodec(b"test-secret", max_snapshot_items=1),
        )

    oversized = [
        {
            "item_id": "large",
            "updated_at": "2026-07-15T00:00:00Z",
            "body": "x" * 100,
        }
    ]
    with pytest.raises(SnapshotCapacityError, match="row byte budget"):
        paginate_items(
            oversized,
            endpoint="row-bytes",
            page_size=20,
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=CursorCodec(b"test-secret", max_snapshot_row_bytes=64),
        )

    with pytest.raises(SnapshotCapacityError, match="total byte budget"):
        paginate_items(
            [
                {
                    "item_id": f"item-{index}",
                    "updated_at": "2026-07-15T00:00:00Z",
                    "body": "x" * 40,
                }
                for index in range(2)
            ],
            endpoint="total-bytes",
            page_size=20,
            cursor=None,
            filters={},
            timestamp_key="updated_at",
            primary_key="item_id",
            codec=CursorCodec(
                b"test-secret",
                max_snapshot_row_bytes=256,
                max_snapshot_bytes=150,
            ),
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
