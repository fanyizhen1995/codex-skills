---
name: long-running-experiment
description: Use when running long experiments, benchmarks, regression checks, deployment verification, monitoring, log-heavy validation, or any task likely to produce large command output while Codex must continue until evidence is collected.
---

# Long Running Experiment

## 核心规则

完整日志落盘。只把紧凑、结构化的证据放进模型上下文。

## 何时使用

当任务涉及长时间验证、benchmark、压测、部署验证、重复重试、监控、调试循环，或命令可能产生大量日志时，使用本 skill。

如果只是一个快速命令，而且完整输出很短、需要直接阅读，则不需要使用本 skill。

## 工作流

1. 运行任何命令前，先定义实验目标、范围、成功标准、失败标准和超时时间。
2. 创建实验目录：

```bash
python3 scripts/new_experiment.py --name <short-name>
```

3. 把可执行命令写入 `command.sh`；完整输出必须写入 `raw.log`。
4. 优先使用能生成 `summary.json`、`report.md`、`failures.txt` 的脚本。如果是临时命令，结束后用 `scripts/summarize_log.py` 生成摘要。
5. 实验运行过程中，只查看状态摘要，不读取完整日志：

```bash
tail -n 40 <experiment-dir>/report.md
tail -n 80 <experiment-dir>/failures.txt
```

6. 只有当摘要指出明确失败区间时，才读取 `raw.log`；读取时使用 `rg`、`jq`、`head`、`tail` 或指定行号范围。
7. 宣称成功前，必须验证成功标准，并引用证据文件。
8. 当实验改变项目状态、部署状态或下一步动作时，更新 `.codex/session-state.md`。

## 输出纪律

- 不要在最终回复中粘贴完整日志。
- 回复中只汇报命令、耗时、状态、关键指标、失败样本、产物路径和下一步。
- 如果输出超过 100 行，保存到文件并摘要。
- 如果需要轮询，只轮询摘要文件或 `tail -n 40`，不要读取完整日志。
- 如果命令预计运行超过 60 秒，必须使用日志重定向和超时控制。

## 目录结构

```text
.codex/experiments/<timestamp>-<name>/
├── command.sh
├── raw.log
├── summary.json
├── report.md
└── failures.txt
```

## 推荐命令模式

```bash
exp_dir=".codex/experiments/<timestamp>-<name>"
timeout 30m bash "$exp_dir/command.sh" >"$exp_dir/raw.log" 2>&1
status=$?
python3 scripts/summarize_log.py "$exp_dir/raw.log" --status "$status" --out-dir "$exp_dir"
```

## 会话状态

在长任务中使用 `.codex/session-state.md` 作为紧凑交接文件：

```text
# Session State
- Goal:
- Current state:
- Key decisions:
- Changed files:
- Experiment evidence:
- Risks:
- Next step:
```

内容必须短小、事实化。不要复制原始日志进去。

## 证据标准

任何验证结论至少需要以下一种证据：

- 通过的测试命令和退出码
- 生成的 `summary.json` / `report.md`
- 指标与阈值的对比结果
- 部署健康检查结果
- 失败样本和根因说明

如果证据缺失，必须说明验证尚不完整，并补充缺失的检查。
