from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

from .models import AgentSummary, Event, FlowNode, LogEntry
from .redaction import redact_text


COMPLETED_PHASES = {"passed_waiting_human_merge", "stopped_no_action", "stopped_budget", "stopped_blocked"}
BLOCKED_PHASES = {"stopped_blocked", "repair_needed", "invalid_artifact"}
LOG_GLOBS = ("*-attempt-*.stdout.log", "*-attempt-*.stderr.log")
FALLBACK_SUMMARY = "暂无可用摘要"
SESSION_EVENT_LIMIT = 200
SESSION_FILE_MAX_BYTES = 2 * 1024 * 1024


class RunSource(NamedTuple):
    run_dir: Path
    source_kind: str


class RunRecord(NamedTuple):
    source: RunSource
    data: dict[str, Any] | None
    updated_at: str


class ChildRun(NamedTuple):
    summary: dict[str, Any]
    source: RunSource


def safe_join(root: Path, relative_path: str) -> Path:
    base = root.resolve()
    candidate_path = Path(relative_path)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        raise ValueError(f"unsafe relative path: {relative_path}")
    candidate = (base / candidate_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {relative_path}") from exc
    return candidate


class LoopDashboardStore:
    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).resolve()
        self.loop_runs_dir = self.project_root / ".codex" / "loop-runs"

    def project_info(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "loop_runs_path": str(self.loop_runs_dir),
            "loop_runs_exists": self.loop_runs_dir.exists(),
            "history_sources": [self._source_path(source.run_dir) for source in self._run_sources()],
        }

    def list_runs(self) -> list[dict[str, Any]]:
        runs = [self._load_run_summary(source.run_dir, source.source_kind) for source in self._run_sources()]
        runs = self._dedupe_runs(runs)
        runs = self._filter_top_level_runs(runs)
        return sorted(runs, key=lambda run: (run.get("updated_at", ""), run.get("run_id", "")), reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        source = self._run_source(run_id)
        if source is None or not source.run_dir.is_dir():
            return None
        run_dir = source.run_dir
        summary = self._load_run_summary(run_dir, source.source_kind)
        run_data = self._read_json(run_dir / "run.json", allowed_root=run_dir)
        planner = self._read_json(run_dir / "planner-output.json", allowed_root=run_dir)
        if not isinstance(run_data, dict):
            run_data = {}
        if not isinstance(planner, dict):
            planner = {}
        evaluator = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
        if not isinstance(evaluator, dict):
            evaluator = {}
        _, rich_evaluator = self._rich_evaluator_result(evaluator)
        if not isinstance(rich_evaluator, dict):
            rich_evaluator = {}
        run_kind = self._run_kind(run_data)
        acceptance_summary = self._acceptance_summary_for_run_dir(run_dir)
        decision_summary = (
            summary.get("decision_summary")
            if summary.get("phase") == "invalid_artifact" and isinstance(summary.get("decision_summary"), dict)
            else self._decision_summary(run_data, evaluator, rich_evaluator)
        )
        summary.update(
            {
                "constraints": run_data.get("constraints", []),
                "stop_conditions": run_data.get("stop_conditions") or planner.get("stop_conditions", []),
                "attempts": run_data.get("attempts", {}),
                "limits": run_data.get("limits", {}),
                "allowed_paths": planner.get("allowed_paths", run_data.get("allowed_paths", [])),
                "denylist_paths": planner.get("denylist_paths", run_data.get("denylist_paths", [])),
                "decision_summary": decision_summary,
                "acceptance_summary": acceptance_summary,
                "flow_nodes": [node.to_dict() for node in self._flow_nodes(run_dir, run_data)],
                "governance_artifacts": self._governance_artifacts(run_dir, evaluator),
            }
        )
        summary["artifact_paths"] = self._unique_nonempty(
            [*self._path_items(summary.get("artifact_paths")), *self._governance_artifact_paths(summary["governance_artifacts"])]
        )
        if run_kind == "parent":
            child_runs, relationship_diagnostics = self._children_for_parent(str(summary.get("run_id") or run_id), run_data)
            aggregate_acceptance = run_data.get("aggregate_acceptance")
            summary.update(
                {
                    "reader_summary": run_data.get("reader_summary") if isinstance(run_data.get("reader_summary"), dict) else {},
                    "aggregate_acceptance": aggregate_acceptance if isinstance(aggregate_acceptance, dict) else {},
                    "children": [child.summary for child in child_runs],
                    "relationship_diagnostics": relationship_diagnostics,
                    "blocked_diagnostics": [*summary.get("blocked_diagnostics", []), *relationship_diagnostics],
                    "acceptance_summary": self._parent_acceptance_summary(
                        run_data,
                        acceptance_summary,
                        child_runs,
                    ),
                }
            )
        return summary

    def get_events(self, run_id: str) -> list[dict[str, Any]] | None:
        source = self._run_source(run_id)
        if source is None or not source.run_dir.is_dir():
            return None
        run_dir = source.run_dir
        events: list[Event] = []
        run_data = self._read_json(run_dir / "run.json", allowed_root=run_dir)
        if not isinstance(run_data, dict):
            run_data = {}
        events.extend(self._structured_events(run_dir))
        for path in self._direct_artifact_files(run_dir):
            events.append(Event("artifact", self._relative_artifact(path), f"updated {path.name}", self._mtime_iso(path)))
        for log in self._collect_logs(run_dir):
            events.append(Event("log", log.source, self._summarize_log(log.content), log.updated_at))
            events.append(Event(log.stream, log.source, self._summarize_log(log.content), log.updated_at))
            lowered = log.content.lower()
            if "skill" in lowered:
                events.append(Event("skill", log.source, self._summarize_log(log.content), log.updated_at))
            if any(name in lowered for name in ("planner", "generator", "evaluator", "agent")):
                events.append(Event("agent", log.source, self._summarize_log(log.content), log.updated_at))
            if "tool" in lowered:
                events.append(Event("tool", log.source, self._summarize_log(log.content), log.updated_at))
        events.extend(self._session_events(run_id))
        if self._run_kind(run_data) == "parent":
            child_runs, _diagnostics = self._children_for_parent(str(run_data.get("run_id") or run_id), run_data)
            for child in child_runs:
                if child.source.run_dir.is_dir():
                    events.extend(self._structured_events(child.source.run_dir))
        return [event.to_dict() for event in sorted(events, key=lambda event: event.updated_at)]

    def get_logs(self, run_id: str) -> list[dict[str, Any]] | None:
        source = self._run_source(run_id)
        if source is None or not source.run_dir.is_dir():
            return None
        return [log.to_dict() for log in self._collect_logs(source.run_dir)]

    def _run_sources(self) -> list[RunSource]:
        sources: list[RunSource] = []
        sources.extend(RunSource(run_dir, "current") for run_dir in self._loop_run_dirs(self.loop_runs_dir))
        worktrees_dir = self.project_root / ".worktrees"
        if worktrees_dir.exists():
            for worktree_path in sorted(worktrees_dir.iterdir(), key=lambda path: path.name):
                if not worktree_path.is_dir():
                    continue
                safe_worktree = self._safe_dir_under(worktree_path, worktrees_dir)
                if safe_worktree is None:
                    continue
                loop_runs_dir = safe_worktree / ".codex" / "loop-runs"
                sources.extend(RunSource(run_dir, "worktree") for run_dir in self._loop_run_dirs(loop_runs_dir))
        return sources

    def _loop_run_dirs(self, loop_runs_dir: Path) -> list[Path]:
        safe_loop_runs_dir = self._safe_dir_under(loop_runs_dir, self.project_root)
        if safe_loop_runs_dir is None:
            return []
        return [
            run_dir
            for run_dir in sorted(safe_loop_runs_dir.iterdir(), key=lambda path: path.name)
            if self._safe_dir_under(run_dir, safe_loop_runs_dir) is not None and run_dir.is_dir()
        ]

    def _run_source(self, run_id: str) -> RunSource | None:
        if not self._safe_run_id(run_id):
            return None
        sources_by_id = self._run_source_index()
        return sources_by_id.get(run_id)

    def _run_source_index(self) -> dict[str, RunSource]:
        return {run_id: record.source for run_id, record in self._run_records_by_id().items()}

    def _run_records_by_id(self) -> dict[str, RunRecord]:
        records_by_id: dict[str, RunRecord] = {}
        for source in self._run_sources():
            data = self._read_json(source.run_dir / "run.json", allowed_root=source.run_dir)
            run_id = str(data.get("run_id") or source.run_dir.name) if isinstance(data, dict) else source.run_dir.name
            if not self._safe_run_id(run_id):
                continue
            updated_at = self._updated_at(source.run_dir)
            previous = records_by_id.get(run_id)
            if previous is None or (updated_at, self._source_path(source.run_dir)) > (
                previous.updated_at,
                self._source_path(previous.source.run_dir),
            ):
                records_by_id[run_id] = RunRecord(source, data if isinstance(data, dict) else None, updated_at)
        return records_by_id

    def _dedupe_runs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        runs_by_id: dict[str, dict[str, Any]] = {}
        for run in runs:
            run_id = str(run.get("run_id") or "")
            if not self._safe_run_id(run_id):
                continue
            previous = runs_by_id.get(run_id)
            if previous is None or (
                str(run.get("updated_at") or ""),
                str(run.get("source_path") or ""),
            ) > (
                str(previous.get("updated_at") or ""),
                str(previous.get("source_path") or ""),
            ):
                runs_by_id[run_id] = run
        return list(runs_by_id.values())

    def _filter_top_level_runs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        aggregated_child_ids: set[str] = set()
        for run in runs:
            if run.get("run_kind") != "parent":
                continue
            parent_run_id = str(run.get("run_id") or "")
            source = self._run_source(parent_run_id)
            if source is None:
                continue
            parent_data = self._read_json(source.run_dir / "run.json", allowed_root=source.run_dir)
            if not isinstance(parent_data, dict):
                continue
            child_runs, _diagnostics = self._children_for_parent(parent_run_id, parent_data)
            aggregated_child_ids.update(
                str(child.summary.get("run_id") or "")
                for child in child_runs
                if self._safe_run_id(str(child.summary.get("run_id") or ""))
            )
        if not aggregated_child_ids:
            return runs
        top_level: list[dict[str, Any]] = []
        for run in runs:
            run_id = str(run.get("run_id") or "")
            if run.get("run_kind") == "child" and run_id in aggregated_child_ids:
                continue
            top_level.append(run)
        return top_level

    def _safe_run_id(self, run_id: str) -> bool:
        candidate_path = Path(run_id)
        return bool(run_id) and not candidate_path.is_absolute() and ".." not in candidate_path.parts and "/" not in run_id and "\\" not in run_id

    def _run_kind(self, run_data: dict[str, Any]) -> str:
        value = run_data.get("run_kind")
        return value if isinstance(value, str) and value in {"parent", "child"} else "single"

    def _safe_child_run_id(self, run_id: str) -> bool:
        return self._safe_run_id(run_id)

    def _all_run_data_by_id(self) -> dict[str, tuple[RunSource, dict[str, Any]]]:
        return {
            run_id: (record.source, record.data)
            for run_id, record in self._run_records_by_id().items()
            if record.data is not None
        }

    def _load_run_summary(self, run_dir: Path, source_kind: str = "current") -> dict[str, Any]:
        run_json = run_dir / "run.json"
        run_data = self._read_json(run_json, allowed_root=run_dir)
        if not isinstance(run_data, dict):
            return self._invalid_summary(run_dir, source_kind)
        planner = self._read_json(run_dir / "planner-output.json", allowed_root=run_dir)
        if not isinstance(planner, dict):
            planner = {}
        phase = str(run_data.get("phase") or "unknown")
        completed = phase in COMPLETED_PHASES
        artifacts = self._artifact_paths(run_dir)
        task_description = self._task_description(run_data)
        aggregate_acceptance = run_data.get("aggregate_acceptance")
        reader_summary = run_data.get("reader_summary")
        return {
            "run_id": str(run_data.get("run_id") or run_dir.name),
            "run_kind": self._run_kind(run_data),
            "parent_run_id": str(run_data.get("parent_run_id") or ""),
            "child_index": self._safe_int(run_data.get("child_index")),
            "current_child_run_id": str(run_data.get("current_child_run_id") or ""),
            "reader_summary": reader_summary if isinstance(reader_summary, dict) else {},
            "children_summary": self._children_summary(aggregate_acceptance),
            "decision_required": bool(aggregate_acceptance.get("user_decision_required")) if isinstance(aggregate_acceptance, dict) else False,
            "project_root": str(self.project_root),
            "source_kind": source_kind,
            "source_path": self._source_path(run_dir),
            "task_summary": self._trim(task_description),
            "task_description": task_description,
            "policy": str(run_data.get("policy") or ""),
            "phase": phase,
            "last_result": str(run_data.get("last_result") or ""),
            "next_action": str(run_data.get("next_action") or ""),
            "health": self._health(phase),
            "updated_at": self._updated_at(run_dir),
            "completed": completed,
            "agents": self._agents(run_dir, run_data),
            "blocked_diagnostics": self._blocked_diagnostics(run_dir, run_data),
            "artifact_paths": artifacts,
            "constraints": run_data.get("constraints", []),
            "stop_conditions": run_data.get("stop_conditions") or planner.get("stop_conditions", []),
            "attempts": run_data.get("attempts", {}),
            "flow_nodes": [node.to_dict() for node in self._flow_nodes(run_dir, run_data)],
        }

    def _invalid_summary(self, run_dir: Path, source_kind: str = "current") -> dict[str, Any]:
        diagnostic = {
            "kind": "invalid_artifact",
            "severity": "critical",
            "title": "Invalid run artifact",
            "message": "run.json could not be parsed",
            "source": self._relative_artifact(run_dir / "run.json"),
        }
        return {
            "run_id": run_dir.name,
            "run_kind": "single",
            "parent_run_id": "",
            "child_index": 0,
            "current_child_run_id": "",
            "reader_summary": {},
            "children_summary": self._children_summary({}),
            "decision_required": True,
            "project_root": str(self.project_root),
            "source_kind": source_kind,
            "source_path": self._source_path(run_dir),
            "task_summary": "invalid_artifact",
            "policy": "",
            "phase": "invalid_artifact",
            "last_result": "invalid_artifact",
            "next_action": "",
            "health": "blocked",
            "updated_at": self._updated_at(run_dir),
            "completed": False,
            "agents": self._empty_agents(),
            "decision_summary": self._invalid_decision_summary(),
            "blocked_diagnostics": [diagnostic],
            "artifact_paths": self._artifact_paths(run_dir),
        }

    def _invalid_decision_summary(self) -> dict[str, Any]:
        return {
            "requires_user_decision": True,
            "decision_label": "需要检查无效产物",
            "next_action": "inspect_invalid_artifact",
            "reason": "run.json could not be parsed",
        }

    def _children_summary(self, aggregate_acceptance: Any) -> dict[str, int]:
        if not isinstance(aggregate_acceptance, dict):
            aggregate_acceptance = {}
        return {
            key: self._safe_int(aggregate_acceptance.get(key))
            for key in ("total", "passed", "failed", "blocked", "pending")
        }

    def _relationship_diagnostic(self, kind: str, message: str, source: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "severity": "warning",
            "title": kind.replace("_", " "),
            "message": message,
            "source": source,
        }

    def _children_for_parent(self, parent_run_id: str, parent_data: dict[str, Any]) -> tuple[list[ChildRun], list[dict[str, Any]]]:
        all_runs = self._all_run_data_by_id()
        explicit_parents_by_child = self._explicit_parents_by_child(all_runs)
        parent_source = all_runs.get(parent_run_id, (None, {}))[0]
        parent_source_path = (
            self._relative_artifact(parent_source.run_dir / "run.json")
            if isinstance(parent_source, RunSource)
            else f"{parent_run_id}/run.json"
        )
        children: list[ChildRun] = []
        diagnostics: list[dict[str, Any]] = []
        included: set[str] = set()
        explicit_ids: set[str] = set()

        def add_diagnostic(kind: str, message: str, source: str) -> None:
            diagnostic = self._relationship_diagnostic(kind, message, source)
            key = (diagnostic["kind"], diagnostic["message"], diagnostic["source"])
            if key not in {
                (item.get("kind"), item.get("message"), item.get("source"))
                for item in diagnostics
            }:
                diagnostics.append(diagnostic)

        def add_child(child_run_id: str, child_source: RunSource, child_data: dict[str, Any]) -> None:
            child_parent_run_id = str(child_data.get("parent_run_id") or "")
            child_source_path = self._relative_artifact(child_source.run_dir / "run.json")
            if child_parent_run_id and child_parent_run_id != parent_run_id:
                add_diagnostic(
                    "child_parent_conflict",
                    f"child {child_run_id} points to parent {child_parent_run_id}, not {parent_run_id}",
                    child_source_path,
                )
                return
            explicit_parent_ids = explicit_parents_by_child.get(child_run_id, [])
            if not child_parent_run_id and len(explicit_parent_ids) > 1:
                owner_parent_id = explicit_parent_ids[0]
                if parent_run_id != owner_parent_id:
                    add_diagnostic(
                        "child_multi_parent_conflict",
                        f"child {child_run_id} is explicitly referenced by {', '.join(explicit_parent_ids)}; owner is {owner_parent_id}",
                        child_source_path,
                    )
                    return
            if child_run_id in included:
                return
            children.append(
                ChildRun(
                    self._load_run_summary(child_source.run_dir, child_source.source_kind),
                    child_source,
                )
            )
            included.add(child_run_id)

        explicit_value = parent_data.get("child_run_ids")
        if isinstance(explicit_value, list):
            for item in explicit_value:
                child_run_id = str(item)
                if not self._safe_child_run_id(child_run_id):
                    add_diagnostic(
                        "unsafe_child_reference",
                        f"child reference is unsafe and was ignored: {child_run_id}",
                        parent_source_path,
                    )
                    continue
                explicit_ids.add(child_run_id)
                child_entry = all_runs.get(child_run_id)
                if child_entry is None:
                    add_diagnostic(
                        "child_artifact_missing",
                        f"child run artifact not found: {child_run_id}",
                        parent_source_path,
                    )
                    continue
                child_source, child_data = child_entry
                add_child(child_run_id, child_source, child_data)

        for child_run_id, (child_source, child_data) in all_runs.items():
            if self._run_kind(child_data) != "child":
                continue
            child_parent_run_id = str(child_data.get("parent_run_id") or "")
            if child_parent_run_id == parent_run_id:
                if child_run_id not in explicit_ids:
                    add_diagnostic(
                        "parent_index_missing",
                        f"child {child_run_id} points to parent {parent_run_id}, but is missing from child_run_ids",
                        self._relative_artifact(child_source.run_dir / "run.json"),
                    )
                add_child(child_run_id, child_source, child_data)
            elif child_run_id.startswith(f"{parent_run_id}-child-"):
                add_diagnostic(
                    "child_parent_conflict",
                    f"child {child_run_id} points to parent {child_parent_run_id or 'unknown'}, not {parent_run_id}",
                    self._relative_artifact(child_source.run_dir / "run.json"),
                )

        return (
            sorted(
                children,
                key=lambda child: (
                    self._child_sort_index(child.summary.get("child_index")),
                    str(child.summary.get("updated_at") or ""),
                    str(child.summary.get("run_id") or ""),
                ),
            ),
            diagnostics,
        )

    def _explicit_parents_by_child(
        self,
        all_runs: dict[str, tuple[RunSource, dict[str, Any]]],
    ) -> dict[str, list[str]]:
        parents_by_child: dict[str, dict[str, str]] = {}
        for parent_run_id, (parent_source, parent_data) in all_runs.items():
            if self._run_kind(parent_data) != "parent":
                continue
            child_run_ids = parent_data.get("child_run_ids")
            if not isinstance(child_run_ids, list):
                continue
            for item in child_run_ids:
                child_run_id = str(item)
                if not self._safe_child_run_id(child_run_id):
                    continue
                parents_by_child.setdefault(child_run_id, {})[parent_run_id] = self._updated_at(parent_source.run_dir)
        return {
            child_run_id: sorted(
                parent_updated_at,
                key=lambda parent_id: (parent_updated_at[parent_id], parent_id),
                reverse=True,
            )
            for child_run_id, parent_updated_at in parents_by_child.items()
        }

    def _child_sort_index(self, value: Any) -> int:
        index = self._safe_int(value)
        return index if index > 0 else 1_000_000

    def _agents(self, run_dir: Path, run_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        attempts = run_data.get("attempts") if isinstance(run_data.get("attempts"), dict) else {}
        next_action = str(run_data.get("next_action") or "")
        planner = self._read_json(run_dir / "planner-output.json", allowed_root=run_dir)
        generator = self._read_json(run_dir / "generator-result.json", allowed_root=run_dir)
        evaluator = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
        return {
            "planner": self._agent("planner", attempts, next_action, planner, run_dir).to_dict(),
            "generator": self._agent("generator", attempts, next_action, generator, run_dir).to_dict(),
            "evaluator": self._agent("evaluator", attempts, next_action, evaluator, run_dir).to_dict(),
        }

    def _empty_agents(self) -> dict[str, dict[str, Any]]:
        return {
            name: AgentSummary(name, "missing", 0, "", FALLBACK_SUMMARY, []).to_dict()
            for name in ("planner", "generator", "evaluator")
        }

    def _agent(
        self,
        name: str,
        attempts: dict[str, Any],
        next_action: str,
        payload: Any,
        run_dir: Path,
    ) -> AgentSummary:
        data = payload if isinstance(payload, dict) else {}
        artifact_paths = self._agent_artifact_labels(run_dir, name, data)
        attempt = (
            self._safe_int(data.get("attempt"))
            or self._safe_int(attempts.get(name))
            or self._attempt_from_logs(run_dir, name)
        )
        status = str(data.get("status") or ("ready" if data else "missing"))
        current_action = next_action if name in next_action else ""
        last_result = self._structured_summary(name, data) or self._log_summary(run_dir, name) or FALLBACK_SUMMARY
        return AgentSummary(name, status, attempt, current_action, last_result, artifact_paths)

    def _agent_artifact_labels(self, run_dir: Path, name: str, data: dict[str, Any]) -> list[str]:
        paths = [self._relative_artifact(path) for path in self._agent_artifacts(run_dir, name)]
        for key in ("artifact_paths", "artifacts", "changed_paths"):
            value = data.get(key)
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, str) and item:
                    paths.append(item)
        unique: list[str] = []
        seen: set[str] = set()
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def _structured_summary(self, name: str, data: dict[str, Any]) -> str:
        if name == "planner":
            return str(data.get("goal") or data.get("title") or "")
        if name == "generator":
            return str(data.get("notes") or data.get("status") or "")
        return str(data.get("summary") or data.get("verdict_reason") or data.get("status") or "")

    def _agent_artifacts(self, run_dir: Path, name: str) -> list[Path]:
        paths = []
        for path in run_dir.iterdir():
            if path.is_file() and (path.name.startswith(f"{name}-") or path.name == f"{name}-output.json" or path.name == f"{name}-result.json"):
                paths.append(path)
        return sorted(paths)

    def _attempt_from_logs(self, run_dir: Path, name: str) -> int:
        attempts: list[int] = []
        for path in run_dir.glob(f"{name}-attempt-*.*.log"):
            if self._safe_file_under(path, run_dir) is None:
                continue
            parts = path.name.split("-attempt-", 1)[-1].split(".", 1)[0]
            if parts.isdigit():
                attempts.append(int(parts))
        return max(attempts, default=0)

    def _log_summary(self, run_dir: Path, name: str) -> str:
        for path in self._agent_artifacts(run_dir, name):
            if path.suffix == ".log":
                safe_path = self._safe_file_under(path, run_dir)
                if safe_path is None:
                    continue
                text = safe_path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return self._trim(redact_text(text), 96)
        return ""

    def _flow_nodes(self, run_dir: Path, run_data: dict[str, Any]) -> list[FlowNode]:
        policy = str(run_data.get("policy") or "demand_development")
        if policy == "autonomous_knowledge":
            labels = [
                ("planner", "Planner"),
                ("generator", "Generator"),
                ("evaluator", "Evaluator"),
                ("artifact_hygiene", "Artifact Hygiene"),
                ("cleanup", "Cleanup"),
                ("commit", "Commit"),
                ("planner_loop", "Planner"),
            ]
        else:
            labels = [
                ("preflight", "Preflight"),
                ("planner", "Planner"),
                ("generator", "Generator"),
                ("evaluator", "Evaluator"),
                ("repair_needed", "Repair Needed"),
                ("artifact_hygiene", "Artifact Hygiene"),
                ("cleanup", "Cleanup"),
                ("human_merge", "Human Merge"),
            ]
        phase = str(run_data.get("phase") or "")
        next_action = str(run_data.get("next_action") or "")
        artifacts_by_node = {
            "preflight": [run_dir / "preflight.md", run_dir / "run.json"],
            "planner": [run_dir / "planner-output.json"],
            "generator": [run_dir / "generator-result.json"],
            "evaluator": [run_dir / "evaluator-result.json"],
            "repair_needed": [run_dir / "evaluator-result.json"],
            "artifact_hygiene": [run_dir / "artifact-manifest.json", run_dir / "redaction-manifest.json"],
            "cleanup": [run_dir / "cleanup-result.json"],
            "commit": [run_dir / "commit-result.json"],
            "planner_loop": [run_dir / "planner-output.json"],
            "human_merge": [run_dir / "run.json"],
        }
        nodes: list[FlowNode] = []
        for node_id, label in labels:
            artifact_paths = [
                self._relative_artifact(path)
                for path in artifacts_by_node.get(node_id, [])
                if self._safe_file_under(path, run_dir) is not None
            ]
            status = self._flow_node_status(node_id, phase, next_action, run_dir)
            recent_result = self._flow_node_result(node_id, run_dir, run_data)
            current_action = self._flow_node_action(node_id, next_action, phase)
            if node_id in next_action and status == "waiting":
                status = "running"
            nodes.append(FlowNode(node_id, label, status, current_action, recent_result, artifact_paths))
        return nodes

    def _node_pending(self, node_id: str, next_action: str) -> str:
        return "running" if node_id in next_action else "waiting"

    def _flow_node_status(self, node_id: str, phase: str, next_action: str, run_dir: Path) -> str:
        evaluator = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
        evaluator_status = evaluator.get("status") if isinstance(evaluator, dict) else ""
        if node_id == "preflight":
            return "done"
        if node_id == "planner":
            return "done" if (run_dir / "planner-output.json").exists() else self._node_pending("planner", next_action)
        if node_id == "generator":
            if "generator" in next_action:
                return "running"
            return "done" if (run_dir / "generator-result.json").exists() else "waiting"
        if node_id == "evaluator":
            if phase in BLOCKED_PHASES or evaluator_status in {"fail", "failed", "blocked"}:
                return "blocked"
            if evaluator_status == "pass" or phase in COMPLETED_PHASES:
                return "done"
            return self._node_pending("evaluator", next_action)
        if node_id == "repair_needed":
            if phase == "repair_needed" or "repair" in next_action:
                return "running"
            if evaluator_status in {"fail", "failed", "blocked"}:
                return "done"
            return "skipped" if phase in COMPLETED_PHASES else "waiting"
        if node_id == "artifact_hygiene":
            if "artifact_hygiene" in next_action or phase == "artifact_hygiene":
                return "running"
            if (run_dir / "artifact-manifest.json").exists():
                return "done"
            return "skipped" if phase in COMPLETED_PHASES else "waiting"
        if node_id == "cleanup":
            if "cleanup" in next_action or phase == "cleanup":
                return "running"
            if (run_dir / "cleanup-result.json").exists():
                return "done"
            return "skipped" if phase in COMPLETED_PHASES else "waiting"
        if node_id == "commit":
            if "commit" in next_action or phase == "commit":
                return "running"
            return "done" if (run_dir / "commit-result.json").exists() else "waiting"
        if node_id == "planner_loop":
            if phase in {"stopped_no_action", "stopped_budget", "stopped_blocked"}:
                return "done"
            return "running" if "planner" in next_action else "waiting"
        if node_id == "human_merge":
            return "running" if phase == "passed_waiting_human_merge" else "waiting"
        return "waiting"

    def _flow_node_result(self, node_id: str, run_dir: Path, run_data: dict[str, Any]) -> str:
        if node_id == "preflight":
            return str(run_data.get("phase") or "")
        if node_id == "planner":
            payload = self._read_json(run_dir / "planner-output.json", allowed_root=run_dir)
            return self._structured_summary("planner", payload if isinstance(payload, dict) else {})
        if node_id == "generator":
            payload = self._read_json(run_dir / "generator-result.json", allowed_root=run_dir)
            return self._structured_summary("generator", payload if isinstance(payload, dict) else {})
        if node_id in {"evaluator", "repair_needed"}:
            payload = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
            return self._structured_summary("evaluator", payload if isinstance(payload, dict) else {})
        if node_id == "artifact_hygiene":
            payload = self._read_json(run_dir / "artifact-manifest.json", allowed_root=run_dir)
            return str(payload.get("status") if isinstance(payload, dict) else "")
        if node_id == "cleanup":
            payload = self._read_json(run_dir / "cleanup-result.json", allowed_root=run_dir)
            return str(payload.get("status") if isinstance(payload, dict) else "")
        if node_id == "commit":
            payload = self._read_json(run_dir / "commit-result.json", allowed_root=run_dir)
            if isinstance(payload, dict):
                return str(payload.get("commit") or payload.get("status") or "")
        if node_id == "human_merge":
            return str(run_data.get("next_action") or "")
        if node_id == "planner_loop":
            return str(run_data.get("last_result") or "")
        return ""

    def _flow_node_action(self, node_id: str, next_action: str, phase: str) -> str:
        if node_id in next_action:
            return next_action
        if node_id == "evaluator" and (phase == "repair_needed" or "repair" in next_action):
            return next_action or "repair_needed"
        if node_id == "repair_needed" and (phase == "repair_needed" or "repair" in next_action):
            return next_action or "repair_needed"
        if node_id == "human_merge" and phase == "passed_waiting_human_merge":
            return "await_human_merge_confirmation"
        return ""

    def _blocked_diagnostics(self, run_dir: Path, run_data: dict[str, Any]) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        evaluator = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
        if isinstance(evaluator, dict):
            diagnostics.extend(self._evaluator_diagnostics(evaluator, run_dir / "evaluator-result.json"))
            rich_path, rich_evaluator = self._rich_evaluator_result(evaluator)
            if rich_path is not None and rich_evaluator is not None:
                diagnostics.extend(self._evaluator_diagnostics(rich_evaluator, rich_path))
        for filename, kind in (
            ("dirty-paths-result.json", "dirty_paths"),
            ("supply-chain-result.json", "supply_chain"),
            ("artifact-manifest.json", "artifact_manifest"),
            ("cleanup-result.json", "cleanup"),
            ("commit-result.json", "commit"),
        ):
            path = run_dir / filename
            payload = self._read_json(path, allowed_root=run_dir)
            if isinstance(payload, dict):
                diagnostics.extend(self._generic_diagnostics(kind, payload, path))
        if str(run_data.get("phase") or "") in BLOCKED_PHASES and not diagnostics:
            diagnostics.append(
                {
                    "kind": "run_phase",
                    "severity": "major",
                    "title": str(run_data.get("phase")),
                    "message": str(run_data.get("last_result") or run_data.get("next_action") or "run is blocked"),
                    "source": self._relative_artifact(run_dir / "run.json"),
                }
            )
        return diagnostics

    def _decision_summary(
        self,
        run_data: dict[str, Any],
        evaluator: dict[str, Any],
        rich_evaluator: dict[str, Any],
    ) -> dict[str, Any]:
        phase = str(run_data.get("phase") or "unknown")
        next_action = str(run_data.get("next_action") or "")
        reason = self._first_text(
            rich_evaluator.get("verdict_reason"),
            rich_evaluator.get("summary"),
            evaluator.get("verdict_reason"),
            evaluator.get("summary"),
            run_data.get("last_result"),
            next_action,
            phase,
        )

        labels = {
            "passed_waiting_human_merge": (True, "等待用户确认合入"),
            "stopped_blocked": (True, "需要处理阻塞"),
            "invalid_artifact": (True, "需要处理无效产物"),
            "stopped_no_action": (False, "无需进一步操作"),
            "stopped_budget": (False, "预算耗尽"),
        }
        if phase == "repair_needed":
            if next_action and "human" not in next_action.lower() and "manual" not in next_action.lower():
                requires_user_decision, decision_label = False, "自动修复后复验"
            else:
                requires_user_decision, decision_label = True, "需要修复后再验收"
        else:
            requires_user_decision, decision_label = labels.get(phase, (False, "继续自动执行"))
        return {
            "requires_user_decision": requires_user_decision,
            "decision_label": decision_label,
            "next_action": next_action,
            "reason": self._trim(redact_text(reason), 160),
        }

    def _acceptance_summary(
        self,
        evaluator: dict[str, Any],
        rich_evaluator: dict[str, Any],
        scenario_contract: dict[str, Any],
    ) -> dict[str, Any]:
        primary = rich_evaluator if rich_evaluator else evaluator
        fallback = evaluator if primary is rich_evaluator else rich_evaluator
        return {
            "status": self._first_text(primary.get("status"), fallback.get("status")),
            "scenarios": self._acceptance_scenarios(primary, fallback, scenario_contract),
            "checked": self._acceptance_checked(primary, fallback, scenario_contract),
            "evidence": self._acceptance_evidence(primary, fallback, scenario_contract),
            "rerun_commands": self._acceptance_rerun_commands(primary, fallback, scenario_contract),
        }

    def _acceptance_summary_for_run_dir(self, run_dir: Path) -> dict[str, Any]:
        evaluator = self._read_json(run_dir / "evaluator-result.json", allowed_root=run_dir)
        if not isinstance(evaluator, dict):
            evaluator = {}
        _, rich_evaluator = self._rich_evaluator_result(evaluator)
        if not isinstance(rich_evaluator, dict):
            rich_evaluator = {}
        return self._acceptance_summary(evaluator, rich_evaluator, self._scenario_contract(evaluator))

    def _governance_artifacts(self, run_dir: Path, evaluator: dict[str, Any]) -> dict[str, Any]:
        task_contract = self._read_json(run_dir / "task-contract.json", allowed_root=run_dir)
        if not isinstance(task_contract, dict):
            task_contract = {}
        formal_summary = evaluator.get("formal_verification")
        if not isinstance(formal_summary, dict):
            formal_summary = {}
        formal_paths = self._formal_verification_artifact_paths(run_dir, evaluator, formal_summary)
        task_contract_artifact_paths = self._safe_artifact_labels(task_contract.get("artifact_paths"))
        evaluator_scenarios = [
            {
                "scenario_id": self._first_text(scenario.get("scenario_id"), scenario.get("id"), "scenario"),
                "user_goal": self._trim(redact_text(self._first_text(scenario.get("user_goal"))), 220),
                "expected_outcomes": self._checked_items(scenario.get("expected_outcomes")),
                "failure_signals": self._checked_items(scenario.get("failure_signals")),
            }
            for scenario in self._contract_user_scenarios(task_contract)
        ]
        return {
            "formal_verification": formal_summary,
            "formal_verification_artifact_paths": formal_paths,
            "task_contract_artifact_paths": task_contract_artifact_paths,
            "evaluator_scenarios": evaluator_scenarios,
            "source_profile_snapshots": [
                path for path in task_contract_artifact_paths if path.endswith("-source-profile-snapshot.json")
            ],
        }

    def _formal_verification_artifact_paths(
        self,
        run_dir: Path,
        evaluator: dict[str, Any],
        formal_summary: dict[str, Any],
    ) -> list[str]:
        paths: list[str] = []
        for value in (evaluator.get("formal_verification_artifact_paths"), formal_summary.get("artifact_paths")):
            paths.extend(self._safe_artifact_labels(value))
        formal_dir = run_dir / "formal-verification"
        if formal_dir.exists():
            for path in sorted(formal_dir.glob("*.json")):
                if self._safe_file_under(path, run_dir) is not None:
                    paths.append(self._relative_artifact(path))
        return self._unique_nonempty(paths)

    def _governance_artifact_paths(self, governance_artifacts: dict[str, Any]) -> list[str]:
        paths: list[str] = []
        for key in (
            "formal_verification_artifact_paths",
            "task_contract_artifact_paths",
            "source_profile_snapshots",
        ):
            paths.extend(self._path_items(governance_artifacts.get(key)))
        return self._unique_nonempty(paths)

    def _path_items(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item]

    def _safe_artifact_labels(self, value: Any) -> list[str]:
        labels: list[str] = []
        if not isinstance(value, list):
            return labels
        for item in value:
            if not isinstance(item, str) or not item:
                continue
            try:
                safe_join(self.project_root, item)
            except ValueError:
                continue
            labels.append(item)
        return self._unique_nonempty(labels)

    def _parent_acceptance_summary(
        self,
        parent_data: dict[str, Any],
        parent_acceptance: dict[str, Any],
        child_runs: list[ChildRun],
    ) -> dict[str, Any]:
        child_acceptances = [
            (str(child.summary.get("run_id") or child.source.run_dir.name), self._acceptance_summary_for_run_dir(child.source.run_dir))
            for child in child_runs
        ]
        summaries_with_content = [
            (child_id, summary)
            for child_id, summary in child_acceptances
            if self._acceptance_has_content(summary)
        ]
        if not summaries_with_content:
            return parent_acceptance

        scenarios: list[dict[str, str]] = []
        checked: list[str] = []
        evidence: list[str] = []
        rerun_commands: list[str] = []
        for child_id, summary in summaries_with_content:
            for scenario in summary.get("scenarios", []):
                if not isinstance(scenario, dict):
                    continue
                scenario_id = self._first_text(scenario.get("scenario_id"), "scenario")
                scenarios.append(
                    {
                        "scenario_id": f"{child_id}:{scenario_id}",
                        "status": self._first_text(scenario.get("status")),
                        "summary": self._trim(f"{child_id}：{self._first_text(scenario.get('summary'))}", 220),
                    }
                )
            checked.extend(self._checked_items(summary.get("checked")))
            for item in self._checked_items(summary.get("evidence")):
                evidence.append(self._trim(f"{child_id}：{item}", 220))
            rerun_commands.extend(self._checked_items(summary.get("rerun_commands")))

        for item in self._checked_items(parent_acceptance.get("checked")):
            checked.append(item)
        for item in self._checked_items(parent_acceptance.get("evidence")):
            evidence.append(item)
        for item in self._checked_items(parent_acceptance.get("rerun_commands")):
            rerun_commands.append(item)

        return {
            "status": self._parent_acceptance_status(parent_data, [summary for _child_id, summary in child_acceptances]),
            "scenarios": self._dedupe_scenarios([
                *self._scenario_summaries(parent_acceptance.get("scenarios")),
                *scenarios,
            ]),
            "checked": self._unique_nonempty(checked),
            "evidence": self._unique_nonempty(evidence),
            "rerun_commands": self._unique_nonempty(rerun_commands),
        }

    def _acceptance_has_content(self, summary: dict[str, Any]) -> bool:
        return bool(
            self._first_text(summary.get("status"))
            or summary.get("scenarios")
            or summary.get("checked")
            or summary.get("evidence")
            or summary.get("rerun_commands")
        )

    def _parent_acceptance_status(self, parent_data: dict[str, Any], child_summaries: list[dict[str, Any]]) -> str:
        statuses = [self._first_text(summary.get("status")).lower() for summary in child_summaries]
        nonempty = [status for status in statuses if status]
        if any(status in {"fail", "failed"} for status in nonempty):
            return "fail"
        if any(status == "blocked" for status in nonempty):
            return "blocked"
        if nonempty and len(nonempty) == len(child_summaries) and all(status in {"pass", "passed"} for status in nonempty):
            return "pass"
        if nonempty:
            return "partial"
        return self._first_text(parent_data.get("last_result"))

    def _acceptance_scenarios(
        self,
        primary: dict[str, Any],
        fallback: dict[str, Any],
        scenario_contract: dict[str, Any],
    ) -> list[dict[str, str]]:
        scenarios = self._dedupe_scenarios(
            [
                *self._scenario_summaries(primary.get("scenario_results")),
                *self._scenario_summaries(fallback.get("scenario_results")),
            ]
        )
        contract_by_id = self._contract_scenarios_by_id(scenario_contract)
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id", "")
            contract = contract_by_id.get(scenario_id, {})
            if not scenario.get("summary") and contract:
                scenario["summary"] = self._trim(redact_text(str(contract.get("user_goal") or "")), 180)
        if not scenarios:
            scenario_id = self._first_text(primary.get("scenario_id"), fallback.get("scenario_id"))
            if scenario_id:
                contract = contract_by_id.get(scenario_id, {})
                scenarios.append(
                    {
                        "scenario_id": scenario_id,
                        "status": self._first_text(primary.get("status"), fallback.get("status")),
                        "summary": self._first_text(
                            primary.get("summary"),
                            primary.get("verdict_reason"),
                            fallback.get("summary"),
                            fallback.get("verdict_reason"),
                            contract.get("user_goal") if isinstance(contract, dict) else "",
                        ),
                    }
                )
        return scenarios

    def _dedupe_scenarios(self, scenarios: list[dict[str, str]]) -> list[dict[str, str]]:
        unique: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for scenario in scenarios:
            key = (
                scenario.get("scenario_id", ""),
                scenario.get("status", ""),
                scenario.get("summary", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(scenario)
        return unique

    def _scenario_summaries(self, value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        scenarios: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            scenarios.append(
                {
                    "scenario_id": self._first_text(item.get("scenario_id"), item.get("id"), item.get("name")),
                    "status": self._first_text(item.get("status"), item.get("verdict"), item.get("outcome")),
                    "summary": self._trim(
                        redact_text(
                            self._first_text(
                                item.get("summary"),
                                item.get("verdict_reason"),
                                item.get("message"),
                                item.get("title"),
                            )
                        ),
                        180,
                    ),
                }
            )
        return scenarios

    def _acceptance_checked(self, primary: dict[str, Any], fallback: dict[str, Any], scenario_contract: dict[str, Any]) -> list[str]:
        checked = self._checked_items(primary.get("checked"))
        if not checked:
            checked = self._checked_items(fallback.get("checked"))
        if not checked:
            checked = self._contract_list_items(scenario_contract, "steps")
        return checked

    def _checked_items(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        checked: list[str] = []
        for item in value:
            if isinstance(item, str):
                checked.append(self._trim(redact_text(item), 120))
            elif isinstance(item, dict):
                checked.append(
                    self._trim(
                        redact_text(
                            self._first_text(
                                item.get("label"),
                                item.get("name"),
                                item.get("id"),
                                item.get("text"),
                                item.get("summary"),
                                json.dumps(item, ensure_ascii=False),
                            )
                        ),
                        120,
                    )
                )
            elif item is not None:
                checked.append(self._trim(redact_text(str(item)), 120))
        return self._unique_nonempty(checked)

    def _acceptance_evidence(self, primary: dict[str, Any], fallback: dict[str, Any], scenario_contract: dict[str, Any]) -> list[str]:
        evidence: list[str] = []
        for payload in (primary, fallback):
            evidence.extend(self._scenario_evidence(payload.get("scenario_results")))
            evidence.extend(self._short_evidence_items(payload.get("browser_evidence")))
            evidence.extend(self._environment_check_evidence(payload.get("environment_checks")))
            evidence.extend(self._finding_evidence(payload.get("findings")))
        evidence.extend(self._contract_list_items(scenario_contract, "expected_outcomes"))
        return self._unique_nonempty(evidence)

    def _short_evidence_items(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [self._evidence_text(item) for item in value]

    def _environment_check_evidence(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [f"environment_check: {self._evidence_text(item)}" for item in value]

    def _scenario_evidence(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        evidence: list[str] = []
        for scenario in value:
            if not isinstance(scenario, dict):
                continue
            scenario_id = self._first_text(scenario.get("scenario_id"), scenario.get("id"), scenario.get("name"), "scenario")
            for item in self._short_evidence_items(scenario.get("evidence")):
                evidence.append(self._trim(f"{redact_text(scenario_id)}: {item}", 220))
        return evidence

    def _finding_evidence(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        evidence: list[str] = []
        for finding in value:
            if not isinstance(finding, dict):
                continue
            title = self._first_text(finding.get("id"), finding.get("category"), finding.get("summary"), "finding")
            redacted_title = redact_text(title)
            action = self._first_text(finding.get("recommended_action"), finding.get("summary"))
            if action:
                evidence.append(self._trim(f"{redacted_title}: {redact_text(action)}", 220))
            for item in self._redacted_evidence(finding.get("evidence", [])):
                evidence.append(self._trim(f"{redacted_title}: {item}", 220))
        return evidence

    def _acceptance_rerun_commands(self, primary: dict[str, Any], fallback: dict[str, Any], scenario_contract: dict[str, Any]) -> list[str]:
        commands: list[str] = []
        for payload in (primary, fallback):
            value = payload.get("rerun_commands")
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, str):
                    commands.append(self._trim(redact_text(item), 220))
        if not commands:
            for scenario in self._contract_user_scenarios(scenario_contract):
                entrypoint = scenario.get("entrypoint")
                if isinstance(entrypoint, str) and entrypoint:
                    commands.append(self._trim(redact_text(entrypoint), 220))
        return self._unique_nonempty(commands)

    def _scenario_contract(self, evaluator: dict[str, Any]) -> dict[str, Any]:
        task_id = evaluator.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return {}
        try:
            path = safe_join(self.project_root / "docs" / "harness" / "evaluator-scenarios", f"{task_id}.json")
        except ValueError:
            return {}
        payload = self._read_json(path, allowed_root=self.project_root)
        return payload if isinstance(payload, dict) else {}

    def _contract_scenarios_by_id(self, scenario_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
        scenarios: dict[str, dict[str, Any]] = {}
        for scenario in self._contract_user_scenarios(scenario_contract):
            scenario_id = scenario.get("scenario_id")
            if isinstance(scenario_id, str) and scenario_id:
                scenarios[scenario_id] = scenario
        return scenarios

    def _contract_user_scenarios(self, scenario_contract: dict[str, Any]) -> list[dict[str, Any]]:
        value = scenario_contract.get("user_scenarios")
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _contract_list_items(self, scenario_contract: dict[str, Any], key: str) -> list[str]:
        values: list[str] = []
        for scenario in self._contract_user_scenarios(scenario_contract):
            items = scenario.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, str):
                    values.append(self._trim(redact_text(item), 180))
                elif item is not None:
                    values.append(self._evidence_text(item))
        return self._unique_nonempty(values)

    def _evidence_text(self, value: Any) -> str:
        if isinstance(value, str):
            raw = value
        else:
            raw = json.dumps(value, ensure_ascii=False)
        return self._trim(redact_text(raw), 220)

    def _first_text(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _unique_nonempty(self, values: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _evaluator_diagnostics(self, evaluator: dict[str, Any], path: Path) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        findings = evaluator.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                diagnostics.append(
                    {
                        "kind": "evaluator_finding",
                        "severity": str(finding.get("severity") or "major"),
                        "title": str(finding.get("id") or finding.get("category") or "evaluator finding"),
                        "message": redact_text(str(finding.get("recommended_action") or finding.get("summary") or "")),
                        "evidence": self._redacted_evidence(finding.get("evidence", [])),
                        "source": self._relative_artifact(path),
                    }
                )
        status = str(evaluator.get("status") or "")
        if status in {"fail", "failed", "blocked"} and not diagnostics:
            message = str(evaluator.get("stderr") or evaluator.get("stdout") or evaluator.get("verdict_reason") or evaluator.get("summary") or "")
            diagnostics.append(
                {
                    "kind": "evaluator_result",
                    "severity": "major",
                    "title": f"evaluator {status}",
                    "message": self._trim(redact_text(message), 160),
                    "returncode": evaluator.get("returncode"),
                    "source": self._relative_artifact(path),
                }
            )
        return diagnostics

    def _redacted_evidence(self, evidence: Any) -> list[str]:
        if not isinstance(evidence, list):
            return []
        redacted: list[str] = []
        for item in evidence:
            if isinstance(item, str):
                redacted.append(redact_text(item))
            elif item is not None:
                redacted.append(redact_text(json.dumps(item, ensure_ascii=False)))
        return redacted

    def _generic_diagnostics(self, kind: str, payload: dict[str, Any], path: Path) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        items = payload.get("findings") or payload.get("errors") or payload.get("diagnostics") or []
        if isinstance(items, list):
            for item in items:
                diagnostics.append(
                    {
                        "kind": kind,
                        "severity": "major",
                        "title": kind,
                        "message": self._trim(redact_text(json.dumps(item, ensure_ascii=False)), 160),
                        "source": self._relative_artifact(path),
                    }
                )
        status = str(payload.get("status") or "")
        if status in {"fail", "failed", "blocked", "error"} and not diagnostics:
            diagnostics.append(
                {
                    "kind": kind,
                    "severity": "major",
                    "title": f"{kind} {status}",
                    "message": self._trim(redact_text(json.dumps(payload, ensure_ascii=False)), 160),
                    "source": self._relative_artifact(path),
                }
            )
        return diagnostics

    def _collect_logs(self, run_dir: Path) -> list[LogEntry]:
        logs: list[LogEntry] = []
        for pattern in LOG_GLOBS:
            for path in sorted(run_dir.glob(pattern)):
                safe_path = self._safe_file_under(path, run_dir)
                if safe_path is None:
                    continue
                stream = "stderr" if path.name.endswith(".stderr.log") else "stdout"
                logs.append(
                    LogEntry(
                        self._relative_artifact(path),
                        stream,
                        redact_text(safe_path.read_text(encoding="utf-8", errors="replace")),
                        self._mtime_iso(safe_path),
                    )
                )
        evaluator_path = run_dir / "evaluator-result.json"
        evaluator = self._read_json(evaluator_path, allowed_root=run_dir)
        if isinstance(evaluator, dict):
            logs.extend(self._inline_logs(evaluator, evaluator_path, run_dir))
            rich_path, rich_evaluator = self._rich_evaluator_result(evaluator)
            if rich_path is not None and rich_evaluator is not None:
                logs.extend(self._inline_logs(rich_evaluator, rich_path, rich_path.parent))
            scenario_path = evaluator.get("scenario_command_results_path")
            if isinstance(scenario_path, str) and scenario_path:
                scenario_result = self._resolve_artifact_reference(scenario_path, run_dir, allowed_roots=[run_dir])
                if scenario_result is not None:
                    scenario_payload = self._read_json(scenario_result, allowed_root=run_dir)
                    if isinstance(scenario_payload, dict):
                        logs.extend(self._inline_logs(scenario_payload, scenario_result, run_dir))
        return sorted(logs, key=lambda log: (log.updated_at, log.source, log.stream))

    def _inline_logs(self, payload: dict[str, Any], source_path: Path, run_dir: Path) -> list[LogEntry]:
        logs: list[LogEntry] = []
        source_dir = source_path.parent

        def visit(value: Any, prefix: str = "") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    lowered = key.lower()
                    if lowered in {"stdout", "stderr"} and isinstance(child, str) and child:
                        logs.append(LogEntry(f"{source_path.name}:{lowered}", lowered, redact_text(child), self._mtime_iso(source_path)))
                    elif lowered in {"stdout_path", "stderr_path"} and isinstance(child, str) and child:
                        stream = lowered.split("_", 1)[0]
                        path = self._resolve_artifact_reference(
                            child,
                            source_dir,
                            allowed_roots=[run_dir, source_dir],
                            relative_roots=[run_dir],
                        )
                        if path is not None:
                            logs.append(
                                LogEntry(
                                    f"{self._relative_artifact(path)}",
                                    stream,
                                    redact_text(path.read_text(encoding="utf-8", errors="replace")),
                                    self._mtime_iso(path),
                                )
                            )
                    else:
                        visit(child, lowered)
            elif isinstance(value, list):
                for child in value:
                    visit(child, prefix)

        visit(payload)
        return logs

    def _structured_events(self, run_dir: Path) -> list[Event]:
        events_path = run_dir / "events.jsonl"
        safe_path = self._safe_file_under(events_path, run_dir)
        if safe_path is None:
            return []
        events: list[Event] = []
        updated_at = self._mtime_iso(safe_path)
        try:
            lines = safe_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            kind = str(payload.get("event_type") or "event")
            summary = str(payload.get("summary") or "")
            timestamp = str(payload.get("timestamp") or updated_at)
            events.append(
                Event(
                    kind,
                    self._relative_artifact(safe_path),
                    self._trim(redact_text(summary), 180),
                    timestamp,
                )
            )
        return events

    def _session_events(self, run_id: str) -> list[Event]:
        sessions_dir = self.project_root / ".codex" / "sessions"
        if not sessions_dir.exists():
            return []
        events: list[Event] = []
        for safe_path in self._safe_jsonl_files(sessions_dir):
            try:
                if safe_path.stat().st_size > SESSION_FILE_MAX_BYTES:
                    continue
                lines = safe_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines[-SESSION_EVENT_LIMIT:]:
                if len(events) >= SESSION_EVENT_LIMIT:
                    break
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict) or payload.get("run_id") != run_id:
                    continue
                event = self._session_event_from_payload(payload, safe_path)
                if event is not None:
                    events.append(event)
            if len(events) >= SESSION_EVENT_LIMIT:
                break
        return events

    def _safe_jsonl_files(self, root: Path) -> list[Path]:
        safe_paths: list[tuple[float, Path]] = []
        for path in root.rglob("*.jsonl"):
            safe_path = self._safe_file_under(path, root)
            if safe_path is None:
                continue
            try:
                safe_paths.append((safe_path.stat().st_mtime, safe_path))
            except OSError:
                continue
        return [path for _mtime, path in sorted(safe_paths, reverse=True)]

    def _session_event_from_payload(self, payload: dict[str, Any], source_path: Path) -> Event | None:
        raw_type = str(payload.get("type") or payload.get("event") or "").lower()
        agent = str(payload.get("agent") or "").strip()
        timestamp = str(payload.get("timestamp") or payload.get("created_at") or self._mtime_iso(source_path))
        source = self._relative_artifact(source_path)
        if raw_type in {"agent_message", "assistant_message", "message"}:
            message = str(payload.get("message") or payload.get("content") or "")
            if not message:
                return None
            prefix = f"{agent}: " if agent else ""
            return Event("agent", source, self._trim(redact_text(prefix + message), 180), timestamp)
        if raw_type in {"token_usage", "tokens", "usage"}:
            tokens = payload.get("tokens") or payload.get("usage") or {}
            if isinstance(tokens, dict):
                parts = [f"{key}={value}" for key, value in tokens.items()]
                token_message = ", ".join(parts)
            else:
                token_message = str(tokens)
            prefix = f"{agent}: " if agent else ""
            return Event("token", source, self._trim(redact_text(prefix + token_message), 180), timestamp)
        if raw_type in {"tool_call", "tool"}:
            name = str(payload.get("name") or payload.get("tool") or "")
            return Event("tool", source, self._trim(redact_text(name or json.dumps(payload, ensure_ascii=False)), 180), timestamp)
        if raw_type in {"skill", "skill_use"}:
            name = str(payload.get("name") or payload.get("skill") or "")
            return Event("skill", source, self._trim(redact_text(name or json.dumps(payload, ensure_ascii=False)), 180), timestamp)
        return None

    def _rich_evaluator_result(self, evaluator: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
        task_id = evaluator.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return None, None
        task_dir = self._safe_task_evaluation_dir(task_id)
        if task_dir is None or not task_dir.exists():
            return None, None
        final_bundle_id = evaluator.get("final_bundle_id")
        if isinstance(final_bundle_id, str) and final_bundle_id:
            try:
                final_result = safe_join(task_dir, f"{final_bundle_id}/result.json")
            except ValueError:
                final_result = None
            safe_final_result = self._safe_file_under(final_result, task_dir) if final_result is not None else None
            if safe_final_result is not None:
                payload = self._read_json(safe_final_result, allowed_root=safe_final_result.parent)
                if isinstance(payload, dict):
                    return safe_final_result, payload
        candidates = [
            safe_path
            for path in task_dir.glob("**/result.json")
            if (safe_path := self._safe_file_under(path, task_dir)) is not None
        ]
        if not candidates:
            return None, None
        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        payload = self._read_json(latest, allowed_root=latest.parent)
        if not isinstance(payload, dict):
            return None, None
        return latest, payload

    def _safe_task_evaluation_dir(self, task_id: str) -> Path | None:
        try:
            return safe_join(self.project_root / ".codex" / "evaluations" / "tasks", task_id)
        except ValueError:
            return None

    def _artifact_paths(self, run_dir: Path) -> list[str]:
        paths = [
            path
            for path in run_dir.rglob("*")
            if self._safe_file_under(path, run_dir) is not None
        ]
        return [self._relative_artifact(path) for path in sorted(paths)]

    def _direct_artifact_files(self, run_dir: Path) -> list[Path]:
        safe_paths: list[tuple[float, Path]] = []
        for path in run_dir.iterdir():
            safe_path = self._safe_file_under(path, run_dir)
            if safe_path is None:
                continue
            try:
                safe_paths.append((safe_path.stat().st_mtime, safe_path))
            except OSError:
                continue
        return [path for _mtime, path in sorted(safe_paths)]

    def _read_json(self, path: Path, allowed_root: Path | None = None) -> Any:
        safe_path = self._safe_file_under(path, allowed_root or self.project_root)
        if safe_path is None:
            return None
        try:
            return json.loads(safe_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _health(self, phase: str) -> str:
        if phase in BLOCKED_PHASES:
            return "blocked"
        if phase in COMPLETED_PHASES:
            return "completed"
        return "progressing"

    def _updated_at(self, run_dir: Path) -> str:
        mtimes = [path.stat().st_mtime for path in self._direct_artifact_files(run_dir)]
        if not mtimes:
            mtimes = [run_dir.stat().st_mtime]
        return self._timestamp_iso(max(mtimes))

    def _mtime_iso(self, path: Path) -> str:
        return self._timestamp_iso(path.stat().st_mtime)

    def _timestamp_iso(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def _relative_artifact(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root))
        except ValueError:
            return path.name

    def _source_path(self, run_dir: Path) -> str:
        try:
            return str(run_dir.resolve().relative_to(self.project_root))
        except (OSError, ValueError):
            return run_dir.name

    def _resolve_artifact_reference(
        self,
        reference: str,
        base_dir: Path,
        allowed_roots: list[Path],
        relative_roots: list[Path] | None = None,
    ) -> Path | None:
        ref_path = Path(reference)
        extra_roots = list(relative_roots or [])
        if ref_path.is_absolute():
            candidates = [ref_path]
        else:
            candidates = [base_dir / ref_path, *(root / ref_path for root in extra_roots), self.project_root / ref_path]
        for candidate in candidates:
            safe_path = self._safe_file_under(candidate, self.project_root)
            if safe_path is not None and self._is_under_any(safe_path, allowed_roots):
                return safe_path
        return None

    def _is_under_any(self, path: Path, roots: list[Path]) -> bool:
        for root in roots:
            try:
                path.resolve().relative_to(root.resolve())
                return True
            except (OSError, ValueError):
                continue
        return False

    def _safe_file_under(self, path: Path, root: Path) -> Path | None:
        try:
            resolved_root = root.resolve()
            resolved_path = path.resolve()
            resolved_path.relative_to(resolved_root)
            resolved_path.relative_to(self.project_root)
        except (OSError, ValueError):
            return None
        if not resolved_path.is_file():
            return None
        return resolved_path

    def _safe_dir_under(self, path: Path, root: Path) -> Path | None:
        try:
            resolved_root = root.resolve()
            resolved_path = path.resolve()
            resolved_path.relative_to(resolved_root)
            resolved_path.relative_to(self.project_root)
        except (OSError, ValueError):
            return None
        if not resolved_path.is_dir():
            return None
        return resolved_path

    def _safe_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    def _trim(self, text: str, limit: int = 96) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1] + "…"

    def _task_description(self, run_data: dict[str, Any]) -> str:
        return " ".join(str(run_data.get("requirement") or run_data.get("task_id") or FALLBACK_SUMMARY).split())

    def _summarize_log(self, content: str) -> str:
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        return self._trim(first_line or FALLBACK_SUMMARY, 120)
