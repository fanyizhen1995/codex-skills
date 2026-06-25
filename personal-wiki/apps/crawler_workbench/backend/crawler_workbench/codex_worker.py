from __future__ import annotations

import subprocess
from typing import Any

EXECUTION_FAILURE_EXIT_CODE = -1


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

    command = [
        settings.codex_command,
        "exec",
        "--cd",
        str(settings.repo_root),
        "--sandbox",
        "workspace-write" if persist else "read-only",
        prompt,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
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
