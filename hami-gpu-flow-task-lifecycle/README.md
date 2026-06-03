# hami-gpu-flow-task-lifecycle

HAMI GPU Flow PoC 任务生命周期 skill，用于把“认领任务、设计、实现、验证、用户验收、squash/merge”当成一条可追踪状态机处理。

## 适用场景

- 认领或拆分 HAMI GPU Flow PoC 任务。
- 更新 `tasks.json`、`progress.md`、`sprint_output.md` 或 `.codex/session-state`。
- 准备 E2E 证据、等待 evaluator/user acceptance。
- 合入、squash 或整理 `poc` 分支前做状态确认。

## 价值

过去一周远端 HAMI 出现 6 次“认领未完成任务”类会话。该 skill 主要减少任务状态遗漏、验收前误标 `done`、共享 k3s/Helm/Volcano 资源未加锁、以及合入前证据不完整的问题。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/hami-gpu-flow-task-lifecycle
cp -R hami-gpu-flow-task-lifecycle ~/.codex/skills/
```

安装后重启 Codex。
