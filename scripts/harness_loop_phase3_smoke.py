#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.harness_loop_autonomous import create_default_loop_state, write_loop_state
    from scripts.harness_loop_contracts import (
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_loop_state_payload,
        validate_run_payload,
    )
    from scripts.harness_loop_orchestrator import create_preflight_run, run_autonomous
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from harness_loop_autonomous import create_default_loop_state, write_loop_state  # type: ignore[no-redef]
    from harness_loop_contracts import (  # type: ignore[no-redef]
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_loop_state_payload,
        validate_run_payload,
    )
    from harness_loop_orchestrator import create_preflight_run, run_autonomous  # type: ignore[no-redef]


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _validate_safe_id(value: str, label: str, pattern: re.Pattern[str] = SAFE_ID_RE) -> None:
    if not pattern.fullmatch(value):
        raise ValueError(f"{label} must be a safe slug")


def _safe_child(root: Path, child: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved_child = child.resolve()
    try:
        resolved_child.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes {resolved_root}") from exc
    return resolved_child


def _assert_git_available(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError(f"repo_root is not a git worktree: {repo_root}")


def _configure_smoke_git_identity(repo_root: Path) -> None:
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_phase3_smoke_in_isolated_clone(repo_root: Path | str, run_id: str, domain: str, task_id: str) -> dict[str, Any]:
    _validate_safe_id(run_id, "run_id")
    _validate_safe_id(task_id, "task_id")
    _validate_safe_id(domain, "domain", SAFE_DOMAIN_RE)
    source_root = Path(repo_root).resolve()
    _assert_git_available(source_root)
    with tempfile.TemporaryDirectory(prefix="phase3-smoke-") as tmp:
        clone_root = Path(tmp) / "repo"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(source_root), str(clone_root)],
            cwd=source_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _configure_smoke_git_identity(clone_root)
        payload = run_phase3_smoke(clone_root, run_id, domain, task_id)
        payload["isolated_clone"] = True
        payload["source_repo_root"] = str(source_root)
        return payload


def _clean_previous_smoke(repo_root: Path, run_id: str, domain: str) -> None:
    run_dir = _safe_child(repo_root / ".codex" / "loop-runs", run_dir_for(repo_root, run_id), "run_id")
    shutil.rmtree(run_dir, ignore_errors=True)
    domain_root = repo_root / "personal-wiki" / "domains" / domain
    raw_root = _safe_child(repo_root / "personal-wiki" / "domains", domain_root, "domain")
    for raw_note in raw_root.glob(f"raw/loop-autonomous/{run_id}-task-*.md"):
        _safe_child(raw_root, raw_note, "raw_note").unlink(missing_ok=True)


def _guard_clean_smoke_paths(repo_root: Path, run_id: str, domain: str) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git status failed before smoke cleanup: {result.stderr.strip()}")
    protected_paths = {
        f"personal-wiki/domains/{domain}/loop-state.json",
    }
    protected_prefix = f"personal-wiki/domains/{domain}/raw/loop-autonomous/{run_id}-task-"
    dirty_paths = []
    for line in result.stdout.splitlines():
        path = _parse_porcelain_path(line)
        if path in protected_paths or path.startswith(protected_prefix):
            dirty_paths.append(path)
    if dirty_paths:
        raise RuntimeError(f"dirty smoke paths must be cleaned before Phase 3 smoke: {', '.join(sorted(dirty_paths))}")


def _parse_porcelain_path(line: str) -> str:
    if not line.strip() or len(line) < 4:
        return ""
    path = line[3:].strip()
    if " -> " in path:
        return path.split(" -> ", 1)[1].strip()
    return path


def _seed_candidate_loop_state(repo_root: Path, domain: str) -> Path:
    state = create_default_loop_state(domain, "Expand autonomous ai_infra wiki coverage")
    state["known_sources"] = [
        {
            "id": "phase-3-smoke-source",
            "title": "Phase 3 smoke seed source",
            "source": "smoke-helper",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded known source"],
        }
    ]
    state["candidate_backlog"] = [
        {
            "id": "phase-3-smoke-candidate",
            "title": "Capture synthetic autonomous note",
            "source": "smoke-helper",
            "status": "pending",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded candidate backlog item"],
        }
    ]
    path = write_loop_state(repo_root, domain, state)
    validate_loop_state_payload(read_json_file(path))
    return path


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def run_phase3_smoke(repo_root: Path | str, run_id: str, domain: str, task_id: str) -> dict[str, Any]:
    _validate_safe_id(run_id, "run_id")
    _validate_safe_id(task_id, "task_id")
    _validate_safe_id(domain, "domain", SAFE_DOMAIN_RE)
    root = Path(repo_root).resolve()
    _assert_git_available(root)
    _guard_clean_smoke_paths(root, run_id, domain)
    _clean_previous_smoke(root, run_id, domain)

    create_preflight_run(
        repo_root=root,
        mode="autonomous-knowledge",
        requirement="Evaluator scenario Phase 3 autonomous smoke",
        run_id=run_id,
        task_id=task_id,
        domain=domain,
        constraints=["Only auto-commit allowlisted personal-wiki domain artifacts."],
        stop_conditions=["stopped_no_action", "stopped_budget", "stopped_blocked"],
        confirm=True,
    )
    loop_state_path = _seed_candidate_loop_state(root, domain)
    status = run_autonomous(
        root,
        run_id,
        planner_driver="fake",
        generator_driver="fake",
        evaluator_driver="fake",
        max_eval_attempts=2,
        max_tasks=2,
    )

    run_dir = run_dir_for(root, run_id)
    run_payload = read_json_file(run_dir / "run.json")
    validate_run_payload(run_payload)
    generator_result = read_json_file(run_dir / "generator-result.json")
    validate_generator_result_payload(generator_result)
    loop_state = read_json_file(loop_state_path)
    validate_loop_state_payload(loop_state)

    if run_payload["phase"] != "stopped_no_action":
        raise RuntimeError(f"Phase 3 smoke ended in phase {run_payload['phase']}")
    if run_payload["next_action"] != "none":
        raise RuntimeError(f"Phase 3 smoke ended with next_action {run_payload['next_action']}")
    if int(run_payload["attempts"]["planner"]) != 2:
        raise RuntimeError("Phase 3 smoke did not perform the second no-action planner pass")
    if not generator_result["commit"]:
        raise RuntimeError("Phase 3 smoke did not create an autonomous commit")
    if loop_state["candidate_backlog"]:
        raise RuntimeError("Phase 3 smoke did not exhaust the candidate backlog")
    if loop_state["last_planner_decision"] != "no_action":
        raise RuntimeError("Phase 3 smoke did not record no-action loop state")

    evidence_paths = {
        "run_dir": run_dir,
        "planner_output_path": run_dir / "planner-output.json",
        "generator_result_path": run_dir / "generator-result.json",
        "evaluator_result_path": run_dir / "evaluator-result.json",
        "artifact_manifest_path": run_dir / "artifact-manifest.json",
        "commit_result_path": run_dir / "commit-result.json",
    }
    missing = [name for name, path in evidence_paths.items() if not path.exists()]
    if missing:
        raise RuntimeError(f"Phase 3 smoke evidence missing: {', '.join(missing)}")

    return {
        "phase": status["phase"],
        "next_action": status["next_action"],
        "commit": generator_result["commit"],
        "loop_state_path": _relative(root, loop_state_path),
        "run_dir": _relative(root, run_dir),
        **{name: _relative(root, path) for name, path in evidence_paths.items() if name != "run_dir"},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Phase 3 autonomous planner loop smoke scenario.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="evaluator-scenario-phase-3")
    parser.add_argument("--domain", default="ai_infra")
    parser.add_argument("--task-id", default="planner-generator-evaluator-loop-phase-3-01")
    parser.add_argument(
        "--isolate-clone",
        action="store_true",
        help="Run the smoke in a temporary clone so the current checkout is not mutated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.isolate_clone:
        payload = run_phase3_smoke_in_isolated_clone(args.repo_root, args.run_id, args.domain, args.task_id)
    else:
        payload = run_phase3_smoke(args.repo_root, args.run_id, args.domain, args.task_id)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
