#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "experiment"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Codex experiment directory.")
    parser.add_argument("--name", required=True, help="Short experiment name.")
    parser.add_argument(
        "--root",
        default=".codex/experiments",
        help="Experiment root directory. Default: .codex/experiments",
    )
    args = parser.parse_args()

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.root) / f"{timestamp}-{slugify(args.name)}"
    out_dir.mkdir(parents=True, exist_ok=False)

    command = out_dir / "command.sh"
    command.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "# Put the experiment command here. Full output should be redirected to raw.log.\n",
        encoding="utf-8",
    )
    command.chmod(0o755)

    (out_dir / "raw.log").write_text("", encoding="utf-8")
    (out_dir / "failures.txt").write_text("", encoding="utf-8")
    (out_dir / "summary.json").write_text("{}\n", encoding="utf-8")
    (out_dir / "report.md").write_text(
        f"# Experiment Report\n\n- Name: {args.name}\n- Directory: {out_dir}\n- Status: pending\n",
        encoding="utf-8",
    )

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
