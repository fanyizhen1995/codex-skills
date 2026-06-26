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

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts import harness_evaluator_hooks, harness_evaluator_orchestrator
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    import harness_evaluator_hooks
    import harness_evaluator_orchestrator


def _write_trace(mode: str, root: Path) -> None:
    trace_file = os.environ.get("HARNESS_EVALUATOR_TRACE_FILE", "").strip()
    if not trace_file:
        return
    payload = {
        "mode": mode,
        "cwd": str(root),
        "recursive_guard": os.environ.get("HARNESS_EVALUATOR_SKIP_HOOKS") == "1",
    }
    path = Path(trace_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _hook_output_payload(
    decision: dict[str, str] | None,
    *,
    stop_hook_active: bool = False,
) -> dict[str, Any]:
    if not decision:
        return {"continue": True}
    if str(decision.get("decision", "")) == "block":
        return {
            "continue": False,
            "stopReason": str(decision.get("reason", "")),
        }
    return {"continue": True}


def _resolve_task_id(root: Path) -> str:
    session = harness_evaluator_hooks._resolve_session(root)
    if session is None or not session.get("task"):
        return ""
    return str(session["task"])


def _run_stop_pipeline(root: Path) -> dict[str, str] | None:
    task_id = _resolve_task_id(root)
    if not task_id:
        return harness_evaluator_hooks.stop_hook(root)
    return harness_evaluator_orchestrator.run_one_stop_auto_gate(task_id, root)


def main_with_payload(mode: str, payload: Mapping[str, Any]) -> int:
    root = Path(str(payload["cwd"]))
    _write_trace(mode, root)
    stop_hook_active = bool(payload.get("stop_hook_active"))
    if os.environ.get("HARNESS_EVALUATOR_SKIP_HOOKS") == "1":
        print(json.dumps(_hook_output_payload(None, stop_hook_active=stop_hook_active)))
        return 0
    if mode == "stop":
        decision = _run_stop_pipeline(root)
    else:
        decision = harness_evaluator_hooks.subagent_stop_hook(root)
    print(json.dumps(_hook_output_payload(decision, stop_hook_active=stop_hook_active)))
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: harness_evaluator_hook_driver.py <mode>")
    mode = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    return main_with_payload(mode, payload)


if __name__ == "__main__":
    raise SystemExit(main())
