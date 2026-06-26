#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


STOP_BLOCK = """[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py stop; else printf '{\\\"continue\\\":true}\\\\n'; fi"
timeout = 180
statusMessage = "Running task evaluator auto-gate"
"""

SUBAGENT_STOP_BLOCK = """[[hooks.SubagentStop]]

[[hooks.SubagentStop.hooks]]
type = "command"
command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py subagent-stop; else printf '{\\\"continue\\\":true}\\\\n'; fi"
timeout = 180
statusMessage = "Checking evaluator subagent output"
"""


def _replace_or_append(text: str, old: str, new: str, block: str, marker: str) -> str:
    if old in text:
        return text.replace(old, new)
    if new in text:
        return text
    if marker in text:
        return text
    stripped = text.rstrip()
    if stripped:
        stripped += "\n\n"
    return stripped + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=False)
    parser.add_argument("--config", default=str(Path.home() / ".codex" / "config.toml"))
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    backup = config_path.with_suffix(".toml.step4.bak")
    backup.write_text(original, encoding="utf-8")

    text = original
    text = text.replace(
        'command = "python3 scripts/harness_evaluator_hook_driver.py stop"',
        'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py stop; else printf \'{\\\\\"continue\\\\\":true}\\\\n\'; fi"',
    )
    text = text.replace(
        'command = "python3 scripts/harness_evaluator_hook_driver.py subagent-stop"',
        'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py subagent-stop; else printf \'{\\\\\"continue\\\\\":true}\\\\n\'; fi"',
    )
    text = text.replace("timeout = 30", "timeout = 180")
    text = _replace_or_append(
        text,
        'command = "python3 scripts/harness_evaluator_hooks.py stop"',
        'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py stop; else printf \'{\\\\\"continue\\\\\":true}\\\\n\'; fi"',
        STOP_BLOCK,
        "[[hooks.Stop]]",
    )
    text = _replace_or_append(
        text,
        'command = "python3 scripts/harness_evaluator_hooks.py subagent-stop"',
        'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py subagent-stop; else printf \'{\\\\\"continue\\\\\":true}\\\\n\'; fi"',
        SUBAGENT_STOP_BLOCK,
        "[[hooks.SubagentStop]]",
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"patched {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
