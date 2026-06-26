#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import re
import shutil
import tempfile
import time
from pathlib import Path

try:
    import pexpect
except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
    raise SystemExit(
        "run_live_smoke.py requires python3-pexpect. Install it before running the Step4 live smoke."
    ) from exc

from patch_codex_config import STOP_BLOCK, SUBAGENT_STOP_BLOCK


IMPLEMENTATION_TIMEOUT_SECONDS = 240
EXIT_TIMEOUT_SECONDS = 180
EXIT_IDLE_GRACE_SECONDS = 90
RESULT_TIMEOUT_SECONDS = 180
TRANSCRIPT_IDLE_SECONDS = 2.0
TRANSCRIPT_IDLE_TIMEOUT_SECONDS = 30.0
CONFIG_KEYS_TO_COPY = (
    "cli_auth_credentials_store",
    "model_provider",
    "model",
    "review_model",
    "model_reasoning_effort",
    "disable_response_storage",
    "personality",
)


def _session_state_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / ".codex" / "session-state" / f"{task_id}-live-smoke.json"


def _trace_path(repo_root: Path, task_id: str, run_id: str) -> Path:
    return repo_root / ".codex" / "tmp" / f"{task_id}-live-smoke-{run_id}.trace.jsonl"


def _transcript_path(repo_root: Path, task_id: str, run_id: str) -> Path:
    return repo_root / ".codex" / "tmp" / f"{task_id}-live-smoke-{run_id}.log"


def _user_codex_home() -> Path:
    override = os.environ.get("CODEX_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex"


def _extract_top_level_setting(config_text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=.*$", config_text)
    if match is None:
        return None
    return match.group(0)


def _extract_named_table(config_text: str, header: str) -> str | None:
    match = re.search(rf"(?ms)^\[{re.escape(header)}\]\n.*?(?=^\[|\Z)", config_text)
    if match is None:
        return None
    return match.group(0).strip()


def _build_minimal_codex_config(source_config_text: str, repo_root: Path) -> str:
    lines: list[str] = []
    copied_keys: set[str] = set()
    for key in CONFIG_KEYS_TO_COPY:
        setting = _extract_top_level_setting(source_config_text, key)
        if setting is None:
            continue
        lines.append(setting)
        copied_keys.add(key)

    if "cli_auth_credentials_store" not in copied_keys:
        lines.append('cli_auth_credentials_store = "file"')
    if "disable_response_storage" not in copied_keys:
        lines.append("disable_response_storage = true")

    provider_name = None
    model_provider_line = _extract_top_level_setting(source_config_text, "model_provider")
    if model_provider_line is not None:
        provider_match = re.search(r'"([^"]+)"', model_provider_line)
        if provider_match is not None:
            provider_name = provider_match.group(1)

    provider_block = None
    if provider_name:
        provider_block = _extract_named_table(source_config_text, f"model_providers.{provider_name}")

    sections = ["\n".join(lines).strip()]
    if provider_block:
        sections.append(provider_block)
    sections.append("[features]\nplugins = false")
    sections.append(f'[projects."{repo_root}"]\ntrust_level = "trusted"')
    sections.append(STOP_BLOCK.strip())
    sections.append(SUBAGENT_STOP_BLOCK.strip())
    return "\n\n".join(section for section in sections if section) + "\n"


def _prepare_isolated_codex_home(repo_root: Path, run_id: str) -> Path:
    source = _user_codex_home()
    target = repo_root / ".codex" / "tmp" / f"live-smoke-codex-home-{run_id}"
    target.mkdir(parents=True, exist_ok=True)
    source_config_path = source / "config.toml"
    source_config_text = ""
    if source_config_path.exists():
        source_config_text = source_config_path.read_text(encoding="utf-8")
    target.joinpath("config.toml").write_text(
        _build_minimal_codex_config(source_config_text, repo_root),
        encoding="utf-8",
    )
    for name in ("auth.json", "installation_id"):
        source_path = source / name
        if source_path.exists():
            shutil.copy2(source_path, target / name)
    return target


def _cleanup_isolated_codex_home(codex_home: Path) -> None:
    if os.environ.get("HARNESS_EVALUATOR_KEEP_LIVE_SMOKE_CODEX_HOME") == "1":
        print(f"[harness-step4] keeping isolated CODEX_HOME at {codex_home}", flush=True)
        return
    shutil.rmtree(codex_home, ignore_errors=True)


def _write_demo_session_state(repo_root: Path, task_id: str) -> Path:
    session_dir = repo_root / ".codex" / "session-state"
    session_dir.mkdir(parents=True, exist_ok=True)
    path = _session_state_path(repo_root, task_id)
    payload = {
        "task": task_id,
        "session": "codex-live-smoke",
        "branch": "task/harness-step4-live-smoke",
        "worktree": str(repo_root),
        "status": "running live smoke",
        "touched_paths": [
            "progress.md",
            ".codex/evaluator-demo/",
            ".codex/evaluations/",
        ],
        "shared_resources": [],
        "evaluator": {
            "phase": "implementation",
            "task_eval_attempt": 0,
            "last_task_eval_result": "",
            "final_eval_attempt": 0,
            "last_final_eval_result": "",
            "repair_from_eval": False,
        },
        "started_at": "2026-06-25T00:00:00+08:00",
        "last_update": "20260625T000000Z",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _park_existing_worktree_sessions(repo_root: Path) -> list[tuple[Path, Path]]:
    session_dir = repo_root / ".codex" / "session-state"
    parked: list[tuple[Path, Path]] = []
    if not session_dir.exists():
        return parked
    parked_dir = session_dir / ".live-smoke-parked"
    parked_dir.mkdir(parents=True, exist_ok=True)
    for path in session_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("worktree") != str(repo_root):
            continue
        target = parked_dir / path.name
        shutil.move(str(path), str(target))
        parked.append((target, path))
    return parked


def _restore_parked_sessions(parked: list[tuple[Path, Path]]) -> None:
    for source, target in parked:
        if source.exists():
            shutil.move(str(source), str(target))


def _git_repo_root(repo_root: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return repo_root.resolve()
    return Path(result.stdout.strip()).resolve()


def _git_common_checkout_root(repo_root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    else:
        common_dir = common_dir.resolve()

    if common_dir.name == ".git":
        return common_dir.parent.resolve()
    return common_dir.resolve()


def _park_repo_local_codex_configs(repo_root: Path) -> list[tuple[Path, Path]]:
    parked: list[tuple[Path, Path]] = []
    roots_to_check: list[Path] = []
    current = repo_root.resolve()
    repo_top = _git_repo_root(repo_root)
    common_checkout_root = _git_common_checkout_root(repo_root)

    while True:
        roots_to_check.append(current)
        if current == repo_top or current.parent == current:
            break
        current = current.parent

    if (
        common_checkout_root is not None
        and common_checkout_root in repo_root.resolve().parents
        and common_checkout_root not in roots_to_check
    ):
        current = repo_top.parent
        while True:
            roots_to_check.append(current)
            if current == common_checkout_root or current.parent == current:
                break
            current = current.parent

    for current in roots_to_check:
        config_path = current / ".codex" / "config.toml"
        if config_path.exists():
            parked_dir = repo_root / ".codex" / "tmp" / ".parked-repo-configs"
            parked_dir.mkdir(parents=True, exist_ok=True)
            target = parked_dir / f"{len(parked):02d}-{current.name or 'root'}-config.toml"
            shutil.move(str(config_path), str(target))
            parked.append((target, config_path))
    return parked


def _restore_parked_repo_local_codex_configs(parked: list[tuple[Path, Path]]) -> None:
    for source, target in reversed(parked):
        if not source.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))


def _latest_result(repo_root: Path, task_id: str) -> tuple[Path, dict]:
    task_root = repo_root / ".codex" / "evaluations" / "tasks" / task_id
    bundles = sorted(path for path in task_root.iterdir() if path.is_dir())
    latest = bundles[-1]
    payload = json.loads((latest / "result.json").read_text(encoding="utf-8"))
    return latest, payload


def _bundle_names(repo_root: Path, task_id: str) -> set[str]:
    task_root = repo_root / ".codex" / "evaluations" / "tasks" / task_id
    if not task_root.exists():
        return set()
    return {path.name for path in task_root.iterdir() if path.is_dir()}


def _demo_output_dir(repo_root: Path, task_id: str) -> Path:
    return repo_root / ".codex" / "evaluator-demo" / task_id


def _strip_previous_demo_output(repo_root: Path, task_id: str) -> None:
    demo_dir = _demo_output_dir(repo_root, task_id)
    if demo_dir.exists():
        shutil.rmtree(demo_dir)


def _strip_previous_task_eval_bundles(repo_root: Path, task_id: str) -> None:
    candidates = [repo_root]
    git_root = _git_repo_root(repo_root)
    if git_root not in candidates:
        candidates.append(git_root)
    for candidate_root in candidates:
        task_root = candidate_root / ".codex" / "evaluations" / "tasks" / task_id
        if task_root.exists():
            shutil.rmtree(task_root)


def _progress_marker(task_id: str, run_id: str) -> str:
    return f"- {task_id} live smoke implementation finished ({run_id})"


def _implementation_prompt(task_id: str, marker: str) -> str:
    return (
        f"You are implementing only task {task_id}. "
        f"Read tasks.json and docs/harness/evaluator-scenarios/{task_id}.json. "
        "Do not inspect unrelated files. "
        f"Run exactly: python3 scripts/harness_evaluator_demo.py write-expected --output-dir .codex/evaluator-demo/{task_id}. "
        f"Then run exactly: python3 scripts/harness_evaluator_demo.py assert-expected --output-dir .codex/evaluator-demo/{task_id}. "
        f"Append exactly one line to progress.md: {marker}. "
        "When those three steps are done, wait for the next user message."
    )


def _demo_output_ready(repo_root: Path, task_id: str) -> bool:
    target = _demo_output_dir(repo_root, task_id) / "result.txt"
    if not target.exists():
        return False
    return target.read_text(encoding="utf-8").strip() == "step4-ready"


def _progress_marker_present(repo_root: Path, marker: str) -> bool:
    progress_path = repo_root / "progress.md"
    if not progress_path.exists():
        return False
    return marker in progress_path.read_text(encoding="utf-8")


def _spawn_interactive_codex(
    repo_root: Path,
    trace_path: Path,
    transcript_path: Path,
    codex_home: Path,
    initial_prompt: str,
) -> pexpect.spawn:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HARNESS_EVALUATOR_TRACE_FILE"] = str(trace_path)
    env["CODEX_HOME"] = str(codex_home)
    env["TERM"] = env.get("TERM") or "xterm-256color"
    if env["TERM"] == "dumb":
        env["TERM"] = "xterm-256color"
    child = pexpect.spawn(
        "codex",
        [
            "--no-alt-screen",
            "--disable",
            "plugins",
            "--dangerously-bypass-hook-trust",
            "--dangerously-bypass-approvals-and-sandbox",
            "--cd",
            str(repo_root),
            "-c",
            'model_reasoning_effort="low"',
            "-c",
            "mcp_servers={}",
            initial_prompt,
        ],
        cwd=str(repo_root.parent),
        env=env,
        encoding="utf-8",
        timeout=10,
    )
    transcript_handle = transcript_path.open("w", encoding="utf-8")
    child.logfile_read = transcript_handle
    child._harness_transcript_handle = transcript_handle  # type: ignore[attr-defined]
    return child


def _close_interactive_codex(child: pexpect.spawn) -> None:
    handle = getattr(child, "_harness_transcript_handle", None)
    try:
        if child.isalive():
            child.close(force=True)
    finally:
        if handle is not None:
            handle.close()


def _send_terminal_line(child: pexpect.spawn, text: str) -> None:
    send = getattr(child, "send", None)
    if callable(send):
        send(text + "\r")
        return
    child.sendline(text)


def _wait_for_transcript_idle(
    transcript_path: Path,
    *,
    idle_seconds: float = TRANSCRIPT_IDLE_SECONDS,
    timeout_seconds: float = TRANSCRIPT_IDLE_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_size = -1
    last_change = time.monotonic()
    while time.monotonic() < deadline:
        size = transcript_path.stat().st_size if transcript_path.exists() else 0
        if size != last_size:
            last_size = size
            last_change = time.monotonic()
        elif time.monotonic() - last_change >= idle_seconds:
            return
        time.sleep(0.2)
    raise TimeoutError("interactive Codex transcript did not become idle before exit")


def _dismiss_interstitial_once(
    child: pexpect.spawn,
    dismissed: set[str],
    key: str,
    response: str,
) -> None:
    if key in dismissed:
        return
    _send_terminal_line(child, response)
    dismissed.add(key)


def _wait_for_startup_prompt(child: pexpect.spawn, dismissed: set[str]) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        index = child.expect(
            [
                r"Update available!",
                r"Hooks need review",
                r"Do you trust the contents of this directory\?",
                r"OpenAI Codex",
                r"Starting MCP servers",
                r"tab to queue message",
                r"MCP startup incomplete",
                r"\n›",
                pexpect.TIMEOUT,
                pexpect.EOF,
            ],
            timeout=5,
        )
        if index == 0:
            _dismiss_interstitial_once(child, dismissed, "update_available", "2")
            continue
        if index == 1:
            _dismiss_interstitial_once(child, dismissed, "hooks_review", "2")
            continue
        if index == 2:
            _dismiss_interstitial_once(child, dismissed, "trust_directory", "1")
            continue
        if index in (3, 4, 5, 6, 7):
            return
        if index == 9:
            raise RuntimeError("interactive Codex session exited during startup")
    raise TimeoutError("timed out waiting for the interactive Codex prompt")


def _wait_for_implementation(
    child: pexpect.spawn,
    repo_root: Path,
    task_id: str,
    marker: str,
    dismissed: set[str],
) -> None:
    deadline = time.monotonic() + IMPLEMENTATION_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _demo_output_ready(repo_root, task_id) and _progress_marker_present(repo_root, marker):
            return
        index = child.expect(
            [
                r"Update available!",
                r"Hooks need review",
                r"Do you trust the contents of this directory\?",
                pexpect.TIMEOUT,
                pexpect.EOF,
            ],
            timeout=3,
        )
        if index == 0:
            _dismiss_interstitial_once(child, dismissed, "update_available", "2")
            continue
        if index == 1:
            _dismiss_interstitial_once(child, dismissed, "hooks_review", "2")
            continue
        if index == 2:
            _dismiss_interstitial_once(child, dismissed, "trust_directory", "1")
            continue
        if index == 4:
            raise RuntimeError("interactive Codex session exited before demo implementation completed")
    raise TimeoutError("timed out waiting for the demo implementation steps to finish")


def _wait_for_exit(
    child: pexpect.spawn,
    dismissed: set[str],
    *,
    exit_requested: bool = False,
) -> bool:
    deadline = time.monotonic() + EXIT_TIMEOUT_SECONDS
    idle_deadline = time.monotonic() + EXIT_IDLE_GRACE_SECONDS
    prompt_seen = False
    while time.monotonic() < deadline:
        index = child.expect(
            [
                r"Stop hook \(failed\)",
                r"hook returned invalid stop hook JSON output",
                r"Update available!",
                r"Hooks need review",
                r"Do you trust the contents of this directory\?",
                r"\n›",
                pexpect.EOF,
                pexpect.TIMEOUT,
            ],
            timeout=5,
        )
        if index == 0:
            raise RuntimeError("Stop hook failed during the live smoke")
        if index == 1:
            raise RuntimeError("Stop hook returned invalid JSON during the live smoke")
        if index == 2:
            _dismiss_interstitial_once(child, dismissed, "update_available", "2")
            idle_deadline = time.monotonic() + EXIT_IDLE_GRACE_SECONDS
            continue
        if index == 3:
            _dismiss_interstitial_once(child, dismissed, "hooks_review", "2")
            idle_deadline = time.monotonic() + EXIT_IDLE_GRACE_SECONDS
            continue
        if index == 4:
            _dismiss_interstitial_once(child, dismissed, "trust_directory", "1")
            idle_deadline = time.monotonic() + EXIT_IDLE_GRACE_SECONDS
            continue
        if index == 5:
            if exit_requested or prompt_seen:
                raise RuntimeError("interactive Codex returned to the prompt instead of exiting after /exit")
            prompt_seen = True
            exit_requested = True
            idle_deadline = time.monotonic() + EXIT_IDLE_GRACE_SECONDS
            _send_terminal_line(child, "/exit")
            continue
        if index == 6:
            return True
        if exit_requested and time.monotonic() >= idle_deadline:
            return False
    return False


def _wait_for_new_result(
    repo_root: Path,
    task_id: str,
    *,
    existing_bundles: set[str],
    timeout_seconds: float = RESULT_TIMEOUT_SECONDS,
) -> tuple[Path, dict]:
    task_root = repo_root / ".codex" / "evaluations" / "tasks" / task_id
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current_bundles = _bundle_names(repo_root, task_id) - existing_bundles
        if current_bundles and task_root.exists():
            candidates = sorted(
                (
                    task_root / bundle_name
                    for bundle_name in current_bundles
                    if (task_root / bundle_name / "result.json").exists()
                ),
                key=lambda path: path.name,
            )
            if candidates:
                latest = candidates[-1]
                payload = json.loads((latest / "result.json").read_text(encoding="utf-8"))
                return latest, payload
        time.sleep(1)
    raise TimeoutError(f"timed out waiting for a new evaluator result for {task_id}")


def _run_interactive_smoke_session(
    repo_root: Path, task_id: str, run_id: str
) -> tuple[pexpect.spawn, Path, Path, Path, bool]:
    trace_path = _trace_path(repo_root, task_id, run_id)
    transcript_path = _transcript_path(repo_root, task_id, run_id)
    codex_home = _prepare_isolated_codex_home(repo_root, run_id)
    marker = _progress_marker(task_id, run_id)
    prompt = _implementation_prompt(task_id, marker)
    dismissed: set[str] = set()
    child = _spawn_interactive_codex(repo_root, trace_path, transcript_path, codex_home, prompt)
    try:
        _wait_for_startup_prompt(child, dismissed)
        _wait_for_implementation(child, repo_root, task_id, marker, dismissed)
        _wait_for_transcript_idle(transcript_path)
        _send_terminal_line(child, "/exit")
        exited_cleanly = _wait_for_exit(child, dismissed, exit_requested=True)
        return child, trace_path, transcript_path, codex_home, exited_cleanly
    except Exception:
        _close_interactive_codex(child)
        _cleanup_isolated_codex_home(codex_home)
        raise


def _run_interactive_smoke(repo_root: Path, task_id: str, run_id: str) -> tuple[Path, Path, bool]:
    child, trace_path, transcript_path, codex_home, exited_cleanly = _run_interactive_smoke_session(
        repo_root,
        task_id,
        run_id,
    )
    try:
        return trace_path, transcript_path, exited_cleanly
    finally:
        _close_interactive_codex(child)
        _cleanup_isolated_codex_home(codex_home)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--task-id", default="harness-evaluator-demo-01")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    task_id = args.task_id
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    parked = _park_existing_worktree_sessions(repo_root)
    parked_repo_configs = _park_repo_local_codex_configs(repo_root)
    session_state = _write_demo_session_state(repo_root, task_id)
    _strip_previous_task_eval_bundles(repo_root, task_id)
    existing_bundles = _bundle_names(repo_root, task_id)
    _strip_previous_demo_output(repo_root, task_id)

    child: pexpect.spawn | None = None
    codex_home: Path | None = None
    try:
        child, trace_path, transcript_path, codex_home, exited_cleanly = _run_interactive_smoke_session(
            repo_root,
            task_id,
            run_id,
        )
        if not trace_path.exists():
            raise SystemExit(f"Stop hook trace was not written: {trace_path}")
        latest, payload = _wait_for_new_result(
            repo_root,
            task_id,
            existing_bundles=existing_bundles,
        )
        if payload.get("status") != "pass" or payload.get("gate") != "task" or payload.get("task_id") != task_id:
            raise SystemExit(
                "unexpected evaluator result in "
                f"{latest}: {json.dumps(payload, ensure_ascii=False)}; inspect {transcript_path}"
            )
        if not exited_cleanly:
            print(
                "[harness-step4] interactive Codex did not exit naturally after /exit; accepted based on trace + new pass result",
                flush=True,
            )

        print(
            json.dumps(
                {
                    "status": "ok",
                    "bundle": str(latest),
                    "task_id": task_id,
                    "trace": str(trace_path),
                    "transcript": str(transcript_path),
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        if session_state.exists():
            session_state.unlink()
        _restore_parked_repo_local_codex_configs(parked_repo_configs)
        _restore_parked_sessions(parked)
        if child is not None:
            _close_interactive_codex(child)
        if codex_home is not None:
            _cleanup_isolated_codex_home(codex_home)


if __name__ == "__main__":
    raise SystemExit(main())
