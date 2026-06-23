from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import paths  # type: ignore
    import validate as validate_module  # type: ignore
else:
    from . import paths
    from . import validate as validate_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wiki-cli")
    parser.add_argument("--root", type=Path)

    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--domain")
    validate_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = args.root if args.root is not None else paths.repo_root_from(Path.cwd())

    if args.command == "validate":
        return _run_validate(root, args.domain, args.json)

    parser.error(f"Unknown command: {args.command}")
    return 1


def _run_validate(root: Path, domain: str | None, output_json: bool) -> int:
    issues = validate_module.validate(root, domain=domain)
    if output_json:
        print(
            json.dumps(
                [
                    {
                        "code": issue.code,
                        "path": str(issue.path),
                        "message": issue.message,
                    }
                    for issue in issues
                ],
                indent=2,
            )
        )
    elif issues:
        for issue in issues:
            print(f"{issue.code} {issue.path} {issue.message}")
    else:
        print("No validation issues")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
