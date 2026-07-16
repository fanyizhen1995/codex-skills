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

import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
from pathlib import Path

try:
    from scripts import harness_evaluator_hooks
    from scripts.harness_evaluator_cli import record_result_payload, update_session_state_evaluator
    from scripts.harness_evaluator_scenarios import load_task_scenarios
    from scripts.harness_evaluator_state import repo_roots_for_harness
    from scripts.harness_loop_contracts import read_json_file, validate_task_contract_payload
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    import harness_evaluator_hooks
    from harness_evaluator_cli import record_result_payload, update_session_state_evaluator
    from harness_evaluator_scenarios import load_task_scenarios
    from harness_evaluator_state import repo_roots_for_harness
    from harness_loop_contracts import read_json_file, validate_task_contract_payload


def next_loop_action(status: str, attempt: int, max_attempts: int, gate: str) -> str:
    if status == "pass":
        return "complete"
    if gate == "final" and status == "fail":
        return "soft_fail"
    if status == "blocked":
        return "stop"
    if attempt >= max_attempts:
        return "stop"
    return "repair"


def _write_summary(
    bundle: Path,
    status: str,
    verdict_reason: str,
    scenario_results: list[dict] | None = None,
) -> None:
    scenario_results = scenario_results or []
    scenario_lines = ["## Scenario Results", ""]
    if scenario_results:
        for entry in scenario_results:
            scenario_lines.extend(
                [
                    f"### {entry['scenario_id']}",
                    "",
                    f"- status: {entry['status']}",
                    f"- evidence: {', '.join(entry['evidence']) if entry['evidence'] else 'none'}",
                    f"- notes: {entry.get('notes', '')}",
                    "",
                ]
            )
    else:
        scenario_lines.extend(["- none", ""])

    (bundle / "summary.md").write_text(
        "\n".join(
            [
                "# Evaluator Summary",
                "",
                "## Verdict",
                "",
                f"- status: {status}",
                f"- reason: {verdict_reason}",
                "",
                *scenario_lines,
                "## Findings",
                "",
                "- none" if status == "pass" else "- see result.json",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _fake_scenario_results(input_payload: dict, status: str) -> list[dict]:
    scenario_status = "pass" if status == "pass" else "fail"
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "status": scenario_status,
            "evidence": [f"summary.md#{scenario['scenario_id']}"],
            "notes": f"simulated {scenario_status} result",
        }
        for scenario in input_payload.get("user_scenarios", [])
    ]


def _write_fake_task_result(bundle: Path, status: str) -> None:
    input_payload = json.loads((bundle / "input.json").read_text(encoding="utf-8"))
    payload = {
        "status": status,
        "gate": "task",
        "task_id": input_payload["task_id"],
        "final_bundle_id": "",
        "attempt": input_payload["attempt"],
        "summary": status,
        "findings": []
        if status == "pass"
        else [
            {
                "id": "F-001",
                "severity": "major",
                "category": "scenario_failed",
                "evidence": [f"summary.md#{input_payload['user_scenarios'][0]['scenario_id']}"],
                "recommended_action": "repair",
            }
        ],
        "scenario_results": _fake_scenario_results(input_payload, status),
        "rerun_commands": [],
        "environment_checks": [],
        "verdict_reason": status,
        "next_action": "proceed_to_user_acceptance"
        if status == "pass"
        else "repair_and_reevaluate",
    }
    (bundle / "result.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_summary(bundle, status, payload["verdict_reason"], payload["scenario_results"])


def _read_text_excerpt(path: Path, max_bytes: int = 4096) -> dict:
    try:
        if not path.exists():
            return {"path": str(path), "status": "missing"}
        if not path.is_file():
            return {"path": str(path), "status": "not_file"}
        size = path.stat().st_size
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError as exc:
        return {"path": str(path), "status": "unreadable", "error": str(exc)}
    truncated = len(raw) > max_bytes or size > max_bytes
    sample = raw[:max_bytes]
    if b"\0" in sample:
        return {
            "path": str(path),
            "status": "binary_omitted",
            "size_bytes": size,
        }
    text = sample.decode("utf-8", errors="replace")
    return {
        "path": str(path),
        "status": "ok",
        "size_bytes": size,
        "truncated": truncated,
        "content": text,
    }


def _inline_evidence_for_prompt(bundle_dir: Path, input_payload: dict) -> dict:
    artifacts_path = bundle_dir / "artifacts.json"
    artifacts_payload: dict = {}
    if artifacts_path.exists():
        try:
            artifacts_payload = json.loads(artifacts_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            artifacts_payload = {
                "read_error": str(exc),
            }
    artifacts_payload = _prompt_safe_artifacts_payload(artifacts_payload)

    artifact_paths: list[str] = []
    for candidate in input_payload.get("artifact_paths", []):
        if isinstance(candidate, str):
            artifact_paths.append(candidate)
    for scenario_output in artifacts_payload.get("scenario_outputs", []):
        if not isinstance(scenario_output, dict):
            continue
        for artifact in scenario_output.get("artifacts", []):
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                artifact_paths.append(artifact["path"])

    seen: set[str] = set()
    excerpts: list[dict] = []
    for candidate in artifact_paths:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_scenario_stream_path(Path(candidate)):
            excerpts.append({"path": candidate, "status": "scenario_stream_omitted"})
            continue
        excerpts.append(_read_text_excerpt(Path(candidate)))

    return {
        "artifacts_json_path": str(artifacts_path),
        "artifacts_json": artifacts_payload,
        "artifact_text_excerpts": excerpts,
    }


def _codex_exec_prompt(bundle_dir: Path, gate: str) -> str:
    input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
    artifacts_path = bundle_dir / "artifacts.json"
    inline_evidence = _inline_evidence_for_prompt(bundle_dir, input_payload)
    constraints = [
        "Return exactly one JSON object matching the evaluator result schema.",
        "Do not modify files.",
        "Prioritize user-scenario completion over internal implementation claims.",
        "If shell scenarios were already executed by the auto-gate, use artifact_paths and artifacts.json scenario_outputs as primary evidence.",
    ]
    if gate == "task":
        constraints.append("Every required user scenario must appear in scenario_results.")
    else:
        constraints.append("For final-gate failures, use status=fail and next_action=proceed_with_risk.")
    return "\n".join(
        [
            "Read-only evaluator task.",
            *constraints,
            f"Gate: {gate}",
            f"Bundle: {bundle_dir / 'input.json'}",
            f"Artifacts: {artifacts_path}",
            json.dumps(input_payload, ensure_ascii=False),
            "Inline evaluator evidence:",
            json.dumps(inline_evidence, ensure_ascii=False, indent=2),
        ]
    )


def _prompt_safe_artifacts_payload(payload: dict) -> dict:
    safe_payload = dict(payload)
    safe_outputs: list[dict] = []
    for output in safe_payload.get("scenario_outputs", []):
        if not isinstance(output, dict):
            continue
        safe_outputs.append(
            {
                key: value
                for key, value in output.items()
                if key not in {"stdout", "stderr"}
            }
        )
    if "scenario_outputs" in safe_payload:
        safe_payload["scenario_outputs"] = safe_outputs
    return safe_payload


def _is_scenario_stream_path(path: Path) -> bool:
    name = path.name
    return name.endswith(".stdout.log") or name.endswith(".stderr.log")


def _load_bundle_input(bundle_dir: Path) -> dict:
    return json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))


def _write_bundle_input(bundle_dir: Path, payload: dict) -> None:
    (bundle_dir / "input.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_bundle_artifacts(bundle_dir: Path) -> dict:
    artifacts_path = bundle_dir / "artifacts.json"
    if not artifacts_path.exists():
        return {
            "logs": [],
            "reports": [],
            "screenshots": [],
            "kubectl_outputs": [],
            "scenario_outputs": [],
        }
    payload = json.loads(artifacts_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifacts.json must be a mapping")
    payload.setdefault("logs", [])
    payload.setdefault("reports", [])
    payload.setdefault("screenshots", [])
    payload.setdefault("kubectl_outputs", [])
    payload.setdefault("scenario_outputs", [])
    return payload


def _write_bundle_artifacts(bundle_dir: Path, payload: dict) -> None:
    (bundle_dir / "artifacts.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _normalize_task_contract_scenarios(contract: dict) -> list[dict]:
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


def _fake_task_input_payload(
    base_root: Path,
    task_id: str,
    attempt: int,
    task_contract_path: Path | None,
) -> dict:
    if task_contract_path is not None:
        contract = read_json_file(task_contract_path)
        validate_task_contract_payload(contract)
        contract_task_id = str(contract["task_id"])
        if contract_task_id != task_id:
            raise ValueError(
                f"task contract task_id {contract_task_id!r} does not match requested task_id {task_id!r}"
            )
        return {
            "gate": "task",
            "task_id": task_id,
            "final_bundle_id": "",
            "attempt": attempt,
            "verify_commands": list(contract["verify_commands"]),
            "scenario_commands": list(contract["scenario_commands"]),
            "artifact_paths": list(contract["artifact_paths"]),
            "required_services": list(contract["required_services"]),
            "allowed_scope": str(contract["allowed_scope"]),
            "evaluator_driver": str(contract["evaluator_driver"]),
            "eval_policy": dict(contract["eval_policy"]),
            "must_simulate": bool(contract["must_simulate"]),
            "scenario_source": str(task_contract_path),
            "user_scenarios": _normalize_task_contract_scenarios(contract),
        }

    scenario_contract = load_task_scenarios(base_root, task_id)
    return {
        "gate": "task",
        "task_id": task_id,
        "final_bundle_id": "",
        "attempt": attempt,
        "verify_commands": [],
        "artifact_paths": [],
        "allowed_scope": "code_and_local_k3s",
        "must_simulate": scenario_contract["must_simulate"],
        "scenario_source": scenario_contract["source"],
        "user_scenarios": scenario_contract["user_scenarios"],
    }


def _append_unique_strings(values: list[str], candidates: list[str]) -> list[str]:
    seen = set(values)
    for candidate in candidates:
        if candidate in seen:
            continue
        values.append(candidate)
        seen.add(candidate)
    return values


def _scenario_output_dir(entrypoint: str, worktree_root: Path) -> Path | None:
    try:
        tokens = shlex.split(entrypoint)
    except ValueError:
        return None
    for index, token in enumerate(tokens):
        if token == "--output-dir" and index + 1 < len(tokens):
            return (worktree_root / tokens[index + 1]).resolve()
        if token.startswith("--output-dir="):
            return (worktree_root / token.split("=", 1)[1]).resolve()
    return None


def _collect_existing_files(root: Path | None) -> list[str]:
    if root is None or not root.exists():
        return []
    return sorted(str(path.resolve()) for path in root.rglob("*") if path.is_file())


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _kill_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _close_process_pipes(process: subprocess.Popen) -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _file_metadata(path: Path) -> dict:
    try:
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        return {
            "path": str(path),
            "status": "unreadable",
            "error": str(exc),
        }
    return {
        "path": str(path),
        "size_bytes": size,
        "sha256": digest,
    }


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _run_shell_scenarios(bundle_dir: Path, worktree_root: Path, timeout_seconds: int = 60) -> None:
    input_payload = _load_bundle_input(bundle_dir)
    if input_payload.get("gate") != "task":
        return

    artifacts_payload = _load_bundle_artifacts(bundle_dir)
    artifact_paths = list(input_payload.get("artifact_paths", []))
    scenario_outputs = list(artifacts_payload.get("scenario_outputs", []))
    logs = list(artifacts_payload.get("logs", []))

    for scenario in input_payload.get("user_scenarios", []):
        automation_hint = str(scenario.get("automation_hint", "")).strip().lower()
        if not automation_hint or automation_hint == "manual":
            continue
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        entrypoint = str(scenario.get("entrypoint", "")).strip()
        if not scenario_id or not entrypoint:
            continue

        output_dir = _scenario_output_dir(entrypoint, worktree_root)
        process = subprocess.Popen(
            entrypoint,
            cwd=worktree_root,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env={
                **os.environ,
                "HARNESS_EVALUATOR_SKIP_HOOKS": "1",
            },
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            exit_code = int(process.returncode)
            status = "pass" if exit_code == 0 else "fail"
            second_communicate_timeout = False
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process)
            second_communicate_timeout = False
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                second_communicate_timeout = True
                _close_process_pipes(process)
                try:
                    process.kill()
                except OSError:
                    pass
                stdout = exc.output
                stderr = exc.stderr
            exit_code = 124
            stdout = _decode_timeout_stream(stdout or exc.output)
            stderr = _decode_timeout_stream(stderr or exc.stderr)
            status = "timeout"
        stdout_path = bundle_dir / f"{scenario_id}.stdout.log"
        stderr_path = bundle_dir / f"{scenario_id}.stderr.log"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        discovered_artifacts = _collect_existing_files(output_dir)
        _append_unique_strings(
            artifact_paths,
            [str(stdout_path), str(stderr_path), *discovered_artifacts],
        )
        _append_unique_strings(
            logs,
            [str(stdout_path), str(stderr_path)],
        )
        scenario_outputs.append(
            {
                "scenario_id": scenario_id,
                "command_size_bytes": len(entrypoint.encode("utf-8")),
                "command_sha256": _text_sha256(entrypoint),
                "exit_code": exit_code,
                "status": status,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "stdout_size_bytes": stdout_path.stat().st_size,
                "stderr_size_bytes": stderr_path.stat().st_size,
                "stdout_sha256": _file_metadata(stdout_path).get("sha256", ""),
                "stderr_sha256": _file_metadata(stderr_path).get("sha256", ""),
                "truncated": False,
                "second_communicate_timeout": second_communicate_timeout,
                "artifacts": [{"path": path} for path in discovered_artifacts],
            }
        )

    input_payload["artifact_paths"] = artifact_paths
    artifacts_payload["logs"] = logs
    artifacts_payload["scenario_outputs"] = scenario_outputs
    _write_bundle_input(bundle_dir, input_payload)
    _write_bundle_artifacts(bundle_dir, artifacts_payload)


def _run_codex_exec_evaluator(bundle_dir: Path, gate: str, worktree_root: Path) -> dict:
    prompt = _codex_exec_prompt(bundle_dir, gate)
    schema_path = worktree_root / ".codex" / "evaluations" / "templates" / "result.schema.json"
    command = [
        "codex",
        "-a",
        "never",
        "-c",
        'model_reasoning_effort="low"',
        "exec",
        "--cd",
        str(worktree_root),
        "--sandbox",
        "read-only",
        "--dangerously-bypass-hook-trust",
        "--output-schema",
        str(schema_path),
        "--color",
        "never",
        "-",
    ]
    result = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "HARNESS_EVALUATOR_SKIP_HOOKS": "1",
        },
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "codex exec failed")
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"codex exec returned invalid JSON: {exc}") from exc


def _consume_decision_with_codex_exec(
    worktree_root: Path,
    state_root: Path,
    branch: str,
    task_id: str,
    decision: dict[str, str],
) -> bool:
    action = decision.get("action", "")
    bundle_dir = Path(decision.get("bundle_dir", ""))
    if action not in {
        "run_task_evaluator",
        "rerun_task_evaluator",
        "run_final_evaluator",
        "rerun_final_evaluator",
    }:
        return False
    if not bundle_dir.exists():
        raise FileNotFoundError(f"bundle_dir does not exist: {bundle_dir}")

    gate = "final" if "final" in action else "task"
    if gate == "task":
        _run_shell_scenarios(bundle_dir, worktree_root)
    payload = _run_codex_exec_evaluator(bundle_dir, gate, worktree_root)
    record_result_payload(bundle_dir, payload)
    _write_summary(
        bundle_dir,
        str(payload["status"]),
        str(payload["verdict_reason"]),
        payload.get("scenario_results", []),
    )

    if gate == "task":
        update_session_state_evaluator(
            state_root,
            worktree_root,
            branch,
            task_id=task_id,
            phase="task_evaluator_passed"
            if payload["status"] == "pass"
            else (
                "repair_after_task_eval_blocked"
                if payload["status"] == "blocked"
                else "repair_after_task_eval_fail"
            ),
            task_eval_attempt=int(payload["attempt"]),
            last_task_eval_result=str(payload["status"]),
            repair_from_eval=payload["status"] != "pass",
        )
    else:
        update_session_state_evaluator(
            state_root,
            worktree_root,
            branch,
            task_id=task_id,
            phase="final_evaluator_passed"
            if payload["status"] == "pass"
            else (
                "repair_after_final_eval_blocked"
                if payload["status"] == "blocked"
                else "repair_after_final_eval_fail"
            ),
            final_eval_attempt=int(payload["attempt"]),
            last_final_eval_result=str(payload["status"]),
            repair_from_eval=payload["status"] != "pass",
    )
    return payload["status"] == "pass"


def consume_decision_with_codex_exec(
    worktree_root: Path,
    state_root: Path,
    branch: str,
    task_id: str,
    decision: dict[str, str],
) -> bool:
    return _consume_decision_with_codex_exec(
        worktree_root,
        state_root,
        branch,
        task_id,
        decision,
    )


def _load_session(repo_root: Path, task_id: str) -> dict:
    candidate_dirs = [
        candidate_root / ".codex" / "session-state"
        for candidate_root in repo_roots_for_harness(repo_root)
    ]
    matches: list[dict] = []
    for session_dir in candidate_dirs:
        if not session_dir.exists():
            continue
        for candidate in session_dir.glob("*.json"):
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if payload.get("task") == task_id:
                matches.append(payload)
    exact_matches = [
        payload for payload in matches if Path(payload.get("worktree", "")).resolve() == repo_root.resolve()
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"session-state not found for task {task_id}")
    raise FileNotFoundError(f"multiple session-state files found for task {task_id}")


def run_one_stop_auto_gate(
    task_id: str,
    repo_root: Path,
    task_contract_path: Path | None = None,
) -> dict[str, str] | None:
    session = _load_session(repo_root, task_id)
    branch = session["branch"]
    worktree_root = Path(session["worktree"])
    state_root = next(
        (
            candidate_root
            for candidate_root in repo_roots_for_harness(worktree_root)
            if (candidate_root / ".codex" / "session-state").exists()
        ),
        worktree_root,
    )

    actionable = {
        "run_task_evaluator",
        "rerun_task_evaluator",
        "run_final_evaluator",
        "rerun_final_evaluator",
    }
    decision = harness_evaluator_hooks.stop_hook_for_session(
        worktree_root,
        session,
        task_id=task_id,
        task_contract_path=task_contract_path,
    )
    if decision is None:
        return None
    action = decision.get("action", "")
    if action not in actionable:
        return decision

    consume_decision_with_codex_exec(
        worktree_root,
        state_root,
        branch,
        task_id,
        decision,
    )

    followup = harness_evaluator_hooks.stop_hook_for_session(
        worktree_root,
        session,
        task_id=task_id,
        task_contract_path=task_contract_path,
    )
    if followup is None:
        return None
    if followup.get("action") != "run_final_evaluator":
        return followup

    consume_decision_with_codex_exec(
        worktree_root,
        state_root,
        branch,
        task_id,
        followup,
    )
    return harness_evaluator_hooks.stop_hook_for_session(
        worktree_root,
        session,
        task_id=task_id,
        task_contract_path=task_contract_path,
    )


def run_fake_auto_task_gate(
    task_id: str,
    repo_root: Path,
    max_attempts: int,
    task_contract_path: Path | None = None,
) -> int:
    session = _load_session(repo_root, task_id)
    branch = session["branch"]
    worktree_root = Path(session["worktree"])
    state_root = next(
        (
            candidate_root
            for candidate_root in repo_roots_for_harness(worktree_root)
            if (candidate_root / ".codex" / "session-state").exists()
        ),
        worktree_root,
    )
    for loop_index in range(max_attempts):
        decision = harness_evaluator_hooks.stop_hook_for_session(
            worktree_root,
            session,
            task_id=task_id,
            task_contract_path=task_contract_path,
        )
        if decision is None:
            return 0
        action = decision.get("action", "")
        bundle_dir = Path(decision.get("bundle_dir", ""))
        if action not in {"run_task_evaluator", "rerun_task_evaluator"} or not bundle_dir.exists():
            return 1
        status = "fail" if loop_index == 0 else "pass"
        _write_fake_task_result(bundle_dir, status)
        if status == "pass":
            update_session_state_evaluator(
                state_root,
                worktree_root,
                branch,
                task_id=task_id,
                phase="task_evaluator_passed",
                task_eval_attempt=int(json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))["attempt"]),
                last_task_eval_result="pass",
                repair_from_eval=False,
            )
        else:
            update_session_state_evaluator(
                state_root,
                worktree_root,
                branch,
                task_id=task_id,
                phase="repair_after_task_eval_fail",
                task_eval_attempt=int(json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))["attempt"]),
                last_task_eval_result="fail",
                repair_from_eval=True,
            )
    final_decision = harness_evaluator_hooks.stop_hook_for_session(
        worktree_root,
        session,
        task_id=task_id,
        task_contract_path=task_contract_path,
    )
    return 0 if final_decision is None else 1


def run_codex_exec_auto_task_gate(
    task_id: str,
    repo_root: Path,
    max_attempts: int,
    task_contract_path: Path | None = None,
) -> int:
    session = _load_session(repo_root, task_id)
    branch = session["branch"]
    worktree_root = Path(session["worktree"])
    state_root = next(
        (
            candidate_root
            for candidate_root in repo_roots_for_harness(worktree_root)
            if (candidate_root / ".codex" / "session-state").exists()
        ),
        worktree_root,
    )
    for _ in range(max_attempts):
        decision = harness_evaluator_hooks.stop_hook_for_session(
            worktree_root,
            session,
            task_id=task_id,
            task_contract_path=task_contract_path,
        )
        if decision is None:
            return 0
        handled = _consume_decision_with_codex_exec(
            worktree_root,
            state_root,
            branch,
            task_id,
            decision,
        )
        if not handled:
            return 1
    final_decision = harness_evaluator_hooks.stop_hook_for_session(
        worktree_root,
        session,
        task_id=task_id,
        task_contract_path=task_contract_path,
    )
    return 0 if final_decision is None else 1


def run_fake_task_loop(
    task_id: str,
    max_attempts: int,
    repo_root: Path | None = None,
    task_contract_path: Path | None = None,
) -> int:
    base_root = repo_root or Path(".")
    bundle_root = base_root / ".codex" / "evaluations" / "tasks" / task_id
    bundle_root.mkdir(parents=True, exist_ok=True)
    input_payload = _fake_task_input_payload(base_root, task_id, 1, task_contract_path)

    if input_payload["must_simulate"] and not input_payload["user_scenarios"]:
        bundle = bundle_root / "fake-attempt-1"
        bundle.mkdir(exist_ok=True)
        (bundle / "input.json").write_text(
            json.dumps(input_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        payload = {
            "status": "blocked",
            "gate": "task",
            "task_id": task_id,
            "final_bundle_id": "",
            "attempt": 1,
            "summary": "missing evaluator user scenarios",
            "findings": [
                {
                    "id": "F-001",
                    "severity": "major",
                    "category": "missing_user_scenarios",
                    "evidence": [input_payload["scenario_source"]],
                    "recommended_action": "add evaluator scenario metadata",
                }
            ],
            "scenario_results": [],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "task bundle requires simulation but no user scenarios were defined",
            "next_action": "request_missing_evidence",
        }
        (bundle / "result.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        _write_summary(
            bundle,
            payload["status"],
            payload["verdict_reason"],
            payload["scenario_results"],
        )
        return 1

    statuses = ["fail", "pass"][:max_attempts]
    for attempt, status in enumerate(statuses, start=1):
        bundle = bundle_root / f"fake-attempt-{attempt}"
        bundle.mkdir(exist_ok=True)
        current_input = _fake_task_input_payload(base_root, task_id, attempt, task_contract_path)
        (bundle / "input.json").write_text(
            json.dumps(current_input, indent=2) + "\n",
            encoding="utf-8",
        )
        payload = {
            "status": status,
            "gate": "task",
            "task_id": task_id,
            "final_bundle_id": "",
            "attempt": attempt,
            "summary": status,
            "findings": []
            if status == "pass"
            else [
                {
                    "id": "F-001",
                    "severity": "major",
                    "category": "scenario_failed",
                    "evidence": [f"summary.md#{current_input['user_scenarios'][0]['scenario_id']}"],
                    "recommended_action": "repair",
                }
            ],
            "scenario_results": _fake_scenario_results(current_input, status),
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": status,
            "next_action": "proceed_to_user_acceptance"
            if status == "pass"
            else "repair_and_reevaluate",
        }
        (bundle / "result.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        _write_summary(bundle, status, payload["verdict_reason"], payload["scenario_results"])
        if next_loop_action(status, attempt, max_attempts, "task") == "complete":
            return 0
    return 1


def run_codex_sdk_task_loop(task_id: str, max_attempts: int) -> int:
    from openai_codex import Codex, Sandbox

    with Codex() as codex:
        thread = codex.thread_start(sandbox=Sandbox.workspace_write)
        for attempt in range(1, max_attempts + 1):
            thread.run(
                f"Continue working on task {task_id}. If evaluator findings exist, fix them before stopping."
            )
            review = thread.run(
                f"Review the diff only for task {task_id} and produce evaluator-ready notes.",
                sandbox=Sandbox.read_only,
            )
            print(review.final_response)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    task = subparsers.add_parser("run-task-loop")
    task.add_argument("--driver", choices=("fake", "codex-sdk"), required=True)
    task.add_argument("--task-id", required=True)
    task.add_argument("--max-attempts", type=int, default=2)
    task.add_argument("--repo-root", default=".")
    task.add_argument("--task-contract", default="")

    auto_task = subparsers.add_parser("run-task-auto-gate")
    auto_task.add_argument("--driver", choices=("fake", "codex-exec"), required=True)
    auto_task.add_argument("--task-id", required=True)
    auto_task.add_argument("--max-attempts", type=int, default=3)
    auto_task.add_argument("--repo-root", default=".")
    auto_task.add_argument("--task-contract", default="")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-task-loop" and args.driver == "fake":
        return run_fake_task_loop(
            args.task_id,
            args.max_attempts,
            Path(args.repo_root),
            Path(args.task_contract) if args.task_contract else None,
        )
    if args.command == "run-task-loop" and args.driver == "codex-sdk":
        return run_codex_sdk_task_loop(args.task_id, args.max_attempts)
    if args.command == "run-task-auto-gate" and args.driver == "fake":
        return run_fake_auto_task_gate(
            args.task_id,
            Path(args.repo_root),
            args.max_attempts,
            Path(args.task_contract) if args.task_contract else None,
        )
    if args.command == "run-task-auto-gate" and args.driver == "codex-exec":
        return run_codex_exec_auto_task_gate(
            args.task_id,
            Path(args.repo_root),
            args.max_attempts,
            Path(args.task_contract) if args.task_contract else None,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
