from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def collect_wiki_metrics(settings: Any, db: sqlite3.Connection) -> dict[str, object]:
    wiki_root = settings.wiki_root
    files = _files_under(wiki_root)
    raw_files = _raw_files(wiki_root)
    wiki_files = _wiki_files(wiki_root)
    global_files = _files_under(wiki_root / "global")

    counts = {
        "domain_count": _domain_count(wiki_root),
        "wiki_page_count": len(wiki_files),
        "raw_file_count": len(raw_files),
        "raw_item_count": _table_count(db, "raw_items"),
        "total_file_count": len(files),
    }
    sizes = {
        "total_bytes": _sum_size(files),
        "wiki_bytes": _sum_size(wiki_files),
        "raw_bytes": _sum_size(raw_files),
        "global_bytes": _sum_size(global_files),
        "state_bytes": _sum_size(_files_under(settings.resolved_state_dir)),
    }
    health = _health_summary(db)
    return {"counts": counts, "sizes": sizes, "health": health}


def _files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


def _wiki_files(wiki_root: Path) -> list[Path]:
    files: list[Path] = []
    domains_root = wiki_root / "domains"
    if domains_root.exists():
        for domain in domains_root.iterdir():
            files.extend(_files_under(domain / "wiki"))
    files.extend(_files_under(wiki_root / "global" / "wiki"))
    return [path for path in files if path.suffix == ".md"]


def _raw_files(wiki_root: Path) -> list[Path]:
    files: list[Path] = []
    domains_root = wiki_root / "domains"
    if domains_root.exists():
        for domain in domains_root.iterdir():
            files.extend(_files_under(domain / "raw"))
    return files


def _domain_count(wiki_root: Path) -> int:
    domains_root = wiki_root / "domains"
    if not domains_root.exists():
        return 0
    return sum(1 for path in domains_root.iterdir() if path.is_dir())


def _sum_size(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            continue
    return total


def _table_count(db: sqlite3.Connection, table: str) -> int:
    row = db.execute(f"select count(*) as count from {table}").fetchone()
    return int(row["count"])


def _health_summary(db: sqlite3.Connection) -> dict[str, object]:
    latest_validation = db.execute(
        """
        select status, created_at
        from validation_runs
        order by created_at desc, id desc
        limit 1
        """
    ).fetchone()
    failed_run_count = _count_where(db, "fetch_runs", "status = 'failed'")
    failed_task_count = _count_where(db, "ingest_tasks", "status = 'failed'")
    pending_task_count = _count_where(db, "ingest_tasks", "status in ('pending', 'approved', 'running')")

    score = 100
    latest_validation_status = latest_validation["status"] if latest_validation is not None else None
    latest_validation_at = latest_validation["created_at"] if latest_validation is not None else None
    if latest_validation is None:
        score -= 15
    elif latest_validation_status != "succeeded":
        score -= 40
    score -= min(failed_run_count * 5, 20)
    score -= min(failed_task_count * 10, 30)
    score -= min(pending_task_count * 2, 10)
    score = max(score, 0)

    if score >= 90:
        status = "healthy"
        summary = "轻量健康度：正常"
    elif score >= 70:
        status = "attention"
        summary = "轻量健康度：需要关注"
    else:
        status = "unhealthy"
        summary = "轻量健康度：异常"

    return {
        "status": status,
        "score": score,
        "summary": summary,
        "latest_validation_status": latest_validation_status,
        "latest_validation_at": latest_validation_at,
        "failed_run_count": failed_run_count,
        "failed_task_count": failed_task_count,
        "pending_task_count": pending_task_count,
    }


def _count_where(db: sqlite3.Connection, table: str, where: str) -> int:
    row = db.execute(f"select count(*) as count from {table} where {where}").fetchone()
    return int(row["count"])
