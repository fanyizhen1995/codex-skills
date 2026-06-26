# Copyright 2024 The HAMi Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence


EXPECTED_CONTENT = "step4-ready\n"


def write_expected(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.txt").write_text(EXPECTED_CONTENT, encoding="utf-8")
    return 0


def assert_expected(args: argparse.Namespace) -> int:
    result_path = Path(args.output_dir) / "result.txt"
    if not result_path.exists():
        raise SystemExit(f"missing expected file: {result_path}")

    if result_path.read_text(encoding="utf-8") != EXPECTED_CONTENT:
        raise SystemExit(f"unexpected content in {result_path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    write_parser = subcommands.add_parser("write-expected")
    write_parser.add_argument("--output-dir", required=True)
    write_parser.set_defaults(func=write_expected)

    assert_parser = subcommands.add_parser("assert-expected")
    assert_parser.add_argument("--output-dir", required=True)
    assert_parser.set_defaults(func=assert_expected)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
