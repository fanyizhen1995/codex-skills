#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DEMO_TASK = {
    "id": "harness-evaluator-demo-01",
    "title": "验证 evaluator auto-trigger wiring 的最小 demo",
    "description": "运行通用 demo helper 生成一个可验证输出，用于证明 Step4 安装后的 Stop hook 能自动触发 evaluator 并写出 verdict。",
    "status": "pending",
    "priority": "medium",
    "blocked_by": "harness-step4-evaluator-gates-01",
    "verify": "python3 scripts/harness_evaluator_demo.py assert-expected --output-dir .codex/evaluator-demo/harness-evaluator-demo-01",
    "requires_eval": True,
    "eval_policy": {
        "task_level_required": True,
        "final_level_required": False,
        "task_scope": "code_and_local_k3s",
        "final_scope": "report_and_artifacts",
        "max_task_eval_attempts": 3,
        "max_final_eval_attempts": 2,
    },
}


def require_path(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing prerequisite: {path}")


def copy_tree(src: Path, dst: Path) -> None:
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        relative = item.relative_to(src)
        target = dst / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def ensure_demo_task(repo_root: Path) -> None:
    tasks_path = repo_root / "tasks.json"
    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    tasks = payload.setdefault("tasks", [])
    for task in tasks:
        if task.get("id") == DEMO_TASK["id"]:
            task.update(DEMO_TASK)
            break
    else:
        tasks.append(dict(DEMO_TASK))
    tasks_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    require_path(repo_root / "AGENTS.md")
    require_path(repo_root / "tasks.json")
    require_path(repo_root / "progress.md")
    require_path(repo_root / "docs")

    skill_root = Path(__file__).resolve().parents[1]
    template_root = skill_root / "assets" / "repo-template"
    require_path(template_root)

    copy_tree(template_root, repo_root)
    ensure_demo_task(repo_root)

    print(json.dumps({"status": "ok", "repo_root": str(repo_root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
