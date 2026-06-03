# project-status-snapshot

`project-status-snapshot` 是一个 Codex skill，用于从仓库、文档、日志和 Codex 历史中恢复项目现状，生成可执行的状态快照。

## 适用场景

- 检查当前任务状态、项目进展、阻塞点和下一步。
- 从中断的 Codex 任务或长线程中恢复上下文。
- 梳理 SCUDA/HAMI 等工程项目的近期改动、benchmark、部署状态。
- 回顾一段时间内的重复工作流，判断是否应创建/增强 skill、custom agent 或 automation。
- 在继续实现、复现、灰度或排障前先建立证据化项目视图。

## 工作方式

skill 本体位于：

```text
project-status-snapshot/
├── README.md
├── SKILL.md
└── agents/openai.yaml
```

它会引导 Codex 优先检查：

- 当前仓库、分支、dirty 状态和近期提交。
- `AGENTS.md`、`README*`、`docs/`、`plans/`、`reports/`、benchmark 或 sprint 输出。
- 相关日志、测试输出、部署配置。
- 可用的 Codex 历史，例如 `~/.codex/session_index.jsonl`、`state_*.sqlite` 和 shell snapshots。

## 安装

从本仓库安装到当前用户的 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R project-status-snapshot ~/.codex/skills/
```

如果已安装旧版本，先删除再复制：

```bash
rm -rf ~/.codex/skills/project-status-snapshot
cp -R project-status-snapshot ~/.codex/skills/
```

安装后重启 Codex，让新的 skill metadata 被重新加载。

## 使用

显式触发：

```text
使用 $project-status-snapshot 检查当前项目状态、最近进展、阻塞点和下一步。
```

常见自然语言触发：

```text
检查下当前任务状态和性能进展。
```

```text
之前任务中断了，帮我恢复一下项目现状并给出下一步。
```

```text
梳理下当前生产灰度状态、最近错误和风险。
```

```text
回顾过去一周的远端工作记录，找出值得打包的重复手动工作流，并量化收益。
```

## 验证

如果本机安装了 Codex skill 校验脚本，可以运行：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ./project-status-snapshot
```
