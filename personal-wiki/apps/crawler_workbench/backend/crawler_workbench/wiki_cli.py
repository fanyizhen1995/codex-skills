from __future__ import annotations

import subprocess
from typing import Any


def wiki_cli_command(settings: Any, *args: object) -> list[str]:
    return [
        "python",
        "personal-wiki/tools/wiki_cli/cli.py",
        "--root",
        "personal-wiki",
        *[str(arg) for arg in args],
    ]


def run_wiki_cli(settings: Any, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        wiki_cli_command(settings, *args),
        cwd=settings.repo_root,
        capture_output=True,
        text=True,
    )


def run_ingest_plan(settings: Any, domain: str, raw_path: str) -> subprocess.CompletedProcess[str]:
    return run_wiki_cli(settings, "ingest-plan", domain, raw_path)


def run_index(settings: Any, domain: str) -> subprocess.CompletedProcess[str]:
    return run_wiki_cli(settings, "index", domain)


def run_backlinks(settings: Any, domain: str) -> subprocess.CompletedProcess[str]:
    return run_wiki_cli(settings, "backlinks", "--domain", domain, "--write-json")


def run_validate(settings: Any, domain: str | None = None) -> subprocess.CompletedProcess[str]:
    args: list[str] = ["validate"]
    if domain is not None:
        args.extend(["--domain", domain])
    return run_wiki_cli(settings, *args)
