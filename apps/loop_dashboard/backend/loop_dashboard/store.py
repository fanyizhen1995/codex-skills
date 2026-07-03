from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AgentSummary, Event, FlowNode, LogEntry
from .redaction import redact_text


COMPLETED_PHASES = {"passed_waiting_human_merge", "stopped_no_action", "stopped_budget", "stopped_blocked"}
BLOCKED_PHASES = {"stopped_blocked", "repair_needed", "invalid_artifact"}
LOG_GLOBS = ("*-attempt-*.stdout.log", "*-attempt-*.stderr.log")
FALLBACK_SUMMARY = "暂无可用摘要"


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
        }

    def list_runs(self) -> list[dict[str, Any]]:
        if not self.loop_runs_dir.exists():
            return []
        runs = [self._load_run_summary(path) for path in self.loop_runs_dir.iterdir() if path.is_dir()]
        return sorted(runs, key=lambda run: (run.get("updated_at", ""), run.get("run_id", "")), reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run_dir = self._run_dir(run_id)
        if run_dir is None or not run_dir.is_dir() or not (run_dir / "run.json").exists():
            return None
        summary = self._load_run_summary(run_dir)
        run_data = self._read_json(run_dir / "run.json")
        planner = self._read_json(run_dir / "planner-output.json")
        if not isinstance(run_data, dict):
            run_data = {}
        if not isinstance(planner, dict):
            planner = {}
        summary.update(
            {
                "constraints": run_data.get("constraints", []),
                "stop_conditions": run_data.get("stop_conditions") or planner.get("stop_conditions", []),
                "attempts": run_data.get("attempts", {}),
                "limits": run_data.get("limits", {}),
                "allowed_paths": planner.get("allowed_paths", run_data.get("allowed_paths", [])),
                "denylist_paths": planner.get("denylist_paths", run_data.get("denylist_paths", [])),
                "flow_nodes": [node.to_dict() for node in self._flow_nodes(run_dir, run_data)],
            }
        )
        return summary

    def get_events(self, run_id: str) -> list[dict[str, Any]] | None:
        run_dir = self._run_dir(run_id)
        if run_dir is None or not run_dir.is_dir():
            return None
        events: list[Event] = []
        for path in sorted(run_dir.iterdir(), key=lambda item: item.stat().st_mtime):
            if not path.is_file():
                continue
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
        return [event.to_dict() for event in sorted(events, key=lambda event: event.updated_at)]

    def get_logs(self, run_id: str) -> list[dict[str, Any]] | None:
        run_dir = self._run_dir(run_id)
        if run_dir is None or not run_dir.is_dir():
            return None
        return [log.to_dict() for log in self._collect_logs(run_dir)]

    def _run_dir(self, run_id: str) -> Path | None:
        try:
            return safe_join(self.loop_runs_dir, run_id)
        except ValueError:
            return None

    def _load_run_summary(self, run_dir: Path) -> dict[str, Any]:
        run_json = run_dir / "run.json"
        run_data = self._read_json(run_json)
        if not isinstance(run_data, dict):
            return self._invalid_summary(run_dir)
        planner = self._read_json(run_dir / "planner-output.json")
        if not isinstance(planner, dict):
            planner = {}
        phase = str(run_data.get("phase") or "unknown")
        completed = phase in COMPLETED_PHASES
        artifacts = self._artifact_paths(run_dir)
        return {
            "run_id": str(run_data.get("run_id") or run_dir.name),
            "project_root": str(self.project_root),
            "task_summary": self._trim(str(run_data.get("requirement") or run_data.get("task_id") or FALLBACK_SUMMARY)),
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

    def _invalid_summary(self, run_dir: Path) -> dict[str, Any]:
        diagnostic = {
            "kind": "invalid_artifact",
            "severity": "critical",
            "title": "Invalid run artifact",
            "message": "run.json could not be parsed",
            "source": self._relative_artifact(run_dir / "run.json"),
        }
        return {
            "run_id": run_dir.name,
            "project_root": str(self.project_root),
            "task_summary": "invalid_artifact",
            "policy": "",
            "phase": "invalid_artifact",
            "last_result": "invalid_artifact",
            "next_action": "",
            "health": "blocked",
            "updated_at": self._updated_at(run_dir),
            "completed": False,
            "agents": self._empty_agents(),
            "blocked_diagnostics": [diagnostic],
            "artifact_paths": self._artifact_paths(run_dir),
        }

    def _agents(self, run_dir: Path, run_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        attempts = run_data.get("attempts") if isinstance(run_data.get("attempts"), dict) else {}
        next_action = str(run_data.get("next_action") or "")
        planner = self._read_json(run_dir / "planner-output.json")
        generator = self._read_json(run_dir / "generator-result.json")
        evaluator = self._read_json(run_dir / "evaluator-result.json")
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
        artifact_paths = [self._relative_artifact(path) for path in self._agent_artifacts(run_dir, name)]
        data = payload if isinstance(payload, dict) else {}
        attempt = int(data.get("attempt") or attempts.get(name) or self._attempt_from_logs(run_dir, name) or 0)
        status = str(data.get("status") or ("ready" if data else "missing"))
        current_action = next_action if name in next_action else ""
        last_result = self._structured_summary(name, data) or self._log_summary(run_dir, name) or FALLBACK_SUMMARY
        return AgentSummary(name, status, attempt, current_action, last_result, artifact_paths)

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
            parts = path.name.split("-attempt-", 1)[-1].split(".", 1)[0]
            if parts.isdigit():
                attempts.append(int(parts))
        return max(attempts, default=0)

    def _log_summary(self, run_dir: Path, name: str) -> str:
        for path in self._agent_artifacts(run_dir, name):
            if path.suffix == ".log":
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return self._trim(redact_text(text), 96)
        return ""

    def _flow_nodes(self, run_dir: Path, run_data: dict[str, Any]) -> list[FlowNode]:
        policy = str(run_data.get("policy") or "demand_development")
        if policy == "autonomous_knowledge":
            labels = [("preflight", "Preflight"), ("planner", "Planner"), ("crawler", "Crawler"), ("curator", "Curator"), ("evaluator", "Evaluator")]
        else:
            labels = [("preflight", "Preflight"), ("planner", "Planner"), ("generator", "Generator"), ("evaluator", "Evaluator"), ("human_merge", "Human Merge")]
        phase = str(run_data.get("phase") or "")
        next_action = str(run_data.get("next_action") or "")
        evaluator = self._read_json(run_dir / "evaluator-result.json")
        evaluator_status = evaluator.get("status") if isinstance(evaluator, dict) else ""
        nodes: list[FlowNode] = []
        for node_id, label in labels:
            status = "waiting"
            if node_id == "preflight":
                status = "done"
            elif node_id == "planner":
                status = "done" if (run_dir / "planner-output.json").exists() else self._node_pending("planner", next_action)
            elif node_id in {"generator", "crawler", "curator"}:
                result_name = "generator-result.json" if node_id == "generator" else f"{node_id}-result.json"
                status = self._node_pending(node_id, next_action)
                if status != "running" and (run_dir / result_name).exists():
                    status = "done"
            elif node_id == "evaluator":
                if phase in BLOCKED_PHASES or evaluator_status in {"fail", "failed", "blocked"}:
                    status = "blocked"
                elif evaluator_status == "pass" or phase in COMPLETED_PHASES:
                    status = "done"
                else:
                    status = self._node_pending("evaluator", next_action)
            elif node_id == "human_merge":
                status = "waiting" if phase == "passed_waiting_human_merge" else "waiting"
            if node_id in next_action and status == "waiting":
                status = "running"
            nodes.append(FlowNode(node_id, label, status))
        return nodes

    def _node_pending(self, node_id: str, next_action: str) -> str:
        return "running" if node_id in next_action else "waiting"

    def _blocked_diagnostics(self, run_dir: Path, run_data: dict[str, Any]) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        evaluator = self._read_json(run_dir / "evaluator-result.json")
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
            payload = self._read_json(path)
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
                        "message": str(finding.get("recommended_action") or finding.get("summary") or ""),
                        "evidence": finding.get("evidence", []),
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
                stream = "stderr" if path.name.endswith(".stderr.log") else "stdout"
                logs.append(LogEntry(self._relative_artifact(path), stream, redact_text(path.read_text(encoding="utf-8", errors="replace")), self._mtime_iso(path)))
        evaluator_path = run_dir / "evaluator-result.json"
        evaluator = self._read_json(evaluator_path)
        if isinstance(evaluator, dict):
            logs.extend(self._inline_logs(evaluator, evaluator_path, run_dir))
            rich_path, rich_evaluator = self._rich_evaluator_result(evaluator)
            if rich_path is not None and rich_evaluator is not None:
                logs.extend(self._inline_logs(rich_evaluator, rich_path, rich_path.parent))
            scenario_path = evaluator.get("scenario_command_results_path")
            if isinstance(scenario_path, str) and scenario_path:
                try:
                    scenario_result = safe_join(run_dir, scenario_path)
                except ValueError:
                    scenario_result = None
                if scenario_result is not None and scenario_result.exists():
                    scenario_payload = self._read_json(scenario_result)
                    if isinstance(scenario_payload, dict):
                        logs.extend(self._inline_logs(scenario_payload, scenario_result, run_dir))
        return sorted(logs, key=lambda log: (log.updated_at, log.source, log.stream))

    def _inline_logs(self, payload: dict[str, Any], source_path: Path, run_dir: Path) -> list[LogEntry]:
        logs: list[LogEntry] = []

        def visit(value: Any, prefix: str = "") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    lowered = key.lower()
                    if lowered in {"stdout", "stderr"} and isinstance(child, str) and child:
                        logs.append(LogEntry(f"{source_path.name}:{lowered}", lowered, redact_text(child), self._mtime_iso(source_path)))
                    elif lowered in {"stdout_path", "stderr_path"} and isinstance(child, str) and child:
                        stream = lowered.split("_", 1)[0]
                        try:
                            path = safe_join(run_dir, child)
                        except ValueError:
                            continue
                        if path.exists() and path.is_file():
                            logs.append(LogEntry(f"{self._relative_artifact(path)}", stream, redact_text(path.read_text(encoding="utf-8", errors="replace")), self._mtime_iso(path)))
                    else:
                        visit(child, lowered)
            elif isinstance(value, list):
                for child in value:
                    visit(child, prefix)

        visit(payload)
        return logs

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
            if final_result is not None and final_result.exists():
                payload = self._read_json(final_result)
                if isinstance(payload, dict):
                    return final_result, payload
        candidates = [path for path in task_dir.glob("**/result.json") if path.is_file()]
        if not candidates:
            return None, None
        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        payload = self._read_json(latest)
        if not isinstance(payload, dict):
            return None, None
        return latest, payload

    def _safe_task_evaluation_dir(self, task_id: str) -> Path | None:
        try:
            return safe_join(self.project_root / ".codex" / "evaluations" / "tasks", task_id)
        except ValueError:
            return None

    def _artifact_paths(self, run_dir: Path) -> list[str]:
        return [self._relative_artifact(path) for path in sorted(run_dir.iterdir()) if path.is_file()]

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _health(self, phase: str) -> str:
        if phase in BLOCKED_PHASES:
            return "blocked"
        if phase in COMPLETED_PHASES:
            return "completed"
        return "progressing"

    def _updated_at(self, run_dir: Path) -> str:
        mtimes = [path.stat().st_mtime for path in run_dir.iterdir() if path.is_file()]
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

    def _trim(self, text: str, limit: int = 96) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1] + "…"

    def _summarize_log(self, content: str) -> str:
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        return self._trim(first_line or FALLBACK_SUMMARY, 120)
