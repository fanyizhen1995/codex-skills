# long-running-experiment

Codex 长时间实验与验证流程 skill。

它用于让 Codex 在长时间开发、实验、部署验证、回归测试、日志监控等任务中减少上下文污染：完整日志落盘，模型默认只读取结构化摘要和失败样本。

## 适用场景

- 长时间实验、benchmark、压测、回归测试
- 部署验证、服务监控、线上日志观察
- 需要 Codex 自己持续运行命令直到收集证据
- 输出很长，容易把大量日志带入上下文的任务

## 安装

把本目录安装到 Codex skills 目录，例如：

```bash
mkdir -p ~/.agents/skills
cp -R long-running-experiment ~/.agents/skills/
```

安装后重启 Codex。

也可以让 Codex 使用 `skill-installer` 从仓库安装：

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 long-running-experiment skill。仓库路径是 long-running-experiment。安装完成后提醒我重启 Codex。
```

## 使用方式

示例：

```text
使用 $long-running-experiment 跑一轮 router 长时间验证，完整日志落盘，只汇报摘要和失败样本。
```

skill 会引导 Codex 创建 `.codex/experiments/<timestamp>-<name>/`，保存 `raw.log`、`summary.json`、`report.md` 和 `failures.txt`。
