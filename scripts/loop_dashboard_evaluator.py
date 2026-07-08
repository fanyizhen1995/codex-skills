#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.harness_evaluator_scenarios import load_task_scenarios
    from scripts.harness_loop_governance import validate_governance_preflight_evidence
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.harness_evaluator_scenarios import load_task_scenarios
    from scripts.harness_loop_governance import validate_governance_preflight_evidence


SCENARIO_ID = "LOOP-DASHBOARD-CLICK-SMOKE"
GOVERNANCE_TASK_ID = "ai-infra-loop-governance-dev-01"
GOVERNANCE_PARENT_RUN_ID = "ai-infra-loop-governance-dev"
GOVERNANCE_EXPANSION_RUN_ID = "ai-infra-expansion-2026-07-07-r10"
GOVERNANCE_OUTPUT_DIR_NAME = "ai-infra-loop-governance-dev-01"
GOVERNANCE_DASHBOARD_URL = "http://127.0.0.1:8766"
GOVERNANCE_CRAWLER_HEALTH_URL = "http://127.0.0.1:8765/api/health"
GOVERNANCE_FRONTEND_URL = "http://127.0.0.1:5173/"
SENSITIVE_FIELD_NAMES = {
    "token",
    "cookie",
    "secret",
    "password",
    "credential",
    "credentials",
    "authorization",
    "auth_ref",
    "access_token",
    "refresh_token",
    "api_key",
    "client_secret",
}
SENSITIVE_VALUE_MARKERS = (
    "bearer ",
    "authorization:",
    "ghp_",
    "github_pat_",
    "xoxb-",
    "xoxp-",
    "sk-",
)
CHECKED = [
    "打开 Loop Dashboard 并确认标题、项目路径和运行目录可见",
    "选择运行记录并查看完整任务摘要",
    "确认页面为左侧选运行、右侧看结论的两栏结构",
    "通过 API 验证父需求、子任务顺序、旧单任务兼容和冲突诊断",
    "通过 API 验证 unsafe run_id 返回 404 且不绕过 store safe-id",
    "通过 tabs 查看概览、子任务、Agent 结果、验收、日志、阻塞诊断和产物",
    "查看流程图中的当前阶段、跳过节点和人工合并节点",
    "查看父需求概览 tab 中的多子任务进度和每个子任务状态",
    "查看父需求子任务 tab 中的完整 child 描述、agent 动作、验收结果和 artifact 路径",
    "查看 Planner、Generator、Evaluator 的状态说明",
    "查看父需求 Agent 结果 tab 中按子任务聚合的 Planner、Generator、Evaluator 说明",
    "确认 evaluator 验证功能实现完整性和设计/mock 匹配，并在验收 tab 中可见",
    "查看验收 tab 中的模拟用户验收场景",
    "查看审计与 Skill tab 中的 Auditor 结论、open must_fix、确定性信号和当前项目 Skill 使用情况",
    "查看阻塞诊断 tab 中的 evaluator finding",
    "查看父需求子任务队列、冲突父需求诊断和移动端父子布局",
    "在日志 tab 中按 Agent、日志类型和关键词过滤原始日志",
    "确认父子任务事件和日志中的敏感 token 已脱敏",
    "切换查看已完成、无需操作、预算耗尽和阻塞运行",
    "查看项目 worktree 中的已完成历史运行，并确认详情展示来源路径",
    "在 390px 移动端宽度确认页面没有横向溢出",
]


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.name == GOVERNANCE_OUTPUT_DIR_NAME:
        return run_governance_evaluator(repo_root, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    port = args.port if args.port is not None else find_free_port()
    dashboard_url = f"http://127.0.0.1:{port}"
    server: subprocess.Popen[str] | None = None
    fixture_root: Path | None = None

    try:
        with tempfile.TemporaryDirectory(prefix="loop-dashboard-fixture-") as tmp:
            fixture_root = Path(tmp)
            seed_fixture_project(fixture_root)
            server = start_dashboard(repo_root, fixture_root, port)
            wait_for_dashboard(dashboard_url, fixture_root, server=server)
            demand_multi_task_api = verify_demand_multi_task_api(dashboard_url)
            browser_evidence = run_browser_checks(dashboard_url, output_dir)
            terminate_process(server)
            server_output = collect_server_output(server)
            server = None
            write_json(
                output_dir / "result.json",
                {
                    "status": "pass",
                    "scenario_id": SCENARIO_ID,
                    "summary": "浏览器模拟用户完成 Loop 看板核心验收场景。",
                    "scenario_results": [
                        {
                            "scenario_id": SCENARIO_ID,
                            "status": "pass",
                            "summary": "模拟用户查看任务、流程、agent、验收摘要、诊断、日志过滤、完成运行和移动端布局。",
                            "evidence": CHECKED,
                        }
                    ],
                    "checked": CHECKED,
                    "rerun_commands": [
                        "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
                    ],
                    "dashboard_url": dashboard_url,
                    "project_root": str(fixture_root.resolve()),
                    "demand_multi_task_api": demand_multi_task_api,
                    "browser_evidence": browser_evidence,
                    "server_stdout": server_output["stdout"],
                    "server_stderr": server_output["stderr"],
                },
            )
        return 0
    except Exception as exc:
        if server is not None:
            terminate_process(server)
        server_output = collect_server_output(server)
        write_json(
            output_dir / "result.json",
            failure_payload(exc, dashboard_url, fixture_root, server_output),
        )
        print(f"loop dashboard evaluator failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            terminate_process(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Loop Dashboard browser-click evaluator.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def run_governance_evaluator(
    repo_root: Path,
    output_dir: Path,
    *,
    dashboard_url: str = GOVERNANCE_DASHBOARD_URL,
    crawler_health_url: str = GOVERNANCE_CRAWLER_HEALTH_URL,
    frontend_url: str = GOVERNANCE_FRONTEND_URL,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = evaluate_governance_repo(
            repo_root,
            dashboard_url=dashboard_url,
            crawler_health_url=crawler_health_url,
            frontend_url=frontend_url,
        )
    except Exception as exc:
        result = governance_failure_payload(exc)
        write_json(output_dir / "result.json", result)
        print(f"loop dashboard governance evaluator failed: {exc}", file=sys.stderr)
        return 1
    write_json(output_dir / "result.json", result)
    return 0 if result["status"] == "pass" else 1


def evaluate_governance_repo(
    repo_root: Path,
    *,
    dashboard_url: str,
    crawler_health_url: str,
    frontend_url: str,
) -> dict[str, Any]:
    contract = load_task_scenarios(repo_root, GOVERNANCE_TASK_ID)
    scenario_ids = [str(scenario.get("scenario_id", "")) for scenario in contract["user_scenarios"]]
    expected_ids = [f"E2E-{index}" for index in range(8)]
    checked: list[str] = []
    diagnostics: list[str] = []
    scenario_results: list[dict[str, Any]] = []

    def record(
        scenario_id: str,
        summary: str,
        *,
        ok: bool,
        evidence: list[str] | None = None,
        scenario_diagnostics: list[str] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "scenario_id": scenario_id,
            "status": "pass" if ok else "fail",
            "summary": summary,
            "evidence": evidence or [],
        }
        if scenario_diagnostics:
            entry["diagnostics"] = scenario_diagnostics
        scenario_results.append(entry)

    contract_path = scenario_file_path(repo_root, GOVERNANCE_TASK_ID)
    contract_ok = scenario_ids == expected_ids
    contract_diagnostics: list[str] = []
    if not contract_ok:
        contract_diagnostics.append(
            f"{contract_path.relative_to(repo_root)} must define exactly {expected_ids}, got {scenario_ids or '[]'}"
        )
        diagnostics.extend(contract_diagnostics)

    parent_run_path = repo_root / ".codex" / "loop-runs" / GOVERNANCE_PARENT_RUN_ID / "run.json"
    parent_run = read_json_file(parent_run_path, diagnostics)
    parent_ok = False
    parent_diagnostics: list[str] = []
    if isinstance(parent_run, dict):
        has_children = isinstance(parent_run.get("child_run_ids"), list) and bool(parent_run.get("child_run_ids"))
        has_progress = isinstance(parent_run.get("reader_summary"), dict) and bool(
            parent_run["reader_summary"].get("current_progress")
        )
        parent_ok = (
            parent_run.get("policy") == "demand_development"
            and parent_run.get("run_kind") == "parent"
            and has_children
            and has_progress
        )
        if not parent_ok:
            parent_diagnostics.append(
                f"{relpath(repo_root, parent_run_path)} must be a demand-development parent run with children and current progress"
            )
    else:
        parent_diagnostics.append(f"missing governance parent run: {relpath(repo_root, parent_run_path)}")
    diagnostics.extend(parent_diagnostics)

    expansion_run_path = repo_root / ".codex" / "loop-runs" / GOVERNANCE_EXPANSION_RUN_ID / "run.json"
    expansion_run = read_json_file(expansion_run_path, diagnostics)
    expansion_diagnostics: list[str] = []
    expansion_ok = isinstance(expansion_run, dict) and expansion_run.get("phase") == "stopped_budget"
    if not expansion_ok:
        expansion_diagnostics.append(f"{relpath(repo_root, expansion_run_path)} must remain stopped_budget")
    else:
        checked.append("stopped-budget expansion run remains stopped_budget")
    diagnostics.extend(expansion_diagnostics)

    preflight_dir = repo_root / ".codex" / "loop-runs" / GOVERNANCE_PARENT_RUN_ID
    preflight = validate_governance_preflight_evidence(preflight_dir)
    preflight_ok = preflight.get("status") == "pass"
    preflight_diagnostics = [str(finding) for finding in preflight.get("findings", [])]
    preflight_diagnostics.extend(str(item) for item in preflight.get("missing_artifacts", []))
    if preflight_ok:
        checked.append("governance preflight evidence passes validation")
    else:
        diagnostics.extend(preflight_diagnostics)
    preflight_evidence = [str(contract_path)]
    preflight_evidence.extend(str(path) for path in preflight.get("artifact_paths", []))
    preflight_evidence.extend(str(path) for path in preflight.get("required_artifacts", []))
    record(
        "E2E-0",
        "Scenario contract and governance preflight artifact gate match the task brief.",
        ok=contract_ok and preflight_ok,
        evidence=preflight_evidence,
        scenario_diagnostics=[*contract_diagnostics, *preflight_diagnostics],
    )

    if parent_ok:
        checked.append("governance parent run remains active with children and progress")
    takeover_diagnostics = [*parent_diagnostics, *expansion_diagnostics]
    record(
        "E2E-1",
        "Governance parent remains the active takeover after r10 stopped at budget.",
        ok=parent_ok and expansion_ok,
        evidence=[
            relpath(repo_root, parent_run_path) if parent_run_path.exists() else "",
            relpath(repo_root, expansion_run_path) if expansion_run_path.exists() else "",
        ],
        scenario_diagnostics=[item for item in takeover_diagnostics if item],
    )

    dashboard_detail: dict[str, Any] = {}
    dashboard_detail_ok = False
    dashboard_diagnostics: list[str] = []
    try:
        payload = read_json_url(f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID}")
        if isinstance(payload, dict):
            dashboard_detail = payload
            dashboard_detail_ok = True
        else:
            dashboard_diagnostics.append(f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} must return a JSON object")
    except Exception as exc:
        dashboard_diagnostics.append(f"dashboard API check failed: {exc}")
    diagnostics.extend(dashboard_diagnostics)

    queue_diagnostics: list[str] = []
    backlog = parent_run.get("backlog") if isinstance(parent_run, dict) else None
    backlog_items = backlog if isinstance(backlog, list) else []
    if not backlog_items:
        queue_diagnostics.append(f"{relpath(repo_root, parent_run_path)} must include backlog items for the needs queue")

    dashboard_children = dashboard_detail.get("children") if dashboard_detail_ok else None
    dashboard_children_summary = dashboard_detail.get("children_summary") if dashboard_detail_ok else None
    dashboard_current_child = dashboard_detail.get("current_child_run_id") if dashboard_detail_ok else None
    dashboard_queue_ok = True
    if not isinstance(dashboard_children, list) or not dashboard_children:
        queue_diagnostics.append(f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} must expose children")
        dashboard_queue_ok = False
    if not isinstance(dashboard_children_summary, dict):
        queue_diagnostics.append(f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} must expose children_summary")
        dashboard_queue_ok = False
    else:
        required_summary_keys = {"total", "pending", "blocked"}
        missing_summary_keys = sorted(key for key in required_summary_keys if key not in dashboard_children_summary)
        if missing_summary_keys:
            queue_diagnostics.append(
                f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} children_summary must include {missing_summary_keys}"
            )
            dashboard_queue_ok = False
    if isinstance(parent_run, dict) and parent_run.get("current_child_run_id") and dashboard_current_child != parent_run.get("current_child_run_id"):
        queue_diagnostics.append(
            f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} must expose current_child_run_id={parent_run.get('current_child_run_id')}"
        )
        dashboard_queue_ok = False
    diagnostics.extend(queue_diagnostics)
    if not queue_diagnostics:
        checked.append("needs queue and blocked split remain visible in parent run and dashboard API")
    record(
        "E2E-2",
        "Needs queue, blocked split, and parent/child dashboard visibility remain aligned.",
        ok=parent_ok and dashboard_detail_ok and dashboard_queue_ok and bool(backlog_items),
        evidence=[
            relpath(repo_root, parent_run_path) if parent_run_path.exists() else "",
            f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID}",
        ],
        scenario_diagnostics=[item for item in [*dashboard_diagnostics, *queue_diagnostics] if item],
    )

    artifact_paths = [str(path) for path in preflight.get("artifact_paths", [])]
    missing_artifacts = [str(path) for path in preflight.get("missing_artifacts", [])]
    candidate_artifacts = [path for path in artifact_paths if "candidate-scoring/" in path]
    candidate_diagnostics = [
        item
        for item in [*preflight_diagnostics, *missing_artifacts]
        if "candidate-scoring" in item.lower()
    ]
    candidate_ok = bool(candidate_artifacts) and not candidate_diagnostics
    if candidate_ok:
        checked.append("candidate scoring hard gates remain enforced")
    diagnostics.extend(item for item in candidate_diagnostics if item not in diagnostics)
    record(
        "E2E-3",
        "High-value candidate scoring remains a hard gate instead of advisory-only.",
        ok=candidate_ok,
        evidence=candidate_artifacts or [path for path in missing_artifacts if "candidate-scoring" in path.lower()],
        scenario_diagnostics=candidate_diagnostics,
    )

    snapshot_path = (
        repo_root
        / "personal-wiki"
        / "domains"
        / "ai_infra"
        / "manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
    )
    snapshot = read_json_file(snapshot_path, diagnostics)
    snapshot_ok = False
    snapshot_diagnostics: list[str] = []
    if isinstance(snapshot, dict):
        channels = snapshot.get("channels")
        sources = snapshot.get("sources")
        if isinstance(channels, list) and channels and isinstance(sources, list) and sources:
            sensitive_findings = find_sensitive_snapshot_findings(snapshot)
            if sensitive_findings:
                snapshot_diagnostics.extend(sensitive_findings)
            else:
                snapshot_ok = True
        else:
            snapshot_diagnostics.append(f"{relpath(repo_root, snapshot_path)} must contain non-empty channels and sources")
    else:
        snapshot_diagnostics.append(f"missing source snapshot manifest: {relpath(repo_root, snapshot_path)}")
    diagnostics.extend(snapshot_diagnostics)

    crawler_diagnostics: list[str] = []
    crawler_ok = check_health_endpoint(crawler_health_url, crawler_diagnostics)
    diagnostics.extend(crawler_diagnostics)
    if snapshot_ok:
        checked.append("source snapshot manifest exists, is populated, and is non-sensitive")
    record(
        "E2E-4",
        "Crawler workbench linkage includes backend health and a populated source snapshot.",
        ok=snapshot_ok and crawler_ok,
        evidence=[
            relpath(repo_root, snapshot_path) if snapshot_path.exists() else "",
            crawler_health_url,
        ],
        scenario_diagnostics=[item for item in [*snapshot_diagnostics, *crawler_diagnostics] if item],
    )

    visibility_diagnostics: list[str] = []
    governance_artifacts = dashboard_detail.get("governance_artifacts") if dashboard_detail_ok else None
    snapshot_paths = governance_artifacts.get("source_profile_snapshots") if isinstance(governance_artifacts, dict) else None
    dashboard_visibility_ok = dashboard_detail_ok and isinstance(snapshot_paths, list) and (
        "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json" in snapshot_paths
    )
    if not dashboard_visibility_ok:
        visibility_diagnostics.append(
            f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID} must expose the source snapshot governance artifact path"
        )
    frontend_diagnostics: list[str] = []
    frontend_ok = check_frontend(frontend_url, frontend_diagnostics)
    visibility_diagnostics.extend(frontend_diagnostics)
    diagnostics.extend(item for item in visibility_diagnostics if item not in diagnostics)
    visibility_ok = dashboard_visibility_ok and frontend_ok and snapshot_ok
    if visibility_ok:
        checked.append("dashboard API, frontend, and source snapshot visibility are live")
    record(
        "E2E-5",
        "Wiki/API/frontend/dashboard visibility is live for governance artifacts and source snapshots.",
        ok=visibility_ok,
        evidence=[
            f"{dashboard_url}/api/runs/{GOVERNANCE_PARENT_RUN_ID}",
            relpath(repo_root, snapshot_path) if snapshot_path.exists() else "",
            frontend_url,
        ],
        scenario_diagnostics=visibility_diagnostics,
    )

    formal_ok, formal_evidence = check_formal_suspicion(repo_root, parent_run, diagnostics)
    if formal_ok:
        checked.append("formal suspicion evidence exists with no unresolved confirmed bug")
    record(
        "E2E-6",
        "Formal suspicion evidence exists and no unresolved confirmed bug remains.",
        ok=formal_ok,
        evidence=formal_evidence,
    )

    readiness_ok = parent_ok and isinstance(parent_run, dict) and (
        bool(parent_run.get("current_child_run_id")) or governance_parent_ready_for_merge(parent_run)
    )
    readiness_diagnostics: list[str] = []
    if readiness_ok:
        checked.append("checkpoint and merge-readiness context remain visible on the parent run")
    else:
        readiness_diagnostics.append(
            "governance parent run must expose current_child_run_id or passed_waiting_human_merge readiness"
        )
    diagnostics.extend(readiness_diagnostics)
    record(
        "E2E-7",
        "Checkpoint context and human-merge readiness remain inspectable from evaluator output.",
        ok=readiness_ok,
        evidence=[relpath(repo_root, parent_run_path)] if parent_run_path.exists() else [],
        scenario_diagnostics=readiness_diagnostics,
    )

    status = "pass" if all(item.get("status") == "pass" for item in scenario_results) else "fail"
    return {
        "status": status,
        "task_id": GOVERNANCE_TASK_ID,
        "summary": "AI infra governance loop evaluator inspected the real repository state.",
        "scenario_results": scenario_results,
        "checked": checked,
        "rerun_commands": [
            "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/ai-infra-loop-governance-dev-01"
        ],
        "diagnostics": diagnostics,
    }


def governance_parent_ready_for_merge(parent_run: dict[str, Any]) -> bool:
    aggregate = parent_run.get("aggregate_acceptance")
    if not isinstance(aggregate, dict):
        return False
    total = safe_int(aggregate.get("total"))
    return (
        parent_run.get("phase") == "passed_waiting_human_merge"
        and parent_run.get("next_action") == "await_human_merge_confirmation"
        and total > 0
        and safe_int(aggregate.get("passed")) == total
        and safe_int(aggregate.get("pending")) == 0
        and safe_int(aggregate.get("failed")) == 0
        and safe_int(aggregate.get("blocked")) == 0
        and aggregate.get("user_decision_required") is True
    )


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def governance_failure_payload(exc: Exception) -> dict[str, Any]:
    return {
        "status": "fail",
        "task_id": GOVERNANCE_TASK_ID,
        "summary": "AI infra governance loop evaluator aborted before completing scenario checks.",
        "scenario_results": [
            {
                "scenario_id": "E2E-7",
                "status": "fail",
                "summary": "Governance evaluator exception path backfilled result.json for the checkpoint gate.",
                "evidence": [],
                "diagnostics": [f"unexpected governance evaluator exception: {exc}"],
            }
        ],
        "checked": [],
        "rerun_commands": [
            "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/ai-infra-loop-governance-dev-01"
        ],
        "diagnostics": [f"unexpected governance evaluator exception: {exc}"],
    }


def scenario_file_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "docs" / "harness" / "evaluator-scenarios" / f"{task_id}.json"


def read_json_file(path: Path, diagnostics: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        diagnostics.append(f"{path} is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        diagnostics.append(f"{path} must contain a JSON object")
        return None
    return payload


def relpath(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def find_sensitive_snapshot_findings(payload: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key).strip().lower()
            if key_text in SENSITIVE_FIELD_NAMES:
                findings.append(f"{path}.{key} uses sensitive field name")
            findings.extend(find_sensitive_snapshot_findings(value, path=f"{path}.{key}"))
        return findings
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            findings.extend(find_sensitive_snapshot_findings(item, path=f"{path}[{index}]"))
        return findings
    if isinstance(payload, str):
        lowered = payload.strip().lower()
        if any(marker in lowered for marker in SENSITIVE_VALUE_MARKERS):
            findings.append(f"{path} contains a sensitive value marker")
    return findings


def check_health_endpoint(url: str, diagnostics: list[str]) -> bool:
    try:
        payload = read_json_url(url)
    except Exception as exc:
        diagnostics.append(f"crawler backend health check failed: {exc}")
        return False
    if payload.get("status") != "ok":
        diagnostics.append(f"crawler backend health returned non-ok payload: {payload!r}")
        return False
    return True


def check_frontend(url: str, diagnostics: list[str]) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                diagnostics.append(f"frontend returned HTTP {status} for {url}")
                return False
    except Exception as exc:
        diagnostics.append(f"frontend reachability check failed: {exc}")
        return False
    return True


def check_formal_suspicion(
    repo_root: Path,
    parent_run: dict[str, Any] | None,
    diagnostics: list[str],
) -> tuple[bool, list[str]]:
    if not isinstance(parent_run, dict):
        diagnostics.append("formal suspicion check requires a readable governance parent run")
        return False, []
    child_ids = parent_run.get("child_run_ids")
    if not isinstance(child_ids, list):
        diagnostics.append("governance parent run must include child_run_ids for formal suspicion check")
        return False, []

    evidence: list[str] = []
    for child_id in child_ids:
        if not isinstance(child_id, str):
            continue
        evaluator_path = repo_root / ".codex" / "loop-runs" / child_id / "evaluator-result.json"
        evaluator_result = read_json_file(evaluator_path, diagnostics)
        if not isinstance(evaluator_result, dict):
            continue
        formal_verification = evaluator_result.get("formal_verification")
        artifact_paths = evaluator_result.get("formal_verification_artifact_paths")
        if not isinstance(formal_verification, dict) or not isinstance(artifact_paths, list) or not artifact_paths:
            continue
        evidence.extend(str(path) for path in artifact_paths)
        if formal_verification.get("status") != "pass":
            diagnostics.append(f"{relpath(repo_root, evaluator_path)} formal_verification status must be pass")
            return False, evidence
        if formal_verification.get("required_counterexample_reruns"):
            diagnostics.append(f"{relpath(repo_root, evaluator_path)} still requires counterexample reruns")
            return False, evidence
        verdict_reason = str(evaluator_result.get("verdict_reason", ""))
        normalized_reason = verdict_reason.strip().lower()
        if normalized_reason and normalized_reason != "no unresolved confirmed formal bug remains." and (
            "unresolved confirmed formal bug remains" in normalized_reason
        ):
            diagnostics.append(f"{relpath(repo_root, evaluator_path)} reports an unresolved confirmed formal bug")
            return False, evidence
        return True, evidence

    diagnostics.append("no governance child evaluator result exposes formal suspicion evidence")
    return False, evidence


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def seed_fixture_project(project_root: Path) -> None:
    runs = [
        (
            "active-repair-run",
            "repair_needed",
            "fail",
            "run_generator_repair",
            "Evaluator 发现日志过滤缺陷，需要 Generator 修复。",
        ),
        (
            "passed-run",
            "passed_waiting_human_merge",
            "pass",
            "await_human_merge_confirmation",
            "Evaluator 通过，等待人工合并确认。",
        ),
        ("no-action-run", "stopped_no_action", "none", "none", "Planner 未发现下一步动作。"),
        ("budget-run", "stopped_budget", "budget_exhausted", "none", "循环达到预算上限。"),
        ("blocked-run", "stopped_blocked", "blocked", "none", "阻塞诊断需要人工处理。"),
    ]
    for index, (run_id, phase, last_result, next_action, summary) in enumerate(runs):
        seed_run(project_root, run_id, phase, last_result, next_action, summary, index)
    seed_run(
        project_root / ".worktrees" / "loop-dashboard",
        "loop-dashboard-dev",
        "passed_waiting_human_merge",
        "pass",
        "await_human_merge_confirmation",
        "历史 worktree 里的 Loop Dashboard 开发任务已经完成。",
        len(runs),
    )
    seed_auditor_fixture(project_root)
    seed_project_skill_fixture(project_root)
    seed_rich_evaluator_result(project_root)
    seed_demand_multi_task_dashboard_fixture(project_root)


def seed_auditor_fixture(project_root: Path) -> None:
    run_dir = project_root / ".codex" / "loop-runs" / "active-repair-run"
    write_json(
        run_dir / "deterministic-signals.json",
        {
            "schema_version": 1,
            "progress_counters": {
                "passed_children_since_last_audit": 3,
                "coverage_layers_changed": 0,
            },
            "repeat_counters": {
                "same_evaluator_finding_count": 2,
            },
            "hygiene_counters": {
                "unclassified_dirty_paths": 1,
                "unpushed_commits": 0,
            },
        },
    )
    write_json(
        run_dir / "audit-reports" / "audit-001.json",
        {
            "schema_version": 1,
            "run_id": "active-repair-run",
            "audit_id": "audit-001",
            "created_at": "2026-07-08T00:00:00Z",
            "verdict": "must_fix",
            "deterministic_signals": {
                "artifact_path": ".codex/loop-runs/active-repair-run/deterministic-signals.json",
                "summary": {
                    "unclassified_dirty_paths": 1,
                    "same_evaluator_finding_count": 2,
                },
            },
            "cadence": {
                "unit": "passed_child",
                "steps_since_last_audit": 1,
                "current_interval": 2,
                "next_interval_after_verdict": 1,
            },
            "direction_control": {
                "action": "switch_task",
                "reason": "同类 evaluator finding 重复出现，先修复流程可见性。",
                "recommended_next_focus": "audit remediation child",
            },
            "finding_lifecycle": {
                "open_findings": [
                    {
                        "finding_id": "audit-001-stagnation-001",
                        "severity": "must_fix",
                        "title": "Loop 存在重复验收失败",
                        "summary": "同类 evaluator finding 连续出现，需要先修复再继续普通开发。",
                    }
                ],
                "closed_findings": [],
            },
        },
    )


def seed_project_skill_fixture(project_root: Path) -> None:
    skill_path = project_root / "project-status-snapshot" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        "---\n"
        "name: project-status-snapshot\n"
        "description: 当用户要求检查、恢复、梳理或继续一个项目的当前状态时使用。\n"
        "---\n\n"
        "# Project Status Snapshot\n",
        encoding="utf-8",
    )


def seed_run(
    project_root: Path,
    run_id: str,
    phase: str,
    last_result: str,
    next_action: str,
    summary: str,
    index: int,
) -> None:
    run_dir = project_root / ".codex" / "loop-runs" / run_id
    requirement = (
        "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、"
        "agent、skill、日志、完成态和阻塞诊断；本次还需要验证开发流程并修复流程 bug。"
    )
    write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "policy": "demand_development",
            "phase": phase,
            "task_id": "loop-dashboard-dev-01",
            "domain": "",
            "branch": "feat/loop-dashboard",
            "worktree": str(project_root),
            "requirement": requirement,
            "constraints": ["只读后端", "中文 UI", "浏览器点击验证"],
            "stop_conditions": ["passed_waiting_human_merge", "stopped_no_action", "stopped_budget", "stopped_blocked"],
            "baseline_dirty_paths": [],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "attempts": {
                "planner": 1 + index,
                "generator": 1 + index,
                "evaluator": 1 + index,
                "artifact_hygiene": 1 if phase.startswith("passed") else 0,
                "cleanup": 1 if phase.startswith("passed") else 0,
            },
            "limits": {"max_eval_attempts": 3, "max_tasks": 5},
            "last_result": last_result,
            "next_action": next_action,
            "attempt_history": [
                {"agent": "planner", "attempt": 1, "status": "pass"},
                {"agent": "generator", "attempt": 1, "status": "implemented"},
                {"agent": "evaluator", "attempt": 1, "status": "fail" if phase == "repair_needed" else "pass"},
            ],
            "cleanup": {
                "worktrees_removed": [],
                "processes_stopped": ["uvicorn-fixture"] if phase.startswith("passed") else [],
                "retained_artifacts": [".codex/loop-runs"],
            },
        },
    )
    write_json(
        run_dir / "planner-output.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Loop 看板",
            "goal": requirement,
            "non_goals": ["不提供写操作"],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "verify_commands": [
                "PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests",
                "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01",
            ],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json",
            "stop_conditions": ["passed_waiting_human_merge"],
            "next_planning_hint": "保持只读监控，不引入登录态。",
        },
    )
    write_json(
        run_dir / "generator-result.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "status": "implemented",
            "changed_paths": [
                "apps/loop_dashboard/backend/loop_dashboard/store.py",
                "apps/loop_dashboard/frontend/app.js",
                "scripts/loop_dashboard_evaluator.py",
            ],
            "commit": "",
            "verify_commands": ["python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v"],
            "verify_results": [{"command": "focused evaluator scenario test", "status": "pass"}],
            "artifacts": ["apps/loop_dashboard/frontend/index.html"],
            "cleanup_required": False,
            "notes": "完成只读 Loop Dashboard 和浏览器点击评估。",
        },
    )
    evaluator_status = "fail" if phase in {"repair_needed", "stopped_blocked"} else "pass"
    findings = []
    if phase == "repair_needed":
        findings = [
            {
                "id": "LD-001",
                "severity": "major",
                "category": "frontend_click",
                "evidence": ["logs filter did not update", "stderr filter was empty"],
                "recommended_action": "修复日志过滤",
            }
        ]
    elif phase == "stopped_blocked":
        findings = [
            {
                "id": "LD-BLOCKED",
                "severity": "major",
                "category": "blocked_state",
                "evidence": ["manual decision required"],
                "recommended_action": "人工解除阻塞后重试",
            }
        ]
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": evaluator_status,
            "gate": "task",
            "task_id": "loop-dashboard-dev-01",
            "final_bundle_id": "bundle-active" if phase == "repair_needed" else "",
            "attempt": 1 + index,
            "summary": summary,
            "findings": findings,
            "scenario_results": [{"scenario_id": SCENARIO_ID, "status": evaluator_status}],
            "rerun_commands": ["python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"],
            "environment_checks": [{"name": "chromium", "status": "available"}],
            "verdict_reason": summary,
            "next_action": "repair_and_reevaluate" if phase == "repair_needed" else "proceed_to_user_acceptance",
            "stdout": "Authorization: Bearer inline-token\n",
            "stderr": "Evaluator stderr: browser assertion context\n",
        },
    )
    write_json(
        run_dir / "artifact-manifest.json",
        {
            "status": "pass",
            "artifacts": [
                {"path": "apps/loop_dashboard/frontend/index.html", "kind": "frontend"},
                {"path": "scripts/loop_dashboard_evaluator.py", "kind": "evaluator"},
            ],
        },
    )
    if phase == "stopped_blocked":
        write_json(
            run_dir / "dirty-paths-result.json",
            {"status": "blocked", "diagnostics": [{"path": "apps/loop_dashboard/frontend/app.js", "reason": "manual review required"}]},
        )
    if phase.startswith("passed"):
        write_json(
            run_dir / "cleanup-result.json",
            {"status": "pass", "processes_stopped": ["uvicorn-fixture"], "worktrees_removed": []},
        )

    (run_dir / "planner-attempt-1.stdout.log").write_text(
        "Planner: 正在拆解需求\nAuthorization: Bearer planner-secret\n",
        encoding="utf-8",
    )
    (run_dir / "generator-attempt-1.stderr.log").write_text(
        "Generator stderr: 使用 skill test-driven-development\n",
        encoding="utf-8",
    )
    (run_dir / "evaluator-attempt-1.stderr.log").write_text(
        "Evaluator stderr: token=evaluator-secret\n",
        encoding="utf-8",
    )


def seed_rich_evaluator_result(project_root: Path) -> None:
    bundle_dir = project_root / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01" / "bundle-active"
    write_json(
        bundle_dir / "result.json",
        {
            "status": "fail",
            "scenario_id": SCENARIO_ID,
            "summary": "浏览器点击发现日志过滤问题",
            "checked": CHECKED,
            "scenario_results": [
                {
                    "scenario_id": SCENARIO_ID,
                    "status": "fail",
                    "summary": "模拟用户过滤日志时发现 stderr 过滤未按预期更新。",
                    "evidence": ["选择日志类型 stderr", "期望只显示 stderr 日志", "实际过滤结果不正确"],
                }
            ],
            "browser_evidence": [
                "已打开 Loop 看板",
                "已点击 active-repair-run",
                "已查看阻塞诊断 LD-001",
            ],
            "rerun_commands": [
                "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
            ],
            "findings": [
                {
                    "id": "LD-001",
                    "severity": "major",
                    "category": "frontend_click",
                    "evidence": ["filter kind stderr did not update before repair"],
                    "recommended_action": "修复日志过滤",
                }
            ],
            "stdout": "Authorization: Bearer rich-secret\n",
            "stderr": "Rich evaluator stderr log line\n",
        },
    )


def seed_demand_multi_task_dashboard_fixture(repo_root: Path) -> None:
    run_root = repo_root / ".codex" / "loop-runs"
    long_requirement = (
        "验证父需求拆分后的子任务可以在 Loop Dashboard 中以中文长文本稳定展示，"
        "包括 Planner 选择、Generator 产物说明、Evaluator 模拟用户检查和验收结果；"
        "这段说明故意较长，用于覆盖移动端换行和父子关系阅读场景。"
    )
    write_json(
        run_root / "parent-run" / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "验证父需求读者摘要和子任务队列在 Loop Dashboard 中可读。",
            "constraints": ["父需求只聚合子任务", "日志必须脱敏"],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "attempts": {"planner": 2, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {"max_tasks": 2},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [{"agent": "planner", "attempt": 1, "status": "pass"}],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-001", "parent-run-child-002", "missing-child"],
            "current_child_run_id": "parent-run-child-002",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 2,
                "passed": 1,
                "failed": 0,
                "blocked": 0,
                "pending": 1,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "验证父需求读者摘要",
                "current_progress": "第一个子任务已通过，第二个子任务正在生成。",
                "next_step": "等待 parent-run-child-002 完成后汇总验收。",
                "decision_needed": "不需要",
            },
            "accepted_changed_paths": ["generated/child-001.txt"],
        },
    )
    write_json(
        run_root / "parent-run" / "evaluator-result.json",
        {
            "status": "pass",
            "gate": "task",
            "task_id": "parent-run",
            "attempt": 1,
            "summary": "父需求聚合关系可读，但保留缺失子任务诊断用于看板检查。",
            "findings": [
                {
                    "id": "child_artifact_missing",
                    "severity": "warning",
                    "category": "relationship",
                    "evidence": ["missing-child"],
                    "recommended_action": "确认缺失子任务是否仍需执行。",
                }
            ],
        },
    )
    for index, phase in [(1, "passed"), (2, "generating")]:
        child_id = f"parent-run-child-{index:03d}"
        write_json(
            run_root / child_id / "run.json",
            {
                "run_id": child_id,
                "run_kind": "child",
                "parent_run_id": "parent-run",
                "child_index": index,
                "policy": "demand_development",
                "phase": phase,
                "task_id": f"{child_id}-task",
                "domain": "",
                "branch": "main",
                "worktree": str(repo_root),
                "requirement": f"{long_requirement} 子任务 {index} 还要展示自己的状态和读者摘要。",
                "constraints": ["保持只读", "展示父子关系", "移动端不能横向溢出"],
                "stop_conditions": ["passed"],
                "baseline_dirty_paths": [],
                "allowed_paths": [f"generated/child-{index:03d}.txt"],
                "denylist_paths": [".env", ".codex/secrets"],
                "attempts": {
                    "planner": 1,
                    "generator": 1 if phase == "passed" else 0,
                    "evaluator": 1 if phase == "passed" else 0,
                    "artifact_hygiene": 0,
                    "cleanup": 0,
                },
                "limits": {"max_eval_attempts": 2},
                "last_result": "pass" if phase == "passed" else "none",
                "next_action": "return_to_parent_planner" if phase == "passed" else "run_child_generator",
                "attempt_history": [
                    {"agent": "planner", "attempt": 1, "status": "pass"},
                    {"agent": "generator", "attempt": 1, "status": "implemented" if phase == "passed" else "pending"},
                ],
                "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
                "reader_summary": {
                    "purpose": f"子任务 {index} 覆盖父需求的一部分。",
                    "planner_action": "Planner 选择了这个子任务",
                    "generator_action": "Generator 正在生成实现产物" if phase == "generating" else "Generator 已生成实现产物",
                    "evaluator_action": "Evaluator 模拟用户检查",
                    "acceptance_result": "通过" if phase == "passed" else "等待验收",
                },
            },
        )
        (
            run_root / child_id / "events.jsonl"
        ).write_text(
            json.dumps(
                {
                    "timestamp": f"2026-07-03T00:00:0{index}Z",
                    "run_id": child_id,
                    "parent_run_id": "parent-run",
                    "child_id": f"child-{index:03d}",
                    "actor": "planner",
                    "event_type": "plan",
                    "summary": f"Planner selected child {index}; Authorization: Bearer secret-token",
                    "details": {},
                    "artifact_paths": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if phase == "passed":
            write_json(
                run_root / child_id / "evaluator-result.json",
                {
                    "status": "pass",
                    "gate": "task",
                    "task_id": f"{child_id}-task",
                    "attempt": 1,
                    "summary": "Evaluator 已模拟用户检查子任务功能完整性和设计匹配。",
                    "scenario_results": [
                        {
                            "scenario_id": f"{child_id}-DESIGN-001",
                            "status": "pass",
                            "summary": "模拟第三方读者打开看板，核对功能实现完整性和设计/mock 匹配。",
                            "evidence": [
                                "点击父需求运行记录",
                                "切换子任务 tab",
                                "核对 Agent 结果和验收内容",
                            ],
                        }
                    ],
                    "checked": [
                        "功能实现完整性",
                        "设计/mock 匹配",
                        "父需求和子任务信息可读",
                    ],
                    "rerun_commands": [
                        "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
                    ],
                },
            )
    write_json(
        run_root / "legacy-single" / "run.json",
        {
            "run_id": "legacy-single",
            "policy": "demand_development",
            "phase": "passed_waiting_human_merge",
            "task_id": "legacy-single-task",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "旧格式单任务没有 run_kind，仍应作为单任务显示。",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "pass",
            "next_action": "await_human_merge_confirmation",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )
    write_json(
        run_root / "conflict-parent" / "run.json",
        {
            "run_id": "conflict-parent",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "冲突父需求引用了另一个父需求的子任务。",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-001"],
            "current_child_run_id": "parent-run-child-001",
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {
                "purpose": "验证冲突父需求诊断",
                "current_progress": "存在多父级引用冲突。",
                "next_step": "查看阻塞诊断。",
                "decision_needed": "需要人工确认归属",
            },
        },
    )


def start_dashboard(repo_root: Path, fixture_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "apps" / "loop_dashboard" / "backend")
    env["LOOP_DASHBOARD_PROJECT_ROOT"] = str(fixture_root)
    return subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "loop_dashboard.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_dashboard(
    dashboard_url: str,
    expected_project_root: Path,
    server: subprocess.Popen[str] | None = None,
    timeout_seconds: float = 20.0,
) -> None:
    health_url = f"{dashboard_url}/api/health"
    project_url = f"{dashboard_url}/api/projects/current"
    expected_root = str(expected_project_root.resolve())
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if server is not None and server.poll() is not None:
            raise RuntimeError(f"dashboard server exited before readiness check; returncode={server.returncode}")
        try:
            health_payload = read_json_url(health_url)
            if health_payload.get("status") != "ok":
                last_error = f"unexpected health payload: {health_payload!r}"
                time.sleep(0.25)
                continue
            project_payload = read_json_url(project_url)
            actual_root = project_payload.get("project_root")
            if actual_root == expected_root:
                return
            raise RuntimeError(f"dashboard project root mismatch: expected {expected_root!r}, got {actual_root!r}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"dashboard did not become ready at {dashboard_url}: {last_error}")


def read_json_url(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=1) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON payload from {url}: {payload!r}")
    return payload


def verify_demand_multi_task_api(base_url: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{base_url}/api/runs", timeout=5) as response:
        runs = json.loads(response.read().decode("utf-8"))
    if not isinstance(runs, list):
        raise AssertionError("/api/runs should return a JSON list")
    parent = find_run_summary(runs, "parent-run")
    expect_equal(parent.get("run_kind"), "parent", "parent-run should be listed as run_kind=parent")
    expect_children_summary(parent, "parent-run list summary")
    run_ids = [run.get("run_id") for run in runs if isinstance(run, dict)]
    for child_id in ["parent-run-child-001", "parent-run-child-002"]:
        if child_id in run_ids:
            raise AssertionError(f"owned child run should not appear as a top-level run: {child_id}")
    legacy = find_run_summary(runs, "legacy-single")
    expect_equal(legacy.get("run_kind"), "single", "legacy-single should remain visible as run_kind=single")

    detail = read_json_url(f"{base_url}/api/runs/parent-run")
    children = detail.get("children")
    if not isinstance(children, list) or not children:
        raise AssertionError("parent-run detail should include child summaries")
    child_ids = [child.get("run_id") for child in children if isinstance(child, dict)]
    expect_equal(child_ids, ["parent-run-child-001", "parent-run-child-002"], "parent-run children should be sorted by child_index")
    expect_children_summary(detail, "parent-run detail summary")
    reader_summary = detail.get("reader_summary")
    if not isinstance(reader_summary, dict) or not reader_summary.get("purpose"):
        raise AssertionError("parent-run detail should include reader_summary.purpose")
    if "relationship_diagnostics" not in detail:
        raise AssertionError("parent-run detail should include relationship_diagnostics")
    events_payload = read_json_url(f"{base_url}/api/runs/parent-run/events")
    events = events_payload.get("events")
    if not isinstance(events, list):
        raise AssertionError("parent-run events endpoint should return an events list")
    if not any(isinstance(event, dict) and event.get("kind") == "plan" for event in events):
        raise AssertionError("parent-run events should include child plan events")
    if any("secret-token" in str(event) for event in events):
        raise AssertionError("parent-run events should redact fixture secret-token")

    conflict = read_json_url(f"{base_url}/api/runs/conflict-parent")
    conflict_children = conflict.get("children")
    if not isinstance(conflict_children, list):
        raise AssertionError("conflict-parent detail should include a children list")
    if any(isinstance(child, dict) and child.get("run_id") == "parent-run-child-001" for child in conflict_children):
        raise AssertionError("conflict-parent should not silently include parent-run-child-001")
    conflict_diagnostics = diagnostics_from(conflict, "relationship_diagnostics") + diagnostics_from(conflict, "blocked_diagnostics")
    conflict_kinds = {diagnostic.get("kind") for diagnostic in conflict_diagnostics if isinstance(diagnostic, dict)}
    if not conflict_kinds.intersection({"child_parent_conflict", "child_multi_parent_conflict"}):
        raise AssertionError(f"conflict-parent should expose a child conflict diagnostic, got {sorted(conflict_kinds)}")

    route_404_cases = [
        expect_route_404(
            f"{base_url}/api/runs/..%2Foutside",
            "..%2Foutside",
        )
    ]
    store_safe_id_cases = [
        expect_store_safe_id_404(f"{base_url}/api/runs/{unsafe_path}", unsafe_path)
        for unsafe_path in ["%2E%2E", "%5C..%5Coutside", "..%5Coutside"]
    ]
    return {
        "parent_children": len(children),
        "events": len(events),
        "conflict_diagnostics": sorted(str(kind) for kind in conflict_kinds),
        "route_404_cases": route_404_cases,
        "store_safe_id_cases": store_safe_id_cases,
    }


def find_run_summary(runs: list[object], run_id: str) -> dict[str, object]:
    for run in runs:
        if isinstance(run, dict) and run.get("run_id") == run_id:
            return run
    available = sorted(str(run.get("run_id")) for run in runs if isinstance(run, dict) and run.get("run_id"))
    raise AssertionError(f"/api/runs should include {run_id}; available run ids: {available}")


def expect_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def expect_children_summary(payload: dict[str, object], context: str) -> None:
    summary = payload.get("children_summary")
    if not isinstance(summary, dict):
        raise AssertionError(f"{context} should include children_summary")
    expected = {"total": 2, "passed": 1, "pending": 1}
    for key, value in expected.items():
        if summary.get(key) != value:
            raise AssertionError(f"{context} children_summary.{key} should be {value}, got {summary.get(key)!r}")


def diagnostics_from(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    diagnostics = payload.get(key)
    if not isinstance(diagnostics, list):
        raise AssertionError(f"{key} should be a list")
    return [diagnostic for diagnostic in diagnostics if isinstance(diagnostic, dict)]


def expect_route_404(url: str, case: str) -> dict[str, object]:
    try:
        urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise AssertionError(f"route-level unsafe run lookup should return 404 for {case}: got {exc.code}") from exc
        detail = read_error_detail(exc)
        if detail != "Not Found":
            raise AssertionError(
                f"route-level unsafe run lookup should be rejected by router for {case}: detail={detail!r}"
            ) from exc
        return {"case": case, "status": exc.code, "detail": detail}
    raise AssertionError(f"route-level unsafe run lookup should return 404 for {case}")


def expect_store_safe_id_404(url: str, case: str) -> dict[str, object]:
    try:
        urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise AssertionError(f"store-level unsafe run lookup should return 404 for {case}: got {exc.code}") from exc
        detail = read_error_detail(exc)
        if not isinstance(detail, str) or not detail.startswith("run not found: "):
            raise AssertionError(
                f"store-level unsafe run lookup should reach run_id handler for {case}: detail={detail!r}"
            ) from exc
        return {"case": case, "status": exc.code, "detail": detail}
    raise AssertionError(f"store-level unsafe run lookup should return 404 for {case}")


def read_error_detail(exc: urllib.error.HTTPError) -> object:
    body = exc.read().decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(payload, dict):
        return payload.get("detail")
    return payload


def run_browser_checks(dashboard_url: str, output_dir: Path) -> dict[str, Any]:
    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright for Python is not installed") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page).to_have_title("Loop Dashboard")
            expect(page.get_by_role("heading", name="Loop Dashboard")).to_be_visible()
            expect(page.get_by_test_id("project-status")).to_contain_text("项目：")
            expect(page.get_by_test_id("project-status")).to_contain_text("运行目录：")
            workbench_columns = page.locator(".workbench").evaluate(
                "el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length"
            )
            if workbench_columns != 2:
                raise AssertionError(f"dashboard should use two primary columns, got {workbench_columns}")
            expect(page.get_by_test_id("run-list")).to_contain_text("active-repair-run")
            expect(page.get_by_test_id("run-list")).to_contain_text("loop-dashboard-dev")
            expect(page.get_by_test_id("run-list")).to_contain_text("parent-run")

            page.get_by_role("button").filter(has_text="active-repair-run").first.click()
            detail = page.get_by_test_id("run-detail")
            expect(detail).to_contain_text("实现独立本地 Loop Dashboard")
            expect(detail).to_contain_text("需要修复")
            expect(detail).to_contain_text("任务摘要")
            expect(detail).to_contain_text("当前进展")
            expect(detail).to_contain_text("下一步")
            expect(detail).to_contain_text("用户决策")
            expect(detail).to_contain_text("运行信息")
            expect(detail).to_contain_text("用户决策不需要")
            expect(detail.locator(".run-summary-card")).to_have_count(1)
            expect(detail.locator(".decision-grid")).to_have_count(1)
            expect(detail.locator(".run-info-grid")).to_have_count(1)
            expect(detail.locator(".run-info-row")).to_have_count(5)
            info_columns = detail.locator(".run-info-grid").evaluate(
                "el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length"
            )
            if info_columns != 1:
                raise AssertionError(f"run info should render one field per row, got {info_columns} columns")

            tabs = page.get_by_test_id("detail-tabs")
            for tab_name in ["概览", "子任务", "Agent结果", "验收", "审计与 Skill", "日志", "阻塞诊断", "产物"]:
                expect(tabs.get_by_role("tab", name=tab_name)).to_be_visible()

            click_run(page, "parent-run")
            parent_detail = page.get_by_test_id("run-detail")
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            expect(parent_detail).to_contain_text("验证父需求读者摘要")
            expect(parent_detail).to_contain_text("parent-run-child-001")
            expect(parent_detail).to_contain_text("parent-run-child-002")
            expect(parent_detail).to_contain_text("Planner 选择了这个子任务")
            expect(parent_detail).to_contain_text("Evaluator 模拟用户检查")
            parent_detail_excerpt = parent_detail.inner_text()[:800]
            for internal_action in [
                "run_parent_planner",
                "run_child_generator",
                "resume_current_child",
                "repair_child",
                "return_to_parent_planner",
                "child_running",
                "1 children passed",
                "Run parent planner",
                "No",
            ]:
                if internal_action in parent_detail.inner_text():
                    raise AssertionError(f"dashboard should translate internal action id: {internal_action}")
            tabs.get_by_role("tab", name="子任务").click()
            child_tab = page.get_by_test_id("tab-children")
            expect(child_tab).to_be_visible()
            expect(child_tab).to_contain_text("子任务详情")
            expect(child_tab).to_contain_text("parent-run-child-001")
            expect(child_tab).to_contain_text("parent-run-child-002")
            expect(child_tab).to_contain_text("Generator 已生成实现产物")
            expect(child_tab).to_contain_text("Evaluator 模拟用户检查")
            expect(child_tab).to_contain_text(".codex/loop-runs/parent-run-child-001/evaluator-result.json")
            tabs.get_by_role("tab", name="概览").click()
            parent_flow = page.get_by_test_id("flow-diagram")
            expect(parent_flow).to_contain_text("父需求进展")
            expect(parent_flow).to_contain_text("1 / 2 通过")
            expect(parent_flow).to_contain_text("parent-run-child-001")
            expect(parent_flow).to_contain_text("parent-run-child-002")
            expect(parent_flow).to_contain_text("Generator 已生成实现产物")
            expect(parent_flow).to_contain_text("Generator 正在生成实现产物")
            expect(parent_flow).not_to_contain_text("Repair Needed")
            tabs.get_by_role("tab", name="Agent结果").click()
            parent_agent_cards = page.get_by_test_id("agent-cards")
            expect(parent_agent_cards).to_contain_text("父需求 Agent 结果")
            expect(parent_agent_cards).to_contain_text("parent-run-child-001")
            expect(parent_agent_cards).to_contain_text("parent-run-child-002")
            expect(parent_agent_cards).to_contain_text("Planner 选择了这个子任务")
            expect(parent_agent_cards).to_contain_text("Generator 已生成实现产物")
            expect(parent_agent_cards).to_contain_text("Generator 正在生成实现产物")
            expect(parent_agent_cards).to_contain_text("Evaluator 模拟用户检查")
            tabs.get_by_role("tab", name="验收").click()
            parent_acceptance = page.get_by_test_id("tab-acceptance")
            expect(parent_acceptance).to_contain_text("验收情况")
            expect(parent_acceptance).to_contain_text("功能实现完整性")
            expect(parent_acceptance).to_contain_text("设计/mock 匹配")
            expect(parent_acceptance).to_contain_text("模拟第三方读者打开看板")
            expect(parent_acceptance).to_contain_text("parent-run-child-001")
            tabs.get_by_role("tab", name="阻塞诊断").click()
            expect(page.get_by_test_id("blocked-diagnostics")).to_contain_text("child_artifact_missing")
            tabs.get_by_role("tab", name="日志").click()
            parent_log_list = page.get_by_test_id("log-list")
            expect(parent_log_list).to_contain_text("Planner selected child 1")
            page.get_by_test_id("log-keyword-filter").fill("secret-token")
            expect(parent_log_list).to_contain_text("没有匹配的日志")
            if "secret-token" in page.content():
                raise AssertionError("dashboard rendered an unredacted fixture token")
            page.set_viewport_size({"width": 390, "height": 844})
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            overflow_after_parent = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow_after_parent:
                raise AssertionError("parent/child dashboard has horizontal overflow at 390px viewport width")
            page.set_viewport_size({"width": 1280, "height": 900})
            page.get_by_test_id("log-keyword-filter").fill("")
            click_run(page, "conflict-parent")
            conflict_detail = page.get_by_test_id("run-detail")
            expect(conflict_detail).to_contain_text("验证冲突父需求诊断")
            expect(conflict_detail.locator(".child-queue")).to_contain_text("暂无子任务")
            expect(conflict_detail.locator(".child-queue")).not_to_contain_text("parent-run-child-001")
            tabs.get_by_role("tab", name="阻塞诊断").click()
            expect(page.get_by_test_id("blocked-diagnostics")).to_contain_text("child parent conflict")
            click_run(page, "active-repair-run")

            overview_tab = page.get_by_test_id("tab-overview")
            expect(overview_tab).to_be_visible()
            expect(page.get_by_test_id("tab-diagnostics")).not_to_be_visible()

            flow = page.get_by_test_id("flow-diagram")
            expect(flow).to_contain_text("Evaluator")
            expect(flow).to_contain_text("阻塞")
            expect(flow).to_contain_text("Artifact Hygiene")
            expect(flow).to_contain_text("Cleanup")
            expect(flow).to_contain_text(".codex/loop-runs/active-repair-run/evaluator-result.json")
            expect(flow.locator(".flow-node-header")).to_have_count(8)
            expect(flow.locator(".flow-node-body")).to_have_count(8)
            expect(flow.locator(".flow-node-long")).to_have_count(8)

            tabs.get_by_role("tab", name="Agent结果").click()
            agent_cards = page.get_by_test_id("agent-cards")
            expect(page.get_by_test_id("tab-agents")).to_be_visible()
            expect(agent_cards).to_contain_text("Planner")
            expect(agent_cards).to_contain_text("Generator")
            expect(agent_cards).to_contain_text("Evaluator")
            expect(agent_cards.locator(".agent-card-layout")).to_have_count(3)
            expect(agent_cards.locator(".agent-main")).to_have_count(3)
            expect(agent_cards.locator(".agent-long-fields")).to_have_count(3)
            expect(agent_cards).to_contain_text("apps/loop_dashboard/frontend/app.js")

            tabs.get_by_role("tab", name="验收").click()
            acceptance = page.get_by_test_id("tab-acceptance")
            expect(acceptance).to_be_visible()
            expect(acceptance).to_contain_text("验收情况")
            expect(acceptance).to_contain_text("模拟用户过滤日志时发现 stderr 过滤未按预期更新")
            expect(acceptance).to_contain_text("选择日志类型 stderr")
            expect(acceptance).to_contain_text("修复日志过滤")

            tabs.get_by_role("tab", name="审计与 Skill").click()
            auditor_tab = page.get_by_test_id("tab-auditor")
            expect(auditor_tab).to_be_visible()
            expect(auditor_tab).to_contain_text("Auditor 审计")
            expect(auditor_tab).to_contain_text("open must_fix")
            expect(auditor_tab).to_contain_text("必须整改")
            expect(auditor_tab).to_contain_text("确定性信号")
            expect(auditor_tab).to_contain_text("重复 finding")
            expect(auditor_tab).to_contain_text("当前项目 Skill 使用情况")
            expect(auditor_tab).to_contain_text("project-status-snapshot")
            expect(auditor_tab).to_contain_text("pge-loop-agent-contract")

            tabs.get_by_role("tab", name="阻塞诊断").click()
            diagnostics = page.get_by_test_id("blocked-diagnostics")
            expect(page.get_by_test_id("tab-diagnostics")).to_be_visible()
            expect(diagnostics).to_contain_text("LD-001")
            expect(diagnostics).to_contain_text("修复日志过滤")

            tabs.get_by_role("tab", name="产物").click()
            artifacts = page.get_by_test_id("tab-artifacts")
            expect(artifacts).to_be_visible()
            expect(artifacts).to_contain_text(".codex/loop-runs/active-repair-run/evaluator-result.json")
            expect(artifacts).to_contain_text("apps/loop_dashboard/frontend/app.js")

            tabs.get_by_role("tab", name="日志").click()
            page.get_by_test_id("agent-filter").select_option("generator")
            log_list = page.get_by_test_id("log-list")
            expect(page.get_by_test_id("tab-logs")).to_be_visible()
            expect(log_list).to_contain_text("Generator stderr")
            expect(log_list).not_to_contain_text("Planner:")

            page.get_by_test_id("log-kind-filter").select_option("stderr")
            expect(log_list).to_contain_text("Generator stderr")

            page.get_by_test_id("agent-filter").select_option("all")
            page.get_by_test_id("log-kind-filter").select_option("all")
            page.get_by_test_id("log-keyword-filter").fill("REDACTED")
            expect(log_list).to_contain_text("Authorization: Bearer [REDACTED]")
            expect(log_list).to_contain_text("token=[REDACTED]")

            page.get_by_test_id("log-kind-filter").select_option("stderr")
            page.get_by_test_id("log-keyword-filter").fill("no-such-keyword")
            expect(log_list).to_contain_text("没有匹配的日志")

            page.get_by_test_id("log-kind-filter").select_option("all")
            page.get_by_test_id("log-keyword-filter").fill("")
            click_run_and_expect_phase(page, expect, "passed-run", "通过，等待人工合并")
            expect(detail).to_contain_text(
                "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、"
                "agent、skill、日志、完成态和阻塞诊断；本次还需要验证开发流程并修复流程 bug。"
            )
            expect(detail).to_contain_text("等待人工合并确认")
            expect(detail).to_contain_text("用户决策")
            tabs.get_by_role("tab", name="概览").click()
            expect(flow).to_contain_text("Repair Needed")
            expect(flow).to_contain_text("跳过")
            expect(flow).to_contain_text("本次未触发")
            click_run_and_expect_phase(page, expect, "loop-dashboard-dev", "通过，等待人工合并")
            expect(detail).to_contain_text("来源")
            expect(detail).to_contain_text(".worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev")
            click_run_and_expect_phase(page, expect, "no-action-run", "停止：无需操作")
            click_run_and_expect_phase(page, expect, "budget-run", "停止：预算耗尽")
            click_run_and_expect_phase(page, expect, "blocked-run", "停止：阻塞")

            page.set_viewport_size({"width": 390, "height": 900})
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Loop Dashboard")).to_be_visible()
            overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow:
                raise AssertionError("dashboard has horizontal overflow at 390px viewport width")
            screenshot_path = output_dir / "success.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            return {
                "screenshot": str(screenshot_path),
                "title": page.title(),
                "detail_excerpt": detail.inner_text()[:240],
                "parent_detail_excerpt": parent_detail_excerpt,
            }
        except Exception:
            try:
                page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            browser.close()


def click_run_and_expect_phase(page: Any, expect: Any, run_id: str, phase_text: str) -> None:
    click_run(page, run_id)
    detail = page.get_by_test_id("run-detail")
    expect(detail).to_contain_text(run_id)
    expect(detail).to_contain_text(phase_text)


def click_run(page: Any, run_id: str) -> None:
    page.locator(f'.run-button[data-run-id="{run_id}"]').click()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_with_timestamp = dict(payload)
    if "generated_at" not in payload_with_timestamp:
        payload_with_timestamp["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload_with_timestamp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failure_payload(
    exc: Exception,
    dashboard_url: str,
    fixture_root: Path | None,
    server_output: dict[str, str] | None,
) -> dict[str, Any]:
    output = server_output or {"stdout": "", "stderr": ""}
    payload: dict[str, Any] = {
        "status": "fail",
        "scenario_id": SCENARIO_ID,
        "error": str(exc),
        "dashboard_url": dashboard_url,
        "server_stdout": output["stdout"],
        "server_stderr": output["stderr"],
    }
    if fixture_root is not None:
        payload["project_root"] = str(fixture_root.resolve())
    return payload


def collect_server_output(process: subprocess.Popen[str] | None) -> dict[str, str]:
    if process is None:
        return {"stdout": "", "stderr": ""}
    stdout = ""
    stderr = ""
    if process.poll() is None:
        return {"stdout": "", "stderr": ""}
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return {"stdout": stdout or "", "stderr": stderr or ""}


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
