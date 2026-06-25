from __future__ import annotations

import subprocess
from typing import Any

EXECUTION_FAILURE_EXIT_CODE = -1
SANDBOX_FALLBACK_MODE = "danger-full-access"


def build_query_prompt(domain: str, question: str, persist: bool) -> str:
    if persist:
        return (
            f'使用 personal-wiki-manager，目标 domain: {domain}，基于已有 wiki/raw 回答 "{question}"，'
            "引用路径；如果答案有长期复用价值，沉淀进最小合适 curated wiki 页面，然后 index+validate 并报告文件。"
        )
    return (
        f'使用 personal-wiki-manager，目标 domain: {domain}，基于已有 wiki/raw 回答 "{question}"，'
        "引用路径；不要修改文件，不要运行写入命令，只返回答案和引用。"
    )


def run_codex_job(
    settings: Any,
    db: Any,
    job_type: str,
    domain: str | None,
    user_input: str,
    persist: bool = False,
) -> int:
    if job_type != "query":
        raise ValueError("Only query codex jobs are supported")

    prompt = build_query_prompt(str(domain), user_input, persist)
    cursor = db.execute(
        "insert into codex_jobs (job_type, target_domain, prompt, status) values (?, ?, ?, ?)",
        (job_type, domain, prompt, "pending"),
    )
    job_id = int(cursor.lastrowid)
    db.commit()

    db.execute("update codex_jobs set status = ?, started_at = current_timestamp where id = ?", ("running", job_id))
    db.commit()

    try:
        result = _run_codex_command(settings, prompt, "workspace-write" if persist else "read-only")
    except subprocess.TimeoutExpired as exc:
        stderr = f"Codex command timed out after {exc.timeout} seconds"
        return _finish_failed_job(db, job_id, stderr)
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return _finish_failed_job(db, job_id, str(exc))

    status = "succeeded" if result.returncode == 0 else "failed"
    db.execute(
        """
        update codex_jobs
        set status = ?, stdout = ?, stderr = ?, exit_code = ?, finished_at = current_timestamp
        where id = ?
        """,
        (status, result.stdout, result.stderr, result.returncode, job_id),
    )
    db.commit()
    return job_id


def _run_codex_command(settings: Any, prompt: str, sandbox: str) -> subprocess.CompletedProcess[str]:
    result = _run_codex_subprocess(settings, prompt, sandbox)
    if _is_sandbox_startup_failure(result):
        fallback = _run_codex_subprocess(settings, prompt, SANDBOX_FALLBACK_MODE)
        fallback.stderr = _fallback_stderr(result, fallback)
        return fallback
    return result


def _run_codex_subprocess(settings: Any, prompt: str, sandbox: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            settings.codex_command,
            "exec",
            "--cd",
            str(settings.repo_root),
            "--sandbox",
            sandbox,
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _is_sandbox_startup_failure(result: subprocess.CompletedProcess[str]) -> bool:
    output = f"{result.stdout}\n{result.stderr}".lower()
    return "bwrap:" in output or "bubblewrap" in output or "命令沙箱启动失败" in output


def _fallback_stderr(original: subprocess.CompletedProcess[str], fallback: subprocess.CompletedProcess[str]) -> str:
    note = "Codex sandbox fallback: retried with danger-full-access after sandbox startup failure."
    parts = [note]
    if original.stderr:
        parts.append(f"Original stderr:\n{original.stderr.strip()}")
    if original.stdout:
        parts.append(f"Original stdout:\n{original.stdout.strip()}")
    if fallback.stderr:
        parts.append(fallback.stderr.strip())
    return "\n\n".join(parts) + "\n"


def _finish_failed_job(db: Any, job_id: int, stderr: str) -> int:
    db.execute(
        """
        update codex_jobs
        set status = ?, stderr = ?, exit_code = ?, finished_at = current_timestamp
        where id = ?
        """,
        ("failed", stderr, EXECUTION_FAILURE_EXIT_CODE, job_id),
    )
    db.commit()
    return job_id
