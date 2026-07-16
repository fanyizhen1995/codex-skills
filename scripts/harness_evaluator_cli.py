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

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.harness_evaluator_scenarios import load_task_scenarios
    from scripts.harness_evaluator_state import (
        find_active_session_state,
        resolve_effective_eval_policy,
        validate_eval_result_payload,
        validate_task_eval_result_against_input,
    )
    from scripts.harness_loop_contracts import (
        read_json_file,
        validate_task_contract_payload,
    )
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from harness_evaluator_scenarios import load_task_scenarios
    from harness_evaluator_state import (
        find_active_session_state,
        resolve_effective_eval_policy,
        validate_eval_result_payload,
        validate_task_eval_result_against_input,
    )
    from harness_loop_contracts import read_json_file, validate_task_contract_payload


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_timestamp(value: str | None) -> datetime:
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


def load_tasks_payload(repo_root: Path) -> dict:
    tasks_path = repo_root / "tasks.json"
    if not tasks_path.exists():
        return {"eval_defaults": {}, "tasks": []}
    return json.loads(tasks_path.read_text(encoding="utf-8"))


def find_task_definition(tasks_payload: Mapping[str, object], task_id: str) -> dict:
    for task in tasks_payload.get("tasks", []):
        if task.get("id") == task_id:
            return dict(task)
    raise KeyError(f"task not found: {task_id}")


def resolve_task_eval_policy(repo_root: Path, task_id: str) -> dict:
    tasks_payload = load_tasks_payload(repo_root)
    try:
        task = find_task_definition(tasks_payload, task_id)
    except KeyError:
        return {}
    return resolve_effective_eval_policy(task, tasks_payload.get("eval_defaults", {}))


def is_task_eval_required(repo_root: Path, task_id: str) -> bool:
    return bool(resolve_task_eval_policy(repo_root, task_id).get("task_level_required", False))


def is_final_eval_required(repo_root: Path, task_id: str) -> bool:
    return bool(resolve_task_eval_policy(repo_root, task_id).get("final_level_required", False))


def _verify_commands(repo_root: Path, task_id: str) -> list[str]:
    try:
        task = find_task_definition(load_tasks_payload(repo_root), task_id)
    except KeyError:
        return []
    verify = task.get("verify", "")
    if not verify:
        return []
    normalized = str(verify).replace("\r\n", "\n").replace("；", "\n").replace(";", "\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _effective_task_scope(repo_root: Path, task_id: str) -> str:
    return str(resolve_task_eval_policy(repo_root, task_id).get("task_scope", ""))


def _normalize_task_contract_scenarios(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    scenario_commands = list(contract["scenario_commands"])
    default_entrypoint = str(scenario_commands[0]) if scenario_commands else ""
    default_automation_hint = "shell" if scenario_commands else "manual"
    normalized = []
    for scenario in contract["user_scenarios"]:
        scenario_payload = dict(scenario)
        scenario_payload.setdefault("entrypoint", default_entrypoint)
        scenario_payload.setdefault("cleanup", [])
        scenario_payload.setdefault("automation_hint", default_automation_hint)
        normalized.append(scenario_payload)
    return normalized


def create_task_bundle(
    repo_root: Path,
    task_id: str,
    attempt: int,
    *,
    bundle_name: str | None = None,
    task_contract_path: Path | None = None,
) -> Path:
    if task_contract_path is not None:
        contract = read_json_file(task_contract_path)
        validate_task_contract_payload(contract)
        task_id = str(contract["task_id"])
        scenario_contract = {
            "must_simulate": contract["must_simulate"],
            "source": str(task_contract_path),
            "user_scenarios": _normalize_task_contract_scenarios(contract),
        }
        verify_commands = list(contract["verify_commands"])
        artifact_paths = list(contract["artifact_paths"])
        allowed_scope = str(contract["allowed_scope"])
        scenario_commands = list(contract["scenario_commands"])
        required_services = list(contract["required_services"])
        evaluator_driver = str(contract["evaluator_driver"])
        eval_policy = dict(contract["eval_policy"])
    else:
        scenario_contract = load_task_scenarios(repo_root, task_id)
        verify_commands = _verify_commands(repo_root, task_id)
        artifact_paths = []
        allowed_scope = _effective_task_scope(repo_root, task_id)
        scenario_commands = []
        required_services = []
        evaluator_driver = ""
        eval_policy = resolve_task_eval_policy(repo_root, task_id)

    bundle_dir = (
        repo_root
        / ".codex"
        / "evaluations"
        / "tasks"
        / task_id
        / (bundle_name or f"{_timestamp()}-attempt-{attempt}")
    )
    templates_dir = repo_root / ".codex" / "evaluations" / "templates"
    bundle_dir.mkdir(parents=True, exist_ok=False)

    input_payload = {
        "gate": "task",
        "task_id": task_id,
        "final_bundle_id": "",
        "attempt": attempt,
        "verify_commands": verify_commands,
        "scenario_commands": scenario_commands,
        "artifact_paths": artifact_paths,
        "required_services": required_services,
        "allowed_scope": allowed_scope,
        "evaluator_driver": evaluator_driver,
        "eval_policy": eval_policy,
        "must_simulate": scenario_contract["must_simulate"],
        "scenario_source": scenario_contract["source"],
        "task_contract_sha256": (
            hashlib.sha256(task_contract_path.read_bytes()).hexdigest()
            if task_contract_path is not None
            else ""
        ),
        "user_scenarios": scenario_contract["user_scenarios"],
    }
    (bundle_dir / "input.json").write_text(
        json.dumps(input_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "artifacts.json").write_text(
        _read_text(templates_dir / "artifacts.template.json"),
        encoding="utf-8",
    )
    (bundle_dir / "summary.md").write_text(
        _read_text(templates_dir / "summary.template.md"),
        encoding="utf-8",
    )
    return bundle_dir


def create_next_attempt_bundle(repo_root: Path, task_id: str, attempt: int) -> Path:
    return create_task_bundle(repo_root, task_id, attempt)


def max_task_eval_attempts(repo_root: Path, task_id: str) -> int:
    return int(resolve_task_eval_policy(repo_root, task_id).get("max_task_eval_attempts", 0))


def create_final_bundle(
    repo_root: Path,
    final_bundle_id: str,
    attempt: int,
    *,
    report_paths: Sequence[str] | None = None,
    task_bundle_paths: Sequence[str] | None = None,
    allowed_scope: str = "report_and_artifacts",
) -> Path:
    bundle_dir = (
        repo_root
        / ".codex"
        / "evaluations"
        / "finals"
        / final_bundle_id
        / f"{_timestamp()}-attempt-{attempt}"
    )
    bundle_dir.mkdir(parents=True, exist_ok=False)
    (bundle_dir / "input.json").write_text(
        json.dumps(
            {
                "gate": "final",
                "task_id": "",
                "final_bundle_id": final_bundle_id,
                "attempt": attempt,
                "report_paths": list(report_paths or []),
                "task_bundle_paths": list(task_bundle_paths or []),
                "allowed_scope": allowed_scope,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "artifacts.json").write_text("{}\n", encoding="utf-8")
    (bundle_dir / "summary.md").write_text(
        "# Final Evaluator Summary\n\n",
        encoding="utf-8",
    )
    return bundle_dir


def create_task_final_bundle(
    repo_root: Path,
    task_id: str,
    attempt: int,
    *,
    task_bundle_paths: Sequence[str] | None = None,
    report_paths: Sequence[str] | None = None,
) -> Path:
    policy = resolve_task_eval_policy(repo_root, task_id)
    return create_final_bundle(
        repo_root,
        task_id,
        attempt,
        report_paths=report_paths,
        task_bundle_paths=task_bundle_paths,
        allowed_scope=str(policy.get("final_scope", "report_and_artifacts")),
    )


def max_final_eval_attempts(repo_root: Path, task_id: str) -> int:
    return int(resolve_task_eval_policy(repo_root, task_id).get("max_final_eval_attempts", 0))


def update_session_state_evaluator(
    repo_root: Path,
    worktree_root: Path,
    branch: str,
    *,
    task_id: str | None = None,
    phase: str | None = None,
    task_eval_attempt: int | None = None,
    last_task_eval_result: str | None = None,
    final_eval_attempt: int | None = None,
    last_final_eval_result: str | None = None,
    repair_from_eval: bool | None = None,
) -> Path:
    session_dir = repo_root / ".codex" / "session-state"
    session_path = None
    if task_id is not None:
        matches: list[tuple[datetime, Path, dict]] = []
        for candidate in session_dir.glob("*.json"):
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("task") != task_id:
                continue
            if payload.get("branch") != branch:
                continue
            if Path(payload.get("worktree", "")).resolve() != worktree_root.resolve():
                continue
            matches.append(
                (
                    _parse_timestamp(payload.get("last_update") or payload.get("started_at")),
                    candidate,
                    payload,
                )
            )
        if matches:
            _, session_path, session = max(matches, key=lambda item: item[0])
        else:
            session = find_active_session_state(worktree_root, branch, session_dir)
    else:
        session = find_active_session_state(worktree_root, branch, session_dir)
    if session_path is None:
        for candidate in session_dir.glob("*.json"):
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload == session:
                session_path = candidate
                break
    if session_path is None:
        raise FileNotFoundError(
            f"session-state file not found for branch={branch!r} worktree={str(worktree_root)!r}"
        )

    evaluator = dict(session.get("evaluator", {}))
    if phase is not None:
        evaluator["phase"] = phase
    if task_eval_attempt is not None:
        evaluator["task_eval_attempt"] = task_eval_attempt
    if last_task_eval_result is not None:
        evaluator["last_task_eval_result"] = last_task_eval_result
    if final_eval_attempt is not None:
        evaluator["final_eval_attempt"] = final_eval_attempt
    if last_final_eval_result is not None:
        evaluator["last_final_eval_result"] = last_final_eval_result
    if repair_from_eval is not None:
        evaluator["repair_from_eval"] = repair_from_eval

    session["evaluator"] = evaluator
    session["last_update"] = _timestamp()
    session_path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    return session_path


def record_result_payload(bundle_dir: Path, payload: Mapping[str, object]) -> Path:
    input_payload: dict[str, object] = {}
    input_path = bundle_dir / "input.json"
    if input_path.exists():
        input_payload = json.loads(input_path.read_text(encoding="utf-8"))

    if input_payload.get("gate") == "task":
        validate_task_eval_result_against_input(input_payload, payload)
    elif input_payload:
        validate_task_eval_result_against_input(input_payload, payload)
    else:
        validate_eval_result_payload(payload)

    result_path = bundle_dir / "result.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return result_path


def _artifact_paths(args: argparse.Namespace) -> list[str]:
    return []


def prepare_task(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    task_contract_path = Path(args.task_contract) if args.task_contract else None
    bundle_dir = create_task_bundle(
        repo_root,
        args.task_id,
        args.attempt,
        task_contract_path=task_contract_path,
    )
    print(bundle_dir)
    return 0


def prepare_final(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    bundle_dir = create_final_bundle(repo_root, args.final_bundle_id, args.attempt)
    print(bundle_dir)
    return 0


def record_result(args: argparse.Namespace) -> int:
    bundle_dir = Path(args.bundle_dir)
    payload = json.load(args.stdin)
    result_path = record_result_payload(bundle_dir, payload)
    print(result_path)
    return 0


def render_final_banner(args: argparse.Namespace) -> int:
    payload = json.loads(
        (Path(args.bundle_dir) / "result.json").read_text(encoding="utf-8")
    )
    if payload["status"] == "fail":
        print("> Final evaluator status: `fail` — not recommended for acceptance.")
    elif payload["status"] == "blocked":
        print(
            "> Final evaluator status: `blocked` — report is incomplete pending missing evidence."
        )
    else:
        print("> Final evaluator status: `pass`.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    prepare_task_parser = subcommands.add_parser("prepare-task")
    prepare_task_parser.add_argument("--repo-root", required=True)
    prepare_task_parser.add_argument("--task-id", required=True)
    prepare_task_parser.add_argument("--attempt", type=int, required=True)
    prepare_task_parser.add_argument("--task-contract", default="")
    prepare_task_parser.set_defaults(func=prepare_task)

    prepare_final_parser = subcommands.add_parser("prepare-final")
    prepare_final_parser.add_argument("--repo-root", required=True)
    prepare_final_parser.add_argument("--final-bundle-id", required=True)
    prepare_final_parser.add_argument("--attempt", type=int, required=True)
    prepare_final_parser.set_defaults(func=prepare_final)

    record_result_parser = subcommands.add_parser("record-result")
    record_result_parser.add_argument("--bundle-dir", required=True)
    record_result_parser.set_defaults(func=record_result, stdin=None)

    banner_parser = subcommands.add_parser("render-final-banner")
    banner_parser.add_argument("--bundle-dir", required=True)
    banner_parser.set_defaults(func=render_final_banner)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) == "record-result":
        args.stdin = __import__("sys").stdin
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
