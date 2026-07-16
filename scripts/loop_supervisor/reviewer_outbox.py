"""Revision-bound, resumable application of validated Reviewer decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import json
from pathlib import Path, PurePosixPath
import secrets
import time
from typing import Any

from scripts.harness_loop_agents import validate_owned_regular_file
from scripts.harness_loop_contracts import validate_run_payload

from .models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    ReviewDecision,
    SupervisorReview,
)
from .registry import review_application_for, transition_for
from .reviewer_runtime import ActionLeaseGuard
from .reviewer_safety import require_review_safety_clear
from .store import LeaseError, SupervisorStore


ApplicationCutpoint = Callable[[str, str], None]
_PROJECTION_CONSISTENCY_ATTEMPTS = 20
_PROJECTION_CONSISTENCY_RETRY_SECONDS = 0.01


class ReviewSupersededError(RuntimeError):
    """The accepted revision-bound decision no longer matches a canonical target."""


def resumable_review_application_target_ids(
    store: SupervisorStore,
    review: SupervisorReview,
) -> tuple[str, ...]:
    """Validate the immutable target and evidence anchors before cold recovery."""
    if review.decision is ReviewDecision.CONTINUE:
        if store.review_application_targets(review.review_id):
            raise LeaseError("continue review must not have application targets")
        return ()

    applications = {
        str(row["review_id"]): row for row in store.fetch_all("review_applications")
    }
    if review.review_id not in applications:
        if store.review_application_targets(review.review_id):
            raise LeaseError("review application targets exist without an application")
        for run_id in review.affected_run_ids:
            _prepare_target(store, review, run_id)
        return tuple(review.affected_run_ids)

    targets = store.review_application_targets_for_recovery(review.review_id)
    target_ids = tuple(str(target["run_id"]) for target in targets)
    if set(target_ids) != set(review.affected_run_ids):
        raise LeaseError("review application target set changed")
    for target in targets:
        run_id = str(target["run_id"])
        reviewed = review.reviewed_runs.get(run_id)
        if not isinstance(reviewed, Mapping):
            raise LeaseError("review application target is outside accepted evidence scope")
        expected_revision = int(target["expected_revision"])
        expected_fingerprint = str(target["expected_fingerprint"])
        if (
            reviewed.get("revision") != expected_revision
            or reviewed.get("state_fingerprint") != expected_fingerprint
        ):
            raise LeaseError("review application target revision changed")
        request = _request_for_stored_target(store, target)
        payload = request.payload
        if (
            request.run_id != run_id
            or request.run_revision != expected_revision
            or payload.get("review_id") != review.review_id
            or payload.get("review_decision") != review.decision.value
            or payload.get("expected_revision") != expected_revision
            or payload.get("expected_fingerprint") != expected_fingerprint
        ):
            raise LeaseError("review application target action changed")
    return target_ids


def apply_review_outbox(
    store: SupervisorStore,
    review: SupervisorReview,
    *,
    lease_checkpoint: Callable[[], None],
    application_cutpoint: ApplicationCutpoint | None = None,
) -> list[ActionRequest]:
    cutpoint = application_cutpoint or (lambda _stage, _run_id: None)
    lease_checkpoint()
    if review.decision is ReviewDecision.CONTINUE:
        _ensure_review_row(store, review)
        lease_checkpoint()
        store.set_review_status(review.review_id, "review_complete")
        return []

    existing_targets = store.review_application_targets(review.review_id)
    if existing_targets:
        if {str(row["run_id"]) for row in existing_targets} != set(
            review.affected_run_ids
        ):
            raise ValueError("review application target set changed")
        requests = [_request_for_stored_target(store, row) for row in existing_targets]
    else:
        try:
            prepared = [
                _prepare_target(store, review, run_id)
                for run_id in review.affected_run_ids
            ]
        except ReviewSupersededError as exc:
            store.supersede_review_application(review.review_id, reason=str(exc))
            raise
        requests = [item[0] for item in prepared]
        _ensure_review_row(store, review, status="review_applying")
        lease_checkpoint()
        store.prepare_review_application(
            review_id=review.review_id,
            decision=review.decision.value,
            targets=[(request, target) for request, target, _root, _path in prepared],
        )

    for request in requests:
        target = next(
            row
            for row in store.review_application_targets(review.review_id)
            if row["run_id"] == request.run_id
        )
        if target["status"] == "applied":
            continue
        lease_checkpoint()
        try:
            _apply_target(
                store,
                review,
                request,
                target,
                lease_checkpoint=lease_checkpoint,
                cutpoint=cutpoint,
            )
        except ReviewSupersededError as exc:
            store.supersede_review_application(review.review_id, reason=str(exc))
            raise
    return requests


def _ensure_review_row(
    store: SupervisorStore,
    review: SupervisorReview,
    *,
    status: str = "review_applying",
) -> None:
    rows = {str(row["review_id"]): row for row in store.fetch_all("reviews")}
    if review.review_id in rows:
        if rows[review.review_id]["status"] != "review_complete":
            store.set_review_status(review.review_id, status)
        return
    store.record_review(
        review_id=review.review_id,
        trigger="direct_application",
        status=status,
        decision=review.decision.value,
        summary=review.summary,
    )


def _prepare_target(
    store: SupervisorStore,
    review: SupervisorReview,
    run_id: str,
) -> tuple[ActionRequest, dict[str, Any], Path, Path]:
    run, execution_root, run_path, payload = _stable_target_snapshot(store, run_id)
    actual_revision = _revision(payload)
    actual_fingerprint = _fingerprint(payload)
    reviewed = review.reviewed_runs.get(run_id)
    if reviewed:
        expected_revision = int(reviewed["revision"])
        expected_fingerprint = str(reviewed["state_fingerprint"])
    else:
        expected_revision = actual_revision
        expected_fingerprint = actual_fingerprint
    _validate_target_payload(payload, run_id)
    projected_revision = int(run["revision"])
    projected_fingerprint = str(run.get("state_fingerprint") or "")
    if (
        projected_revision == expected_revision
        and projected_fingerprint == expected_fingerprint
        and actual_revision == expected_revision
        and actual_fingerprint == expected_fingerprint
    ):
        pass
    elif (
        projected_revision == actual_revision
        and projected_fingerprint == actual_fingerprint
    ):
        raise ReviewSupersededError(f"review target advanced after evidence: {run_id}")
    else:
        raise LeaseError(f"review target canonical state is corrupt: {run_id}")
    rule = review_application_for(
        review.decision,
        policy=str(run["policy"]),
        run_kind=str(payload.get("run_kind") or "single"),
    )
    identity = {
        "review_id": review.review_id,
        "run_id": run_id,
        "expected_revision": expected_revision,
        "decision": review.decision.value,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    request = ActionRequest(
        action_id=f"action-review-decision-{digest[:16]}",
        run_id=run_id,
        run_revision=expected_revision,
        policy=str(run["policy"]),
        phase=str(run["phase"]),
        action_type=rule.action_type,
        idempotency_key=f"review-decision:{digest}",
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=execution_root.relative_to(store.project_root).as_posix()
        or ".",
        task_id=f"review:{review.review_id}:{run_id}",
        next_action=review.decision.value,
        payload={
            "review_id": review.review_id,
            "review_decision": review.decision.value,
            "expected_revision": expected_revision,
            "expected_fingerprint": expected_fingerprint,
            "decision_provenance_token": (
                secrets.token_urlsafe(32)
                if review.decision is ReviewDecision.ASK_USER
                else ""
            ),
            "worker_executable": False,
        },
    )
    target = {
        "expected_revision": expected_revision,
        "expected_fingerprint": expected_fingerprint,
        "source_phase": str(run["phase"]),
        "target_phase": rule.target_phase,
        "target_next_action": rule.target_next_action,
        "target_last_result": rule.target_last_result,
    }
    if review.decision is not ReviewDecision.ASK_USER:
        expected_post_write = _updated_payload(payload, review, target)
        expected_post_write["state_revision"] = expected_revision + 1
        target["expected_post_write_fingerprint"] = _fingerprint(expected_post_write)
    return request, target, execution_root, run_path


def _apply_target(
    store: SupervisorStore,
    review: SupervisorReview,
    request: ActionRequest,
    target: Mapping[str, Any],
    *,
    lease_checkpoint: Callable[[], None],
    cutpoint: ApplicationCutpoint,
) -> None:
    owner_id = f"supervisor-review-application-{review.review_id}"
    run, _execution_root, _run_path, payload = _stable_target_snapshot(
        store,
        request.run_id,
        review=review,
        target=target,
    )
    _review_application_state(run, payload, review, target, request.run_id)
    action = store.get_action(request.action_id)
    if action.status == "pending":
        action = store.claim_pending_action(
            request.action_id,
            owner_id,
            lease_seconds=120,
            expected_queue_owner=ActionOwner.SUPERVISOR,
        )
        if action is None:
            raise RuntimeError("review application action could not be claimed")
    elif action.status not in {"leased", "running"} or action.lease_owner != owner_id:
        raise RuntimeError("review application action has incompatible lease state")

    with ActionLeaseGuard(
        store,
        action_id=request.action_id,
        owner_id=owner_id,
        lease_seconds=120,
        heartbeat_seconds=30,
        safety_checkpoint=lambda: require_review_safety_clear(store),
    ) as guard:
        lease_checkpoint()
        guard.checkpoint()
        run, execution_root, run_path, payload = _stable_target_snapshot(
            store,
            request.run_id,
            review=review,
            target=target,
        )
        application_state = _review_application_state(
            run,
            payload,
            review,
            target,
            request.run_id,
        )
        if review.decision is ReviewDecision.ASK_USER:
            provenance_token = str(
                request.payload.get("decision_provenance_token") or ""
            )
            if not provenance_token:
                raise ValueError("ask_user action lacks decision provenance token")
            store.open_user_decision(
                scope="run",
                run_id=request.run_id,
                failure_key=f"review:{review.review_id}:{request.run_id}",
                summary=review.summary,
                required_decision="Resolve the Reviewer question for this run.",
                source_action_id=request.action_id,
                source_action_owner=owner_id,
                provenance_token=provenance_token,
            )
            applied_revision = int(target["expected_revision"])
            artifacts: tuple[str, ...] = ()
        else:
            expected_revision = int(target["expected_revision"])
            expected_fingerprint = str(target["expected_fingerprint"])
            expected_post_write_fingerprint = str(
                target.get("expected_post_write_fingerprint") or ""
            )
            if not expected_post_write_fingerprint:
                raise LeaseError(
                    f"review application lacks immutable post-write state: {request.run_id}"
                )
            current_revision = _revision(payload)
            if application_state == "prewrite":
                updated = _updated_payload(payload, review, target)
                cutpoint("before_file_write", request.run_id)
                guard.checkpoint()
                lease_checkpoint()
                from .reconciler import atomic_save_run

                with guard.suspend_safety():
                    try:
                        saved = atomic_save_run(
                            execution_root,
                            request.run_id,
                            updated,
                            expected_revision=expected_revision,
                            expected_fingerprint=expected_fingerprint,
                        )
                    except ValueError as exc:
                        (
                            run,
                            execution_root,
                            run_path,
                            saved,
                        ) = _reclassify_cas_failure(
                            store,
                            review,
                            target,
                            request.run_id,
                            exc,
                        )
                    _project_saved_run(store, run, saved)
                if _fingerprint(saved) != expected_post_write_fingerprint:
                    raise LeaseError(
                        f"review application wrote unexpected canonical state: {request.run_id}"
                    )
                applied_revision = int(saved["state_revision"])
                canonical_payload = saved
            elif application_state == "postwrite":
                applied_revision = current_revision
                canonical_payload = payload
            if (
                current_revision != expected_revision
                and not _projection_matches_payload(run, canonical_payload)
            ):
                _project_saved_run(store, run, canonical_payload)
            artifacts = (run_path.relative_to(execution_root).as_posix(),)
        cutpoint("after_file_write", request.run_id)
        guard.checkpoint()
        lease_checkpoint()
        store.complete_review_application_target(
            review_id=review.review_id,
            run_id=request.run_id,
            action_id=request.action_id,
            owner_id=owner_id,
            result=ActionResult(
                result_class=ActionResultClass.SUCCESS,
                summary=f"applied Reviewer {review.decision.value} decision",
                artifact_paths=artifacts,
                checkpoint=f"review-decision:{review.decision.value}",
            ),
            applied_revision=applied_revision,
        )


def _project_saved_run(
    store: SupervisorStore,
    previous: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> None:
    from .reconciler import _STATE_SUMMARY_KEYS

    summary = previous.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError("run projection summary is invalid")
    phase = str(payload.get("phase") or "")
    next_action = str(payload.get("next_action") or "")
    transition = transition_for(
        str(payload.get("policy") or previous["policy"]),
        phase,
        next_action,
    )
    resolved_lineage_id = str(
        payload.get("loop_lineage_id")
        or previous.get("loop_lineage_id")
        or previous["run_id"]
    )
    summary_state = {key: payload.get(key) for key in _STATE_SUMMARY_KEYS}
    summary_state["loop_lineage_id"] = resolved_lineage_id
    store.upsert_run_projection(
        {
            "run_id": str(previous["run_id"]),
            "revision": _revision(payload),
            "repo_relative_root": str(previous.get("repo_relative_root") or "."),
            "loop_lineage_id": resolved_lineage_id,
            "parent_run_id": str(previous.get("parent_run_id") or ""),
            "policy": str(payload.get("policy") or previous["policy"]),
            "phase": phase,
            "status": "terminal" if transition.terminal else "actionable",
            "state_fingerprint": _fingerprint(payload),
            "summary": json.dumps(
                summary_state,
                sort_keys=True,
                separators=(",", ":"),
            ),
            "artifact_refs": summary.get("artifact_refs", []),
        }
    )


def _updated_payload(
    payload: Mapping[str, Any],
    review: SupervisorReview,
    target: Mapping[str, Any],
) -> dict[str, Any]:
    updated = dict(payload)
    directives = list(updated.get("reviewer_directives") or [])
    directive = {
        "review_id": review.review_id,
        "decision": review.decision.value,
        "summary": review.summary,
        "evidence_refs": list(review.evidence_refs),
    }
    if directive not in directives:
        directives.append(directive)
    updated["reviewer_directives"] = directives
    updated["phase"] = str(target["target_phase"])
    updated["next_action"] = str(target["target_next_action"])
    updated["last_result"] = str(target["target_last_result"])
    return updated


def _already_applied(
    payload: Mapping[str, Any],
    review: SupervisorReview,
    target: Mapping[str, Any],
) -> bool:
    return (
        _review_directive_applied(payload, review)
        and payload.get("phase") == target["target_phase"]
        and payload.get("next_action") == target["target_next_action"]
    )


def _review_directive_applied(
    payload: Mapping[str, Any],
    review: SupervisorReview,
) -> bool:
    directives = payload.get("reviewer_directives")
    directive = {
        "review_id": review.review_id,
        "decision": review.decision.value,
        "summary": review.summary,
        "evidence_refs": list(review.evidence_refs),
    }
    return isinstance(directives, list) and directive in directives


def _validate_target_payload(payload: Mapping[str, Any], run_id: str) -> None:
    try:
        validate_run_payload(payload)
    except (TypeError, ValueError) as exc:
        raise LeaseError(f"review target canonical state is corrupt: {run_id}") from exc
    if payload.get("run_id") != run_id:
        raise LeaseError(f"review target canonical state is corrupt: {run_id}")


def _review_application_state(
    run: Mapping[str, Any],
    payload: Mapping[str, Any],
    review: SupervisorReview,
    target: Mapping[str, Any],
    run_id: str,
) -> str:
    _validate_target_payload(payload, run_id)
    actual_revision = _revision(payload)
    actual_fingerprint = _fingerprint(payload)
    projected_revision = int(run["revision"])
    projected_fingerprint = str(run.get("state_fingerprint") or "")
    expected_revision = int(target["expected_revision"])
    expected_fingerprint = str(target["expected_fingerprint"])
    expected_post_write_fingerprint = str(
        target.get("expected_post_write_fingerprint") or ""
    )
    if (
        actual_revision == expected_revision
        and actual_fingerprint == expected_fingerprint
        and projected_revision == expected_revision
        and projected_fingerprint == expected_fingerprint
    ):
        return "prewrite"
    if (
        expected_post_write_fingerprint
        and actual_revision == expected_revision + 1
        and actual_fingerprint == expected_post_write_fingerprint
        and _already_applied(payload, review, target)
        and (
            (
                projected_revision == expected_revision
                and projected_fingerprint == expected_fingerprint
            )
            or (
                projected_revision == actual_revision
                and projected_fingerprint == actual_fingerprint
            )
        )
    ):
        return "postwrite"
    if (
        expected_post_write_fingerprint
        and actual_revision > expected_revision + 1
        and projected_revision == actual_revision
        and projected_fingerprint == actual_fingerprint
        and _review_directive_applied(payload, review)
    ):
        return "postwrite"
    if (
        projected_revision == actual_revision
        and projected_fingerprint == actual_fingerprint
    ):
        raise ReviewSupersededError(f"review target advanced before application: {run_id}")
    raise LeaseError(f"review target canonical state is corrupt: {run_id}")


def _stable_target_snapshot(
    store: SupervisorStore,
    run_id: str,
    *,
    review: SupervisorReview | None = None,
    target: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], Path, Path, dict[str, Any]]:
    last_file_ahead: tuple[Mapping[str, Any], Path, Path, dict[str, Any]] | None = None
    for attempt in range(_PROJECTION_CONSISTENCY_ATTEMPTS):
        before = store.get_run(run_id)
        execution_root, run_path, payload = _target_run(store, before)
        after = store.get_run(run_id)
        if _projection_anchor(before) != _projection_anchor(after):
            if attempt + 1 < _PROJECTION_CONSISTENCY_ATTEMPTS:
                time.sleep(_PROJECTION_CONSISTENCY_RETRY_SECONDS)
            continue
        snapshot = (after, execution_root, run_path, payload)
        if _projection_matches_payload(after, payload):
            return snapshot
        if (
            review is not None
            and target is not None
            and _is_anchored_reviewer_postwrite(after, payload, review, target, run_id)
        ):
            return snapshot
        if not _is_plausible_projection_lag(after, payload, run_id):
            return snapshot
        last_file_ahead = snapshot
        if attempt + 1 < _PROJECTION_CONSISTENCY_ATTEMPTS:
            time.sleep(_PROJECTION_CONSISTENCY_RETRY_SECONDS)
    if last_file_ahead is not None:
        return last_file_ahead
    raise LeaseError(f"review target canonical state changed during read: {run_id}")


def _projection_matches_payload(
    run: Mapping[str, Any], payload: Mapping[str, Any]
) -> bool:
    try:
        return (
            int(run["revision"]) == _revision(payload)
            and str(run.get("state_fingerprint") or "") == _fingerprint(payload)
        )
    except (TypeError, ValueError):
        return False


def _is_plausible_projection_lag(
    run: Mapping[str, Any], payload: Mapping[str, Any], run_id: str
) -> bool:
    try:
        _validate_target_payload(payload, run_id)
        return _revision(payload) == int(run["revision"]) + 1
    except (LeaseError, TypeError, ValueError):
        return False


def _is_anchored_reviewer_postwrite(
    run: Mapping[str, Any],
    payload: Mapping[str, Any],
    review: SupervisorReview,
    target: Mapping[str, Any],
    run_id: str,
) -> bool:
    try:
        return (
            _review_application_state(run, payload, review, target, run_id)
            == "postwrite"
        )
    except (LeaseError, ReviewSupersededError, TypeError, ValueError):
        return False


def _projection_anchor(run: Mapping[str, Any]) -> tuple[int, str, str]:
    return (
        int(run["revision"]),
        str(run.get("state_fingerprint") or ""),
        str(run.get("repo_relative_root") or "."),
    )


def _reclassify_cas_failure(
    store: SupervisorStore,
    review: SupervisorReview,
    target: Mapping[str, Any],
    run_id: str,
    error: ValueError,
) -> tuple[Mapping[str, Any], Path, Path, dict[str, Any]]:
    try:
        run, execution_root, run_path, payload = _stable_target_snapshot(
            store,
            run_id,
            review=review,
            target=target,
        )
    except LeaseError:
        raise
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as state_error:
        raise LeaseError(
            f"review target canonical state is corrupt after CAS failure: {run_id}"
        ) from state_error
    state = _review_application_state(run, payload, review, target, run_id)
    if state == "postwrite":
        return run, execution_root, run_path, payload
    raise LeaseError(
        f"review target canonical state is corrupt after CAS failure: {run_id}"
    ) from error


def _request_for_stored_target(
    store: SupervisorStore,
    target: Mapping[str, Any],
) -> ActionRequest:
    row = next(
        item
        for item in store.fetch_all("actions")
        if item["action_id"] == target["action_id"]
    )
    return ActionRequest(
        action_id=str(row["action_id"]),
        run_id=str(row["run_id"]),
        run_revision=int(row["run_revision"]),
        policy=str(row["policy"]),
        phase=str(row["phase"]),
        action_type=ActionType(str(row["action_type"])),
        idempotency_key=str(row["idempotency_key"]),
        queue_owner=ActionOwner(str(row["queue_owner"])),
        not_before=str(row["not_before"]),
        repo_relative_root=str(row["repo_relative_root"]),
        task_id=str(row["task_id"]),
        next_action=str(row["next_action"]),
        payload=json.loads(str(row["payload_json"])),
    )


def _target_run(
    store: SupervisorStore,
    run: Mapping[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    summary = run.get("summary")
    refs = summary.get("artifact_refs", []) if isinstance(summary, Mapping) else []
    from .models import validate_repo_relative_root

    repo_relative_root = validate_repo_relative_root(
        run.get("repo_relative_root", ".")
    )
    expected_parts = (
        *PurePosixPath(repo_relative_root).parts,
        ".codex",
        "loop-runs",
        str(run["run_id"]),
        "run.json",
    )
    canonical_refs = [
        value
        for value in refs
        if isinstance(value, str)
        and not PurePosixPath(value).is_absolute()
        and PurePosixPath(value).as_posix() == value
        and tuple(PurePosixPath(value).parts) == expected_parts
    ]
    if len(canonical_refs) != 1:
        raise ValueError(f"run projection lacks canonical run.json evidence: {run['run_id']}")
    relative = PurePosixPath(canonical_refs[0])
    path = store.project_root.joinpath(*relative.parts)
    safe = validate_owned_regular_file(store.project_root, path, "Reviewer target run")
    payload = json.loads(safe.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Reviewer target run must be an object")
    execution_root = store.project_root.joinpath(*PurePosixPath(repo_relative_root).parts).resolve()
    execution_root.relative_to(store.project_root)
    return execution_root, safe, payload


def repair_resumable_review_projection(
    store: SupervisorStore,
    review: SupervisorReview,
) -> None:
    """Repair only the durable file-write/projection-persist cutpoint."""
    for target in store.review_application_targets(review.review_id):
        if str(target["status"]) == "applied":
            continue
        request = _request_for_stored_target(store, target)
        run = store.get_run(request.run_id)
        if str(run.get("repo_relative_root") or ".") != request.repo_relative_root:
            raise LeaseError(
                f"review outbox source projection is corrupt: {request.run_id}"
            )
        run, _execution_root, _run_path, payload = _stable_target_snapshot(
            store,
            request.run_id,
            review=review,
            target=target,
        )
        state = _review_application_state(
            run,
            payload,
            review,
            target,
            request.run_id,
        )
        if state == "prewrite":
            continue
        _project_saved_run(store, run, payload)


def _revision(payload: Mapping[str, Any]) -> int:
    value = payload.get("state_revision", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("run state_revision must be a non-negative int")
    return value


def _fingerprint(payload: Mapping[str, Any]) -> str:
    from .reconciler import _state_fingerprint

    return _state_fingerprint(payload)
