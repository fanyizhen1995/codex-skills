#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ERROR_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\berror\b",
        r"\bfailed\b",
        r"\bfail\b",
        r"\bexception\b",
        r"\btraceback\b",
        r"\btimeout\b",
        r"\bpanic\b",
        r"\b502\b",
        r"\b5\d\d\b",
    )
]


def tail(lines: list[str], n: int) -> list[str]:
    return lines[-n:] if len(lines) > n else lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a long experiment log.")
    parser.add_argument("log", help="Path to raw log file.")
    parser.add_argument("--status", type=int, default=None, help="Command exit status.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for summary.json/report.md/failures.txt. Defaults to log parent.",
    )
    parser.add_argument("--failure-lines", type=int, default=120)
    parser.add_argument("--tail-lines", type=int, default=80)
    args = parser.parse_args()

    log_path = Path(args.log)
    out_dir = Path(args.out_dir) if args.out_dir else log_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    failure_rows = []
    pattern_counts: Counter[str] = Counter()
    for index, line in enumerate(lines, start=1):
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                pattern_counts[pattern.pattern] += 1
                failure_rows.append({"line": index, "text": line[:500]})
                break

    failures = failure_rows[: args.failure_lines]
    summary = {
        "log": str(log_path),
        "status": args.status,
        "ok": args.status == 0 and not failures,
        "line_count": len(lines),
        "char_count": len(text),
        "failure_count": len(failure_rows),
        "failure_pattern_counts": dict(pattern_counts),
        "tail": tail(lines, args.tail_lines),
        "failures": failures,
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "failures.txt").write_text(
        "\n".join(f"{row['line']}: {row['text']}" for row in failures) + ("\n" if failures else ""),
        encoding="utf-8",
    )

    report_lines = [
        "# Experiment Report",
        "",
        f"- Log: {log_path}",
        f"- Exit status: {args.status}",
        f"- OK: {summary['ok']}",
        f"- Lines: {summary['line_count']}",
        f"- Characters: {summary['char_count']}",
        f"- Failure matches: {summary['failure_count']}",
        "",
        "## Failure Samples",
        "",
    ]
    if failures:
        report_lines.extend(f"- line {row['line']}: `{row['text'][:240]}`" for row in failures[:20])
    else:
        report_lines.append("- None")
    report_lines.extend(["", "## Tail", ""])
    report_lines.extend(f"    {line[:240]}" for line in tail(lines, min(args.tail_lines, 40)))
    (out_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps({k: summary[k] for k in ("ok", "status", "line_count", "failure_count")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
