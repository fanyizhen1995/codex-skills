---
name: codex-engineering-context-optimizer
description: 当工程类 Codex 任务出现长上下文、测试日志/构建日志/远程日志过大、exec_command/write_stdin 输出反复进入上下文、频繁 compaction、需要证明 token 节省、量化收益或上下文压缩效果时使用。
---

# Codex 工程上下文优化器

## 目标

在不牺牲工程可验证性的前提下，减少大段工具输出进入 Codex 上下文。原则是：**原始证据落盘，模型上下文只保留结构化摘要、关键错误和可追溯路径。**

## 何时使用

- 运行测试、构建、benchmark、远程日志分析、`git diff` 或批量 `rg` 时，输出可能超过几百行。
- 长 session 频繁触发 context checkpoint compaction。
- 用户要求节省 token、分析上下文膨胀、证明 skill 的正确性、量化收益或效果。
- SCUDA/HAMI/libsmctrl 等工程项目需要反复跑测试并比较失败原因。

不适合替代代码阅读、补丁编辑或用户明确要求查看完整输出的场景；这时应直接读取相关文件或日志。

## 核心工作流

1. 先判断命令输出是否可能很大。可能很大时，不直接用普通 `exec_command` 返回完整 stdout/stderr。
2. 使用本 skill 的 `scripts/run_with_summary.py` 包装命令：

```bash
python3 /path/to/codex-engineering-context-optimizer/scripts/run_with_summary.py \
  --cwd "$PWD" \
  --label test \
  -- pytest -q
```

3. 把返回给模型的内容限制为摘要：
   - 命令、cwd、退出码、耗时。
   - stdout/stderr 字符数和行数。
   - 失败测试、错误栈、关键错误行。
   - 完整日志路径。
   - 建议下一步 probe。
4. 只有当摘要不足以定位问题时，再按路径用 `rg`、`sed -n`、`tail` 精读日志片段。
5. 修改代码后，用同一包装方式重跑相同命令，比较摘要和退出码。

## 输出预算

- 默认让一次命令返回给上下文的摘要控制在 150-250 行以内。
- 对测试/构建日志，优先保留失败位置，不保留完整 pass 列表。
- 对远程日志，优先按时间、状态码、错误类型、request id 聚合。
- 对 diff，优先用 `git diff --stat`、文件列表和关键 hunk，再按文件读取。

## 正确性证明

每次用摘要替代完整输出时，要能回答这四个问题：

1. **证据完整性**：完整 stdout/stderr 是否已保存到日志路径？
2. **行为等价性**：摘要是否保留了命令、cwd、退出码、耗时和失败关键信息？
3. **可复现性**：是否能用同一命令或日志路径复查原始证据？
4. **决策一致性**：基于摘要得出的下一步，是否能由原始日志中的关键行支持？

如果任何一项不能满足，不要把摘要当成最终证据；回到原始日志精读。

## 效果证明

用 `scripts/context_audit.py` 对 Codex session 做前后对比：

```bash
python3 /path/to/codex-engineering-context-optimizer/scripts/context_audit.py \
  ~/.codex/sessions \
  --since 2026-05-20 \
  --cwd-contains /home/fanyz4/scuda
```

重点看：

- `function_call_output` / `custom_tool_call` 数量。
- 工具输出字符总量、p50/p95/max。
- 超过 20k/50k/100k 字符的工具输出次数。
- `context_compacted` 次数。
- `exec_command`、`write_stdin`、`apply_patch` 的占比。

判断标准：

- 相同任务类型下，大输出次数下降。
- 工具输出 p95 和 max 下降。
- compaction 触发频率下降。
- 失败定位仍能通过日志路径复查。
- 测试/构建结果和未包装命令一致。

## 收益量化

当用户要求“是否有效”或“量化收益”时，用同一时间窗、同一项目范围做审计：

1. 先统计任务量：相关 thread 数、重复模式数、代表标题、涉及项目；如果可用，再统计大输出次数和 compaction 次数。
2. 再估算节省：按每次避免的上下文恢复、日志重读、重复试错时间给出保守区间；把质量收益单独列为返工/误判/证据污染风险下降，不伪装成精确分钟数。
3. 对 `tokens_used` 保持谨慎：只有确认字段口径时才换算成本；否则只用作相对消耗排序。
4. 报告必须包含证据来源、时间窗、已覆盖/未覆盖的数据源，以及“结构校验”和“真实任务压测”的区别。

## 常见错误

- 只保留摘要、不保存原始日志。这会破坏可审计性。
- 摘要只截头尾，漏掉中间失败栈。要优先抽取 error/fail/traceback/panic/segfault/assert 等关键行。
- 把所有命令都包装。小输出命令直接运行更清晰。
- 在摘要里隐藏退出码或 cwd。这样无法判断命令是否真的成功。
- 修改代码后只比较摘要文字，不比较退出码、失败用例和关键错误。
