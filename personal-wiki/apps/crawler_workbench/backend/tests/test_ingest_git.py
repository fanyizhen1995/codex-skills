import json
import subprocess

from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import connect, migrate
from crawler_workbench.git_ops import auto_commit, git_dirty_paths, paths_owned_by_task
from crawler_workbench.ingest import IngestInputError, InvalidTaskStateError, approve_trusted_source_tasks, list_queue, run_approved_task
from crawler_workbench.main import create_app
from crawler_workbench.settings import Settings
from crawler_workbench.trusted_sources import trust_task_source


def ok_process(stdout="ok\n"):
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=stdout, stderr="")


def init_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def seed_source(db):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule, topic
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("src", "Source", "web", "ai_infra", "https://example.com", "trusted", "manual", "topic"),
    )


def seed_approved_task(settings, db, raw_path=None, domain="ai_infra"):
    seed_source(db)
    raw = raw_path or (settings.wiki_root / "domains" / domain / "raw" / "crawler" / "src" / "item.md")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw", encoding="utf-8")
    raw_item_id = db.execute(
        """
        insert into raw_items (
          source_id, target_domain, canonical_url, raw_path, title,
          content_hash, content_bytes, metadata_json
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("src", domain, "https://example.com/raw", str(raw), "Raw", "hash", 3, "{}"),
    ).lastrowid
    task_id = db.execute(
        """
        insert into ingest_tasks (
          source_id, raw_item_id, target_domain, status, risk_level, reason
        )
        values (?, ?, ?, ?, ?, ?)
        """,
        ("src", raw_item_id, domain, "approved", "low", "approved"),
    ).lastrowid
    db.commit()
    return int(task_id)


def test_list_queue_returns_pending_tasks(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        db.execute(
            "insert into ingest_tasks (source_id, target_domain, status, risk_level, reason) values (?, ?, ?, ?, ?)",
            ("src", "ai_infra", "pending", "untrusted", "needs review"),
        )
        db.commit()
        rows = list_queue(db)
    assert rows[0]["status"] == "pending"
    assert rows[0]["reason"] == "needs review"


def test_list_queue_includes_raw_item_details(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "item.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("# Raw title\n\nThis is the captured article body with NCCL details.", encoding="utf-8")

    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "src",
                "ai_infra",
                "https://developer.nvidia.com/blog/nccl",
                str(raw),
                "NCCL Article",
                "hash",
                raw.stat().st_size,
                json.dumps({"published": "2026-06-26", "author": "NVIDIA"}),
            ),
        ).lastrowid
        db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        )
        db.commit()
        rows = list_queue(db)

    assert rows[0]["title"] == "NCCL Article"
    assert rows[0]["canonical_url"] == "https://developer.nvidia.com/blog/nccl"
    assert rows[0]["raw_path"] == str(raw)
    assert rows[0]["content_bytes"] == raw.stat().st_size
    assert rows[0]["metadata"]["published"] == "2026-06-26"
    assert "captured article body" in rows[0]["content_preview"]


def test_approve_trusted_source_tasks_approves_matching_pending_urls(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        other_raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "other.md"
        other_raw.parent.mkdir(parents=True)
        other_raw.write_text("other", encoding="utf-8")
        trusted_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "src",
                "ai_infra",
                "https://aws.amazon.com/blogs/hpc/nccl",
                str(other_raw),
                "Trusted",
                "trusted-hash",
                5,
                "{}",
            ),
        ).lastrowid
        untrusted_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "src",
                "ai_infra",
                "https://example.com/nccl",
                str(other_raw),
                "Untrusted",
                "untrusted-hash",
                5,
                "{}",
            ),
        ).lastrowid
        trusted_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", trusted_raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        ).lastrowid
        untrusted_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", untrusted_raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        ).lastrowid
        db.commit()

        result = approve_trusted_source_tasks(db, ["arxiv.org", "aws.amazon.com", "developer.nvidia.com"])
        rows = {
            row["id"]: row["status"]
            for row in db.execute("select id, status from ingest_tasks order by id").fetchall()
        }

    assert result["approved_count"] == 1
    assert rows[trusted_task_id] == "approved"
    assert rows[untrusted_task_id] == "pending"


def test_trust_task_source_updates_profile_and_approves_same_site_pending_tasks(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "item.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("raw", encoding="utf-8")
    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        vllm_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://blog.vllm.ai/posts/nccl", str(raw), "vLLM NCCL", "hash-1", 3, "{}"),
        ).lastrowid
        sibling_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://vllm.ai/blog/other", str(raw), "vLLM Other", "hash-2", 3, "{}"),
        ).lastrowid
        other_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://lambda.ai/blog/nccl", str(raw), "Lambda", "hash-3", 3, "{}"),
        ).lastrowid
        task_id = db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", vllm_raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        ).lastrowid
        sibling_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", sibling_raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        ).lastrowid
        other_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", other_raw_item_id, "ai_infra", "pending", "manual", "needs review"),
        ).lastrowid
        db.commit()

        result = trust_task_source(settings, db, int(task_id), mode="scheduled", frequency="weekly")
        profile = db.execute("select trust_level, schedule, auto_ingest from source_profiles where id = 'src'").fetchone()
        rows = {
            row["id"]: row["status"]
            for row in db.execute("select id, status from ingest_tasks order by id").fetchall()
        }

    assert result["domain"] == "vllm.ai"
    assert result["source_id"] == "src"
    assert result["approved_count"] == 2
    assert profile["trust_level"] == "trusted"
    assert profile["schedule"] == "weekly"
    assert profile["auto_ingest"] == 1
    assert rows[task_id] == "approved"
    assert rows[sibling_task_id] == "approved"
    assert rows[other_task_id] == "pending"


def test_git_dirty_paths_and_owned_paths(tmp_path):
    init_git_repo(tmp_path)
    owned = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "x.md"
    other = tmp_path / "other.txt"
    owned.parent.mkdir(parents=True)
    owned.write_text("x", encoding="utf-8")
    other.write_text("y", encoding="utf-8")
    dirty = git_dirty_paths(tmp_path)
    assert "personal-wiki/domains/ai_infra/wiki/x.md" in dirty
    assert "other.txt" in dirty
    assert paths_owned_by_task(dirty, ["personal-wiki/domains/ai_infra/"]) is False


def test_git_dirty_paths_includes_tracked_modified_paths(tmp_path):
    init_git_repo(tmp_path)
    tracked = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "x.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "--", "personal-wiki/domains/ai_infra/wiki/x.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed tracked file"], cwd=tmp_path, check=True, capture_output=True, text=True)

    tracked.write_text("changed", encoding="utf-8")

    dirty = git_dirty_paths(tmp_path)
    assert "personal-wiki/domains/ai_infra/wiki/x.md" in dirty


def test_git_dirty_paths_returns_unquoted_paths_with_spaces(tmp_path):
    init_git_repo(tmp_path)
    tracked = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "file with space.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "--", "personal-wiki/domains/ai_infra/wiki/file with space.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed spaced file"], cwd=tmp_path, check=True, capture_output=True, text=True)

    tracked.write_text("changed", encoding="utf-8")

    assert "personal-wiki/domains/ai_infra/wiki/file with space.md" in git_dirty_paths(tmp_path)


def test_git_dirty_paths_include_rename_source_and_destination(tmp_path):
    init_git_repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "--", "outside.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed outside file"], cwd=tmp_path, check=True, capture_output=True, text=True)

    destination = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "moved.txt"
    destination.parent.mkdir(parents=True)
    subprocess.run(["git", "mv", "outside.txt", "personal-wiki/domains/ai_infra/wiki/moved.txt"], cwd=tmp_path, check=True)

    dirty = git_dirty_paths(tmp_path)
    assert {"outside.txt", "personal-wiki/domains/ai_infra/wiki/moved.txt"}.issubset(dirty)
    assert paths_owned_by_task(dirty, ["personal-wiki/domains/ai_infra/"]) is False


def test_auto_commit_rejects_preexisting_staged_changes(tmp_path):
    init_git_repo(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "--", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed repo"], cwd=tmp_path, check=True, capture_output=True, text=True)
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    other = tmp_path / "other.txt"
    other.write_text("unrelated", encoding="utf-8")
    subprocess.run(["git", "add", "--", "other.txt"], cwd=tmp_path, check=True)
    owned = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "x.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="staged changes already exist"):
        auto_commit(tmp_path, ["personal-wiki/domains/ai_infra/wiki/x.md"], "chore(wiki): ingest ai_infra src")

    after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()
    committed_paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert after == before
    assert "other.txt" not in committed_paths


def test_auto_commit_unstages_requested_paths_when_commit_fails(tmp_path):
    init_git_repo(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "--", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed repo"], cwd=tmp_path, check=True, capture_output=True, text=True)
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    owned = tmp_path / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "x.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("x", encoding="utf-8")

    with pytest.raises(RuntimeError, match="git commit failed"):
        auto_commit(tmp_path, ["personal-wiki/domains/ai_infra/wiki/x.md"], "chore(wiki): ingest ai_infra src")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert staged == []


def test_run_approved_task_defers_on_dirty_same_domain_baseline(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    unrelated = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "unrelated.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unrelated", encoding="utf-8")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())
        result = run_approved_task(settings, db, task_id, auto_commit_enabled=True, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason, commit_id from ingest_tasks where id = ?", (task_id,)).fetchone()
        commit_count = db.execute("select count(*) as count from commit_records").fetchone()["count"]

    assert result["status"] == "approved"
    assert task["status"] == "approved"
    assert "baseline" in task["reason"]
    assert task["commit_id"] is None
    assert commit_count == 0


def test_run_approved_task_clears_defer_reason_after_successful_retry(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    unrelated = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "unrelated.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unrelated", encoding="utf-8")

    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())

        deferred = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())
        unrelated.unlink()
        retried = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert deferred["status"] == "approved"
    assert retried["status"] == "succeeded"
    assert task["status"] == "succeeded"
    assert "baseline" not in task["reason"]


def test_run_approved_task_replaces_defer_reason_when_claimed_running(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        db.execute(
            """
            update ingest_tasks
            set reason = 'waiting for clean git baseline before automatic retry'
            where id = ?
            """,
            (task_id,),
        )
        db.commit()

        def assert_running_reason(received_settings, domain, raw_path):
            task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()
            assert task["status"] == "running"
            assert task["reason"] == "ingest running"
            return subprocess.CompletedProcess(args=["fake"], returncode=1, stdout="", stderr="stop after claim")

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", assert_running_reason)

        result = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

    assert result["status"] == "failed"
    assert result["reason"] == "ingest-plan failed: stop after claim"


def test_run_approved_task_allows_other_approved_raw_files_in_same_domain_baseline(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    first_raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "first.md"
    second_raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "second.md"
    first_raw.parent.mkdir(parents=True)
    first_raw.write_text("first", encoding="utf-8")
    second_raw.write_text("second", encoding="utf-8")

    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        first_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://example.com/first", str(first_raw), "First", "first-hash", 5, "{}"),
        ).lastrowid
        second_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://example.com/second", str(second_raw), "Second", "second-hash", 6, "{}"),
        ).lastrowid
        first_task_id = db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", first_raw_item_id, "ai_infra", "approved", "low", "approved"),
        ).lastrowid
        db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", second_raw_item_id, "ai_infra", "approved", "low", "approved"),
        )
        db.commit()

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())
        result = run_approved_task(
            settings,
            db,
            int(first_task_id),
            auto_commit_enabled=False,
            codex_runner=lambda *args: ok_process(),
        )

        first_task = db.execute("select status, reason from ingest_tasks where id = ?", (first_task_id,)).fetchone()

    assert result["status"] == "succeeded"
    assert first_task["status"] == "succeeded"
    assert "baseline" not in first_task["reason"]


def test_run_approved_task_does_not_commit_other_approved_raw_files(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    seed = tmp_path / "README.md"
    seed.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "--", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True, text=True)

    first_raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "first.md"
    second_raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "second.md"
    first_raw.parent.mkdir(parents=True)
    first_raw.write_text("first", encoding="utf-8")
    second_raw.write_text("second", encoding="utf-8")
    wiki_page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "references" / "first.md"

    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        first_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://example.com/first", str(first_raw), "First", "first-hash", 5, "{}"),
        ).lastrowid
        second_raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "https://example.com/second", str(second_raw), "Second", "second-hash", 6, "{}"),
        ).lastrowid
        first_task_id = db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", first_raw_item_id, "ai_infra", "approved", "low", "approved"),
        ).lastrowid
        db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", second_raw_item_id, "ai_infra", "approved", "low", "approved"),
        )
        db.commit()

        def write_wiki_page(*args):
            wiki_page.parent.mkdir(parents=True, exist_ok=True)
            wiki_page.write_text("curated", encoding="utf-8")
            return ok_process()

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())
        result = run_approved_task(
            settings,
            db,
            int(first_task_id),
            auto_commit_enabled=True,
            codex_runner=write_wiki_page,
        )
        first_task = db.execute("select status from ingest_tasks where id = ?", (first_task_id,)).fetchone()

    assert result["status"] == "succeeded"
    assert first_task["status"] == "succeeded"
    committed_paths = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/first.md" in committed_paths
    assert "personal-wiki/domains/ai_infra/wiki/references/first.md" in committed_paths
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/second.md" not in committed_paths
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/second.md" in git_dirty_paths(tmp_path)


def test_run_approved_task_allows_sources_yaml_and_task_attachment_baseline(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".personal-wiki-workbench")
    settings.sources_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    settings.sources_yaml_path.write_text("sources:\n- id: src\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", ".personal-wiki-workbench/sources.yaml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed workbench sources"], cwd=tmp_path, check=True, capture_output=True, text=True)
    settings.sources_yaml_path.write_text("sources:\n- id: src\n  schedule: manual\n", encoding="utf-8")

    raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src" / "item.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw", encoding="utf-8")
    attachment = raw.with_suffix(".pdf")
    attachment.write_bytes(b"%PDF-1.4\n")
    wiki_page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "references" / "manual-url.md"

    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "src",
                "ai_infra",
                "https://example.com/manual.pdf",
                str(raw),
                "Manual PDF",
                "hash",
                raw.stat().st_size,
                json.dumps({"attachment_filename": attachment.name}),
            ),
        ).lastrowid
        task_id = db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            ("src", raw_item_id, "ai_infra", "approved", "low", "approved"),
        ).lastrowid
        db.commit()

        def write_wiki_page(*args):
            wiki_page.parent.mkdir(parents=True, exist_ok=True)
            wiki_page.write_text("curated", encoding="utf-8")
            return ok_process()

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())
        result = run_approved_task(
            settings,
            db,
            int(task_id),
            auto_commit_enabled=True,
            codex_runner=write_wiki_page,
        )
        task = db.execute("select status, reason, commit_id from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert result["status"] == "succeeded"
    assert task["status"] == "succeeded"
    assert task["commit_id"] is not None
    assert ".personal-wiki-workbench/sources.yaml" in git_dirty_paths(tmp_path)
    committed_paths = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/item.md" in committed_paths
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/item.pdf" in committed_paths
    assert "personal-wiki/domains/ai_infra/wiki/references/manual-url.md" in committed_paths
    committed_sources = subprocess.run(
        ["git", "show", "HEAD:.personal-wiki-workbench/sources.yaml"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "schedule: manual" not in committed_sources


def test_run_approved_task_ignores_local_runtime_artifacts_in_baseline(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".personal-wiki-workbench")
    seed = tmp_path / "README.md"
    seed.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "--", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True, text=True)

    (tmp_path / ".codex").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".codex" / "loop-dashboard-8766.log").write_text("dashboard log", encoding="utf-8")
    (tmp_path / ".codex" / "loop-dashboard-8766.pid").write_text("8766\n", encoding="utf-8")
    (tmp_path / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / "generated" / "child-001.txt").write_text("child 1", encoding="utf-8")

    wiki_page = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "references" / "runtime-artifacts.md"
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        original_git_dirty_paths = __import__("crawler_workbench.ingest", fromlist=["git_dirty_paths"]).git_dirty_paths
        sqlite_sidecars = {
            ".personal-wiki-workbench/workbench.sqlite3-journal",
            ".personal-wiki-workbench/workbench.sqlite3-wal",
            ".personal-wiki-workbench/workbench.sqlite3-shm",
        }

        def write_wiki_page(*args):
            wiki_page.parent.mkdir(parents=True, exist_ok=True)
            wiki_page.write_text("curated", encoding="utf-8")
            return ok_process()

        def dirty_paths_with_runtime_sidecars(repo_root):
            return original_git_dirty_paths(repo_root) | sqlite_sidecars

        monkeypatch.setattr("crawler_workbench.ingest.git_dirty_paths", dirty_paths_with_runtime_sidecars)
        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())
        result = run_approved_task(
            settings,
            db,
            task_id,
            auto_commit_enabled=True,
            codex_runner=write_wiki_page,
        )
        task = db.execute("select status, reason, commit_id from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert result["status"] == "succeeded"
    assert task["status"] == "succeeded"
    assert task["commit_id"] is not None
    committed_paths = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "personal-wiki/domains/ai_infra/raw/crawler/src/item.md" in committed_paths
    assert "personal-wiki/domains/ai_infra/wiki/references/runtime-artifacts.md" in committed_paths
    assert ".codex/loop-dashboard-8766.log" not in committed_paths
    assert ".codex/loop-dashboard-8766.pid" not in committed_paths
    assert "generated/child-001.txt" not in committed_paths
    assert ".personal-wiki-workbench/workbench.sqlite3-journal" not in committed_paths
    assert ".personal-wiki-workbench/workbench.sqlite3-wal" not in committed_paths
    assert ".personal-wiki-workbench/workbench.sqlite3-shm" not in committed_paths
    dirty_paths = git_dirty_paths(tmp_path)
    assert ".codex/loop-dashboard-8766.log" in dirty_paths
    assert ".codex/loop-dashboard-8766.pid" in dirty_paths
    assert "generated/child-001.txt" in dirty_paths


def test_run_approved_task_defers_on_dirty_baseline_without_auto_commit(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    unrelated = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "unrelated.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unrelated", encoding="utf-8")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        calls = []

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: calls.append(args) or ok_process())
        result = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert result["status"] == "approved"
    assert task["status"] == "approved"
    assert "baseline" in task["reason"]
    assert calls == []


def test_run_approved_task_claims_approved_state_atomically(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        loaded = {"count": 0}

        def competing_git_dirty_paths(repo_root):
            loaded["count"] += 1
            db.execute("update ingest_tasks set status = 'running' where id = ?", (task_id,))
            db.commit()
            return set()

        monkeypatch.setattr("crawler_workbench.ingest.git_dirty_paths", competing_git_dirty_paths)
        with pytest.raises(InvalidTaskStateError):
            run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        status = db.execute("select status from ingest_tasks where id = ?", (task_id,)).fetchone()["status"]

    assert loaded["count"] == 1
    assert status == "running"


def test_run_approved_task_preclaim_failure_does_not_overwrite_competing_state(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    unrelated = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "unrelated.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("unrelated", encoding="utf-8")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        original_load_task = __import__("crawler_workbench.ingest", fromlist=["_load_task"])._load_task

        def racing_load_task(db, loaded_task_id):
            row = original_load_task(db, loaded_task_id)
            if loaded_task_id == task_id:
                db.execute("update ingest_tasks set status = 'rejected' where id = ?", (task_id,))
                db.commit()
            return row

        monkeypatch.setattr("crawler_workbench.ingest._load_task", racing_load_task)

        with pytest.raises(InvalidTaskStateError):
            run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert task["status"] == "rejected"
    assert task["reason"] == "approved"


def test_run_approved_task_preclaim_exception_does_not_overwrite_competing_state(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)
        original_load_task = __import__("crawler_workbench.ingest", fromlist=["_load_task"])._load_task

        def racing_load_task(db, loaded_task_id):
            row = original_load_task(db, loaded_task_id)
            if loaded_task_id == task_id:
                db.execute("update ingest_tasks set status = 'rejected' where id = ?", (task_id,))
                db.commit()
            return row

        def broken_git_dirty_paths(repo_root):
            raise RuntimeError("git status exploded")

        monkeypatch.setattr("crawler_workbench.ingest._load_task", racing_load_task)
        monkeypatch.setattr("crawler_workbench.ingest.git_dirty_paths", broken_git_dirty_paths)

        with pytest.raises(InvalidTaskStateError):
            run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert task["status"] == "rejected"
    assert task["reason"] == "approved"


def test_run_approved_task_fails_for_raw_path_outside_domain_raw(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    outside_raw = settings.wiki_root / "domains" / "other_domain" / "raw" / "item.md"
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db, raw_path=outside_raw)
        calls = []

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: calls.append(args) or ok_process())
        with pytest.raises(IngestInputError, match="raw path"):
            run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=lambda *args: ok_process())

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()

    assert task["status"] == "failed"
    assert "raw path" in task["reason"]
    assert calls == []


def test_run_approved_task_marks_failed_when_codex_runner_raises(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())

        def fail_codex(settings, prompt):
            raise RuntimeError("codex exploded")

        result = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=fail_codex)

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()
        job = db.execute("select status, stderr from codex_jobs").fetchone()

    assert result["status"] == "failed"
    assert task["status"] == "failed"
    assert "codex exploded" in task["reason"]
    assert job["status"] == "failed"
    assert "codex exploded" in job["stderr"]


def test_run_approved_task_marks_failed_when_codex_reports_sandbox_blocker(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path.parent / f"{tmp_path.name}-state")
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db)

        monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_index", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_backlinks", lambda *args: ok_process())
        monkeypatch.setattr("crawler_workbench.ingest.run_validate", lambda *args: ok_process())

        def blocked_codex(settings, prompt):
            return subprocess.CompletedProcess(
                args=["fake"],
                returncode=0,
                stdout="我现在被执行环境阻塞，没法安全执行这次入库流程。\nbwrap: loopback: Failed RTM_NEWADDR\n",
                stderr="",
            )

        result = run_approved_task(settings, db, task_id, auto_commit_enabled=False, codex_runner=blocked_codex)

        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()
        job = db.execute("select status, stdout, stderr, exit_code from codex_jobs").fetchone()

    assert result["status"] == "failed"
    assert task["status"] == "failed"
    assert "sandbox startup failure" in task["reason"]
    assert job["status"] == "failed"
    assert job["exit_code"] == 0
    assert "bwrap" in job["stdout"]
    assert "sandbox startup failure" in job["stderr"]


def test_default_ingest_codex_runner_uses_workspace_write_sandbox(tmp_path, monkeypatch):
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="completed\n", stderr="")

    monkeypatch.setattr("crawler_workbench.ingest.subprocess.run", fake_run)
    from crawler_workbench.ingest import _default_codex_runner

    result = _default_codex_runner(
        Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", codex_command="codex"),
        "prompt",
    )

    assert [call[call.index("--sandbox") + 1] for call in calls] == ["workspace-write"]
    assert result.returncode == 0
    assert result.stdout == "completed\n"


def test_validate_endpoint_records_validation_run(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    def fake_run_validate(settings, domain=None):
        return subprocess.CompletedProcess(
            args=["python", "personal-wiki/tools/wiki_cli/cli.py"],
            returncode=0,
            stdout="No validation issues\n",
            stderr="",
        )

    monkeypatch.setattr("crawler_workbench.api.run_validate", fake_run_validate)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/validate", json={"domain": "ai_infra"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["validation_run_id"] == 1

    with connect(settings.database_path) as db:
        row = db.execute("select * from validation_runs").fetchone()
    assert row["id"] == payload["validation_run_id"]
    assert row["status"] == "succeeded"
    assert row["target_domain"] == "ai_infra"


def test_validate_endpoint_records_failed_validation_as_200(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    def fake_run_validate(settings, domain=None):
        return subprocess.CompletedProcess(
            args=["python", "personal-wiki/tools/wiki_cli/cli.py"],
            returncode=1,
            stdout="validation failed\n",
            stderr="broken link\n",
        )

    monkeypatch.setattr("crawler_workbench.api.run_validate", fake_run_validate)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/validate", json={"domain": "ai_infra"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["validation_run_id"] == 1

    with connect(settings.database_path) as db:
        row = db.execute("select * from validation_runs").fetchone()
    assert row["status"] == "failed"
    assert "validation failed" in row["output"]
    assert "broken link" in row["output"]


def test_validate_endpoint_rejects_nested_domain(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    calls = []
    monkeypatch.setattr("crawler_workbench.api.run_validate", lambda *args: calls.append(args) or ok_process())
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/validate", json={"domain": "team/ai"})

    assert response.status_code == 400
    assert "Invalid domain" in response.json()["detail"]
    assert calls == []


def test_run_queue_task_endpoint_maps_missing_and_invalid_state(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)

    with TestClient(app) as client:
        missing = client.post("/api/queue/999/run", json={"auto_commit_enabled": False})

    assert missing.status_code == 404

    with connect(settings.database_path) as db:
        seed_source(db)
        task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "pending", "manual", "waiting"),
        ).lastrowid
        db.commit()

    with TestClient(app) as client:
        invalid = client.post(f"/api/queue/{task_id}/run", json={"auto_commit_enabled": False})

    assert invalid.status_code == 409

    with connect(settings.database_path) as db:
        running_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "running", "manual", "already running"),
        ).lastrowid
        db.commit()

    with TestClient(app) as client:
        running = client.post(f"/api/queue/{running_task_id}/run", json={"auto_commit_enabled": False})

    assert running.status_code == 409


def test_approve_and_reject_endpoints_reject_terminal_or_running_states(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        succeeded_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "succeeded", "low", "done"),
        ).lastrowid
        running_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "running", "low", "busy"),
        ).lastrowid
        db.commit()

    with TestClient(app) as client:
        approve_succeeded = client.post(f"/api/queue/{succeeded_id}/approve")
        reject_running = client.post(f"/api/queue/{running_id}/reject", json={"reason": "stop"})

    assert approve_succeeded.status_code == 409
    assert reject_running.status_code == 409
    with connect(settings.database_path) as db:
        statuses = {
            row["id"]: row["status"]
            for row in db.execute("select id, status from ingest_tasks where id in (?, ?)", (succeeded_id, running_id))
        }
    assert statuses[succeeded_id] == "succeeded"
    assert statuses[running_id] == "running"


def test_approve_and_reject_state_changes_are_conditional(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with connect(settings.database_path) as db:
        migrate(db)
        seed_source(db)
        approve_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "pending", "low", "waiting"),
        ).lastrowid
        reject_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values (?, ?, ?, ?, ?)
            """,
            ("src", "ai_infra", "approved", "low", "ready"),
        ).lastrowid
        db.commit()

    original_load_task = __import__("crawler_workbench.ingest", fromlist=["_load_task"])._load_task

    def racing_load_task(db, task_id):
        row = original_load_task(db, task_id)
        if task_id == approve_id:
            db.execute("update ingest_tasks set status = 'succeeded' where id = ?", (task_id,))
            db.commit()
        elif task_id == reject_id:
            db.execute("update ingest_tasks set status = 'running' where id = ?", (task_id,))
            db.commit()
        return row

    monkeypatch.setattr("crawler_workbench.ingest._load_task", racing_load_task)

    with TestClient(app) as client:
        approve_response = client.post(f"/api/queue/{approve_id}/approve")
        reject_response = client.post(f"/api/queue/{reject_id}/reject", json={"reason": "stop"})

    assert approve_response.status_code == 409
    assert reject_response.status_code == 409
    with connect(settings.database_path) as db:
        statuses = {
            row["id"]: row["status"]
            for row in db.execute("select id, status from ingest_tasks where id in (?, ?)", (approve_id, reject_id))
        }
    assert statuses[approve_id] == "succeeded"
    assert statuses[reject_id] == "running"


def test_run_queue_task_endpoint_maps_invalid_raw_path_to_400(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    outside_raw = settings.wiki_root / "domains" / "other_domain" / "raw" / "item.md"
    with connect(settings.database_path) as db:
        migrate(db)
        task_id = seed_approved_task(settings, db, raw_path=outside_raw)

    calls = []
    monkeypatch.setattr("crawler_workbench.ingest.run_ingest_plan", lambda *args: calls.append(args) or ok_process())

    with TestClient(app) as client:
        response = client.post(f"/api/queue/{task_id}/run", json={"auto_commit_enabled": False})

    assert response.status_code == 400
    assert "raw path" in response.json()["detail"]
    assert calls == []
    with connect(settings.database_path) as db:
        task = db.execute("select status, reason from ingest_tasks where id = ?", (task_id,)).fetchone()
    assert task["status"] == "failed"
    assert "raw path" in task["reason"]


def test_commit_endpoint_commits_explicit_owned_paths_and_records_commit(tmp_path):
    init_git_repo(tmp_path)
    seed = tmp_path / "README.md"
    seed.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "--", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed repo"], cwd=tmp_path, check=True, capture_output=True, text=True)

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    owned = settings.wiki_root / "domains" / "ai_infra" / "wiki" / "manual.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("manual", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/commit",
            json={
                "domain": "ai_infra",
                "paths": ["personal-wiki/domains/ai_infra/wiki/manual.md"],
                "message": "chore(wiki): manual commit",
                "source_id": "manual",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["commit_sha"]
    assert payload["commit_record_id"] == 1
    with connect(settings.database_path) as db:
        row = db.execute("select * from commit_records").fetchone()
    assert row["source_id"] == "manual"
    assert row["target_domain"] == "ai_infra"
    assert row["commit_sha"] == payload["commit_sha"]
    assert row["message"] == "chore(wiki): manual commit"


def test_commit_endpoint_rejects_unowned_paths(tmp_path):
    init_git_repo(tmp_path)
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    other = tmp_path / "other.txt"
    other.write_text("other", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/commit",
            json={
                "domain": "ai_infra",
                "paths": ["other.txt"],
                "message": "chore(wiki): bad commit",
            },
        )

    assert response.status_code == 400
    assert "outside" in response.json()["detail"]


def test_api_request_validation_errors_return_400(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)

    with TestClient(app) as client:
        commit_response = client.post(
            "/api/commit",
            json={"domain": "ai_infra", "paths": ["personal-wiki/domains/ai_infra/wiki/x.md"], "message": ""},
        )
        run_response = client.post("/api/queue/1/run", json={"auto_commit_enabled": "false"})

    assert commit_response.status_code == 400
    assert run_response.status_code == 400
