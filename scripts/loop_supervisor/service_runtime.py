"""Runtime entrypoint for fixed allowlisted Supervisor-managed services."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .services import run_managed_service_runtime


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Supervisor-managed service")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--service-id", required=True)
    args = parser.parse_args(argv)
    return run_managed_service_runtime(args.project_root, args.service_id)


if __name__ == "__main__":
    raise SystemExit(main())
