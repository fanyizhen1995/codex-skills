"""Project-global read-only Reviewer scheduling, evidence, and decisions."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any
from uuid import uuid4

from scripts.harness_loop_agents import run_codex_prompt, validate_owned_regular_file
from scripts.harness_loop_contracts import validate_run_id

from .models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    ReviewDecision,
    ReviewEvidenceBundle,
    ReviewerExecutionResult,
    SupervisorReview,
)
from .registry import reviewer_schedule_transition
from .reviewer_runtime import ActionLeaseGuard
from .reviewer_safety import ReviewSafetyGate, evaluate_review_safety_gate
from .reviewer_outbox import ApplicationCutpoint, apply_review_outbox
from .store import LeaseError, SupervisorStore


ALLOWED_REVIEW_DECISIONS = frozenset(decision.value for decision in ReviewDecision)
ALLOWED_SKILL_RECOMMENDATIONS = frozenset({"keep", "merge", "delete_candidate"})
REVIEW_INTERVAL_PARENTS = 2
REVIEW_COALESCE_WINDOW = timedelta(minutes=10)
REVIEW_TIMEOUT_SECONDS = 300
_HASH_REF = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
_FINDING_STATUSES = frozenset({"open", "closed", "accepted_risk"})
_FINDING_SEVERITIES = frozenset({"must_fix", "should_fix", "observe"})
_SKILL_SCAN_EXCLUDED_DIRS = frozenset(
    {".git", ".codex", ".worktrees", "node_modules", "dist", "build", "__pycache__"}
)
_REVIEW_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "review_id",
        "scope",
        "decision",
        "affected_run_ids",
        "summary",
        "evidence_refs",
        "findings",
        "skill_governance",
        "next_review_after_parent_tasks",
    }
)


@dataclass(frozen=True)
class ReviewerContext:
    project_root: Path
    store: SupervisorStore
    triggering_lineages: tuple[str, ...]
    deterministic_safety_gates_pass: bool = False
    timeout_seconds: int = REVIEW_TIMEOUT_SECONDS
    source_action_id: str = ""

    def __post_init__(self) -> None:
        root = Path(self.project_root).resolve()
        if self.store.project_root != root:
            raise ValueError("Reviewer store does not belong to project_root")
        lineages = tuple(sorted(set(self.triggering_lineages)))
        if not lineages or not all(isinstance(value, str) and value for value in lineages):
            raise ValueError("triggering_lineages must contain non-empty strings")
        if not isinstance(self.deterministic_safety_gates_pass, bool):
            raise TypeError("deterministic_safety_gates_pass must be a bool")
        if (
            not isinstance(self.timeout_seconds, int)
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive int")
        if not isinstance(self.source_action_id, str):
            raise TypeError("source_action_id must be a string")
        object.__setattr__(self, "project_root", root)
        object.__setattr__(self, "triggering_lineages", lineages)


@dataclass(frozen=True)
class _DueLineage:
    lineage_id: str
    due_at: datetime
    cadence_position: int
    representative_run: Mapping[str, Any]


def review_due_lineages(store: SupervisorStore, now: datetime) -> list[str]:
    """Return lineages with two unreviewed semantic-parent completions."""
    current = _coerce_datetime(now)
    return [item.lineage_id for item in _due_lineage_states(store, current)]


def schedule_due_reviews(
    store: SupervisorStore,
    *,
    now: datetime | None = None,
) -> list[ActionRequest]:
    """Coalesce due lineages and queue project-global non-Worker reviews."""
    current = _coerce_datetime(now or store.current_time())
    due = _due_lineage_states(store, current)
    groups: list[list[_DueLineage]] = []
    for item in due:
        if not groups or item.due_at - groups[-1][0].due_at > REVIEW_COALESCE_WINDOW:
            groups.append([item])
        else:
            groups[-1].append(item)

    requests: list[ActionRequest] = []
    for group in groups:
        lineages = sorted(item.lineage_id for item in group)
        positions = {item.lineage_id: item.cadence_position for item in group}
        due_at = min(item.due_at for item in group)
        not_before = due_at + REVIEW_COALESCE_WINDOW
        representative = min(group, key=lambda item: item.lineage_id).representative_run
        pending = _pending_review_for_window(store, due_at)
        if pending is not None:
            pending_payload = _json_object(pending.get("payload"))
            lineages = sorted(
                set(lineages) | set(_string_list(pending_payload.get("triggering_lineages")))
            )
            pending_positions = pending.get("positions")
            if isinstance(pending_positions, Mapping):
                positions.update(
                    {
                        str(key): int(value)
                        for key, value in pending_positions.items()
                        if isinstance(key, str)
                        and isinstance(value, int)
                        and not isinstance(value, bool)
                    }
                )
            pending_due_at = _coerce_datetime(str(pending.get("due_at") or ""))
            due_at = min(due_at, pending_due_at)
            not_before = _coerce_datetime(str(pending.get("not_before") or ""))
            representative = store.get_run(str(pending["run_id"]))
        rule = reviewer_schedule_transition()
        identity = {
            "trigger": "regular_cadence",
            "triggering_lineages": lineages,
            "cadence_positions": positions,
        }
        reservation_id = (
            str(pending["reservation_id"])
            if pending is not None
            else "review-reservation-"
            + hashlib.sha256(_canonical_json(identity)).hexdigest()[:24]
        )
        payload = {
            **identity,
            "due_at": due_at.isoformat(),
            "not_before": not_before.isoformat(),
            "reservation_id": reservation_id,
            "mutates_git": rule.mutates_git,
            "worker_executable": rule.worker_executable,
        }
        if pending is not None:
            request = ActionRequest(
                action_id=str(pending["action_id"]),
                run_id=str(pending["run_id"]),
                run_revision=int(pending["run_revision"]),
                policy=str(pending["policy"]),
                phase=str(pending["phase"]),
                action_type=rule.action_type,
                idempotency_key=str(pending["idempotency_key"]),
                queue_owner=ActionOwner.REVIEWER,
                not_before=not_before.isoformat(),
                repo_relative_root=str(pending["repo_relative_root"]),
                task_id=str(pending["task_id"]),
                next_action="supervisor_reviewer",
                payload=payload,
            )
            store.coalesce_review_reservation(
                request,
                reservation_id=reservation_id,
                lineage_positions=positions,
            )
        else:
            digest = hashlib.sha256(_canonical_json(identity)).hexdigest()
            request = ActionRequest(
                action_id=f"action-review-{digest[:20]}",
                run_id=str(representative["run_id"]),
                run_revision=int(representative["revision"]),
                policy=str(representative["policy"]),
                phase=str(representative["phase"]),
                action_type=rule.action_type,
                idempotency_key=f"review-cadence:{digest}",
                queue_owner=ActionOwner.REVIEWER,
                not_before=not_before.isoformat(),
                repo_relative_root=".",
                task_id=f"review:{digest[:24]}",
                next_action="supervisor_reviewer",
                payload=payload,
            )
            store.reserve_review_action(
                request,
                reservation_id=reservation_id,
                lineage_positions=positions,
                due_at=due_at,
                not_before=not_before,
                priority=25,
            )
        requests.append(request)
    return requests


def _pending_review_for_window(
    store: SupervisorStore,
    due_at: datetime,
) -> Mapping[str, Any] | None:
    candidates: list[tuple[datetime, Mapping[str, Any]]] = []
    for row in store.pending_review_reservations():
        payload = _json_object(row.get("payload"))
        if payload.get("trigger") != "regular_cadence":
            continue
        try:
            pending_due_at = _coerce_datetime(str(row.get("due_at") or ""))
        except (TypeError, ValueError):
            continue
        if abs(due_at - pending_due_at) <= REVIEW_COALESCE_WINDOW:
            candidates.append((pending_due_at, row))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], str(item[1]["action_id"])))[1]


def build_review_evidence(
    project_root: Path,
    store: SupervisorStore,
    triggering_lineages: Sequence[str],
) -> ReviewEvidenceBundle:
    """Build and hash the project-global evidence accepted by Reviewer."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("Reviewer store does not belong to project_root")
    lineages = tuple(sorted(set(str(value) for value in triggering_lineages if str(value))))
    if not lineages:
        raise ValueError("triggering_lineages must not be empty")

    runs = _decoded_store_rows(store, "runs")
    run_payloads = _run_payloads(root, runs)
    completions = _semantic_parent_completions(runs, run_payloads)
    reviewed_positions = _reviewed_cadence_positions(store)
    cadence_positions = {lineage: len(completions.get(lineage, ())) for lineage in lineages}
    skill_snapshot = _build_skill_snapshot(root, run_payloads, store)
    agent_summaries = _agent_evaluator_summaries(root, run_payloads)
    generated_at = store.format_time(store.current_time())
    from .reconciler import _state_fingerprint

    objective_constraints = []
    for row in sorted(runs, key=lambda item: str(item.get("run_id") or "")):
        run_id = str(row.get("run_id") or "")
        payload = run_payloads.get(run_id, {})
        objective_constraints.append(
            {
                "run_id": run_id,
                "loop_lineage_id": str(row.get("loop_lineage_id") or run_id),
                "objective": str(payload.get("requirement") or payload.get("objective") or ""),
                "constraints": _string_list(payload.get("constraints")),
                "stop_conditions": _string_list(payload.get("stop_conditions")),
                "policy": str(row.get("policy") or ""),
                "phase": str(row.get("phase") or ""),
                "revision": int(row.get("revision") or 0),
                "state_fingerprint": str(row.get("state_fingerprint") or "")
                or _state_fingerprint(payload),
            }
        )

    parent_progress = []
    for lineage_id in sorted(completions):
        items = completions[lineage_id]
        reviewed = reviewed_positions.get(lineage_id, 0)
        parent_progress.append(
            {
                "loop_lineage_id": lineage_id,
                "completed_total": len(items),
                "reviewed_position": reviewed,
                "completed_since_last_review": [item[0] for item in items[reviewed:]],
                "triggering": lineage_id in lineages,
            }
        )

    evidence: dict[str, Any] = {
        "objective_constraints": objective_constraints,
        "parent_progress": parent_progress,
        "agent_evaluator_summaries": agent_summaries,
        "commits_pushes": _commit_push_evidence(runs, run_payloads, store),
        "domain_output_metrics": _domain_output_metrics(agent_summaries),
        "failures_recoveries": {
            "failures": _decoded_store_rows(store, "failures"),
            "recovery_actions": [
                row
                for row in _decoded_store_rows(store, "actions")
                if int(row.get("recovery_tier") or 0) > 0
                or str(row.get("action_type") or "").startswith("recover_")
                or row.get("action_type") == ActionType.RUN_ALTERNATE_RECOVERY.value
            ],
            "attempts": _decoded_store_rows(store, "action_attempts"),
        },
        "services_freshness": {
            "services": _decoded_store_rows(store, "services"),
            "freshness_checks": _decoded_store_rows(store, "freshness_checks"),
        },
        "user_decisions": {
            "decisions": _decoded_store_rows(store, "user_decisions"),
            "blocked_run_ids": sorted(
                {
                    str(row.get("run_id") or "")
                    for row in store.fetch_all("user_decisions")
                    if row.get("status") == "open" and row.get("scope") == "run"
                }
            ),
        },
        "skill_governance": skill_snapshot,
        "prior_findings": _prior_finding_evidence(root, store),
    }
    evidence_hashes = {
        name: f"sha256:{hashlib.sha256(_canonical_json({'section': name, 'value': value})).hexdigest()}"
        for name, value in evidence.items()
    }
    bundle_body = {
        "triggering_lineages": lineages,
        "cadence_positions": cadence_positions,
        "evidence_hashes": evidence_hashes,
    }
    bundle = ReviewEvidenceBundle(
        generated_at=generated_at,
        triggering_lineages=lineages,
        cadence_positions=cadence_positions,
        evidence=evidence,
        evidence_hashes=evidence_hashes,
        bundle_hash=f"sha256:{hashlib.sha256(_canonical_json(bundle_body)).hexdigest()}",
    )
    return bundle


def validate_review_payload(
    payload: Mapping[str, Any],
    *,
    expected_evidence_hashes: Sequence[str] | None = None,
    allowed_run_ids: Sequence[str] | None = None,
    allowed_skill_paths: Sequence[str] | None = None,
    reviewed_runs: Mapping[str, Mapping[str, Any]] | None = None,
    existing_findings: Sequence[Mapping[str, Any]] | None = None,
) -> SupervisorReview:
    """Validate one untrusted Reviewer candidate before Supervisor accepts it."""
    if not isinstance(payload, Mapping):
        raise TypeError("review payload must be an object")
    unsupported = set(payload) - _REVIEW_PAYLOAD_KEYS
    missing = _REVIEW_PAYLOAD_KEYS - set(payload)
    if unsupported:
        raise ValueError(f"review payload contains unsupported or prohibited keys: {sorted(unsupported)}")
    if missing:
        raise ValueError(f"review payload is missing keys: {sorted(missing)}")
    if payload.get("schema_version") != 1:
        raise ValueError("review schema_version must be 1")
    review_id = _required_string(payload.get("review_id"), "review_id")
    validate_run_id(review_id)
    if payload.get("scope") != "project":
        raise ValueError("review scope must be project")
    try:
        decision = ReviewDecision(str(payload.get("decision") or ""))
    except ValueError as exc:
        raise ValueError("review decision is not allowed") from exc

    affected = _validated_run_ids(payload.get("affected_run_ids"), "affected_run_ids")
    if decision is not ReviewDecision.CONTINUE and not affected:
        raise ValueError(f"{decision.value} decision requires affected_run_ids")
    if allowed_run_ids is not None:
        unknown = set(affected) - set(allowed_run_ids)
        if unknown:
            raise ValueError(f"review references unknown affected runs: {sorted(unknown)}")
    reviewed = dict(reviewed_runs or {})
    if reviewed and not set(affected) <= set(reviewed):
        raise ValueError("reviewed_runs must cover every affected run")
    for run_id, state in reviewed.items():
        if not isinstance(state, Mapping):
            raise TypeError("reviewed run state must be an object")
        revision = state.get("revision")
        fingerprint = state.get("state_fingerprint")
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 0
            or not isinstance(fingerprint, str)
            or not _HASH_REF.fullmatch(fingerprint)
        ):
            raise ValueError(f"reviewed run state is invalid: {run_id}")

    summary = _required_string(payload.get("summary"), "summary")
    if len(summary) > 4_096:
        raise ValueError("review summary is too long")
    evidence_refs = _validated_hash_refs(payload.get("evidence_refs"), "evidence_refs")
    expected = set(expected_evidence_hashes or ())
    if expected and not set(evidence_refs) <= expected:
        raise ValueError("review evidence_refs contain untrusted hashes")

    findings = _validated_findings(
        payload.get("findings"),
        expected,
        allowed_run_ids=set(allowed_run_ids or ()),
        existing_findings=tuple(existing_findings or ()),
    )
    governance = _validated_skill_governance(
        payload.get("skill_governance"),
        expected_hashes=expected,
        allowed_skill_paths=set(allowed_skill_paths or ()),
    )
    interval = payload.get("next_review_after_parent_tasks")
    if interval != REVIEW_INTERVAL_PARENTS:
        raise ValueError("next_review_after_parent_tasks must be 2")
    return SupervisorReview(
        schema_version=1,
        review_id=review_id,
        scope="project",
        decision=decision,
        affected_run_ids=affected,
        summary=summary,
        evidence_refs=evidence_refs,
        findings=findings,
        skill_governance=governance,
        next_review_after_parent_tasks=REVIEW_INTERVAL_PARENTS,
        reviewed_runs=reviewed,
    )


def apply_review_decision(
    store: SupervisorStore,
    review: SupervisorReview,
    *,
    lease_checkpoint: Callable[[], None] | None = None,
    application_cutpoint: ApplicationCutpoint | None = None,
) -> list[ActionRequest]:
    """Apply a validated decision through registry-owned Supervisor actions."""
    if not isinstance(review, SupervisorReview):
        raise TypeError("review must be a SupervisorReview")
    checkpoint = lease_checkpoint or (lambda: None)
    return apply_review_outbox(
        store,
        review,
        lease_checkpoint=checkpoint,
        application_cutpoint=application_cutpoint,
    )


def _persisted_review(review: SupervisorReview) -> dict[str, Any]:
    return {
        "schema_version": review.schema_version,
        "review_id": review.review_id,
        "scope": review.scope,
        "decision": review.decision.value,
        "affected_run_ids": list(review.affected_run_ids),
        "summary": review.summary,
        "evidence_refs": list(review.evidence_refs),
        "findings": _mutable_json(review.findings),
        "skill_governance": _mutable_json(review.skill_governance),
        "next_review_after_parent_tasks": review.next_review_after_parent_tasks,
        "reviewed_runs": _mutable_json(review.reviewed_runs),
    }


def _mutable_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _mutable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mutable_json(item) for item in value]
    return value


def _review_from_persisted(payload: object) -> SupervisorReview:
    if not isinstance(payload, Mapping):
        raise TypeError("persisted accepted review must be an object")
    return SupervisorReview(
        schema_version=int(payload["schema_version"]),
        review_id=str(payload["review_id"]),
        scope=str(payload["scope"]),
        decision=ReviewDecision(str(payload["decision"])),
        affected_run_ids=tuple(_string_list(payload["affected_run_ids"])),
        summary=str(payload["summary"]),
        evidence_refs=tuple(_string_list(payload["evidence_refs"])),
        findings=tuple(payload["findings"]),
        skill_governance=tuple(payload["skill_governance"]),
        next_review_after_parent_tasks=int(payload["next_review_after_parent_tasks"]),
        reviewed_runs=dict(payload["reviewed_runs"]),
    )


def run_reviewer(
    context: ReviewerContext,
    *,
    driver: Callable[..., Mapping[str, Any]] = run_codex_prompt,
    lease_checkpoint: Callable[[], None] | None = None,
) -> ReviewerExecutionResult:
    """Run one real read-only Codex Reviewer and accept only validated JSON."""
    if not isinstance(context, ReviewerContext):
        raise TypeError("context must be a ReviewerContext")
    store = context.store
    checkpoint = lease_checkpoint or (lambda: None)
    timestamp = store.current_time().strftime("%Y%m%dT%H%M%SZ")
    review_id = f"review-{timestamp}-{uuid4().hex[:12]}"
    review_dir = context.project_root / ".codex" / "supervisor" / "reviews" / review_id
    evidence_path = review_dir / f"{review_id}-evidence.json"
    prompt_path = review_dir / f"{review_id}-prompt.md"
    candidate_path = review_dir / f"{review_id}-candidate.json"
    accepted_path = review_dir / f"{review_id}.json"
    evidence_ref = ""
    trigger = _canonical_json(
        {
            "kind": "project_global",
            "triggering_lineages": list(context.triggering_lineages),
        }
    ).decode("utf-8")
    gate: ReviewSafetyGate | None = None
    accepted_review = False

    try:
        checkpoint()
        gate = evaluate_review_safety_gate(store)
        checkpoint()
        bundle = build_review_evidence(
            context.project_root,
            store,
            context.triggering_lineages,
        )
        checkpoint()
        review_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(evidence_path, bundle.as_dict())
        evidence_ref = evidence_path.relative_to(context.project_root).as_posix()
        trigger = _review_trigger(bundle, gate)
        checkpoint()
        prompt_path.write_text(_review_prompt(review_id, evidence_path), encoding="utf-8")
        candidate_path.unlink(missing_ok=True)
        checkpoint()
        attempt = driver(
            role="supervisor_reviewer",
            run_id=review_id,
            repo_root=context.project_root,
            run_dir=review_dir,
            prompt_path=prompt_path,
            output_json_path=candidate_path,
            attempt=1,
            timeout_seconds=context.timeout_seconds,
        )
        if not isinstance(attempt, Mapping) or attempt.get("status") != "pass":
            status = str(attempt.get("status") if isinstance(attempt, Mapping) else "invalid_driver_result")
            raise RuntimeError(f"Reviewer execution did not pass: {status}")
        checkpoint()
        candidate = _read_owned_json(review_dir, candidate_path)
        review = validate_review_payload(
            candidate,
            expected_evidence_hashes=tuple(bundle.evidence_hashes.values()),
            allowed_run_ids=tuple(str(row["run_id"]) for row in store.fetch_all("runs")),
            allowed_skill_paths=tuple(
                str(item["path"])
                for item in bundle.evidence["skill_governance"]["inventory"]
            ),
            reviewed_runs={
                str(item["run_id"]): {
                    "revision": int(item["revision"]),
                    "state_fingerprint": str(item["state_fingerprint"]),
                }
                for item in bundle.evidence["objective_constraints"]
            },
            existing_findings=tuple(
                _decoded_store_rows(store, "review_findings")
            ),
        )
        if review.review_id != review_id:
            raise ValueError("Reviewer candidate review_id does not match invocation")
        checkpoint()
        _write_json_atomic(accepted_path, candidate)
        accepted_ref = accepted_path.relative_to(context.project_root).as_posix()
        skill_snapshot = bundle.as_dict()["evidence"]["skill_governance"]
        skill_snapshot["reviewer_recommendations"] = json.loads(
            json.dumps(candidate["skill_governance"])
        )
        checkpoint()
        store.record_skill_snapshot(
            skill_snapshot,
            snapshot_id=f"skill-snapshot-{review.review_id}",
        )
        checkpoint()
        store.record_review(
            review_id=review.review_id,
            trigger=trigger,
            status="review_applying",
            decision=review.decision.value,
            summary=review.summary,
            evidence_refs=[evidence_ref, accepted_ref],
            findings=review.findings,
            accepted_review=_persisted_review(review),
            source_action_id=context.source_action_id,
        )
        accepted_review = True
        checkpoint()
        actions = apply_review_decision(
            store,
            review,
            lease_checkpoint=checkpoint,
        )
        return ReviewerExecutionResult(
            status="review_complete",
            blocks_safe_runs=False,
            review_id=review_id,
            review=review,
            actions=tuple(actions),
            evidence_path=evidence_ref,
            accepted_review_path=accepted_ref,
        )
    except LeaseError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        if accepted_review:
            raise
        checkpoint()
        store.record_review(
            review_id=review_id,
            trigger=trigger,
            status="review_degraded",
            summary=str(exc)[:4_096],
            evidence_refs=[evidence_ref] if evidence_ref else [],
            source_action_id=context.source_action_id,
        )
        return ReviewerExecutionResult(
            status="review_degraded",
            blocks_safe_runs=not (gate is not None and gate.passed),
            review_id=review_id,
            evidence_path=evidence_ref,
            error=str(exc),
        )


def run_queued_reviewer(
    store: SupervisorStore,
    *,
    reviewer_id: str,
    driver: Callable[..., Mapping[str, Any]] = run_codex_prompt,
    timeout_seconds: int = REVIEW_TIMEOUT_SECONDS,
    heartbeat_seconds: float = 30.0,
) -> ReviewerExecutionResult | None:
    """Lease and execute one Reviewer action outside the ordinary Worker."""
    action = store.lease_next_action(
        reviewer_id,
        lease_seconds=timeout_seconds + 60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )
    if action is None:
        return None
    lineages = action.payload.get("triggering_lineages")
    if not isinstance(lineages, list) or not lineages:
        run = store.get_run(action.run_id)
        lineages = [str(run.get("loop_lineage_id") or action.run_id)]
    lease_seconds = timeout_seconds + 60
    with ActionLeaseGuard(
        store,
        action_id=action.action_id,
        owner_id=reviewer_id,
        lease_seconds=lease_seconds,
        heartbeat_seconds=heartbeat_seconds,
    ) as guard:
        persisted = store.resumable_review_for_action(action.action_id)
        if persisted is not None:
            review = _review_from_persisted(persisted["accepted_review"])
            actions = apply_review_decision(
                store,
                review,
                lease_checkpoint=guard.checkpoint,
            )
            evidence_refs = tuple(str(value) for value in persisted["evidence"])
            result = ReviewerExecutionResult(
                status="review_complete",
                blocks_safe_runs=False,
                review_id=review.review_id,
                review=review,
                actions=tuple(actions),
                evidence_path=evidence_refs[0] if evidence_refs else "",
                accepted_review_path=evidence_refs[1] if len(evidence_refs) > 1 else "",
            )
        else:
            result = run_reviewer(
                ReviewerContext(
                    project_root=store.project_root,
                    store=store,
                    triggering_lineages=tuple(str(value) for value in lineages),
                    timeout_seconds=timeout_seconds,
                    source_action_id=action.action_id,
                ),
                driver=driver,
                lease_checkpoint=guard.checkpoint,
            )
        artifacts = tuple(
            value
            for value in (result.evidence_path, result.accepted_review_path)
            if value
        )
        guard.checkpoint()
        completion = ActionResult(
            result_class=(
                ActionResultClass.SUCCESS
                if not result.blocks_safe_runs
                else ActionResultClass.POLICY_BLOCK
            ),
            summary=(
                "Supervisor Reviewer completed"
                if result.status == "review_complete"
                else "Supervisor Reviewer degraded"
            ),
            failure_key=(
                "" if not result.blocks_safe_runs else f"reviewer:{result.review_id}:safety"
            ),
            error_class="" if not result.blocks_safe_runs else "deterministic_safety_gate",
            artifact_paths=artifacts,
            checkpoint="supervisor-reviewer",
        )
        reservation_id = str(action.payload.get("reservation_id") or "")
        if reservation_id and result.status != "review_complete":
            guard.checkpoint()
            store.release_review_reservation(
                reservation_id,
                reason=f"{result.status}: {result.review_id}",
            )
        elif reservation_id:
            store.complete_reviewer_action(
                action.action_id,
                reviewer_id,
                completion,
                reservation_id=reservation_id,
                review_id=result.review_id,
            )
        else:
            store.complete_action(action.action_id, reviewer_id, completion)
    return result


def reviewer_service_once(
    project_root: Path,
    *,
    reviewer_id: str,
    driver: Callable[..., Mapping[str, Any]] = run_codex_prompt,
    timeout_seconds: int = REVIEW_TIMEOUT_SECONDS,
) -> ReviewerExecutionResult | None:
    """Open the project store and execute at most one queued Reviewer action."""
    root = Path(project_root).resolve()
    with SupervisorStore.open(root) as store:
        store.migrate()
        return run_queued_reviewer(
            store,
            reviewer_id=reviewer_id,
            driver=driver,
            timeout_seconds=timeout_seconds,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one queued Supervisor Reviewer action outside the Worker."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--reviewer-id", default=f"supervisor-reviewer-{os.getpid()}"
    )
    parser.add_argument("--timeout-seconds", type=int, default=REVIEW_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    result = reviewer_service_once(
        Path(args.project_root),
        reviewer_id=args.reviewer_id,
        timeout_seconds=args.timeout_seconds,
    )
    payload = (
        {"status": "idle", "reviewer_id": args.reviewer_id}
        if result is None
        else {
            "status": result.status,
            "reviewer_id": args.reviewer_id,
            "review_id": result.review_id,
            "blocks_safe_runs": result.blocks_safe_runs,
            "error": result.error,
        }
    )
    json.dump(payload, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _due_lineage_states(store: SupervisorStore, now: datetime) -> list[_DueLineage]:
    runs = _decoded_store_rows(store, "runs")
    payloads = _run_payloads(store.project_root, runs)
    completions = _semantic_parent_completions(runs, payloads)
    reviewed = _scheduled_cadence_positions(store)
    by_lineage: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in runs:
        by_lineage[str(row.get("loop_lineage_id") or row.get("run_id") or "")].append(row)
    due: list[_DueLineage] = []
    for lineage_id, items in completions.items():
        prior = min(reviewed.get(lineage_id, 0), len(items))
        if len(items) - prior < REVIEW_INTERVAL_PARENTS:
            continue
        due_at = items[prior + REVIEW_INTERVAL_PARENTS - 1][1]
        if due_at > now:
            continue
        representative = max(
            by_lineage[lineage_id],
            key=lambda row: (str(row.get("updated_at") or ""), str(row.get("run_id") or "")),
        )
        due.append(
            _DueLineage(
                lineage_id=lineage_id,
                due_at=due_at,
                cadence_position=prior + REVIEW_INTERVAL_PARENTS,
                representative_run=representative,
            )
        )
    return sorted(due, key=lambda item: (item.due_at, item.lineage_id))


def _semantic_parent_completions(
    runs: Sequence[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[tuple[str, datetime]]]:
    grouped: dict[str, dict[str, datetime]] = defaultdict(dict)
    for row in runs:
        run_id = str(row.get("run_id") or "")
        lineage_id = str(row.get("loop_lineage_id") or run_id)
        payload = payloads.get(run_id, {})
        summary = _projection_summary(row)
        completed_ids = set(_completion_ids(payload)) | set(_completion_ids(summary))
        updated_at = _coerce_datetime(str(row.get("updated_at") or row.get("created_at") or ""))
        for parent_id in completed_ids:
            current = grouped[lineage_id].get(parent_id)
            if current is None or updated_at < current:
                grouped[lineage_id][parent_id] = updated_at
    return {
        lineage: sorted(items.items(), key=lambda item: (item[1], item[0]))
        for lineage, items in grouped.items()
    }


def _completion_ids(payload: Mapping[str, Any]) -> list[str]:
    completed: list[str] = []
    for key in (
        "completed_semantic_parent_ids",
        "semantic_parent_ids",
        "_autonomous_completed_task_ids",
    ):
        completed.extend(_string_list(payload.get(key)))
    if payload.get("last_result") == "pass" or payload.get("phase") in {
        "passed",
        "stopped_budget",
        "stopped_no_action",
        "passed_waiting_human_merge",
    }:
        task_id = str(payload.get("task_id") or "")
        match = re.search(r"parent-(\d+)", task_id)
        if match:
            completed.append(f"parent-{match.group(1)}")
    if payload.get("run_kind") == "parent":
        aggregate = payload.get("aggregate_acceptance")
        child_ids = _string_list(payload.get("child_run_ids"))
        if isinstance(aggregate, Mapping):
            passed = aggregate.get("passed")
            if isinstance(passed, int) and not isinstance(passed, bool) and passed > 0:
                completed.extend(child_ids[:passed])
    return list(dict.fromkeys(value for value in completed if value))


def _reviewed_cadence_positions(store: SupervisorStore) -> dict[str, int]:
    return {
        lineage_id: int(row.get("reviewed_position") or 0)
        for lineage_id, row in store.review_cadence_positions().items()
    }


def _scheduled_cadence_positions(store: SupervisorStore) -> dict[str, int]:
    return {
        lineage_id: max(
            int(row.get("reviewed_position") or 0),
            int(row.get("reserved_position") or 0),
        )
        for lineage_id, row in store.review_cadence_positions().items()
    }


def _merge_positions(target: dict[str, int], value: object) -> None:
    if not isinstance(value, Mapping):
        return
    for lineage_id, position in value.items():
        if isinstance(lineage_id, str) and isinstance(position, int) and not isinstance(position, bool):
            target[lineage_id] = max(target.get(lineage_id, 0), position)


def _run_payloads(
    root: Path,
    runs: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    payloads: dict[str, Mapping[str, Any]] = {}
    for row in runs:
        run_id = str(row.get("run_id") or "")
        summary = row.get("summary")
        refs = summary.get("artifact_refs", []) if isinstance(summary, Mapping) else []
        for ref in refs if isinstance(refs, list) else []:
            if not isinstance(ref, str) or not ref.endswith("/run.json"):
                continue
            try:
                payloads[run_id] = _read_repo_json(root, ref)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            break
        payloads.setdefault(run_id, _projection_summary(row))
    return payloads


def _projection_summary(row: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = row.get("summary")
    raw = summary.get("summary") if isinstance(summary, Mapping) else ""
    return _json_object(raw)


def _decoded_store_rows(store: SupervisorStore, table: str) -> list[dict[str, Any]]:
    decoded: list[dict[str, Any]] = []
    for raw in store.fetch_all(table):
        row = dict(raw)
        for key in tuple(row):
            if key.endswith("_json"):
                row[key.removesuffix("_json")] = _json_value(row.pop(key))
        decoded.append(row)
    return decoded


def _agent_evaluator_summaries(
    root: Path,
    run_payloads: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    names = {
        "planner-output.json": "planner",
        "planner-result.json": "planner",
        "generator-result.json": "generator",
        "evaluator-result.json": "evaluator",
    }
    for run_id, payload in sorted(run_payloads.items()):
        run_dir = _payload_run_dir(root, run_id, payload)
        for filename, role in names.items():
            path = run_dir / filename
            if not path.exists():
                continue
            try:
                result = _read_owned_json(run_dir, path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            summaries.append(
                {
                    "run_id": run_id,
                    "role": role,
                    "status": str(result.get("status") or result.get("planner_decision") or ""),
                    "summary": str(result.get("summary") or result.get("reason") or "")[:2_000],
                    "findings": result.get("findings", []) if isinstance(result.get("findings"), list) else [],
                    "changed_paths": _string_list(result.get("changed_paths")),
                    "artifact": path.resolve().relative_to(root).as_posix(),
                }
            )
    return summaries


def _commit_push_evidence(
    runs: Sequence[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
    store: SupervisorStore,
) -> dict[str, Any]:
    return {
        "run_commits": [
            {
                "run_id": str(row.get("run_id") or ""),
                "commit": str(payloads.get(str(row.get("run_id") or ""), {}).get("commit") or ""),
                "previous_commit": str(
                    payloads.get(str(row.get("run_id") or ""), {}).get("previous_commit") or ""
                ),
            }
            for row in runs
        ],
        "actions": [
            row
            for row in _decoded_store_rows(store, "actions")
            if row.get("action_type") in {ActionType.COMMIT.value, ActionType.PUSH.value}
        ],
    }


def _domain_output_metrics(
    agent_summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    changed_paths = sorted(
        {
            path
            for summary in agent_summaries
            for path in _string_list(summary.get("changed_paths"))
        }
    )
    return {
        "changed_paths": changed_paths,
        "changed_path_count": len(changed_paths),
        "raw_evidence_paths": sum("/raw/" in f"/{path}" for path in changed_paths),
        "wiki_page_paths": sum("/wiki/" in f"/{path}" for path in changed_paths),
    }


def _prior_finding_evidence(root: Path, store: SupervisorStore) -> dict[str, Any]:
    closure_evidence: list[dict[str, Any]] = []
    for review in _decoded_store_rows(store, "reviews"):
        for ref in review.get("evidence", []):
            if not isinstance(ref, str) or not ref.endswith(".json"):
                continue
            try:
                payload = _read_repo_json(root, ref)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            findings = payload.get("findings")
            if not isinstance(findings, list):
                continue
            for finding in findings:
                if not isinstance(finding, Mapping) or finding.get("status") != "closed":
                    continue
                refs = finding.get("closure_evidence_refs")
                if not isinstance(refs, list) or not refs:
                    continue
                closure_evidence.append(
                    {
                        "review_id": str(review.get("review_id") or ""),
                        "finding_id": str(finding.get("finding_id") or ""),
                        "finding_key": str(finding.get("finding_key") or ""),
                        "closure_evidence_refs": [
                            str(value) for value in refs if isinstance(value, str)
                        ],
                        "accepted_review_ref": ref,
                    }
                )
    return {
        "findings": _decoded_store_rows(store, "review_findings"),
        "closure_evidence": closure_evidence,
    }


def _build_skill_snapshot(
    root: Path,
    run_payloads: Mapping[str, Mapping[str, Any]],
    store: SupervisorStore,
) -> dict[str, Any]:
    roots = _declared_skill_roots(root, run_payloads.values())
    inventory: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for skill_root in roots:
        for path in _iter_skill_files(skill_root):
            safe = validate_owned_regular_file(root, path, "Skill definition")
            relative = safe.relative_to(root).as_posix()
            if relative in seen_paths:
                continue
            seen_paths.add(relative)
            name, description = _skill_frontmatter(safe)
            purpose = _normalize_purpose(description or name or safe.parent.name)
            inventory.append(
                {
                    "name": name or safe.parent.name,
                    "description": description[:500],
                    "path": relative,
                    "normalized_purpose": purpose,
                }
            )
    inventory.sort(key=lambda item: (item["normalized_purpose"], item["path"]))
    by_path = {str(item["path"]): item for item in inventory}
    usage: dict[str, dict[str, Any]] = {}
    for invocation in store.fetch_all("skill_invocations"):
        skill_path = str(invocation.get("skill_path") or "")
        skill = by_path.get(skill_path)
        if skill is None:
            continue
        artifact_ref = str(invocation.get("artifact_path") or "")
        try:
            artifact = validate_owned_regular_file(
                root,
                root.joinpath(*PurePosixPath(artifact_ref).parts),
                "Skill invocation evidence",
            )
        except (OSError, TypeError, ValueError):
            continue
        artifact_hash = f"sha256:{hashlib.sha256(artifact.read_bytes()).hexdigest()}"
        if artifact_hash != invocation.get("artifact_sha256"):
            continue
        current = usage.setdefault(
            skill_path,
            {
                "name": skill["name"],
                "path": skill_path,
                "evidence_refs": [],
                "invocation_ids": [],
            },
        )
        if artifact_ref not in current["evidence_refs"]:
            current["evidence_refs"].append(artifact_ref)
        invocation_id = str(invocation.get("invocation_id") or "")
        if invocation_id and invocation_id not in current["invocation_ids"]:
            current["invocation_ids"].append(invocation_id)

    purpose_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for skill in inventory:
        purpose_groups[str(skill["normalized_purpose"])].append(skill)
    duplicate_groups = [
        {
            "group_id": f"purpose-{hashlib.sha256(purpose.encode('utf-8')).hexdigest()[:12]}",
            "normalized_purpose": purpose,
            "skill_paths": sorted(str(item["path"]) for item in items),
        }
        for purpose, items in sorted(purpose_groups.items())
        if purpose and len(items) > 1
    ]
    candidate_process_skills = [
        item["path"]
        for item in inventory
        if any(
            word in str(item["normalized_purpose"]).split()
            for word in ("process", "workflow", "loop", "review", "validate", "evaluation")
        )
    ]
    return {
        "declared_skill_roots": [path.relative_to(root).as_posix() or "." for path in roots],
        "inventory": inventory,
        "confirmed_usage": sorted(usage.values(), key=lambda item: str(item["path"])),
        "used_skills": len(usage),
        "candidate_process_skills": sorted(candidate_process_skills),
        "duplicate_groups": duplicate_groups,
        "usage_proof": "supervisor_recorded_invocation_evidence_only",
    }


def _declared_skill_roots(
    root: Path,
    run_payloads: Sequence[Mapping[str, Any]],
) -> tuple[Path, ...]:
    declared: list[str] = []
    config_path = root / ".codex" / "supervisor" / "config.json"
    if config_path.exists():
        try:
            config = _read_owned_json(root, config_path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            config = {}
        declared.extend(_string_list(config.get("skill_roots")))
    for payload in run_payloads:
        declared.extend(_string_list(payload.get("skill_roots")))
    if not declared:
        declared.append(".")

    roots: list[Path] = []
    for value in dict.fromkeys(declared):
        relative = PurePosixPath(value)
        if relative.is_absolute() or ".." in relative.parts or "\\" in value:
            raise ValueError(f"unsafe declared skill root: {value}")
        candidate = root.joinpath(*relative.parts)
        if candidate.is_symlink():
            raise ValueError(f"declared skill root is a symlink: {value}")
        if candidate.is_dir():
            candidate.resolve().relative_to(root)
            roots.append(candidate)
    return tuple(roots)


def _iter_skill_files(root: Path) -> list[Path]:
    found: list[Path] = []

    def visit(directory: Path) -> None:
        for entry in sorted(directory.iterdir(), key=lambda item: item.name):
            if entry.name in _SKILL_SCAN_EXCLUDED_DIRS or entry.is_symlink():
                continue
            if entry.is_file() and entry.name == "SKILL.md":
                found.append(entry)
            elif entry.is_dir():
                visit(entry)

    visit(root)
    return found


def _skill_frontmatter(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return "", ""
    values: dict[str, str] = {}
    for line in lines[1:80]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"name", "description"}:
            values[key] = value.strip().strip("\"'")
    return values.get("name", ""), values.get("description", "")


def _validated_findings(
    value: object,
    expected_hashes: set[str],
    *,
    allowed_run_ids: set[str],
    existing_findings: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        raise TypeError("findings must be a list")
    findings: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    seen_keys: set[str] = set()
    allowed_keys = {
        "finding_id",
        "finding_key",
        "status",
        "summary",
        "severity",
        "evidence_refs",
        "closure_evidence_refs",
        "affected_run_ids",
    }
    required_keys = set(allowed_keys)
    existing_by_key = {
        str(item.get("finding_key") or ""): item
        for item in existing_findings
        if str(item.get("finding_key") or "")
    }
    for raw in value:
        if not isinstance(raw, Mapping):
            raise TypeError("each finding must be an object")
        unsupported = set(raw) - allowed_keys
        if unsupported:
            raise ValueError(f"finding contains prohibited keys: {sorted(unsupported)}")
        missing = required_keys - set(raw)
        if missing:
            raise ValueError(f"finding is missing keys: {sorted(missing)}")
        finding_id = _required_string(raw.get("finding_id"), "finding_id")
        if finding_id in seen:
            raise ValueError("finding_id values must be unique")
        seen.add(finding_id)
        finding_key = _required_string(raw.get("finding_key"), "finding_key")
        if finding_key in seen_keys:
            raise ValueError("finding_key values must be unique")
        seen_keys.add(finding_key)
        status = str(raw.get("status") or "")
        if status not in _FINDING_STATUSES:
            raise ValueError("finding status is not allowed")
        previous = existing_by_key.get(finding_key)
        if previous is None and status != "open":
            raise ValueError("new findings must enter lifecycle as open")
        if previous is not None:
            if str(previous.get("finding_id") or "") != finding_id:
                raise ValueError("finding_key must retain stable identity")
            previous_status = str(previous.get("status") or "")
            allowed_transitions = {
                "open": {"open", "closed", "accepted_risk"},
                "closed": {"closed"},
                "accepted_risk": {"accepted_risk"},
            }
            if status not in allowed_transitions.get(previous_status, set()):
                raise ValueError(
                    f"finding lifecycle transition is not allowed: {previous_status}->{status}"
                )
        severity = str(raw.get("severity") or "")
        if severity not in _FINDING_SEVERITIES:
            raise ValueError("finding severity is not allowed")
        evidence_refs = _validated_hash_refs(
            raw.get("evidence_refs"), "finding evidence_refs"
        )
        closure_refs = _validated_hash_refs(
            raw.get("closure_evidence_refs", []),
            "finding closure evidence",
            allow_empty=True,
        )
        if status == "closed" and not closure_refs:
            raise ValueError("closed finding requires closure evidence")
        if status == "closed" and previous is not None:
            previous_evidence = set(
                _json_list(previous.get("evidence_json", previous.get("evidence", [])))
            )
            previous_closure = set(
                _json_list(
                    previous.get(
                        "closure_evidence_json",
                        previous.get("closure_evidence", []),
                    )
                )
            )
            if not set(closure_refs) - previous_evidence - previous_closure:
                raise ValueError("closed finding requires fresh closure evidence")
        if expected_hashes and not set((*evidence_refs, *closure_refs)) <= expected_hashes:
            raise ValueError("finding references untrusted evidence hashes")
        affected_run_ids = _validated_run_ids(
            raw.get("affected_run_ids"), "finding affected_run_ids"
        )
        unknown = set(affected_run_ids) - allowed_run_ids if allowed_run_ids else set()
        if unknown:
            raise ValueError(f"finding references unknown affected runs: {sorted(unknown)}")
        finding = dict(raw)
        finding["finding_key"] = finding_key
        finding["summary"] = _required_string(raw.get("summary"), "finding summary")
        finding["evidence_refs"] = list(evidence_refs)
        finding["closure_evidence_refs"] = list(closure_refs)
        finding["affected_run_ids"] = list(affected_run_ids)
        findings.append(finding)
    return tuple(findings)


def _validated_skill_governance(
    value: object,
    *,
    expected_hashes: set[str],
    allowed_skill_paths: set[str],
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        raise TypeError("skill_governance must be a list")
    recommendations: list[Mapping[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            raise TypeError("each Skill Governance recommendation must be an object")
        action = str(raw.get("action") or "")
        if action not in ALLOWED_SKILL_RECOMMENDATIONS:
            raise ValueError("Skill Governance action is not allowed")
        if action == "merge":
            required_keys = {"action", "source_paths", "target_path", "reason", "evidence_refs"}
            source_paths = tuple(
                _normalize_relative_path(path)
                for path in _string_list(raw.get("source_paths"))
            )
            if len(source_paths) < 2 or len(set(source_paths)) != len(source_paths):
                raise ValueError("Skill Governance merge requires unique source_paths")
            referenced_paths = set(source_paths)
            referenced_paths.add(_normalize_relative_path(str(raw.get("target_path") or "")))
        else:
            required_keys = {"action", "skill_path", "reason", "evidence_refs"}
            referenced_paths = {
                _normalize_relative_path(str(raw.get("skill_path") or ""))
            }
        unsupported = set(raw) - required_keys
        missing = required_keys - set(raw)
        if unsupported or missing:
            raise ValueError(
                "Skill Governance recommendation keys do not match action schema"
            )
        if allowed_skill_paths and not referenced_paths <= allowed_skill_paths:
            raise ValueError("Skill Governance recommendation references an unknown skill path")
        evidence_refs = _validated_hash_refs(
            raw.get("evidence_refs"),
            "Skill Governance evidence_refs",
        )
        if expected_hashes and not set(evidence_refs) <= expected_hashes:
            raise ValueError("Skill Governance recommendation references untrusted evidence")
        recommendation = dict(raw)
        recommendation["reason"] = _required_string(raw.get("reason"), "Skill Governance reason")
        recommendation["evidence_refs"] = list(evidence_refs)
        recommendations.append(recommendation)
    return tuple(recommendations)


def _validated_hash_refs(
    value: object,
    label: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{label} must be a list of strings")
    refs = tuple(value)
    if not allow_empty and not refs:
        raise ValueError(f"{label} must not be empty")
    if len(set(refs)) != len(refs) or not all(_HASH_REF.fullmatch(item) for item in refs):
        raise ValueError(f"{label} must contain unique sha256 evidence references")
    return refs


def _validated_run_ids(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{label} must be a list of strings")
    values = tuple(value)
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")
    for run_id in values:
        validate_run_id(run_id)
    return values


def _review_prompt(review_id: str, evidence_path: Path) -> str:
    hash_schema = {
        "type": "string",
        "pattern": r"^sha256:[0-9a-f]{64}$",
    }
    run_ids_schema = {
        "type": "array",
        "items": {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9._-]*$"},
        "uniqueItems": True,
    }
    evidence_refs_schema = {
        "type": "array",
        "items": hash_schema,
        "minItems": 1,
        "uniqueItems": True,
    }
    finding_keys = [
        "finding_id",
        "finding_key",
        "status",
        "severity",
        "summary",
        "evidence_refs",
        "closure_evidence_refs",
        "affected_run_ids",
    ]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(_REVIEW_PAYLOAD_KEYS),
        "properties": {
            "schema_version": {"const": 1},
            "review_id": {"const": review_id},
            "scope": {"const": "project"},
            "decision": {"enum": sorted(ALLOWED_REVIEW_DECISIONS)},
            "affected_run_ids": run_ids_schema,
            "summary": {"type": "string", "minLength": 1, "maxLength": 4096},
            "evidence_refs": evidence_refs_schema,
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": finding_keys,
                    "properties": {
                        "finding_id": {"type": "string", "minLength": 1},
                        "finding_key": {"type": "string", "minLength": 1},
                        "status": {"enum": sorted(_FINDING_STATUSES)},
                        "severity": {"enum": sorted(_FINDING_SEVERITIES)},
                        "summary": {"type": "string", "minLength": 1},
                        "evidence_refs": evidence_refs_schema,
                        "closure_evidence_refs": {
                            "type": "array",
                            "items": hash_schema,
                            "uniqueItems": True,
                        },
                        "affected_run_ids": run_ids_schema,
                    },
                },
            },
            "skill_governance": {
                "type": "array",
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "action",
                                "skill_path",
                                "reason",
                                "evidence_refs",
                            ],
                            "properties": {
                                "action": {"enum": ["keep", "delete_candidate"]},
                                "skill_path": {"type": "string", "minLength": 1},
                                "reason": {"type": "string", "minLength": 1},
                                "evidence_refs": evidence_refs_schema,
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "action",
                                "source_paths",
                                "target_path",
                                "reason",
                                "evidence_refs",
                            ],
                            "properties": {
                                "action": {"const": "merge"},
                                "source_paths": {
                                    "type": "array",
                                    "items": {"type": "string", "minLength": 1},
                                    "minItems": 2,
                                    "uniqueItems": True,
                                },
                                "target_path": {"type": "string", "minLength": 1},
                                "reason": {"type": "string", "minLength": 1},
                                "evidence_refs": evidence_refs_schema,
                            },
                        },
                    ]
                },
            },
            "next_review_after_parent_tasks": {"const": REVIEW_INTERVAL_PARENTS},
        },
        "allOf": [
            {
                "if": {"properties": {"decision": {"not": {"const": "continue"}}}},
                "then": {"properties": {"affected_run_ids": {"minItems": 1}}},
            }
        ],
    }
    fixture = {
        "schema_version": 1,
        "review_id": review_id,
        "scope": "project",
        "decision": "continue",
        "affected_run_ids": [],
        "summary": "Project-global evidence supports continuing safe work.",
        "evidence_refs": ["sha256:" + "a" * 64],
        "findings": [],
        "skill_governance": [],
        "next_review_after_parent_tasks": REVIEW_INTERVAL_PARENTS,
    }
    return (
        "You are the Supervisor Reviewer. Evaluate the project globally from the attached "
        "trusted evidence bundle. This is a read-only review: do not modify repository files, "
        "run mutating commands, request permissions, or perform irreversible operations.\n"
        "Return exactly one JSON object as your final response. The Supervisor validates it "
        "against the exact structural schema below and rejects every extra key. Use only run "
        "IDs, skill paths, and sha256 evidence hashes present in the evidence bundle. Replace "
        "the fixture evidence hash with one or more actual bundle hashes.\n"
        "Finding rules: a new finding starts open; retain finding_id for an existing "
        "finding_key; only open may transition to closed or accepted_risk; closed findings "
        "require fresh finding-specific closure_evidence_refs. Skill Governance entries are "
        "recommendations only. Decisions other than continue require affected_run_ids.\n"
        f"Set review_id to {review_id}. Evidence bundle: {evidence_path}\n"
        "BEGIN_REVIEW_JSON_SCHEMA\n"
        f"{json.dumps(schema, sort_keys=True, indent=2, ensure_ascii=True)}\n"
        "END_REVIEW_JSON_SCHEMA\n"
        "BEGIN_REVIEW_JSON_FIXTURE\n"
        f"{json.dumps(fixture, sort_keys=True, indent=2, ensure_ascii=True)}\n"
        "END_REVIEW_JSON_FIXTURE\n"
    )


def _review_trigger(
    bundle: ReviewEvidenceBundle,
    gate: ReviewSafetyGate,
) -> str:
    return _canonical_json(
        {
            "kind": "project_global",
            "triggering_lineages": list(bundle.triggering_lineages),
            "cadence_positions": dict(bundle.cadence_positions),
            "safety_gate_id": gate.gate_id,
        }
    ).decode("utf-8")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_repo_json(root: Path, relative_path: str) -> Mapping[str, Any]:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in relative_path:
        raise ValueError("artifact reference must be project relative")
    return _read_owned_json(root, root.joinpath(*relative.parts))


def _read_owned_json(owner_root: Path, path: Path) -> Mapping[str, Any]:
    safe = validate_owned_regular_file(owner_root, path, "Reviewer JSON evidence")
    if safe.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Reviewer JSON evidence exceeds 2 MiB")
    value = json.loads(safe.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError("Reviewer JSON evidence must be an object")
    return value


def _payload_run_dir(root: Path, run_id: str, payload: Mapping[str, Any]) -> Path:
    worktree = payload.get("worktree")
    if isinstance(worktree, str) and worktree:
        candidate = Path(worktree).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            candidate = root
    else:
        candidate = root
    return candidate / ".codex" / "loop-runs" / run_id


def _json_value(value: object) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _json_object(value: object) -> Mapping[str, Any]:
    parsed = _json_value(value)
    return parsed if isinstance(parsed, Mapping) else {}


def _json_list(value: object) -> list[Any]:
    parsed = _json_value(value)
    return list(parsed) if isinstance(parsed, (list, tuple)) else []


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("timestamp must be a datetime or ISO-8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _normalize_purpose(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _normalize_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or not path.parts:
        raise ValueError("Skill path must be normalized and project relative")
    return path.as_posix()


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess tests.
    raise SystemExit(main())
