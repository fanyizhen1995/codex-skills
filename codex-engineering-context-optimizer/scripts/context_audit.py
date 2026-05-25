#!/usr/bin/env python3
"""Audit Codex session JSONL files for tool-output context bloat."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", help="Directory containing Codex session JSONL files.")
    parser.add_argument("--since", default=None, help="Only include records on/after YYYY-MM-DD.")
    parser.add_argument("--until", default=None, help="Only include records before YYYY-MM-DD.")
    parser.add_argument("--cwd-contains", default=None, help="Only include sessions whose cwd contains this text.")
    parser.add_argument("--large-thresholds", default="20000,50000,100000")
    return parser.parse_args()


def iter_jsonl_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
    else:
        yield from sorted(root.glob("**/*.jsonl"))


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return values[lo]
    return int(values[lo] * (hi - k) + values[hi] * (k - lo))


def in_date_range(ts: str, since: str | None, until: str | None) -> bool:
    day = ts[:10] if ts else ""
    if since and day < since:
        return False
    if until and day >= until:
        return False
    return True


def main() -> int:
    args = parse_args()
    root = Path(args.session_root).expanduser()
    thresholds = [int(x) for x in args.large_thresholds.split(",") if x.strip()]

    files_seen = 0
    files_included = 0
    response_types: Counter[str] = Counter()
    event_types: Counter[str] = Counter()
    function_calls: Counter[str] = Counter()
    custom_calls: Counter[str] = Counter()
    web_search_calls = 0
    tool_search_calls = 0
    output_lengths: list[int] = []
    output_lengths_by_kind: defaultdict[str, list[int]] = defaultdict(list)
    large_counts = Counter()
    by_day_outputs: defaultdict[str, list[int]] = defaultdict(list)
    by_cwd_outputs: defaultdict[str, list[int]] = defaultdict(list)
    compactions_by_day: Counter[str] = Counter()

    for path in iter_jsonl_files(root):
        files_seen += 1
        cwd = "?"
        include_file = True
        rows: list[dict] = []
        with path.open(errors="ignore") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                rows.append(row)
                if row.get("type") == "session_meta":
                    payload = row.get("payload") or {}
                    cwd = payload.get("cwd") or cwd
        if args.cwd_contains and args.cwd_contains not in cwd:
            include_file = False
        if not include_file:
            continue
        files_included += 1

        for row in rows:
            ts = row.get("timestamp") or ""
            if not in_date_range(ts, args.since, args.until):
                continue
            day = ts[:10] or "unknown"
            payload = row.get("payload") or {}
            typ = row.get("type")
            if typ == "event_msg":
                event_type = payload.get("type") or "<missing>"
                event_types[event_type] += 1
                if event_type == "context_compacted":
                    compactions_by_day[day] += 1
                continue
            if typ != "response_item":
                continue

            ptype = payload.get("type") or "<missing>"
            response_types[ptype] += 1
            if ptype == "function_call":
                function_calls[payload.get("name") or "<missing>"] += 1
            elif ptype == "custom_tool_call":
                custom_calls[payload.get("name") or "<missing>"] += 1
                text = payload.get("input") or ""
                length = len(text)
                output_lengths_by_kind["custom_tool_call_input"].append(length)
            elif ptype == "web_search_call":
                web_search_calls += 1
            elif ptype == "tool_search_call":
                tool_search_calls += 1

            if ptype in {"function_call_output", "custom_tool_call_output", "tool_search_output"}:
                text = payload.get("output") or ""
                length = len(text)
                output_lengths.append(length)
                output_lengths_by_kind[ptype].append(length)
                by_day_outputs[day].append(length)
                by_cwd_outputs[cwd].append(length)
                for threshold in thresholds:
                    if length >= threshold:
                        large_counts[f">={threshold}"] += 1

    print("# Codex Context Audit")
    print()
    print(f"- files_seen: {files_seen}")
    print(f"- files_included: {files_included}")
    print(f"- outputs: {len(output_lengths)}")
    print(f"- output_chars_total: {sum(output_lengths)}")
    print(f"- output_chars_p50: {percentile(output_lengths, 0.50)}")
    print(f"- output_chars_p95: {percentile(output_lengths, 0.95)}")
    print(f"- output_chars_p99: {percentile(output_lengths, 0.99)}")
    print(f"- output_chars_max: {max(output_lengths) if output_lengths else 0}")
    for key in sorted(large_counts):
        print(f"- large_outputs_{key}: {large_counts[key]}")
    print(f"- context_compacted: {event_types.get('context_compacted', 0)}")
    print(f"- web_search_call: {web_search_calls}")
    print(f"- tool_search_call: {tool_search_calls}")
    print()

    print("## Response Types")
    for key, value in response_types.most_common(20):
        print(f"- {key}: {value}")
    print()

    print("## Function Calls")
    for key, value in function_calls.most_common(30):
        print(f"- {key}: {value}")
    print()

    print("## Custom Tool Calls")
    for key, value in custom_calls.most_common(20):
        print(f"- {key}: {value}")
    print()

    print("## Output Length By Kind")
    for key, values in sorted(output_lengths_by_kind.items()):
        print(
            f"- {key}: count={len(values)} total={sum(values)} "
            f"p95={percentile(values, 0.95)} max={max(values) if values else 0}"
        )
    print()

    print("## By Day")
    for day in sorted(by_day_outputs):
        values = by_day_outputs[day]
        print(
            f"- {day}: outputs={len(values)} total={sum(values)} "
            f"p95={percentile(values, 0.95)} max={max(values) if values else 0} "
            f"compactions={compactions_by_day.get(day, 0)}"
        )
    print()

    print("## By CWD")
    for cwd, values in sorted(by_cwd_outputs.items(), key=lambda item: -sum(item[1]))[:20]:
        print(
            f"- {cwd}: outputs={len(values)} total={sum(values)} "
            f"p95={percentile(values, 0.95)} max={max(values) if values else 0}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
