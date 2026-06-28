# hami-gpu-flow-task-lifecycle

HAMI GPU Flow PoC 任务生命周期 skill，用于把“认领任务、设计、实现、验证、用户验收、squash/merge”当成一条可追踪状态机处理。

## 适用场景

- 认领或拆分 HAMI GPU Flow PoC 任务。
- 更新 `tasks.json`、`progress.md`、`sprint_output.md` 或 `.codex/session-state`。
- 准备 E2E 证据、等待 evaluator/user acceptance。
- 合入、squash 或整理 `poc` 分支前做状态确认。

## 价值

过去一周远端 HAMI 出现 6 次“认领未完成任务”类会话。该 skill 主要减少任务状态遗漏、验收前误标 `done`、共享 k3s/Helm/Volcano 资源未加锁、以及合入前证据不完整的问题。

## 自动化脚本

```bash
python3 hami-gpu-flow-task-lifecycle/scripts/gpu_flow_status_snapshot.py --repo /home/fanyz4/hami
python3 hami-gpu-flow-task-lifecycle/scripts/gpu_flow_task_candidates.py --repo /home/fanyz4/hami
python3 hami-gpu-flow-task-lifecycle/scripts/gpu_flow_cleanup_candidates.py --repo /home/fanyz4/hami
```

- `gpu_flow_status_snapshot.py`：只读汇总分支、dirty files、任务计数、session-state、locks、worktrees、progress 顶部记录和近期 commit。
- `gpu_flow_task_candidates.py`：只读排序可认领任务，并标出已有 session、锁、blocked_by、existing worktree 和 requires_eval。
- `gpu_flow_cleanup_candidates.py`：只读输出 worktree、session-state、locks 的清理复核候选，分为 `active_keep`、`stale_review`、`safe_review`、`unknown_manual`；不执行删除。
- 三个脚本都支持 `--json`，不会修改 HAMI 仓库状态。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/hami-gpu-flow-task-lifecycle
cp -R hami-gpu-flow-task-lifecycle ~/.codex/skills/
```

安装后重启 Codex。
