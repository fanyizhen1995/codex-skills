"""Three-tier recovery planning and partial action artifact salvage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

from scripts.harness_ai_infra_evidence import (
    resolve_manifest_artifact_path,
    validate_required_evidence_manifest,
)
from scripts.harness_loop_agents import (
    load_validated_attempt_evidence,
    validate_owned_regular_file,
)
from scripts.harness_loop_artifacts import _redact_sensitive_text
from scripts.harness_loop_autonomous import check_autonomous_scope
from scripts.harness_loop_contracts import (
    read_json_file,
    validate_agent_attempt_payload,
    validate_artifact_hygiene_result_payload,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_run_payload,
    validate_scenario_command_result_payload,
)

from .models import (
    ActionOwner,
    ActionRequest,
    ActionResultClass,
    ActionType,
    RecoveryStage,
)
from .registry import recovery_transition_for


_ERROR_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("model_capacity", ("model is at capacity", "selected model is at capacity")),
    ("sse_disconnect", ("stream disconnected", "sse disconnect")),
    ("dns_failure", ("name resolution", "could not resolve", "dns failure")),
    ("git_lock", ("index.lock", "git lock")),
    ("timeout", ("timed out", "timeout")),
    ("transport_failure", ("connection reset", "transport", "connection aborted")),
)
_BACKOFF_SECONDS = {
    "model_capacity": 60,
    "sse_disconnect": 10,
    "dns_failure": 15,
    "git_lock": 5,
    "timeout": 30,
    "transport_failure": 10,
}


@dataclass(frozen=True)
class FailureClassification:
    error_class: str
    result_class: ActionResultClass
    retryable: bool


@dataclass(frozen=True)
class RecoveryPlan:
    tier: int
    action_type: ActionType
    strategy: str
    failure_key: str = ""
    episode_number: int = 0
    episode_attempts: int = 0
    retry_after_seconds: float = 0.0
    retry_at: str = ""
    source_action_id: str = ""
    source_action_type: str = ""
    lineage_id: str = ""
    source_policy: str = ""
    source_phase: str = ""
    source_next_action: str = ""
    stage: RecoveryStage | None = None


@dataclass(frozen=True)
class PartialArtifactAssessment:
    status: str
    run_id: str
    task_id: str
    action_type: ActionType
    run_dir: Path
    missing_checks: tuple[str, ...] = ()
    recovered_attempts: tuple[int, ...] = ()
    attempt_hashes: Mapping[int, str] | None = None
    attempt_stream_hashes: Mapping[int, Mapping[str, str]] | None = None
    changed_paths: tuple[str, ...] = ()
    verify_commands: tuple[str, ...] = ()
    verify_results: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    artifact_hashes: Mapping[str, str] | None = None
    checks: tuple[str, ...] = ()
    safety_signal: str = ""


@dataclass
class _RecoveryIndex:
    attempts_by_action: dict[str, dict[str, Any]]
    failures_by_key: dict[str, dict[str, Any]]
    episodes_by_key: dict[str, dict[str, Any]]
    episodes_by_source_action: dict[str, list[dict[str, Any]]]
    latest_direct_recovery_revision: dict[tuple[str, str], int]


def _value(source: object, key: str, default: Any = "") -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def classify_attempt_failure(attempt: Mapping[str, Any]) -> FailureClassification:
    """Classify one bounded attempt without depending on unstable message text."""
    text = " ".join(
        str(attempt.get(key) or "")
        for key in ("error_class", "summary", "stderr", "stdout")
    ).lower()
    for error_class, markers in _ERROR_PATTERNS:
        if any(marker in text for marker in markers):
            return FailureClassification(
                error_class=error_class,
                result_class=ActionResultClass.RETRYABLE_FAILURE,
                retryable=True,
            )
    if any(marker in text for marker in ("secret", "permission", "scope", "ownership")):
        return FailureClassification(
            error_class="policy_block",
            result_class=ActionResultClass.POLICY_BLOCK,
            retryable=False,
        )
    return FailureClassification(
        error_class=str(attempt.get("error_class") or "process_failure"),
        result_class=ActionResultClass.RETRYABLE_FAILURE,
        retryable=True,
    )


def _key_part(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    return normalized.strip("-") or "none"


def _stable_failure_key(
    run: Mapping[str, Any], action_type: ActionType, error_class: str
) -> str:
    lineage_id = run.get("loop_lineage_id") or run.get("run_id") or "none"
    return "recovery:" + ":".join(
        _key_part(value)
        for value in (
            lineage_id,
            run.get("run_id"),
            run.get("task_id"),
            run.get("policy"),
            run.get("phase"),
            run.get("next_action"),
            action_type.value,
            error_class,
        )
    )


def _class_failure_key(
    run: Mapping[str, Any], action_type: ActionType, error_class: str
) -> str:
    return _stable_failure_key(run, action_type, error_class).replace(
        "recovery:", "recovery-class:", 1
    )


def _episode_identity(run: Mapping[str, Any], action_type: ActionType) -> dict[str, str]:
    run_id = str(run.get("run_id") or "")
    return {
        "lineage_id": str(run.get("loop_lineage_id") or run_id),
        "run_id": run_id,
        "task_id": str(run.get("task_id") or ""),
        "source_policy": str(run.get("policy") or ""),
        "phase": str(run.get("phase") or ""),
        "source_next_action": str(run.get("next_action") or ""),
        "source_action_type": action_type.value,
    }


def _matching_episode_rows(
    store: Any, run: Mapping[str, Any], action_type: ActionType
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    identity = _episode_identity(run, action_type)
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in store.fetch_all("failures"):
        state = _load_episode(row)
        if state.get("kind") != "episode":
            continue
        if all(state.get(key) == value for key, value in identity.items()):
            matches.append((row, state))
    return matches


def _load_episode(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {}
    try:
        state = json.loads(str(row.get("resolution") or ""))
    except (TypeError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _failure_row(store: Any, failure_key: str) -> dict[str, Any] | None:
    return next(
        (row for row in store.fetch_all("failures") if row["failure_key"] == failure_key),
        None,
    )


def _plan_from_state(state: Mapping[str, Any], failure_key: str) -> RecoveryPlan:
    return RecoveryPlan(
        tier=int(state.get("planned_tier", 0)),
        action_type=ActionType(str(state.get("planned_action_type", ActionType.NO_OP.value))),
        strategy=str(state.get("strategy") or ""),
        failure_key=failure_key,
        episode_number=int(state.get("episode_number", 0)),
        episode_attempts=int(state.get("episode_attempts", 0)),
        retry_after_seconds=float(state.get("retry_after_seconds", 0.0)),
        retry_at=str(state.get("retry_at") or ""),
        source_action_id=str(state.get("source_action_id") or ""),
        source_action_type=str(state.get("source_action_type") or ""),
        lineage_id=str(state.get("lineage_id") or ""),
        source_policy=str(state.get("source_policy") or ""),
        source_phase=str(state.get("phase") or ""),
        source_next_action=str(state.get("source_next_action") or ""),
        stage=RecoveryStage(str(state["recovery_stage"]))
        if state.get("recovery_stage")
        else None,
    )


def _write_resolution(store: Any, failure_key: str, state: Mapping[str, Any]) -> None:
    store.update_failure_resolution(
        failure_key, json.dumps(dict(state), sort_keys=True)
    )


def _close_matching_episodes(
    store: Any, run: Mapping[str, Any], action_type: ActionType, result: object
) -> None:
    recovery_failure_key = str(_value(result, "recovery_failure_key", ""))
    action_id = str(_value(result, "action_id", ""))
    recovery_episode = int(_value(result, "recovery_episode", 0) or 0)
    source_action_id = str(_value(result, "source_action_id", ""))
    for row in store.fetch_all("failures"):
        state = _load_episode(row)
        if state.get("status") != "open":
            continue
        if recovery_failure_key:
            recovery_for = str(
                _value(result, "recovery_for_action_type", "")
                or state.get("source_action_type")
                or ""
            )
            try:
                source_action_type = ActionType(recovery_for)
            except ValueError:
                continue
            matches = (
                row["failure_key"] == recovery_failure_key
                and _episode_matches_action(state, run, source_action_type)
                and (
                    not recovery_episode
                    or int(state.get("episode_number", 0)) == recovery_episode
                )
                and (
                    not source_action_id
                    or state.get("source_action_id") == source_action_id
                )
            )
        else:
            matches = (
                _episode_matches_action(state, run, action_type)
                and state.get("source_action_id") == action_id
            )
        if not matches:
            continue
        state.update(
            {
                "status": "closed",
                "closed_by_attempt_id": str(_value(result, "attempt_id", "")),
                "lifetime_count": int(row["occurrence_count"]),
            }
        )
        _write_resolution(store, str(row["failure_key"]), state)


def plan_recovery(
    store: Any,
    run: Mapping[str, Any],
    action_result: object,
    *,
    jitter: Callable[[], float] | None = None,
) -> RecoveryPlan:
    """Record one failure observation and return its bounded recovery action."""
    result_class = str(_value(action_result, "result_class", ""))
    if isinstance(_value(action_result, "result_class", ""), ActionResultClass):
        result_class = _value(action_result, "result_class").value
    action_type = ActionType(str(_value(action_result, "action_type", ActionType.NO_OP.value)))
    if result_class == ActionResultClass.SUCCESS.value:
        _close_matching_episodes(store, run, action_type, action_result)
        return RecoveryPlan(tier=0, action_type=ActionType.NO_OP, strategy="episode_closed")

    recovery_failure_key = str(_value(action_result, "recovery_failure_key", ""))
    if recovery_failure_key:
        row = _failure_row(store, recovery_failure_key)
        state = _load_episode(row)
        attempt_id = str(_value(action_result, "attempt_id", ""))
        if state.get("alternate_failure_attempt_id") != attempt_id:
            transition = recovery_transition_for(
                str(run.get("policy") or ""),
                str(run.get("phase") or ""),
                str(run.get("next_action") or ""),
                RecoveryStage.REVIEWER,
            )
            state.update(
                {
                    "alternate_failure_attempt_id": attempt_id,
                    "alternate_failed": True,
                    "planned_tier": 3,
                    "planned_action_type": transition.action_type.value,
                    "strategy": transition.strategy,
                    "recovery_stage": RecoveryStage.REVIEWER.value,
                }
            )
            _write_resolution(store, recovery_failure_key, state)
        return _plan_from_state(state, recovery_failure_key)

    classification = classify_attempt_failure(
        {
            "error_class": _value(action_result, "error_class", ""),
            "summary": _value(action_result, "summary", ""),
        }
    )
    error_class = classification.error_class
    episodes = _matching_episode_rows(store, run, action_type)
    open_episode = next(
        ((row, state) for row, state in episodes if state.get("status") == "open"),
        None,
    )
    if open_episode is None:
        failure_key = _stable_failure_key(run, action_type, error_class)
        existing = _failure_row(store, failure_key)
        state = _load_episode(existing)
    else:
        existing, state = open_episode
        failure_key = str(existing["failure_key"])
    attempt_id = str(_value(action_result, "attempt_id", ""))
    if state.get("status") == "open" and state.get("last_attempt_id") == attempt_id:
        return _plan_from_state(state, failure_key)

    new_episode = not state or state.get("status") != "open"
    prior_episode_number = max(
        (int(item.get("episode_number", 0)) for _row, item in episodes),
        default=0,
    )
    episode_number = prior_episode_number + 1 if new_episode else int(state["episode_number"])
    episode_attempts = 1 if new_episode else int(state.get("episode_attempts", 0)) + 1
    lifetime_count = int(existing["occurrence_count"]) + 1 if existing else 1
    jitter_value = float((jitter or (lambda: 0.0))())
    if not 0.0 <= jitter_value <= 1.0:
        raise ValueError("jitter must return a value between 0 and 1")
    base_delay = _BACKOFF_SECONDS.get(error_class, 10)
    retry_after = float(base_delay * (2 ** max(episode_attempts - 1, 0)))
    retry_after += retry_after * 0.25 * jitter_value
    retry_at = store.format_time(
        store.current_time() + timedelta(seconds=retry_after)
    )

    if result_class == ActionResultClass.RECOVERABLE_PARTIAL.value:
        tier = 2
        recovery_stage = RecoveryStage.ALTERNATE
        alternate_used = True
    elif episode_attempts < 3:
        tier = 1
        recovery_stage = RecoveryStage.RETRY
        alternate_used = False
    elif episode_attempts == 3:
        tier = 2
        recovery_stage = RecoveryStage.ALTERNATE
        alternate_used = True
    else:
        tier = 3
        recovery_stage = RecoveryStage.REVIEWER
        alternate_used = bool(state.get("alternate_used"))

    transition = recovery_transition_for(
        str(run.get("policy") or ""),
        str(run.get("phase") or ""),
        str(run.get("next_action") or ""),
        recovery_stage,
    )
    planned_action = transition.action_type
    strategy = transition.strategy

    state = {
        "kind": "episode",
        **_episode_identity(run, action_type),
        "status": "open",
        "episode_number": episode_number,
        "episode_attempts": episode_attempts,
        "lifetime_count": lifetime_count,
        "last_attempt_id": attempt_id,
        "source_action_id": str(_value(action_result, "action_id", "")),
        "source_action_type": action_type.value,
        "alternate_used": alternate_used,
        "planned_tier": tier,
        "planned_action_type": planned_action.value,
        "strategy": strategy,
        "recovery_stage": recovery_stage.value,
        "retry_after_seconds": retry_after,
        "retry_at": retry_at,
        "current_error_class": error_class,
    }
    store.record_failure(
        _class_failure_key(run, action_type, error_class),
        run_id=str(run.get("run_id") or ""),
        task_id=str(run.get("task_id") or ""),
        error_class=error_class,
        summary=str(_value(action_result, "summary", "")),
        resolution=json.dumps({"kind": "class_lifetime"}, sort_keys=True),
    )
    store.record_failure(
        failure_key,
        run_id=str(run.get("run_id") or ""),
        task_id=str(run.get("task_id") or ""),
        error_class=error_class,
        summary=str(_value(action_result, "summary", "")),
        resolution=json.dumps(state, sort_keys=True),
    )
    return _plan_from_state(state, failure_key)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_repo_path(repo_root: Path, value: str, *, require_file: bool = True) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or value != relative.as_posix() or ".." in relative.parts:
        raise PermissionError(f"unsafe path: {value}")
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError(f"path ownership changed: {value}")
    resolved = current.resolve(strict=False)
    resolved.relative_to(repo_root)
    if require_file and not resolved.is_file():
        raise FileNotFoundError(value)
    return resolved


def _artifact_reference(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def _read_object(path: Path) -> dict[str, Any]:
    payload = read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain an object")
    return payload


def _owned_regular_file(owner_root: Path, path: Path, label: str) -> Path:
    return validate_owned_regular_file(owner_root, path, label)


def _read_owned_object(owner_root: Path, path: Path, label: str) -> dict[str, Any]:
    return _read_object(_owned_regular_file(owner_root, path, label))


def _dirty_path(line: object) -> str:
    value = str(line)
    return value[3:].strip() if len(value) > 3 and value[2] == " " else value.strip()


def _git_dirty_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git status failed while assessing partial artifacts")
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = _dirty_path(line)
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1]
        if path:
            paths.add(path)
    return paths


def _is_freshness_requirement(value: object) -> bool:
    text = str(value).lower()
    return "freshness" in text or "visibility" in text or "service availability" in text


def inspect_partial_artifacts(
    repo_root: Path, run: Mapping[str, Any], action_type: ActionType
) -> PartialArtifactAssessment:
    """Validate partial Generator evidence against the normal safety contracts."""
    root = Path(repo_root).resolve()
    run_id = str(run.get("run_id") or "")
    task_id = str(run.get("task_id") or "")
    run_dir = root / ".codex" / "loop-runs" / run_id
    missing: list[str] = []
    unsafe: list[str] = []
    checks: list[str] = []
    changed_paths: tuple[str, ...] = ()
    verify_commands: tuple[str, ...] = ()
    verify_results: tuple[str, ...] = ()
    artifacts: list[str] = []
    artifact_hashes: dict[str, str] = {}
    attempt_hashes: dict[int, str] = {}
    attempt_stream_hashes: dict[int, Mapping[str, str]] = {}
    recovered_attempts: list[int] = []
    safety_signals: list[str] = []

    try:
        validate_run_payload(dict(run))
        if action_type is not ActionType.RUN_GENERATOR:
            raise ValueError("partial recovery currently requires a Generator action")
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise PermissionError("run directory ownership is not trustworthy")
        declared_worktree = Path(str(run.get("worktree") or root)).resolve()
        if declared_worktree != root:
            raise PermissionError("run worktree ownership does not match repo root")
        checks.append("run_contract_and_ownership")
    except PermissionError as exc:
        unsafe.append(f"ownership: {exc}")
        safety_signals.append("repo_corruption")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"run_contract: {exc}")

    planner_path = run_dir / "planner-output.json"
    try:
        planner = _read_owned_object(run_dir, planner_path, "planner output")
        validate_planner_output_payload(planner)
        if planner.get("task_id") != task_id:
            raise PermissionError("planner task ownership does not match run")
        verify_commands = tuple(str(item) for item in planner["verify_commands"])
        artifacts.append(_artifact_reference(root, planner_path))
        checks.append("planner_contract")
    except PermissionError as exc:
        unsafe.append(f"ownership: {exc}")
        safety_signals.append("repo_corruption")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"planner_contract: {exc}")

    try:
        attempt_evidence = load_validated_attempt_evidence(
            run_dir,
            role="generator",
            expected_run_id=run_id,
        )
        for attempt in attempt_evidence:
            if attempt.status != "timeout":
                continue
            recovered_attempts.append(attempt.attempt)
            attempt_hashes[attempt.attempt] = attempt.attempt_sha256
            attempt_stream_hashes[attempt.attempt] = dict(attempt.stream_sha256)
            artifacts.append(_artifact_reference(root, attempt.path))
    except PermissionError as exc:
        unsafe.append(f"attempt_ownership: {exc}")
        safety_signals.append("repo_corruption")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"attempt_contract: {exc}")
    if not recovered_attempts:
        missing.append("attempt_contract: no valid timeout Generator attempts")
    else:
        checks.append("agent_attempt_contracts")

    dirty_path = run_dir / "dirty-paths-result.json"
    try:
        dirty = _read_owned_object(run_dir, dirty_path, "dirty paths manifest")
        declared = tuple(str(item) for item in dirty.get("declared_paths", []))
        actual = tuple(str(item) for item in dirty.get("actual_paths", []))
        if not declared:
            raise ValueError("declared paths are empty")
        if set(actual) != set(declared) or dirty.get("unexpected_paths"):
            raise PermissionError("actual paths do not equal declared paths")
        current_dirty = _git_dirty_paths(root)
        if any(path not in current_dirty for path in declared):
            raise ValueError("declared changed path is not currently dirty")
        baseline = {_dirty_path(item) for item in run.get("baseline_dirty_paths", [])}
        overlap = baseline.intersection(declared)
        if overlap:
            raise PermissionError(f"changed paths overlap baseline: {sorted(overlap)}")
        changed_paths = declared
        artifacts.append(_artifact_reference(root, dirty_path))
        checks.extend(("declared_paths", "baseline_ownership"))
    except PermissionError as exc:
        label = "baseline_ownership" if "baseline" in str(exc) else "declared_paths"
        unsafe.append(f"{label}: {exc}")
        safety_signals.append("user_decision_required")
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        missing.append(f"declared_paths: {exc}")

    if changed_paths:
        scope = check_autonomous_scope(
            changed_paths,
            [str(item) for item in run.get("allowed_paths", [])],
            [str(item) for item in run.get("denylist_paths", [])],
            [str(item) for item in run.get("manual_confirm_paths", [])],
        )
        if scope.allowed:
            checks.append("path_scope")
        else:
            unsafe.append(f"path_scope: {'; '.join(scope.findings)}")
            safety_signals.append("permission_expansion_required")

    verification_path = run_dir / "scenario-command-results.json"
    try:
        verification = _read_owned_object(
            run_dir, verification_path, "verification manifest"
        )
        results = verification.get("results")
        if verification.get("status") != "pass" or not isinstance(results, list) or not results:
            raise ValueError("verification manifest is not passing")
        observed_commands: list[str] = []
        summaries: list[str] = []
        for result in results:
            if not isinstance(result, dict):
                raise ValueError("verification result must be an object")
            validate_scenario_command_result_payload(result)
            if result["status"] != "pass" or result["exit_code"] != 0:
                raise ValueError(f"verification failed: {result['command']}")
            for key in ("stdout_path", "stderr_path"):
                _owned_regular_file(
                    run_dir / "scenario-commands",
                    Path(str(result[key])),
                    f"verification {key}",
                )
            command = str(result["command"])
            observed_commands.append(command)
            summaries.append(f"{command}: pass")
        if set(verify_commands) != set(observed_commands):
            raise ValueError("verification commands do not match Planner contract")
        verify_results = tuple(summaries)
        artifacts.append(_artifact_reference(root, verification_path))
        checks.append("verification_manifest")
    except PermissionError as exc:
        unsafe.append(f"verification_manifest: {exc}")
        safety_signals.append("repo_corruption")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"verification_manifest: {exc}")

    required = [str(item) for item in run.get("required_evidence", [])]
    manifest_path = run_dir / "required-evidence-manifest.json"
    if required:
        try:
            manifest = _read_owned_object(
                run_dir, manifest_path, "required evidence manifest"
            )
            if manifest.get("run_id") != run_id or manifest.get("task_id") != task_id:
                raise PermissionError("required evidence ownership does not match run")
            for item in manifest.get("items", []):
                if not isinstance(item, Mapping):
                    continue
                for artifact in item.get("artifacts", []):
                    resolved = resolve_manifest_artifact_path(
                        str(artifact), root, run_dir
                    )
                    if resolved is None:
                        raise PermissionError(
                            f"required evidence artifact escapes run: {artifact}"
                        )
                    _owned_regular_file(
                        run_dir, resolved, "required evidence artifact"
                    )
            findings = validate_required_evidence_manifest(
                required,
                manifest,
                root,
                run_dir,
                trusted_live_evidence_state=run.get("trusted_live_evidence_state")
                if isinstance(run.get("trusted_live_evidence_state"), Mapping)
                else None,
            )
            if findings:
                label = (
                    "freshness_evidence"
                    if any(_is_freshness_requirement(item) for item in required)
                    else "required_evidence"
                )
                missing.append(f"{label}: {'; '.join(findings)}")
            else:
                checks.append("required_evidence")
                if any(_is_freshness_requirement(item) for item in required):
                    checks.append("freshness_evidence")
            artifacts.append(_artifact_reference(root, manifest_path))
        except PermissionError as exc:
            unsafe.append(f"required_evidence: {exc}")
            safety_signals.append("repo_corruption")
        except (OSError, TypeError, ValueError) as exc:
            missing.append(f"required_evidence: {exc}")

    hygiene_path = run_dir / "artifact-manifest.json"
    try:
        hygiene = _read_owned_object(run_dir, hygiene_path, "artifact manifest")
        validate_artifact_hygiene_result_payload(hygiene)
        if hygiene.get("status") != "pass" or hygiene.get("redacted_paths") or hygiene.get("omitted_paths"):
            safety_signals.append("secret_exposure_confirmed")
            raise PermissionError("artifact hygiene did not prove a clean secret scan")
        scanned = {str(item) for item in hygiene["scanned_paths"]}
        hashes = hygiene["original_hashes"]
        if not isinstance(hashes, dict) or not set(changed_paths).issubset(scanned):
            raise PermissionError("artifact hygiene does not cover every changed path")
        for relative in changed_paths:
            current = _safe_repo_path(root, relative)
            expected_hash = str(hashes.get(relative) or "")
            actual_hash = _sha256(current)
            if not expected_hash or expected_hash != actual_hash:
                safety_signals.append("repo_corruption")
                raise PermissionError(f"artifact hash changed after secret scan: {relative}")
            _redacted, sensitive_rules = _redact_sensitive_text(
                current.read_text(encoding="utf-8")
            )
            if sensitive_rules:
                safety_signals.append("secret_exposure_confirmed")
                raise PermissionError(
                    f"artifact contains sensitive text rules {sorted(set(sensitive_rules))}: {relative}"
                )
            artifact_hashes[relative] = actual_hash
            artifacts.append(relative)
        artifacts.append(_artifact_reference(root, hygiene_path))
        checks.append("secret_scope_manifest")
    except PermissionError as exc:
        unsafe.append(f"secret_scope_manifest: {exc}")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"secret_scope_manifest: {exc}")

    if unsafe:
        status = "unsafe"
        findings = tuple(dict.fromkeys((*unsafe, *missing)))
    elif missing:
        status = "missing_work"
        findings = tuple(dict.fromkeys(missing))
    else:
        status = "recoverable"
        findings = ()
        checks.append("generator_contract")
    safety_signal = next(
        (
            signal
            for signal in (
                "secret_exposure_confirmed",
                "repo_corruption",
                "permission_expansion_required",
                "irreversible_operation_required",
                "user_decision_required",
            )
            if signal in safety_signals
        ),
        "",
    )
    return PartialArtifactAssessment(
        status=status,
        run_id=run_id,
        task_id=task_id,
        action_type=action_type,
        run_dir=run_dir,
        missing_checks=findings,
        recovered_attempts=tuple(sorted(recovered_attempts)),
        attempt_hashes=dict(sorted(attempt_hashes.items())),
        attempt_stream_hashes=dict(sorted(attempt_stream_hashes.items())),
        changed_paths=changed_paths,
        verify_commands=verify_commands,
        verify_results=verify_results,
        artifacts=tuple(dict.fromkeys(artifacts)),
        artifact_hashes=dict(sorted(artifact_hashes.items())),
        checks=tuple(dict.fromkeys(checks)),
        safety_signal=safety_signal,
    )


def inspect_legacy_generator_artifacts(
    repo_root: Path, run: Mapping[str, Any]
) -> PartialArtifactAssessment:
    """Validate pre-Supervisor Generator output without trusting stale run manifests."""
    root = Path(repo_root).resolve()
    run_id = str(run.get("run_id") or "")
    task_id = str(run.get("task_id") or "")
    run_dir = root / ".codex" / "loop-runs" / run_id
    missing: list[str] = []
    unsafe: list[str] = []
    checks: list[str] = []
    artifacts: list[str] = []
    attempt_hashes: dict[int, str] = {}
    attempt_stream_hashes: dict[int, Mapping[str, str]] = {}
    artifact_hashes: dict[str, str] = {}
    recovered_attempts: list[int] = []
    changed_paths: tuple[str, ...] = ()
    verify_commands: tuple[str, ...] = ()
    verify_results: tuple[str, ...] = ()

    try:
        validate_run_payload(dict(run))
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise PermissionError("run directory ownership is not trustworthy")
        if Path(str(run.get("worktree") or root)).resolve() != root:
            raise PermissionError("run worktree ownership does not match repo root")
        checks.append("run_contract_and_ownership")
    except PermissionError as exc:
        unsafe.append(f"ownership: {exc}")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"run_contract: {exc}")

    planner_path = run_dir / "planner-output.json"
    try:
        planner = _read_owned_object(run_dir, planner_path, "legacy planner output")
        planner.setdefault("skill_invocations", [])
        validate_planner_output_payload(planner)
        if planner.get("task_id") != task_id:
            raise PermissionError("planner task ownership does not match run")
        verify_commands = tuple(str(item) for item in planner["verify_commands"])
        artifacts.append(_artifact_reference(root, planner_path))
        checks.append("planner_contract")
    except PermissionError as exc:
        unsafe.append(f"planner_ownership: {exc}")
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"planner_contract: {exc}")

    for discovered in sorted(run_dir.glob("generator-attempt-*.json")):
        try:
            path = _owned_regular_file(run_dir, discovered, "legacy attempt JSON")
            payload = _read_object(path)
            validate_agent_attempt_payload(payload)
            if payload["run_id"] != run_id or payload["role"] != "generator":
                raise PermissionError("attempt payload ownership does not match run")
            if payload["status"] != "timeout":
                continue
            streams: dict[str, str] = {}
            for name in ("stdout", "stderr"):
                stream = _owned_regular_file(
                    run_dir,
                    Path(str(payload[f"{name}_path"])),
                    f"legacy attempt {name}",
                )
                streams[name] = _sha256(stream)
            attempt_number = int(payload["attempt"])
            recovered_attempts.append(attempt_number)
            attempt_hashes[attempt_number] = _sha256(path)
            attempt_stream_hashes[attempt_number] = streams
            artifacts.append(_artifact_reference(root, path))
        except PermissionError as exc:
            unsafe.append(f"attempt_ownership: {exc}")
            break
        except (OSError, TypeError, ValueError):
            continue
    if recovered_attempts:
        checks.append("agent_attempt_contracts")
    else:
        missing.append("attempt_contract: no valid timeout Generator attempts")

    verification: dict[str, Any] | None = None
    domain = str(run.get("domain") or "")
    domain_root = root / "personal-wiki" / "domains" / domain
    if domain and domain_root.is_dir() and not domain_root.is_symlink():
        for candidate in sorted(domain_root.glob("manifest-*verification.json")):
            try:
                payload = _read_owned_object(root, candidate, "legacy verification manifest")
            except (OSError, TypeError, ValueError):
                continue
            if (
                payload.get("run_id") == run_id
                and payload.get("task_id") == task_id
                and payload.get("status") == "pass"
            ):
                if verification is not None:
                    unsafe.append("verification_manifest: multiple task-owned manifests")
                    verification = None
                    break
                verification = payload
                artifacts.append(_artifact_reference(root, candidate))
    if verification is None:
        missing.append("verification_manifest: task-owned passing manifest is absent")
    else:
        raw_changed = verification.get("changed_paths")
        raw_results = verification.get("verify_results")
        if not isinstance(raw_changed, list) or not raw_changed:
            missing.append("verification_manifest: changed_paths are absent")
        elif not isinstance(raw_results, list) or not raw_results:
            missing.append("verification_manifest: verify_results are absent")
        else:
            changed_paths = tuple(str(item) for item in raw_changed)
            invalid_results = [
                item
                for item in raw_results
                if not isinstance(item, Mapping) or item.get("status") not in {"pass", "delegated"}
            ]
            if invalid_results:
                missing.append("verification_manifest: a verification result did not pass")
            else:
                verify_results = tuple(
                    f"{item.get('command', 'legacy verification')}: {item['status']}"
                    for item in raw_results
                    if isinstance(item, Mapping)
                )
                checks.append("legacy_verification_manifest")

    if changed_paths:
        try:
            current_dirty = _git_dirty_paths(root)
            absent = sorted(set(changed_paths) - current_dirty)
            if absent:
                raise ValueError(f"declared changed paths are not dirty: {absent}")
            baseline = {_dirty_path(item) for item in run.get("baseline_dirty_paths", [])}
            overlap = sorted(baseline.intersection(changed_paths))
            if overlap:
                raise PermissionError(f"changed paths overlap baseline: {overlap}")
            scope = check_autonomous_scope(
                changed_paths,
                [str(item) for item in run.get("allowed_paths", [])],
                [str(item) for item in run.get("denylist_paths", [])],
                [str(item) for item in run.get("manual_confirm_paths", [])],
            )
            if not scope.allowed:
                raise PermissionError(f"path scope failed: {'; '.join(scope.findings)}")
            checks.extend(("declared_paths", "baseline_ownership", "path_scope"))
        except PermissionError as exc:
            unsafe.append(f"path_scope: {exc}")
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            missing.append(f"declared_paths: {exc}")

    if changed_paths and not unsafe:
        try:
            for relative in changed_paths:
                current = _safe_repo_path(root, relative)
                _owned_regular_file(root, current, "legacy changed artifact")
                _redacted, sensitive_rules = _redact_sensitive_text(
                    current.read_text(encoding="utf-8")
                )
                if sensitive_rules:
                    raise PermissionError(
                        f"artifact contains sensitive text rules {sorted(set(sensitive_rules))}: {relative}"
                    )
                artifact_hashes[relative] = _sha256(current)
                artifacts.append(relative)
            for field in ("raw_sources", "curated_paths"):
                values = verification.get(field, []) if verification else []
                if not isinstance(values, list):
                    raise ValueError(f"{field} must be a list")
                for relative in values:
                    _owned_regular_file(
                        root,
                        _safe_repo_path(root, str(relative)),
                        f"legacy verification {field}",
                    )
            checks.append("secret_scope_manifest")
        except PermissionError as exc:
            unsafe.append(f"secret_scope_manifest: {exc}")
        except (OSError, TypeError, ValueError) as exc:
            missing.append(f"secret_scope_manifest: {exc}")

    if unsafe:
        status = "unsafe"
        findings = tuple(dict.fromkeys((*unsafe, *missing)))
        safety_signal = "repo_corruption"
    elif missing:
        status = "missing_work"
        findings = tuple(dict.fromkeys(missing))
        safety_signal = ""
    else:
        status = "recoverable"
        findings = ()
        safety_signal = ""
        checks.append("generator_contract")
    return PartialArtifactAssessment(
        status=status,
        run_id=run_id,
        task_id=task_id,
        action_type=ActionType.RUN_GENERATOR,
        run_dir=run_dir,
        missing_checks=findings,
        recovered_attempts=tuple(sorted(set(recovered_attempts))),
        attempt_hashes=dict(sorted(attempt_hashes.items())),
        attempt_stream_hashes=dict(sorted(attempt_stream_hashes.items())),
        changed_paths=changed_paths,
        verify_commands=verify_commands,
        verify_results=verify_results,
        artifacts=tuple(dict.fromkeys(artifacts)),
        artifact_hashes=dict(sorted(artifact_hashes.items())),
        checks=tuple(dict.fromkeys(checks)),
        safety_signal=safety_signal,
    )


def reconstruct_result_envelope(
    repo_root: Path, assessment: PartialArtifactAssessment
) -> Path:
    """Reconstruct only a missing Generator envelope with recovery provenance."""
    if assessment.status != "recoverable":
        raise ValueError(f"partial artifacts are not recoverable: {assessment.missing_checks}")
    root = Path(repo_root).resolve()
    assessment.run_dir.resolve().relative_to(root)
    target = assessment.run_dir / "generator-result.json"
    if target.exists() or target.is_symlink():
        raise FileExistsError("Generator result envelope already exists")
    payload = {
        "task_id": assessment.task_id,
        "status": "implemented",
        "changed_paths": list(assessment.changed_paths),
        "commit": "",
        "verify_commands": list(assessment.verify_commands),
        "verify_results": list(assessment.verify_results),
        "artifacts": list(assessment.artifacts),
        "cleanup_required": True,
        "notes": "Reconstructed from validated partial Generator artifacts; independent Evaluator required.",
        "skill_invocations": [],
        "recovery": {
            "recovered_from_attempts": list(assessment.recovered_attempts),
            "attempt_hashes": {
                str(key): value for key, value in (assessment.attempt_hashes or {}).items()
            },
            "attempt_stream_hashes": {
                str(key): dict(value)
                for key, value in (assessment.attempt_stream_hashes or {}).items()
            },
            "artifact_hashes": dict(assessment.artifact_hashes or {}),
            "checks": list(assessment.checks),
            "recovered_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "next_required_action": ActionType.RUN_EVALUATOR.value,
        },
    }
    validate_generator_result_payload(payload)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def _action_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(str(row.get("payload_json") or "{}"))
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_recovery_index(
    store: Any, actions: list[dict[str, Any]]
) -> _RecoveryIndex:
    action_ids = {str(row["action_id"]) for row in actions}
    attempts_by_action: dict[str, dict[str, Any]] = {}
    for attempt in store.fetch_all("action_attempts"):
        action_id = str(attempt.get("action_id") or "")
        if action_id not in action_ids:
            continue
        previous = attempts_by_action.get(action_id)
        identity = (str(attempt.get("created_at") or ""), str(attempt["attempt_id"]))
        if previous is None or identity > (
            str(previous.get("created_at") or ""),
            str(previous["attempt_id"]),
        ):
            attempts_by_action[action_id] = attempt

    failure_rows = store.fetch_all("failures")
    failures_by_key = {str(row["failure_key"]): row for row in failure_rows}
    episodes_by_key: dict[str, dict[str, Any]] = {}
    episodes_by_source_action: dict[str, list[dict[str, Any]]] = {}
    for row in failure_rows:
        state = _load_episode(row)
        if state.get("kind") != "episode":
            continue
        failure_key = str(row["failure_key"])
        episodes_by_key[failure_key] = state
        source_action_id = str(state.get("source_action_id") or "")
        if source_action_id:
            episodes_by_source_action.setdefault(source_action_id, []).append(state)

    latest_direct_recovery_revision: dict[tuple[str, str], int] = {}
    for row in actions:
        if (
            row.get("status") != "completed"
            or row.get("action_type") != ActionType.RECOVER_GENERATOR_RESULT.value
            or _action_payload(row).get("recovery_failure_key")
        ):
            continue
        key = (str(row.get("task_id") or ""), str(row.get("policy") or ""))
        latest_direct_recovery_revision[key] = max(
            latest_direct_recovery_revision.get(key, -1),
            int(row.get("run_revision") or 0),
        )
    return _RecoveryIndex(
        attempts_by_action=attempts_by_action,
        failures_by_key=failures_by_key,
        episodes_by_key=episodes_by_key,
        episodes_by_source_action=episodes_by_source_action,
        latest_direct_recovery_revision=latest_direct_recovery_revision,
    )


def _completed_action_matches_episode(
    row: Mapping[str, Any],
    payload: Mapping[str, Any],
    state: Mapping[str, Any],
    run: Mapping[str, Any],
) -> bool:
    failure_key = str(payload.get("recovery_failure_key") or "")
    if failure_key:
        identity = payload.get("recovery_semantic_identity")
        return (
            isinstance(identity, Mapping)
            and all(state.get(key) == value for key, value in identity.items())
            and int(state.get("episode_number", 0))
            == int(payload.get("recovery_episode") or 0)
            and state.get("source_action_id") == payload.get("source_action_id")
            and state.get("source_action_type")
            == payload.get("recovery_for_action_type")
            and state.get("planned_action_type") == row.get("action_type")
        )
    try:
        action_type = ActionType(str(row.get("action_type") or ""))
    except ValueError:
        return False
    return (
        state.get("source_action_id") == row.get("action_id")
        and _episode_matches_action(state, run, action_type)
        and state.get("run_id") == row.get("run_id")
        and state.get("task_id") == row.get("task_id")
        and state.get("source_policy") == row.get("policy")
        and state.get("phase") == row.get("phase")
        and state.get("source_next_action") == row.get("next_action")
    )


def _close_completed_action_episodes(
    store: Any,
    run: Mapping[str, Any],
    actions: list[dict[str, Any]],
    index: _RecoveryIndex,
) -> None:
    for row in actions:
        if row.get("status") != "completed":
            continue
        attempt = index.attempts_by_action.get(str(row["action_id"]))
        if attempt is None or attempt.get("result_class") != ActionResultClass.SUCCESS.value:
            continue
        payload = _action_payload(row)
        failure_key = str(payload.get("recovery_failure_key") or "")
        if failure_key:
            candidates = [(failure_key, index.episodes_by_key.get(failure_key))]
        else:
            candidates = [
                (key, state)
                for key, state in index.episodes_by_key.items()
                if state.get("source_action_id") == row.get("action_id")
            ]
        for key, state in candidates:
            if (
                not state
                or state.get("status") != "open"
                or not _completed_action_matches_episode(row, payload, state, run)
            ):
                continue
            failure_row = index.failures_by_key[key]
            state.update(
                {
                    "status": "closed",
                    "closed_by_attempt_id": str(attempt["attempt_id"]),
                    "lifetime_count": int(failure_row["occurrence_count"]),
                }
            )
            _write_resolution(store, key, state)


def _retry_is_due(store: Any, retry_at: str) -> bool:
    if not retry_at:
        return True
    normalized = retry_at.replace("Z", "+00:00")
    return store.current_time() >= datetime.fromisoformat(normalized)


def _requeue_failed_action(store: Any, action_id: str, tier: int) -> None:
    store.requeue_failed_action(action_id, recovery_tier=tier)


def _episode_matches_action(
    state: Mapping[str, Any], run: Mapping[str, Any], action_type: ActionType
) -> bool:
    identity = _episode_identity(run, action_type)
    return (
        state.get("kind") == "episode"
        and all(state.get(key) == value for key, value in identity.items())
    )


def _is_open_failed_alternate_for_action(
    row: Mapping[str, Any],
    run: Mapping[str, Any],
    desired: ActionRequest,
    index: _RecoveryIndex,
) -> bool:
    if (
        row.get("status") != "failed"
        or row.get("action_type")
        not in {
            ActionType.RECOVER_GENERATOR_RESULT.value,
            ActionType.RUN_ALTERNATE_RECOVERY.value,
        }
    ):
        return False
    payload = _action_payload(row)
    failure_key = str(payload.get("recovery_failure_key") or "")
    recovery_for = str(payload.get("recovery_for_action_type") or "")
    if not failure_key or recovery_for != desired.action_type.value:
        return False
    state = index.episodes_by_key.get(failure_key, {})
    return state.get("status") == "open" and _episode_matches_action(
        state, run, desired.action_type
    )


def _latest_failed_semantic_source(
    actions: list[dict[str, Any]],
    run: Mapping[str, Any],
    desired: ActionRequest,
    index: _RecoveryIndex,
) -> dict[str, Any] | None:
    expected_identity = _episode_identity(run, desired.action_type)

    def has_matching_lineage_provenance(row: Mapping[str, Any]) -> bool:
        if int(row.get("run_revision") or 0) == desired.run_revision:
            return True
        payload_identity = _action_payload(row).get("recovery_semantic_identity")
        if isinstance(payload_identity, Mapping) and dict(payload_identity) == expected_identity:
            return True
        return any(
            _episode_matches_action(state, run, desired.action_type)
            for state in index.episodes_by_source_action.get(
                str(row["action_id"]), []
            )
        )

    candidates = [
        row
        for row in actions
        if row.get("status") == "failed"
        and row.get("task_id") == desired.task_id
        and row.get("policy") == desired.policy
        and row.get("phase") == desired.phase
        and row.get("next_action") == desired.next_action
        and row.get("action_type") == desired.action_type.value
        and index.latest_direct_recovery_revision.get(
            (str(row.get("task_id") or ""), str(row.get("policy") or "")), -1
        )
        <= int(row.get("run_revision") or 0)
        and has_matching_lineage_provenance(row)
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (str(row.get("updated_at") or ""), str(row["action_id"])),
    )


def _with_semantic_provenance(
    desired: ActionRequest, run: Mapping[str, Any]
) -> ActionRequest:
    payload = desired.payload_for_storage()
    identity = _episode_identity(run, desired.action_type)
    if payload.get("recovery_semantic_identity") == identity:
        return desired
    payload["recovery_semantic_identity"] = identity
    return ActionRequest(
        action_id=desired.action_id,
        run_id=desired.run_id,
        run_revision=desired.run_revision,
        policy=desired.policy,
        phase=desired.phase,
        action_type=desired.action_type,
        queue_owner=desired.queue_owner,
        not_before=desired.not_before,
        idempotency_key=desired.idempotency_key,
        repo_relative_root=desired.repo_relative_root,
        task_id=desired.task_id,
        next_action=desired.next_action,
        payload=payload,
    )


def _recovery_payload(
    desired: ActionRequest, plan: RecoveryPlan
) -> dict[str, Any]:
    source_action_type = plan.source_action_type or desired.action_type.value
    semantic_identity = {
        "lineage_id": plan.lineage_id or desired.run_id,
        "run_id": desired.run_id,
        "task_id": desired.task_id,
        "source_policy": plan.source_policy or desired.policy,
        "phase": plan.source_phase or desired.phase,
        "source_next_action": plan.source_next_action or desired.next_action,
        "source_action_type": source_action_type,
    }
    return {
        "recovery_failure_key": plan.failure_key,
        "recovery_episode": plan.episode_number,
        "recovery_tier": plan.tier,
        "recovery_stage": plan.stage.value if plan.stage is not None else "",
        "recovery_strategy": plan.strategy,
        "recovery_for_action_type": source_action_type,
        "source_action_id": plan.source_action_id or desired.action_id,
        "recovery_semantic_identity": semantic_identity,
    }


def _retry_request(desired: ActionRequest, plan: RecoveryPlan) -> ActionRequest:
    return ActionRequest(
        action_id=desired.action_id,
        run_id=desired.run_id,
        run_revision=desired.run_revision,
        policy=desired.policy,
        phase=desired.phase,
        action_type=desired.action_type,
        queue_owner=desired.queue_owner,
        not_before=desired.not_before,
        idempotency_key=desired.idempotency_key,
        repo_relative_root=desired.repo_relative_root,
        task_id=desired.task_id,
        next_action=desired.next_action,
        payload={**desired.payload_for_storage(), **_recovery_payload(desired, plan)},
    )


def _recovery_request(desired: ActionRequest, plan: RecoveryPlan) -> ActionRequest:
    queue_owner = (
        ActionOwner.REVIEWER
        if plan.action_type is ActionType.RUN_REVIEWER
        else desired.queue_owner
    )
    identity = {
        "failure_key": plan.failure_key,
        "episode": plan.episode_number,
        "action_type": plan.action_type.value,
        "run_id": desired.run_id,
        "run_revision": desired.run_revision,
        "policy": desired.policy,
        "phase": desired.phase,
        "task_id": desired.task_id,
        "next_action": desired.next_action,
        "repo_relative_root": desired.repo_relative_root,
        "queue_owner": queue_owner.value,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ActionRequest(
        action_id=f"action-{digest[:24]}",
        run_id=desired.run_id,
        run_revision=desired.run_revision,
        policy=desired.policy,
        phase=desired.phase,
        action_type=plan.action_type,
        queue_owner=queue_owner,
        idempotency_key=f"recovery:{digest}",
        repo_relative_root=desired.repo_relative_root,
        task_id=desired.task_id,
        next_action=desired.next_action,
        payload=_recovery_payload(desired, plan),
    )


def recovery_action_for_run(
    store: Any,
    run: Mapping[str, Any],
    desired: ActionRequest,
) -> ActionRequest | None:
    """Return the currently eligible normal, retry, alternate, or Reviewer action."""
    desired = _with_semantic_provenance(desired, run)
    actions = [
        row
        for row in store.fetch_all("actions")
        if row.get("run_id") == desired.run_id
    ]
    index = _build_recovery_index(store, actions)
    _close_completed_action_episodes(store, run, actions, index)

    failed_alternates = [
        row
        for row in actions
        if _is_open_failed_alternate_for_action(row, run, desired, index)
    ]
    if failed_alternates:
        alternate = max(
            failed_alternates,
            key=lambda row: (str(row.get("updated_at") or ""), str(row["action_id"])),
        )
        attempt = index.attempts_by_action.get(str(alternate["action_id"]))
        if attempt is not None:
            payload = _action_payload(alternate)
            plan = plan_recovery(
                store,
                run,
                {
                    **attempt,
                    "action_type": alternate["action_type"],
                    "recovery_failure_key": payload["recovery_failure_key"],
                },
                jitter=lambda: 0.0,
            )
            return _recovery_request(desired, plan)

    source = _latest_failed_semantic_source(actions, run, desired, index)
    if source is None:
        return desired
    source_action_id = str(source["action_id"])
    attempt = index.attempts_by_action.get(source_action_id)
    if attempt is None:
        return None
    reviewed_episode = next(
        (
            state
            for state in index.episodes_by_key.values()
            if _episode_matches_action(state, run, desired.action_type)
            if state.get("status") == "closed"
            and state.get("last_attempt_id") == attempt.get("attempt_id")
        ),
        None,
    )
    if reviewed_episode is not None:
        if source_action_id == desired.action_id:
            _requeue_failed_action(store, source_action_id, 0)
        return desired
    plan = plan_recovery(
        store,
        run,
        {**attempt, "action_type": desired.action_type.value},
        jitter=lambda: 0.0,
    )
    if plan.tier == 1:
        if not _retry_is_due(store, plan.retry_at):
            return None
        if source_action_id == desired.action_id:
            _requeue_failed_action(store, source_action_id, plan.tier)
        return _retry_request(desired, plan)
    return _recovery_request(desired, plan)
