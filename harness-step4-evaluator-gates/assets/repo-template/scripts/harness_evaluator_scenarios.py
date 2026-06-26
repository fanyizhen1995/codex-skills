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
from pathlib import Path
from typing import Any, Mapping


SCENARIO_REQUIRED_KEYS = {
    "scenario_id",
    "user_goal",
    "prerequisites",
    "entrypoint",
    "steps",
    "expected_outcomes",
    "failure_signals",
    "cleanup",
    "automation_hint",
}


def scenario_file_path(repo_root: Path | str, task_id: str) -> Path:
    return Path(repo_root) / "docs" / "harness" / "evaluator-scenarios" / f"{task_id}.json"


def validate_scenario_contract(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("scenario contract must be a mapping")
    if payload.get("task_id") is None:
        raise ValueError("scenario contract is missing task_id")
    if "user_scenarios" not in payload:
        raise ValueError("scenario contract is missing user_scenarios")
    for index, scenario in enumerate(payload["user_scenarios"]):
        if not isinstance(scenario, Mapping):
            raise ValueError(f"scenario at index {index} must be a mapping")
        missing = SCENARIO_REQUIRED_KEYS - scenario.keys()
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(
                f"scenario at index {index} is missing required keys: {missing_list}"
            )


def load_task_scenarios(repo_root: Path | str, task_id: str) -> dict[str, Any]:
    path = scenario_file_path(repo_root, task_id)
    if not path.exists():
        return {
            "task_id": task_id,
            "must_simulate": True,
            "source": str(path),
            "user_scenarios": [],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_scenario_contract(payload)
    if payload["task_id"] != task_id:
        raise ValueError(
            f"scenario contract task_id {payload['task_id']!r} does not match requested task_id {task_id!r}"
        )
    return {
        "task_id": payload["task_id"],
        "must_simulate": bool(payload.get("must_simulate", True)),
        "source": str(path),
        "user_scenarios": payload["user_scenarios"],
    }
