#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import yaml


TASK_ID = "compute-accelerator-formal-crawl-01"
RAW_PREFIX = Path("personal-wiki/domains/ai_infra/raw/crawler")
ACCELERATOR_METADATA_KEYS = {"source_rank", "accelerator_scope", "extract_mode"}
REQUIRED_MANIFEST_KEYS: dict[str, type[object]] = {
    "task_id": str,
    "generated_at": str,
    "repo_root": str,
    "sources_yaml": str,
    "ran_source_ids": list,
    "succeeded": list,
    "failed": list,
    "skipped_disabled": list,
    "raw_paths": list,
    "ingest_tasks": list,
    "summary": dict,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or verify a formal compute accelerator crawl.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repo-root", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--source-id", action="append", default=[])

    verify_parser = subparsers.add_parser("verify-manifest")
    verify_parser.add_argument("--repo-root", required=True)
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--min-succeeded", type=int, default=1)

    args = parser.parse_args(argv)
    if args.command == "run":
        try:
            manifest = run_formal_crawl(
                repo_root=Path(args.repo_root).resolve(),
                output_dir=Path(args.output_dir).resolve(),
                source_ids=args.source_id,
            )
        except Exception as exc:
            print(f"formal crawl failed: {exc}", file=sys.stderr)
            return 1
        if not manifest["ran_source_ids"]:
            print("formal crawl selected no enabled accelerator profiles to attempt", file=sys.stderr)
            return 1
        print(json.dumps({"manifest": str(Path(args.output_dir) / "manifest.json")}, ensure_ascii=False))
        return 0

    ok, message = verify_manifest(
        repo_root=Path(args.repo_root).resolve(),
        manifest_path=Path(args.manifest),
        min_succeeded=args.min_succeeded,
    )
    if ok:
        print(message)
        return 0
    print(message, file=sys.stderr)
    return 1


def run_formal_crawl(repo_root: Path, output_dir: Path, source_ids: Sequence[str]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_dir = output_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    source_path = repo_root / "personal-wiki/apps/crawler_workbench/config/sources.example.yaml"
    profiles = _load_yaml_profiles(source_path)
    selected_profiles, skipped_disabled = select_run_profiles(profiles, source_ids=source_ids)
    run_profiles = prepare_run_profiles(selected_profiles)
    disabled_profiles = [
        dict(profile)
        for profile in profiles
        if _is_accelerator_profile(profile)
        and not _is_enabled(profile)
        and (not source_ids or str(profile["id"]) in set(source_ids))
    ]
    local_sources_yaml = state_dir / "sources.yaml"
    _write_profiles_yaml(local_sources_yaml, [*run_profiles, *disabled_profiles])

    manifest: dict[str, Any] = {
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "sources_yaml": str(local_sources_yaml),
        "ran_source_ids": [],
        "succeeded": [],
        "failed": [],
        "skipped_disabled": skipped_disabled,
        "raw_paths": [],
        "ingest_tasks": [],
        "summary": {
            "selected_count": len(selected_profiles),
            "attempted_count": 0,
            "succeeded_count": 0,
            "failed_count": 0,
            "skipped_disabled_count": len(skipped_disabled),
        },
    }

    if run_profiles:
        _mirror_profiles_and_run(repo_root, state_dir, run_profiles, manifest)

    manifest["summary"] = {
        "selected_count": len(selected_profiles),
        "attempted_count": len(manifest["ran_source_ids"]),
        "succeeded_count": len(manifest["succeeded"]),
        "failed_count": len(manifest["failed"]),
        "skipped_disabled_count": len(manifest["skipped_disabled"]),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def select_run_profiles(
    profiles: Sequence[dict[str, Any]],
    source_ids: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    requested = set(source_ids)
    selected: list[dict[str, Any]] = []
    skipped_disabled: list[dict[str, str]] = []
    for profile in profiles:
        if not _is_accelerator_profile(profile):
            continue
        source_id = str(profile["id"])
        if requested and source_id not in requested:
            continue
        if not _is_enabled(profile):
            skipped_disabled.append({"source_id": source_id, "reason": "disabled"})
            continue
        selected.append(profile)
    return selected, skipped_disabled


def prepare_run_profiles(profiles: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for profile in profiles:
        mirrored = dict(profile)
        mirrored["baseline_on_first_run"] = False
        prepared.append(mirrored)
    return prepared


def verify_manifest(repo_root: Path, manifest_path: Path, min_succeeded: int = 1) -> tuple[bool, str]:
    if not manifest_path.exists():
        return False, f"missing manifest: {manifest_path}"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"manifest is not valid JSON: {exc}"
    if not isinstance(manifest, dict):
        return False, "manifest must be a JSON object"

    for key, expected_type in REQUIRED_MANIFEST_KEYS.items():
        if key not in manifest:
            return False, f"missing required manifest key: {key}"
        if not isinstance(manifest[key], expected_type):
            return False, f"manifest {key} must be a {expected_type.__name__}"

    summary = manifest["summary"]
    succeeded_count = summary.get("succeeded_count")
    if not isinstance(succeeded_count, int):
        return False, "manifest summary.succeeded_count must be an integer"
    if succeeded_count < min_succeeded:
        return False, f"manifest succeeded_count {succeeded_count} is below required {min_succeeded}"

    succeeded = manifest["succeeded"]
    for entry in succeeded:
        if not isinstance(entry, dict) or not entry.get("source_id"):
            return False, "each succeeded entry must include source_id"
        raw_paths = entry.get("raw_paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            return False, f"succeeded source {entry.get('source_id')} has no raw_paths"
        for raw_path_value in raw_paths:
            raw_path = Path(str(raw_path_value))
            if raw_path.is_absolute():
                try:
                    relative_raw_path = raw_path.relative_to(repo_root)
                except ValueError:
                    return False, f"raw path is outside repo root: {raw_path}"
            else:
                relative_raw_path = raw_path
                raw_path = repo_root / raw_path
            if not _is_under_raw_prefix(relative_raw_path):
                return False, f"raw path is outside accelerator crawler raw area: {relative_raw_path}"
            if not raw_path.exists():
                return False, f"missing raw path: {relative_raw_path}"

    failed = manifest["failed"]
    for entry in failed:
        if not isinstance(entry, dict) or not entry.get("source_id") or not entry.get("error"):
            return False, "each failed entry must include source_id and error"

    skipped = manifest["skipped_disabled"]
    for entry in skipped:
        if not isinstance(entry, dict) or not entry.get("source_id") or not entry.get("reason"):
            return False, "each skipped_disabled entry must include source_id and reason"

    return True, "manifest verified"


def _mirror_profiles_and_run(
    repo_root: Path,
    state_dir: Path,
    run_profiles: Sequence[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    backend_root = repo_root / "personal-wiki/apps/crawler_workbench/backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from crawler_workbench.db import migrate, open_db, transaction
    from crawler_workbench.fetch_service import run_source_once
    from crawler_workbench.profiles import load_profiles_from_yaml, mirror_profiles
    from crawler_workbench.settings import Settings

    settings = Settings(repo_root=repo_root, state_dir=state_dir, bind_host="127.0.0.1")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(settings.sources_yaml_path))
        for profile in run_profiles:
            source_id = str(profile["id"])
            manifest["ran_source_ids"].append(source_id)
            try:
                run_result = run_source_once(settings, db, source_id)
                raw_paths = _raw_paths_for_fetch_run(repo_root, db, int(run_result["fetch_run_id"]))
                ingest_tasks = _ingest_tasks_for_source(db, source_id)
                manifest["raw_paths"].extend(raw_paths)
                manifest["ingest_tasks"].extend(ingest_tasks)
                manifest["succeeded"].append(
                    {
                        "source_id": source_id,
                        "fetch_run": run_result,
                        "raw_paths": raw_paths,
                        "ingest_task_ids": [task["id"] for task in ingest_tasks],
                    }
                )
            except Exception as exc:
                manifest["failed"].append({"source_id": source_id, "error": str(exc)})


def _raw_paths_for_fetch_run(repo_root: Path, db: Any, fetch_run_id: int) -> list[str]:
    rows = db.execute(
        "select raw_path from raw_items where fetch_run_id = ? order by id",
        (fetch_run_id,),
    ).fetchall()
    paths: list[str] = []
    for row in rows:
        raw_path = Path(str(row["raw_path"]))
        if raw_path.is_absolute():
            try:
                raw_path = raw_path.relative_to(repo_root)
            except ValueError:
                pass
        paths.append(raw_path.as_posix())
    return paths


def _ingest_tasks_for_source(db: Any, source_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        select id, source_id, raw_item_id, target_domain, status, risk_level, reason
        from ingest_tasks
        where source_id = ?
        order by id
        """,
        (source_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _load_yaml_profiles(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing sources yaml: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("sources")
    if not isinstance(profiles, list):
        raise ValueError(f"{path} must contain a sources list")
    return profiles


def _write_profiles_yaml(path: Path, profiles: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"sources": list(profiles)}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _is_accelerator_profile(profile: dict[str, Any]) -> bool:
    return any(key in profile for key in ACCELERATOR_METADATA_KEYS)


def _is_enabled(profile: dict[str, Any]) -> bool:
    return bool(profile.get("enabled", True))


def _is_under_raw_prefix(path: Path) -> bool:
    normalized = Path(*path.parts)
    return normalized == RAW_PREFIX or RAW_PREFIX in normalized.parents


if __name__ == "__main__":
    raise SystemExit(main())
