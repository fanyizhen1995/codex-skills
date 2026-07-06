#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.harness_ai_infra_evidence import check_service_availability
    from scripts.harness_loop_autonomous import create_default_coverage_map, create_default_loop_state, write_loop_state
    from scripts.harness_loop_contracts import read_json_file, run_dir_for, validate_run_payload, write_json_file
    from scripts.harness_loop_orchestrator import create_preflight_run, run_autonomous
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from harness_ai_infra_evidence import check_service_availability  # type: ignore[no-redef]
    from harness_loop_autonomous import create_default_coverage_map, create_default_loop_state, write_loop_state  # type: ignore[no-redef]
    from harness_loop_contracts import read_json_file, run_dir_for, validate_run_payload, write_json_file  # type: ignore[no-redef]
    from harness_loop_orchestrator import create_preflight_run, run_autonomous  # type: ignore[no-redef]


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
POLICY_FILE = "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"
SERVICE_TARGETS = (
    {"service": "crawler-backend", "url": "http://127.0.0.1:8765/api/health"},
    {"service": "crawler-frontend", "url": "http://127.0.0.1:5173/"},
    {"service": "loop-dashboard", "url": "http://127.0.0.1:8766/api/health"},
)


def _validate_safe_id(value: str, label: str) -> None:
    if not SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe slug")


def _assert_git_repo(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError(f"repo_root is not a git worktree: {repo_root}")


def _configure_git_identity(repo_root: Path) -> None:
    subprocess.run(["git", "config", "user.email", "codex@example.invalid"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Codex"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _seed_ai_infra_candidate(repo_root: Path) -> None:
    state = create_default_loop_state("ai_infra", "Evaluator scenario AI infra meta loop smoke")
    state["known_sources"] = [
        {
            "id": "meta-loop-smoke-source",
            "title": "Meta loop smoke source",
            "source": "smoke-helper",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded source"],
        }
    ]
    state["candidate_backlog"] = [
        {
            "id": "meta-loop-smoke-candidate",
            "title": "Create deterministic expanded runtime smoke artifact",
            "source": "smoke-helper",
            "status": "pending",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded candidate backlog item"],
        }
    ]
    write_loop_state(repo_root, "ai_infra", state)

    coverage_map = create_default_coverage_map("ai_infra", state["domain_goal"])
    for layer_payload in coverage_map["layers"].values():
        layer_payload["status"] = "covered"
        layer_payload["covered_pages"] = ["wiki/seeded.md"]
        layer_payload["raw_evidence"] = ["raw/seeded.json"]
        layer_payload["candidate_gaps"] = []
        layer_payload["blocked_reason"] = ""
        layer_payload["last_scanned_at"] = state["last_scan_at"]
        layer_payload["notes"] = "Seeded coverage map for meta loop smoke."
    write_json_file(repo_root / "personal-wiki" / "domains" / "ai_infra" / "coverage-map.json", coverage_map)

    subprocess.run(
        ["git", "add", "--", "personal-wiki/domains/ai_infra/loop-state.json", "personal-wiki/domains/ai_infra/coverage-map.json"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "commit", "-m", "test: seed ai infra meta loop smoke"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _reset_to_clean_head(repo_root: Path) -> None:
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "clean", "-fd"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _run_preflight(repo_root: Path, run_id: str) -> dict[str, Any]:
    payload = create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement="Evaluator scenario AI infra meta loop runtime smoke",
        run_id=run_id,
        domain="ai_infra",
        policy_file=POLICY_FILE,
        constraints=["Only write deterministic local smoke artifacts."],
        stop_conditions=["stopped_no_action", "stopped_budget", "stopped_blocked"],
        confirm=True,
    )
    validate_run_payload(payload)
    return payload


def _run_missing_evidence_round(repo_root: Path, run_id: str) -> dict[str, Any]:
    status = run_autonomous(
        repo_root,
        run_id,
        planner_driver="fake",
        generator_driver="fake-missing-evidence",
        evaluator_driver="fake",
        max_eval_attempts=2,
        max_tasks=1,
    )
    required_evidence = read_json_file(run_dir_for(repo_root, run_id) / "required-evidence-result.json")
    blocked = (
        status["phase"] == "stopped_blocked"
        and status["next_action"] == "inspect_required_evidence"
        and required_evidence.get("status") == "blocked"
    )
    return {
        "status": "pass" if blocked else "fail",
        "run_status": status,
        "required_evidence_result_path": _relative(repo_root, run_dir_for(repo_root, run_id) / "required-evidence-result.json"),
    }


def _run_expanded_code_round(repo_root: Path, run_id: str) -> dict[str, Any]:
    status = run_autonomous(
        repo_root,
        run_id,
        planner_driver="fake",
        generator_driver="fake-expanded-code",
        evaluator_driver="fake",
        max_eval_attempts=2,
        max_tasks=2,
    )
    run_dir = run_dir_for(repo_root, run_id)
    generator_result = read_json_file(run_dir / "generator-result.json")
    commit_result = read_json_file(run_dir / "commit-result.json")
    required_evidence = read_json_file(run_dir / "required-evidence-result.json")
    smoke_file = repo_root / "scripts" / "ai_infra_expanded_runtime_smoke.txt"
    passed = (
        status["phase"] == "stopped_no_action"
        and status["next_action"] == "none"
        and required_evidence.get("status") == "pass"
        and commit_result.get("status") == "pass"
        and bool(generator_result.get("commit"))
        and smoke_file.exists()
    )
    return {
        "status": "pass" if passed else "fail",
        "run_status": status,
        "run_dir": _relative(repo_root, run_dir),
        "generator_result_path": _relative(repo_root, run_dir / "generator-result.json"),
        "required_evidence_result_path": _relative(repo_root, run_dir / "required-evidence-result.json"),
        "commit_result_path": _relative(repo_root, run_dir / "commit-result.json"),
        "smoke_file": _relative(repo_root, smoke_file),
    }


def _service_availability_summary() -> dict[str, Any]:
    result = check_service_availability(SERVICE_TARGETS)
    status = "pass" if result.get("overall_status") == "pass" else "blocked"
    return {
        "status": status,
        "services": result["services"],
    }


def _run_smoke_in_repo(repo_root: Path, run_id: str) -> dict[str, Any]:
    _assert_git_repo(repo_root)
    _configure_git_identity(repo_root)
    _seed_ai_infra_candidate(repo_root)

    preflight = _run_preflight(repo_root, run_id)
    preflight_summary = {
        "status": "pass" if preflight.get("policy_file") == POLICY_FILE else "fail",
        "policy_file": str(preflight.get("policy_file", "")),
        "run_dir": _relative(repo_root, run_dir_for(repo_root, run_id)),
    }

    missing_evidence_gate = _run_missing_evidence_round(repo_root, run_id)
    _reset_to_clean_head(repo_root)
    _configure_git_identity(repo_root)
    _seed_ai_infra_candidate(repo_root)
    _run_preflight(repo_root, run_id)
    expanded_code_scope = _run_expanded_code_round(repo_root, run_id)
    service_availability = _service_availability_summary()

    overall_status = "pass"
    for section in (preflight_summary, missing_evidence_gate, expanded_code_scope):
        if section["status"] != "pass":
            overall_status = "fail"
            break
    if overall_status == "pass" and service_availability["status"] != "pass":
        overall_status = "blocked"

    return {
        "overall_status": overall_status,
        "expanded_policy_preflight": preflight_summary,
        "missing_evidence_gate": missing_evidence_gate,
        "expanded_code_scope": expanded_code_scope,
        "service_availability_evidence": service_availability,
    }


def run_ai_infra_meta_loop_smoke(repo_root: Path | str, run_id: str, *, isolate_clone: bool = False) -> dict[str, Any]:
    _validate_safe_id(run_id, "run_id")
    source_root = Path(repo_root).resolve()
    if isolate_clone:
        _assert_git_repo(source_root)
        with tempfile.TemporaryDirectory(prefix="ai-infra-meta-loop-smoke-") as tmp:
            clone_root = Path(tmp) / "repo"
            subprocess.run(
                ["git", "clone", "--quiet", "--no-hardlinks", str(source_root), str(clone_root)],
                cwd=source_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            payload = _run_smoke_in_repo(clone_root, run_id)
            payload["isolated_clone"] = True
            payload["source_repo_root"] = str(source_root)
            payload["repo_root"] = str(clone_root)
            return payload

    payload = _run_smoke_in_repo(source_root, run_id)
    payload["isolated_clone"] = False
    payload["repo_root"] = str(source_root)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI infra meta loop runtime smoke helper.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="evaluator-scenario-ai-infra-meta-loop-runtime")
    parser.add_argument("--isolate-clone", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_ai_infra_meta_loop_smoke(args.repo_root, args.run_id, isolate_clone=args.isolate_clone)
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
