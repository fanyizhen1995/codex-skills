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

import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


REQUIRED_RESULT_KEYS = {
    "status",
    "gate",
    "task_id",
    "final_bundle_id",
    "attempt",
    "summary",
    "findings",
    "scenario_results",
    "rerun_commands",
    "environment_checks",
    "verdict_reason",
    "next_action",
}

REQUIRED_FINDING_KEYS = {
    "id",
    "severity",
    "category",
    "evidence",
    "recommended_action",
}

REQUIRED_SCENARIO_RESULT_KEYS = {
    "scenario_id",
    "status",
    "evidence",
    "notes",
}

ALLOWED_RESULT_STATUSES = {"pass", "fail", "blocked"}
ALLOWED_RESULT_GATES = {"task", "final"}
ALLOWED_NEXT_ACTIONS = {
    "repair_and_reevaluate",
    "request_missing_evidence",
    "proceed_to_user_acceptance",
    "proceed_with_risk",
}
ALLOWED_SCENARIO_RESULT_STATUSES = {"pass", "fail", "blocked"}


def repo_roots_for_harness(root: Path | str) -> list[Path]:
    current_root = Path(root).resolve()
    roots = [current_root]
    try:
        git_common_dir = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=current_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return roots

    common_dir = Path(git_common_dir)
    if not common_dir.is_absolute():
        common_dir = (current_root / common_dir).resolve()
    shared_root = common_dir.parent.resolve()
    if shared_root not in roots:
        roots.append(shared_root)
    return roots


def resolve_effective_eval_policy(
    task: Mapping[str, Any], defaults: Mapping[str, Any]
) -> dict[str, Any]:
    policy = copy.deepcopy(dict(defaults))
    policy.update(task.get("eval_policy", {}))
    if task.get("requires_eval") is False:
        policy["task_level_required"] = False
        policy["final_level_required"] = False
    return policy


def find_active_session_state(
    worktree: Path | str, branch: str, session_state_dir: Path | str
) -> dict[str, Any]:
    expected_worktree = Path(worktree).resolve()
    for state_file in Path(session_state_dir).glob("*.json"):
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if payload.get("branch") != branch:
            continue

        payload_worktree = payload.get("worktree")
        if not payload_worktree:
            continue

        if Path(payload_worktree).resolve() == expected_worktree:
            return payload

    raise FileNotFoundError(
        f"no active session state for branch={branch!r} worktree={str(expected_worktree)!r}"
    )


def validate_eval_result_payload(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("result payload must be a mapping")

    missing_keys = REQUIRED_RESULT_KEYS - payload.keys()
    if missing_keys:
        missing_list = ", ".join(sorted(missing_keys))
        raise ValueError(f"missing required result keys: {missing_list}")

    if payload["status"] not in ALLOWED_RESULT_STATUSES:
        raise ValueError(f"invalid result status: {payload['status']}")
    if payload["gate"] not in ALLOWED_RESULT_GATES:
        raise ValueError(f"invalid result gate: {payload['gate']}")
    if payload["next_action"] not in ALLOWED_NEXT_ACTIONS:
        raise ValueError(f"invalid result next_action: {payload['next_action']}")

    findings = payload["findings"]
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")

    for index, finding in enumerate(findings):
        if not isinstance(finding, Mapping):
            raise ValueError(f"finding at index {index} must be a mapping")
        missing_finding_keys = REQUIRED_FINDING_KEYS - finding.keys()
        if missing_finding_keys:
            missing_list = ", ".join(sorted(missing_finding_keys))
            raise ValueError(
                f"finding at index {index} is missing required keys: {missing_list}"
            )

    scenario_results = payload["scenario_results"]
    if not isinstance(scenario_results, list):
        raise ValueError("scenario_results must be a list")

    scenario_ids: list[str] = []
    for index, scenario_result in enumerate(scenario_results):
        if not isinstance(scenario_result, Mapping):
            raise ValueError(f"scenario_result at index {index} must be a mapping")
        missing_scenario_keys = REQUIRED_SCENARIO_RESULT_KEYS - scenario_result.keys()
        if missing_scenario_keys:
            missing_list = ", ".join(sorted(missing_scenario_keys))
            raise ValueError(
                "scenario_result at index "
                f"{index} is missing required keys: {missing_list}"
            )
        if scenario_result["status"] not in ALLOWED_SCENARIO_RESULT_STATUSES:
            raise ValueError(
                f"scenario_result at index {index} has invalid status: {scenario_result['status']}"
            )
        if not isinstance(scenario_result["evidence"], list):
            raise ValueError(
                f"scenario_result at index {index} must use a list for evidence"
            )
        if any(not isinstance(item, str) for item in scenario_result["evidence"]):
            raise ValueError(
                f"scenario_result at index {index} must use only strings for evidence"
            )
        scenario_ids.append(scenario_result["scenario_id"])
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("result contains duplicate scenario_result scenario_id values")


def validate_task_eval_result_against_input(
    input_payload: Mapping[str, Any], result_payload: Mapping[str, Any]
) -> None:
    validate_eval_result_payload(result_payload)

    if result_payload.get("gate") != input_payload.get("gate"):
        raise ValueError("result gate does not match bundle input gate")
    if result_payload.get("attempt") != input_payload.get("attempt"):
        raise ValueError("result attempt does not match bundle input attempt")
    if input_payload.get("gate") == "task":
        if result_payload.get("task_id") != input_payload.get("task_id"):
            raise ValueError("result task_id does not match bundle input task_id")
    elif input_payload.get("gate") == "final":
        if result_payload.get("final_bundle_id") != input_payload.get("final_bundle_id"):
            raise ValueError(
                "result final_bundle_id does not match bundle input final_bundle_id"
            )
        return
    else:
        return
    if not input_payload.get("must_simulate", False):
        return

    scenario_results = result_payload.get("scenario_results", [])
    required_ids = [scenario["scenario_id"] for scenario in input_payload.get("user_scenarios", [])]

    if result_payload["status"] == "pass":
        if not required_ids:
            raise ValueError("task pass is invalid when must_simulate=true and no user_scenarios were provided")
        if not scenario_results:
            raise ValueError("task pass is missing scenario_results")

        result_by_id = {entry["scenario_id"]: entry for entry in scenario_results}
        for scenario_id in required_ids:
            entry = result_by_id.get(scenario_id)
            if entry is None:
                raise ValueError(f"task pass is missing scenario_result for {scenario_id}")
            if entry.get("status") != "pass":
                raise ValueError(f"task pass requires scenario_result status=pass for {scenario_id}")
            if not entry.get("evidence"):
                raise ValueError(f"task pass requires evidence for {scenario_id}")
