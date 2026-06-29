from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .git_ops import auto_commit, git_dirty_paths, paths_owned_by_task
from .wiki_cli import run_backlinks, run_index, run_ingest_plan, run_validate, wiki_cli_command


EXECUTION_FAILURE_EXIT_CODE = -1
ALLOWED_BASELINE_REASON = "waiting for clean git baseline before automatic retry"
QUEUE_PREVIEW_CHARS = 1600

CodexRunner = Callable[[Any, str], subprocess.CompletedProcess[str]]


def list_queue(db: sqlite3.Connection) -> list[dict[str, object]]:
    rows = db.execute(
        """
        select
          ingest_tasks.*,
          raw_items.canonical_url,
          raw_items.raw_path,
          raw_items.title,
          raw_items.content_bytes,
          raw_items.metadata_json
        from ingest_tasks
        left join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.status in ('pending', 'approved', 'running', 'failed')
        order by ingest_tasks.created_at, ingest_tasks.id
        """
    ).fetchall()
    return [_queue_row_response(row) for row in rows]


def approve_trusted_source_tasks(db: sqlite3.Connection, trusted_domains: list[str]) -> dict[str, object]:
    normalized_domains = {_normalize_domain(domain) for domain in trusted_domains if domain.strip()}
    if not normalized_domains:
        return {"approved_count": 0, "task_ids": []}

    rows = db.execute(
        """
        select ingest_tasks.id, raw_items.canonical_url
        from ingest_tasks
        join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.status = 'pending'
        """
    ).fetchall()
    task_ids = [
        int(row["id"])
        for row in rows
        if _url_matches_trusted_domain(str(row["canonical_url"]), normalized_domains)
    ]
    if not task_ids:
        return {"approved_count": 0, "task_ids": []}

    placeholders = ", ".join("?" for _ in task_ids)
    db.execute(
        f"""
        update ingest_tasks
        set status = 'approved',
            reason = ?,
            updated_at = current_timestamp
        where status = 'pending' and id in ({placeholders})
        """,
        ["approved by trusted source domain", *task_ids],
    )
    db.commit()
    return {"approved_count": len(task_ids), "task_ids": task_ids}


def approve_task(settings: Any, db: sqlite3.Connection, task_id: int) -> dict[str, object]:
    task = _load_task(db, task_id)
    if task["status"] not in ("pending", "failed"):
        raise InvalidTaskStateError(f"task cannot be approved from state {task['status']}: {task_id}")
    cursor = db.execute(
        """
        update ingest_tasks
        set status = 'approved',
            reason = ?,
            updated_at = current_timestamp
        where id = ? and status in ('pending', 'failed')
        """,
        ("approved by user", task_id),
    )
    if cursor.rowcount != 1:
        _raise_invalid_current_state(db, task_id, "approved")
    db.commit()
    return _task_response(db, int(task["id"]))


def reject_task(db: sqlite3.Connection, task_id: int, reason: str) -> dict[str, object]:
    task = _load_task(db, task_id)
    if task["status"] not in ("pending", "approved", "failed"):
        raise InvalidTaskStateError(f"task cannot be rejected from state {task['status']}: {task_id}")
    cursor = db.execute(
        """
        update ingest_tasks
        set status = 'rejected',
            reason = ?,
            updated_at = current_timestamp
        where id = ? and status in ('pending', 'approved', 'failed')
        """,
        (reason, task_id),
    )
    if cursor.rowcount != 1:
        _raise_invalid_current_state(db, task_id, "rejected")
    db.commit()
    return _task_response(db, task_id)


def run_approved_task(
    settings: Any,
    db: sqlite3.Connection,
    task_id: int,
    auto_commit_enabled: bool,
    codex_runner: CodexRunner | None = None,
) -> dict[str, object]:
    claimed_running: set[int] = set()
    try:
        return _run_approved_task(settings, db, task_id, auto_commit_enabled, codex_runner, claimed_running)
    except (TaskNotFoundError, InvalidTaskStateError, IngestInputError):
        raise
    except Exception as exc:
        try:
            allowed_states = {"running"} if task_id in claimed_running else {"approved"}
            _mark_task_failed(db, task_id, str(exc), allowed_states=allowed_states)
            return _task_response(db, task_id)
        except (TaskNotFoundError, InvalidTaskStateError):
            raise
        except Exception:
            raise exc


def _run_approved_task(
    settings: Any,
    db: sqlite3.Connection,
    task_id: int,
    auto_commit_enabled: bool,
    codex_runner: CodexRunner | None,
    claimed_running: set[int],
) -> dict[str, object]:
    task = _load_task(db, task_id)
    if task["status"] != "approved":
        raise InvalidTaskStateError(f"task is not approved: {task_id}")
    raw_item = _load_raw_item(db, int(task["raw_item_id"])) if task["raw_item_id"] is not None else None
    if raw_item is None:
        _mark_task_failed(db, task_id, "raw item is required for ingest", allowed_states={"approved"})
        return _task_response(db, task_id)

    domain = str(task["target_domain"])
    source_id = str(task["source_id"])
    try:
        raw_path = _domain_relative_raw_path(settings, domain, str(raw_item["raw_path"]))
    except IngestInputError as exc:
        _mark_task_failed(db, task_id, str(exc), allowed_states={"approved"})
        raise

    baseline_dirty_paths = git_dirty_paths(settings.repo_root)
    allowed_baseline_paths = _approved_raw_repo_paths(settings, db, domain)
    disallowed_baseline_paths = baseline_dirty_paths - allowed_baseline_paths
    if disallowed_baseline_paths:
        _defer_approved_task(db, task_id, ALLOWED_BASELINE_REASON)
        return _task_response(db, task_id)

    cursor = db.execute(
        """
        update ingest_tasks
        set status = 'running',
            reason = 'ingest running',
            updated_at = current_timestamp
        where id = ? and status = 'approved'
        """,
        (task_id,),
    )
    if cursor.rowcount != 1:
        _raise_invalid_current_state(db, task_id, "running")
    db.commit()
    claimed_running.add(task_id)

    ingest_plan = _run_step(run_ingest_plan(settings, domain, raw_path), db, task_id, "ingest-plan")
    if ingest_plan is not None:
        return ingest_plan

    prompt = _ingest_prompt(domain, raw_path)
    codex_job_id = _run_ingest_codex_job(settings, db, domain, prompt, codex_runner or _default_codex_runner)
    db.execute("update ingest_tasks set codex_job_id = ?, updated_at = current_timestamp where id = ?", (codex_job_id, task_id))
    db.commit()
    codex_job = db.execute("select status, stderr from codex_jobs where id = ?", (codex_job_id,)).fetchone()
    if codex_job["status"] != "succeeded":
        _mark_task_failed(db, task_id, str(codex_job["stderr"]))
        return _task_response(db, task_id)

    index = _run_step(run_index(settings, domain), db, task_id, "index")
    if index is not None:
        return index
    backlinks = _run_step(run_backlinks(settings, domain), db, task_id, "backlinks")
    if backlinks is not None:
        return backlinks

    validation_result = run_validate(settings, domain)
    validation_run_id = _insert_validation_run(settings, db, domain, validation_result)
    db.execute(
        "update ingest_tasks set validation_run_id = ?, updated_at = current_timestamp where id = ?",
        (validation_run_id, task_id),
    )
    db.commit()
    if validation_result.returncode != 0:
        _mark_task_failed(db, task_id, validation_result.stdout + validation_result.stderr)
        return _task_response(db, task_id)

    commit_id: int | None = None
    if auto_commit_enabled:
        dirty_paths = git_dirty_paths(settings.repo_root)
        owned_prefixes = [f"personal-wiki/domains/{domain}/", "personal-wiki/global/"]
        if not paths_owned_by_task(dirty_paths, owned_prefixes):
            _mark_task_failed(db, task_id, "dirty paths include files outside the ingest task")
            return _task_response(db, task_id)
        commit_message = f"chore(wiki): ingest {domain} {source_id}"
        try:
            commit_sha = auto_commit(settings.repo_root, sorted(dirty_paths), commit_message)
        except ValueError as exc:
            _mark_task_failed(db, task_id, str(exc))
            return _task_response(db, task_id)
        commit_id = db.execute(
            """
            insert into commit_records (source_id, target_domain, commit_sha, message)
            values (?, ?, ?, ?)
            """,
            (source_id, domain, commit_sha, commit_message),
        ).lastrowid

    db.execute(
        """
        update ingest_tasks
        set status = 'succeeded',
            commit_id = ?,
            reason = 'ingest succeeded',
            updated_at = current_timestamp
        where id = ?
        """,
        (commit_id, task_id),
    )
    db.commit()
    return _task_response(db, task_id)


def commit_paths(
    settings: Any,
    db: sqlite3.Connection,
    domain: str,
    paths: list[str],
    message: str,
    source_id: str | None = None,
) -> dict[str, object]:
    owned_prefixes = [f"personal-wiki/domains/{domain}/", "personal-wiki/global/"]
    requested_paths = set(paths)
    if not requested_paths:
        raise ValueError("paths are required")
    if not paths_owned_by_task(requested_paths, owned_prefixes):
        raise ValueError("paths include files outside the commit domain")

    dirty_paths = git_dirty_paths(settings.repo_root)
    if not requested_paths.issubset(dirty_paths):
        raise ValueError("requested paths are not dirty")

    commit_sha = auto_commit(settings.repo_root, sorted(requested_paths), message)
    commit_record_id = db.execute(
        """
        insert into commit_records (source_id, target_domain, commit_sha, message)
        values (?, ?, ?, ?)
        """,
        (source_id, domain, commit_sha, message),
    ).lastrowid
    db.commit()
    return {"commit_sha": commit_sha, "commit_record_id": commit_record_id}


def _run_step(
    result: subprocess.CompletedProcess[str],
    db: sqlite3.Connection,
    task_id: int,
    step_name: str,
) -> dict[str, object] | None:
    if result.returncode == 0:
        return None
    _mark_task_failed(db, task_id, f"{step_name} failed: {result.stdout}{result.stderr}")
    return _task_response(db, task_id)


def _run_ingest_codex_job(
    settings: Any,
    db: sqlite3.Connection,
    domain: str,
    prompt: str,
    codex_runner: CodexRunner,
) -> int:
    cursor = db.execute(
        "insert into codex_jobs (job_type, target_domain, prompt, status) values (?, ?, ?, ?)",
        ("ingest", domain, prompt, "pending"),
    )
    job_id = int(cursor.lastrowid)
    db.commit()

    db.execute("update codex_jobs set status = ?, started_at = current_timestamp where id = ?", ("running", job_id))
    db.commit()

    try:
        result = codex_runner(settings, prompt)
    except subprocess.TimeoutExpired as exc:
        return _finish_failed_codex_job(db, job_id, f"Codex command timed out after {exc.timeout} seconds")
    except Exception as exc:
        return _finish_failed_codex_job(db, job_id, str(exc))

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


def _default_codex_runner(settings: Any, prompt: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            settings.codex_command,
            "exec",
            "--cd",
            str(settings.repo_root),
            "--sandbox",
            "workspace-write",
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _finish_failed_codex_job(db: sqlite3.Connection, job_id: int, stderr: str) -> int:
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


def _insert_validation_run(
    settings: Any,
    db: sqlite3.Connection,
    domain: str,
    result: subprocess.CompletedProcess[str],
) -> int:
    command = " ".join(wiki_cli_command(settings, "validate", "--domain", domain))
    status = "succeeded" if result.returncode == 0 else "failed"
    return db.execute(
        """
        insert into validation_runs (target_domain, status, command, output)
        values (?, ?, ?, ?)
        """,
        (domain, status, command, result.stdout + result.stderr),
    ).lastrowid

def _load_task(db: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    row = db.execute("select * from ingest_tasks where id = ?", (task_id,)).fetchone()
    if row is None:
        raise TaskNotFoundError(f"ingest task not found: {task_id}")
    return row


def _raise_invalid_current_state(db: sqlite3.Connection, task_id: int, target_state: str) -> None:
    current = _load_task(db, task_id)
    raise InvalidTaskStateError(f"task cannot be set to {target_state} from state {current['status']}: {task_id}")


def _load_raw_item(db: sqlite3.Connection, raw_item_id: int) -> sqlite3.Row | None:
    return db.execute("select * from raw_items where id = ?", (raw_item_id,)).fetchone()


def _task_response(db: sqlite3.Connection, task_id: int) -> dict[str, object]:
    return dict(_load_task(db, task_id))


def _queue_row_response(row: sqlite3.Row) -> dict[str, object]:
    item = dict(row)
    metadata_json = item.pop("metadata_json", None)
    item["metadata"] = _parse_metadata(metadata_json)
    raw_path = item.get("raw_path")
    item["path"] = raw_path
    item["content_preview"] = _read_preview(raw_path)
    return item


def _parse_metadata(metadata_json: object) -> dict[str, object]:
    if not metadata_json or not isinstance(metadata_json, str):
        return {}
    try:
        parsed = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _read_preview(raw_path: object) -> str:
    if not raw_path or not isinstance(raw_path, str):
        return ""
    path = Path(raw_path)
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:QUEUE_PREVIEW_CHARS]
    except OSError:
        return ""


def _normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower()
    return normalized[4:] if normalized.startswith("www.") else normalized


def _url_matches_trusted_domain(url: str, trusted_domains: set[str]) -> bool:
    host = _normalize_domain(urlparse(url).hostname or "")
    return any(host == domain or host.endswith(f".{domain}") for domain in trusted_domains)


def _mark_task_failed(db: sqlite3.Connection, task_id: int, reason: str, allowed_states: set[str] | None = None) -> None:
    params: list[object] = [reason[-1000:], task_id]
    state_filter = ""
    if allowed_states:
        placeholders = ", ".join("?" for _ in allowed_states)
        state_filter = f" and status in ({placeholders})"
        params.extend(sorted(allowed_states))
    cursor = db.execute(
        f"""
        update ingest_tasks
        set status = 'failed',
            reason = ?,
            updated_at = current_timestamp
        where id = ?{state_filter}
        """,
        params,
    )
    if allowed_states and cursor.rowcount != 1:
        _raise_invalid_current_state(db, task_id, "failed")
    db.commit()


def _defer_approved_task(db: sqlite3.Connection, task_id: int, reason: str) -> None:
    cursor = db.execute(
        """
        update ingest_tasks
        set reason = ?,
            updated_at = current_timestamp
        where id = ? and status = 'approved'
        """,
        (reason[-1000:], task_id),
    )
    if cursor.rowcount != 1:
        _raise_invalid_current_state(db, task_id, "approved")
    db.commit()


def _domain_relative_raw_path(settings: Any, domain: str, raw_path: str) -> str:
    raw = Path(raw_path)
    domain_root = settings.wiki_root / "domains" / domain
    domain_raw_root = domain_root / "raw"
    candidates = [raw] if raw.is_absolute() else [settings.repo_root / raw, settings.wiki_root / raw]
    for path in candidates:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(domain_raw_root.resolve(strict=False))
            return resolved.relative_to(domain_root.resolve(strict=False)).as_posix()
        except ValueError:
            continue
    raise IngestInputError(f"raw path is not under domain raw directory: {raw_path}")


def _task_raw_repo_path(settings: Any, domain: str, raw_path: str) -> str:
    raw = Path(raw_path)
    candidates = [raw] if raw.is_absolute() else [settings.repo_root / raw, settings.wiki_root / raw]
    domain_raw_root = settings.wiki_root / "domains" / domain / "raw"
    for path in candidates:
        try:
            relative_to_raw = path.resolve(strict=False).relative_to(domain_raw_root.resolve(strict=False))
        except ValueError:
            continue
        return (Path("personal-wiki") / "domains" / domain / "raw" / relative_to_raw).as_posix()
    raise IngestInputError(f"raw path is not under domain raw directory: {raw_path}")


def _approved_raw_repo_paths(settings: Any, db: sqlite3.Connection, domain: str) -> set[str]:
    rows = db.execute(
        """
        select raw_items.raw_path
        from ingest_tasks
        join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.target_domain = ?
          and ingest_tasks.status = 'approved'
        """,
        (domain,),
    ).fetchall()
    paths: set[str] = set()
    for row in rows:
        paths.add(_task_raw_repo_path(settings, domain, str(row["raw_path"])))
    return paths


def _ingest_prompt(domain: str, raw_path: str) -> str:
    return (
        f"使用 personal-wiki-manager，目标 domain: {domain}，入库 {raw_path}，"
        "按 raw->ingest-plan->wiki->compact->index->validate 完整流程处理；"
        "大型资料 raw 保完整但可 gzip 压缩，wiki 只沉淀索引/综合/关键结论，"
        "优先更新已有页面，报告文件和验证结果。"
    )


class TaskNotFoundError(ValueError):
    pass


class InvalidTaskStateError(ValueError):
    pass


class IngestInputError(ValueError):
    pass
