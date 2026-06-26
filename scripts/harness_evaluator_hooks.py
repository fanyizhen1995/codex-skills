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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.harness_evaluator_cli import (
        create_final_bundle,
        create_next_attempt_bundle,
        create_task_final_bundle,
        create_task_bundle,
        find_task_definition,
        is_final_eval_required,
        is_task_eval_required,
        load_tasks_payload,
        max_task_eval_attempts,
        max_final_eval_attempts,
        update_session_state_evaluator,
    )
    from scripts.harness_evaluator_scenarios import validate_scenario_contract
    from scripts.harness_evaluator_state import (
        find_active_session_state,
        repo_roots_for_harness,
        validate_task_eval_result_against_input,
    )
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from harness_evaluator_cli import (
        create_final_bundle,
        create_next_attempt_bundle,
        create_task_final_bundle,
        create_task_bundle,
        find_task_definition,
        is_final_eval_required,
        is_task_eval_required,
        load_tasks_payload,
        max_task_eval_attempts,
        max_final_eval_attempts,
        update_session_state_evaluator,
    )
    from harness_evaluator_scenarios import validate_scenario_contract
    from harness_evaluator_state import (
        find_active_session_state,
        repo_roots_for_harness,
        validate_task_eval_result_against_input,
    )


def _current_branch(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _maybe_current_branch(root: Path) -> str | None:
    try:
        return _current_branch(root)
    except subprocess.CalledProcessError:
        return None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_sort_key(bundle: Path) -> tuple[int, str, int, str, str]:
    name = bundle.name
    if name.startswith("fake-attempt-"):
        try:
            attempt = int(name.removeprefix("fake-attempt-"))
        except ValueError:
            attempt = -1
        return (0, "", attempt, name, str(bundle))
    prefix, separator, attempt_text = name.rpartition("-attempt-")
    try:
        attempt = int(attempt_text) if separator else -1
    except ValueError:
        attempt = -1
    timestamp = prefix if separator else ""
    return (1, timestamp, attempt, name, str(bundle))


def _current_session(root: Path) -> dict[str, str] | None:
    for candidate_root in repo_roots_for_harness(root):
        session_dir = candidate_root / ".codex" / "session-state"
        if not session_dir.exists():
            continue

        matches: list[dict[str, str]] = []
        for path in session_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("worktree") == str(root):
                matches.append(payload)

        if len(matches) == 1:
            return matches[0]
    return None


def _parse_session_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _resolve_session(root: Path, task_id: str | None = None) -> dict[str, str] | None:
    if task_id is None:
        session = _current_session(root)
    else:
        session = None
    if session is not None:
        return session
    branch = _maybe_current_branch(root)
    candidates: list[dict[str, str]] = []
    for candidate_root in repo_roots_for_harness(root):
        session_dir = candidate_root / ".codex" / "session-state"
        if not session_dir.exists():
            continue
        if task_id is None:
            if branch is None:
                continue
            try:
                return find_active_session_state(root, branch, session_dir)
            except FileNotFoundError:
                continue
        for path in session_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("task") != task_id:
                continue
            if branch is not None and payload.get("branch") != branch:
                continue
            if Path(payload.get("worktree", "")).resolve() != root.resolve():
                continue
            candidates.append(payload)
    if candidates:
        return max(
            candidates,
            key=lambda payload: _parse_session_timestamp(
                payload.get("last_update") or payload.get("started_at")
            ),
        )
    return None


def _session_roots(root: Path, session: dict[str, str]) -> tuple[Path, Path]:
    state_root = root
    worktree_root = Path(session.get("worktree", str(root))).resolve()
    for candidate_root in repo_roots_for_harness(root):
        session_dir = candidate_root / ".codex" / "session-state"
        if session_dir.exists():
            state_root = candidate_root
            break
    return state_root, worktree_root


def _auto_prepare_task_bundle(root: Path, session: dict[str, str]) -> Path | None:
    state_root, worktree_root = _session_roots(root, session)
    task_id = session.get("task", "")
    branch = session.get("branch", "")
    if not task_id or not branch:
        return None
    bundle = create_task_bundle(worktree_root, task_id, 1)
    update_session_state_evaluator(
        state_root,
        worktree_root,
        branch,
        task_id=task_id,
        phase="task_eval",
        task_eval_attempt=1,
        last_task_eval_result="pending",
        repair_from_eval=False,
    )
    return bundle


def _auto_prepare_next_attempt(
    root: Path,
    session: dict[str, str],
    result_payload: dict,
) -> Path | None:
    state_root, worktree_root = _session_roots(root, session)
    task_id = session.get("task", "")
    branch = session.get("branch", "")
    if not task_id or not branch:
        return None

    current_attempt = int(result_payload.get("attempt", 0))
    next_attempt = current_attempt + 1
    max_attempts = max_task_eval_attempts(worktree_root, task_id)
    if max_attempts and next_attempt > max_attempts:
        return None
    bundle = create_next_attempt_bundle(worktree_root, task_id, next_attempt)
    phase = (
        "repair_after_task_eval_blocked"
        if result_payload.get("status") == "blocked"
        else "repair_after_task_eval_fail"
    )
    update_session_state_evaluator(
        state_root,
        worktree_root,
        branch,
        task_id=task_id,
        phase=phase,
        task_eval_attempt=next_attempt,
        last_task_eval_result=str(result_payload.get("status", "")),
        repair_from_eval=True,
    )
    return bundle


def latest_task_bundle(root: Path, task_id: str | None = None) -> Path | None:
    if task_id is None:
        session = _resolve_session(root, task_id)
        if session is None:
            return None
        resolved_task_id = session["task"]
    else:
        resolved_task_id = task_id

    if not resolved_task_id:
        return None

    candidate_bundles: list[Path] = []
    candidate_roots = repo_roots_for_harness(root)
    if task_id is not None:
        candidate_roots = [root] + [candidate for candidate in candidate_roots if candidate != root]
    for candidate_root in candidate_roots:
        bundle_root = candidate_root / ".codex" / "evaluations" / "tasks" / resolved_task_id
        if not bundle_root.exists():
            continue
        candidate_bundles.extend(sorted(path for path in bundle_root.iterdir() if path.is_dir()))

    if not candidate_bundles:
        return None
    if task_id is not None:
        worktree_bundles = [bundle for bundle in candidate_bundles if bundle.is_relative_to(root)]
        if worktree_bundles:
            return max(worktree_bundles, key=_bundle_sort_key)
    return max(candidate_bundles, key=_bundle_sort_key)


def latest_final_bundle(root: Path, final_bundle_id: str) -> Path | None:
    candidate_bundles: list[Path] = []
    candidate_roots = [root] + [candidate for candidate in repo_roots_for_harness(root) if candidate != root]
    for candidate_root in candidate_roots:
        bundle_root = candidate_root / ".codex" / "evaluations" / "finals" / final_bundle_id
        if not bundle_root.exists():
            continue
        candidate_bundles.extend(sorted(path for path in bundle_root.iterdir() if path.is_dir()))
    if not candidate_bundles:
        return None
    worktree_bundles = [bundle for bundle in candidate_bundles if bundle.is_relative_to(root)]
    if worktree_bundles:
        return max(worktree_bundles, key=_bundle_sort_key)
    return max(candidate_bundles, key=_bundle_sort_key)


def _bundle_contract_issue(bundle: Path) -> str | None:
    input_path = bundle / "input.json"
    if not input_path.exists():
        return "Task-level evaluator bundle is missing input.json."
    try:
        input_payload = _load_json(input_path)
    except json.JSONDecodeError as exc:
        return f"Task-level evaluator bundle contract is incomplete: invalid input.json ({exc})"
    if not isinstance(input_payload, dict):
        return "Task-level evaluator bundle contract is incomplete: input.json must be a mapping."
    if input_payload.get("gate") != "task":
        return "Task-level evaluator bundle contract is incomplete: input.json must declare gate=task."
    if "task_id" not in input_payload or "attempt" not in input_payload:
        return "Task-level evaluator bundle contract is incomplete: input.json is missing task_id or attempt."
    user_scenarios = input_payload.get("user_scenarios", [])
    if not isinstance(user_scenarios, list):
        return "Task-level evaluator bundle contract is incomplete: user_scenarios must be a list."
    try:
        validate_scenario_contract(
            {
                "task_id": input_payload.get("task_id"),
                "user_scenarios": user_scenarios,
            }
        )
    except ValueError as exc:
        return f"Task-level evaluator bundle contract is incomplete: {exc}"
    if input_payload.get("must_simulate") and not input_payload.get("user_scenarios"):
        return (
            "Task-level evaluator requires user scenarios before stopping. "
            f"Add scenario metadata at {input_payload.get('scenario_source', 'docs/harness/evaluator-scenarios/<task-id>.json')}."
        )

    result_path = bundle / "result.json"
    if result_path.exists():
        try:
            result_payload = _load_json(result_path)
            validate_task_eval_result_against_input(input_payload, result_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            return f"Task-level evaluator result contract is incomplete: {exc}"
    return None


def _final_bundle_contract_issue(bundle: Path) -> str | None:
    input_path = bundle / "input.json"
    if not input_path.exists():
        return "Final-level evaluator bundle is missing input.json."
    try:
        input_payload = _load_json(input_path)
    except json.JSONDecodeError as exc:
        return f"Final-level evaluator bundle contract is incomplete: invalid input.json ({exc})"
    if not isinstance(input_payload, dict):
        return "Final-level evaluator bundle contract is incomplete: input.json must be a mapping."
    if input_payload.get("gate") != "final":
        return "Final-level evaluator bundle contract is incomplete: input.json must declare gate=final."
    if "final_bundle_id" not in input_payload or "attempt" not in input_payload:
        return "Final-level evaluator bundle contract is incomplete: input.json is missing final_bundle_id or attempt."

    result_path = bundle / "result.json"
    if result_path.exists():
        try:
            result_payload = _load_json(result_path)
            validate_task_eval_result_against_input(input_payload, result_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            return f"Final-level evaluator result contract is incomplete: {exc}"
    return None


def _report_paths_for_final_bundle(worktree_root: Path) -> list[str]:
    paths: list[str] = []
    for relative in ("sprint_output.md", "progress.md"):
        candidate = worktree_root / relative
        if candidate.exists():
            paths.append(str(candidate))
    return paths


def _auto_prepare_final_bundle(root: Path, session: dict[str, str]) -> Path | None:
    state_root, worktree_root = _session_roots(root, session)
    task_id = session.get("task", "")
    branch = session.get("branch", "")
    if not task_id or not branch:
        return None
    task_bundle = latest_task_bundle(worktree_root, task_id)
    task_bundle_paths = [str(task_bundle)] if task_bundle is not None else []
    bundle = create_task_final_bundle(
        worktree_root,
        task_id,
        1,
        task_bundle_paths=task_bundle_paths,
        report_paths=_report_paths_for_final_bundle(worktree_root),
    )
    update_session_state_evaluator(
        state_root,
        worktree_root,
        branch,
        task_id=task_id,
        phase="final_eval",
        final_eval_attempt=1,
        last_final_eval_result="pending",
        repair_from_eval=False,
    )
    return bundle


def _auto_prepare_next_final_attempt(
    root: Path,
    session: dict[str, str],
    result_payload: dict,
) -> Path | None:
    state_root, worktree_root = _session_roots(root, session)
    task_id = session.get("task", "")
    branch = session.get("branch", "")
    if not task_id or not branch:
        return None

    current_attempt = int(result_payload.get("attempt", 0))
    next_attempt = current_attempt + 1
    max_attempts = max_final_eval_attempts(worktree_root, task_id)
    if max_attempts and next_attempt > max_attempts:
        return None
    task_bundle = latest_task_bundle(worktree_root, task_id)
    task_bundle_paths = [str(task_bundle)] if task_bundle is not None else []
    bundle = create_task_final_bundle(
        worktree_root,
        task_id,
        next_attempt,
        task_bundle_paths=task_bundle_paths,
        report_paths=_report_paths_for_final_bundle(worktree_root),
    )
    phase = (
        "repair_after_final_eval_blocked"
        if result_payload.get("status") == "blocked"
        else "repair_after_final_eval_fail"
    )
    update_session_state_evaluator(
        state_root,
        worktree_root,
        branch,
        task_id=task_id,
        phase=phase,
        final_eval_attempt=next_attempt,
        last_final_eval_result=str(result_payload.get("status", "")),
        repair_from_eval=True,
    )
    return bundle


def _task_gate_decision(root: Path, session: dict[str, str], task_id: str) -> dict[str, str] | None:
    bundle = latest_task_bundle(root, task_id)
    if bundle is None:
        bundle = _auto_prepare_task_bundle(root, session)
        if bundle is None:
            return None
        return {
            "decision": "block",
            "reason": f"Task-level evaluator bundle prepared at {bundle}. Run evaluator before ending the turn.",
            "action": "run_task_evaluator",
            "bundle_dir": str(bundle),
        }
    contract_issue = _bundle_contract_issue(bundle)
    if contract_issue is not None:
        if (
            "result contract is incomplete" in contract_issue
            and (bundle / "result.json").exists()
        ):
            next_bundle = _auto_prepare_next_attempt(
                root,
                session,
                {
                    "status": "fail",
                    "attempt": _load_json(bundle / "input.json").get("attempt", 0),
                },
            )
            if next_bundle is not None:
                return {
                    "decision": "block",
                    "reason": f"{contract_issue} A new task-level evaluator attempt was prepared at {next_bundle}.",
                    "action": "rerun_task_evaluator",
                    "bundle_dir": str(next_bundle),
                }
        return {"decision": "block", "reason": contract_issue}

    result_path = bundle / "result.json"
    if not result_path.exists():
        return {
            "decision": "block",
            "reason": f"Run the task_evaluator subagent against {bundle / 'input.json'} and record a result before ending the turn.",
            "action": "run_task_evaluator",
            "bundle_dir": str(bundle),
        }
    payload = _load_json(result_path)
    if payload["status"] in {"fail", "blocked"} and payload["gate"] == "task":
        next_bundle = _auto_prepare_next_attempt(root, session, payload)
        return {
            "decision": "block",
            "reason": f"Resolve findings from {bundle / 'summary.md'} and rerun task-level evaluation before requesting user acceptance.",
            "action": "rerun_task_evaluator",
            "bundle_dir": str(next_bundle or bundle),
        }
    return None


def _final_gate_decision(root: Path, session: dict[str, str], final_bundle_id: str) -> dict[str, str] | None:
    bundle = latest_final_bundle(root, final_bundle_id)
    if bundle is None:
        bundle = _auto_prepare_final_bundle(root, session)
        if bundle is None:
            return None
        return {
            "decision": "block",
            "reason": f"Final-level evaluator bundle prepared at {bundle}. Run evaluator before ending the turn.",
            "action": "run_final_evaluator",
            "bundle_dir": str(bundle),
        }

    contract_issue = _final_bundle_contract_issue(bundle)
    if contract_issue is not None:
        if (
            "result contract is incomplete" in contract_issue
            and (bundle / "result.json").exists()
        ):
            next_bundle = _auto_prepare_next_final_attempt(
                root,
                session,
                {
                    "status": "fail",
                    "attempt": _load_json(bundle / "input.json").get("attempt", 0),
                },
            )
            if next_bundle is not None:
                return {
                    "decision": "block",
                    "reason": f"{contract_issue} A new final-level evaluator attempt was prepared at {next_bundle}.",
                    "action": "rerun_final_evaluator",
                    "bundle_dir": str(next_bundle),
                }
        return {"decision": "block", "reason": contract_issue}

    result_path = bundle / "result.json"
    if not result_path.exists():
        return {
            "decision": "block",
            "reason": f"Run the final_evaluator against {bundle / 'input.json'} and record a result before ending the turn.",
            "action": "run_final_evaluator",
            "bundle_dir": str(bundle),
        }

    payload = _load_json(result_path)
    if payload["status"] in {"fail", "blocked"} and payload["gate"] == "final":
        next_bundle = _auto_prepare_next_final_attempt(root, session, payload)
        return {
            "decision": "soft_block",
            "reason": f"Final-level evaluator reported {payload['status']}. External reporting may continue, but this result is not recommended for acceptance.",
            "action": "rerun_final_evaluator" if next_bundle is not None else "final_evaluator_soft_failed",
            "bundle_dir": str(next_bundle or bundle),
        }
    return None


def stop_hook(root: Path, task_id: str | None = None) -> dict[str, str] | None:
    session = _resolve_session(root, task_id)
    if session is None:
        return None
    return stop_hook_for_session(root, session, task_id=task_id)


def stop_hook_for_session(
    root: Path,
    session: dict[str, str],
    task_id: str | None = None,
) -> dict[str, str] | None:
    worktree_root = Path(session.get("worktree", str(root))).resolve()
    current_task_id = task_id or session.get("task", "")
    if not current_task_id:
        return None

    existing_task_bundle = latest_task_bundle(root, current_task_id)
    existing_final_bundle = latest_final_bundle(root, current_task_id)
    task_required = is_task_eval_required(worktree_root, current_task_id)
    final_required = is_final_eval_required(worktree_root, current_task_id)
    try:
        find_task_definition(load_tasks_payload(worktree_root), current_task_id)
        task_defined = True
    except KeyError:
        task_defined = False

    if task_defined and not task_required and not final_required:
        return None

    should_run_task_gate = task_required or (not task_defined and existing_task_bundle is not None)
    should_run_final_gate = final_required or (not task_defined and existing_final_bundle is not None)

    if should_run_task_gate:
        task_decision = _task_gate_decision(root, session, current_task_id)
        if task_decision is not None:
            return task_decision

    if should_run_final_gate:
        return _final_gate_decision(root, session, current_task_id)

    return None


def subagent_stop_hook(root: Path, task_id: str | None = None) -> dict[str, str] | None:
    bundle = latest_task_bundle(root, task_id)
    if bundle is None:
        return None
    if not (bundle / "result.json").exists():
        return {
            "decision": "block",
            "reason": f"Write {bundle / 'result.json'} before the evaluator subagent exits.",
        }
    return None


def _hook_output_payload(decision: dict[str, str] | None) -> dict[str, object]:
    if decision is None:
        return {"continue": True}
    if str(decision.get("decision", "")) == "block":
        return {
            "continue": False,
            "stopReason": str(decision.get("reason", "")),
        }
    return {"continue": True}


def main() -> int:
    mode = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    root = Path(payload["cwd"])
    decision = stop_hook(root) if mode == "stop" else subagent_stop_hook(root)
    print(json.dumps(_hook_output_payload(decision)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
