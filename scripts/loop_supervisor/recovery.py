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

from scripts.harness_ai_infra_evidence import validate_required_evidence_manifest
from scripts.harness_loop_agents import load_validated_attempt_evidence
from scripts.harness_loop_artifacts import _redact_sensitive_text
from scripts.harness_loop_autonomous import check_autonomous_scope
from scripts.harness_loop_contracts import (
    read_json_file,
    validate_artifact_hygiene_result_payload,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_run_payload,
    validate_scenario_command_result_payload,
)

from .models import ActionRequest, ActionResultClass, ActionType


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
            action_type.value,
            error_class,
        )
    )


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
    )


def _write_resolution(store: Any, failure_key: str, state: Mapping[str, Any]) -> None:
    now = store._now_text()
    with store._immediate_transaction():
        store._connection.execute(
            "UPDATE failures SET resolution = ?, updated_at = ? WHERE failure_key = ?",
            (json.dumps(dict(state), sort_keys=True), now, failure_key),
        )


def _close_matching_episodes(
    store: Any, run: Mapping[str, Any], action_type: ActionType, result: object
) -> None:
    recovery_failure_key = str(_value(result, "recovery_failure_key", ""))
    for row in store.fetch_all("failures"):
        state = _load_episode(row)
        if state.get("status") != "open":
            continue
        if recovery_failure_key:
            matches = row["failure_key"] == recovery_failure_key
        else:
            matches = (
                row.get("run_id") == str(run.get("run_id") or "")
                and row.get("task_id") == str(run.get("task_id") or "")
                and state.get("source_action_type") == action_type.value
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
            state.update(
                {
                    "alternate_failure_attempt_id": attempt_id,
                    "alternate_failed": True,
                    "planned_tier": 3,
                    "planned_action_type": ActionType.RUN_REVIEWER.value,
                    "strategy": "review_recovery_exhaustion",
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
    failure_key = _stable_failure_key(run, action_type, error_class)
    existing = _failure_row(store, failure_key)
    state = _load_episode(existing)
    attempt_id = str(_value(action_result, "attempt_id", ""))
    if state.get("status") == "open" and state.get("last_attempt_id") == attempt_id:
        return _plan_from_state(state, failure_key)

    new_episode = not state or state.get("status") != "open"
    episode_number = int(state.get("episode_number", 0)) + (1 if new_episode else 0)
    episode_attempts = 1 if new_episode else int(state.get("episode_attempts", 0)) + 1
    lifetime_count = int(existing["occurrence_count"]) + 1 if existing else 1
    jitter_value = float((jitter or (lambda: 0.0))())
    if not 0.0 <= jitter_value <= 1.0:
        raise ValueError("jitter must return a value between 0 and 1")
    base_delay = _BACKOFF_SECONDS.get(error_class, 10)
    retry_after = float(base_delay * (2 ** max(episode_attempts - 1, 0)))
    retry_after += retry_after * 0.25 * jitter_value
    retry_at = store._time_text(store._now() + timedelta(seconds=retry_after))

    if result_class == ActionResultClass.RECOVERABLE_PARTIAL.value:
        tier = 2
        planned_action = (
            ActionType.RECOVER_GENERATOR_RESULT
            if action_type is ActionType.RUN_GENERATOR
            else ActionType.RUN_ALTERNATE_RECOVERY
        )
        strategy = (
            "reconstruct_result_envelope"
            if planned_action is ActionType.RECOVER_GENERATOR_RESULT
            else "bounded_alternate_recovery"
        )
        alternate_used = True
    elif episode_attempts < 3:
        tier = 1
        planned_action = action_type
        strategy = "retry_same_action"
        alternate_used = False
    elif episode_attempts == 3:
        tier = 2
        planned_action = (
            ActionType.RECOVER_GENERATOR_RESULT
            if action_type is ActionType.RUN_GENERATOR
            else ActionType.RUN_ALTERNATE_RECOVERY
        )
        strategy = (
            "reconstruct_result_envelope"
            if planned_action is ActionType.RECOVER_GENERATOR_RESULT
            else "bounded_alternate_recovery"
        )
        alternate_used = True
    else:
        tier = 3
        planned_action = ActionType.RUN_REVIEWER
        strategy = "review_recovery_exhaustion"
        alternate_used = bool(state.get("alternate_used"))

    state = {
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
        "retry_after_seconds": retry_after,
        "retry_at": retry_at,
    }
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
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"run_contract: {exc}")

    planner_path = run_dir / "planner-output.json"
    try:
        planner = _read_object(planner_path)
        validate_planner_output_payload(planner)
        if planner.get("task_id") != task_id:
            raise PermissionError("planner task ownership does not match run")
        verify_commands = tuple(str(item) for item in planner["verify_commands"])
        artifacts.append(_artifact_reference(root, planner_path))
        checks.append("planner_contract")
    except PermissionError as exc:
        unsafe.append(f"ownership: {exc}")
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
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"attempt_contract: {exc}")
    if not recovered_attempts:
        missing.append("attempt_contract: no valid timeout Generator attempts")
    else:
        checks.append("agent_attempt_contracts")

    dirty_path = run_dir / "dirty-paths-result.json"
    try:
        dirty = _read_object(dirty_path)
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

    verification_path = run_dir / "scenario-command-results.json"
    try:
        verification = _read_object(verification_path)
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
                evidence_path = Path(str(result[key]))
                evidence_path.resolve().relative_to(root)
                if evidence_path.is_symlink() or not evidence_path.is_file():
                    raise PermissionError(f"verification {key} is not trustworthy")
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
    except (OSError, TypeError, ValueError) as exc:
        missing.append(f"verification_manifest: {exc}")

    required = [str(item) for item in run.get("required_evidence", [])]
    manifest_path = run_dir / "required-evidence-manifest.json"
    if required:
        try:
            manifest = _read_object(manifest_path)
            if manifest.get("run_id") != run_id or manifest.get("task_id") != task_id:
                raise PermissionError("required evidence ownership does not match run")
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
        except (OSError, TypeError, ValueError) as exc:
            missing.append(f"required_evidence: {exc}")

    hygiene_path = run_dir / "artifact-manifest.json"
    try:
        hygiene = _read_object(hygiene_path)
        validate_artifact_hygiene_result_payload(hygiene)
        if hygiene.get("status") != "pass" or hygiene.get("redacted_paths") or hygiene.get("omitted_paths"):
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
                raise PermissionError(f"artifact hash changed after secret scan: {relative}")
            _redacted, sensitive_rules = _redact_sensitive_text(
                current.read_text(encoding="utf-8")
            )
            if sensitive_rules:
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


def _latest_attempt(store: Any, action_id: str) -> dict[str, Any] | None:
    attempts = [
        row
        for row in store.fetch_all("action_attempts")
        if row.get("action_id") == action_id
    ]
    if not attempts:
        return None
    return max(attempts, key=lambda row: (str(row.get("created_at") or ""), str(row["attempt_id"])))


def _close_completed_action_episodes(
    store: Any, run: Mapping[str, Any], actions: list[dict[str, Any]]
) -> None:
    for row in actions:
        if row.get("status") != "completed":
            continue
        attempt = _latest_attempt(store, str(row["action_id"]))
        if attempt is None or attempt.get("result_class") != ActionResultClass.SUCCESS.value:
            continue
        payload = _action_payload(row)
        plan_recovery(
            store,
            run,
            {
                "attempt_id": attempt["attempt_id"],
                "action_id": row["action_id"],
                "action_type": row["action_type"],
                "result_class": ActionResultClass.SUCCESS.value,
                "summary": attempt.get("summary", ""),
                "recovery_failure_key": payload.get("recovery_failure_key", ""),
            },
            jitter=lambda: 0.0,
        )


def _retry_is_due(store: Any, retry_at: str) -> bool:
    if not retry_at:
        return True
    normalized = retry_at.replace("Z", "+00:00")
    return store._now() >= datetime.fromisoformat(normalized)


def _requeue_failed_action(store: Any, action_id: str, tier: int) -> None:
    now = store._now_text()
    with store._immediate_transaction():
        store._connection.execute(
            """
            UPDATE actions
            SET status = 'pending', recovery_tier = ?, lease_owner = '',
                lease_expires_at = '', lease_heartbeat_at = '', updated_at = ?
            WHERE action_id = ? AND status = 'failed'
            """,
            (tier, now, action_id),
        )


def _recovery_request(
    desired: ActionRequest, plan: RecoveryPlan
) -> ActionRequest:
    identity = f"{plan.failure_key}:{plan.episode_number}:{plan.action_type.value}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return ActionRequest(
        action_id=f"action-{digest[:24]}",
        run_id=desired.run_id,
        run_revision=desired.run_revision,
        policy=desired.policy,
        phase=desired.phase,
        action_type=plan.action_type,
        idempotency_key=f"recovery:{digest}",
        repo_relative_root=desired.repo_relative_root,
        task_id=desired.task_id,
        next_action=desired.next_action,
        payload={
            "recovery_failure_key": plan.failure_key,
            "recovery_episode": plan.episode_number,
            "recovery_tier": plan.tier,
            "recovery_strategy": plan.strategy,
            "recovery_for_action_type": ActionType.RUN_GENERATOR.value
            if plan.action_type is ActionType.RECOVER_GENERATOR_RESULT
            else desired.action_type.value,
            "source_action_id": plan.source_action_id or desired.action_id,
        },
    )


def recovery_action_for_run(
    store: Any,
    run: Mapping[str, Any],
    desired: ActionRequest,
) -> ActionRequest | None:
    """Return the currently eligible normal, retry, alternate, or Reviewer action."""
    actions = [
        row
        for row in store.fetch_all("actions")
        if row.get("run_id") == desired.run_id
    ]
    _close_completed_action_episodes(store, run, actions)

    failed_alternates = [
        row
        for row in actions
        if row.get("status") == "failed"
        and _action_payload(row).get("recovery_failure_key")
        and row.get("action_type")
        in {
            ActionType.RECOVER_GENERATOR_RESULT.value,
            ActionType.RUN_ALTERNATE_RECOVERY.value,
        }
    ]
    if failed_alternates:
        alternate = max(
            failed_alternates,
            key=lambda row: (str(row.get("updated_at") or ""), str(row["action_id"])),
        )
        attempt = _latest_attempt(store, str(alternate["action_id"]))
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

    source = next(
        (row for row in actions if row.get("action_id") == desired.action_id),
        None,
    )
    if source is None or source.get("status") != "failed":
        return desired
    attempt = _latest_attempt(store, desired.action_id)
    if attempt is None:
        return None
    plan = plan_recovery(
        store,
        run,
        {**attempt, "action_type": desired.action_type.value},
        jitter=lambda: 0.0,
    )
    if plan.tier == 1:
        if not _retry_is_due(store, plan.retry_at):
            return None
        _requeue_failed_action(store, desired.action_id, plan.tier)
        return desired
    return _recovery_request(desired, plan)
