# 2026-06-03 远端重复工作流与 skill 收益报告

## 范围

- 远端环境：`fanyz4@100.106.201.107`
- 项目：`/home/fanyz4/hami`、`/home/fanyz4/scuda`
- 时间窗：`2026-05-27 00:00` 到 `2026-06-04 00:00`，Asia/Shanghai
- 主要证据：`/home/fanyz4/.codex/state_5.sqlite`、`session_index.jsonl`、项目文档和已有 skills
- 缺口：`memories_1.sqlite` 没有可用 summary；Chronicle 未发现

`tokens_used` 在该远端库中的绝对值偏大，本报告只把它作为相对上下文消耗信号，不换算 API 成本。

## 量化观察

| 项目/模式 | 过去一周 thread 数 | 相对 token/上下文消耗 | 结论 |
| --- | ---: | ---: | --- |
| HAMI 全部相关 | 22 | 1,494,481,899 | 有重复任务生命周期和灰度发布模式 |
| HAMI 认领未完成任务 | 6 | 438,454,345 | 适合打包为任务生命周期 skill |
| HAMI 灰度相关 | 9 | 1,188,014,349 | 适合增强已有灰度 readiness skill |
| SCUDA 全部相关 | 60 | 1,928,288,648 | 性能/证据工作占主导 |
| SCUDA performance/profile/benchmark/gap/CQV2 | 38 | 588,531,805 | 适合拆成 fresh runbook + evidence review |

## 候选与处理

| 优先级 | 候选工作流 | 处理 | 原因 |
| --- | --- | --- | --- |
| P0 | HAMI GPU Flow 任务认领、设计、实现、验证、验收、合入 | 新建 `hami-gpu-flow-task-lifecycle` | 一周 6 次，输入/输出稳定，遗漏验收和状态更新代价高 |
| P0 | SCUDA fresh benchmark/profile/correctness 执行 | 新建 `scuda-fresh-performance-runbook` | 一周 38 次性能相关 thread，重复 cleanup、artifact sync、evidence class 判断 |
| P1 | HAMI 生产灰度 retained state/rollback | 增强 `hami-production-gray-readiness` | 灰度相关 9 次，重来和误判成本高 |
| P1 | SCUDA 已有性能证据复盘 | 增强 `scuda-performance-evidence-review` | 需要和 fresh runbook 明确边界 |
| P1 | 跨项目重复工作流审计 | 增强 `project-status-snapshot` | 用户会重复询问“过去一周/是否有效/量化收益” |
| P1 | 上下文节省收益量化 | 增强 `codex-engineering-context-optimizer` | 需要固定 tokens_used 谨慎口径和审计方法 |
| P2 | SCUDA issue-ledger 防再犯 | Skip | 已被项目 docs 和 evidence review 覆盖 |
| P2 | 项目状态恢复/上下文压缩 | Skip | 已有 `project-status-snapshot` 和 context optimizer |
| P3 | LLM benchmark workload 变更 | 需要更多证据 | 近期有迹象，但流程尚不稳定 |
| P3 | 架构瘦身/冗余清理审计 | 需要更多证据 | 还不像固定可重复流程 |

## 保守收益估算

估算只计算人工/agent 反复恢复上下文、重建检查清单、重读日志和纠正证据口径的时间，不把质量收益硬折算成精确成本。

| Skill | 主要节省来源 | 保守节省 |
| --- | --- | ---: |
| `scuda-fresh-performance-runbook` | 避免 stale endpoint、artifact mismatch、cleanup 未闭环和 profile/benchmark 混用 | 6-13 小时/周 |
| `scuda-performance-evidence-review` | 更快拒绝无效证据、减少错误性能结论 | 1-3 小时/周 |
| `hami-gpu-flow-task-lifecycle` | 减少任务认领、验收、E2E、squash/merge 状态重建 | 1-2 小时/周 |
| `hami-production-gray-readiness` | 减少灰度状态遗失、rollback target 不清、live state 误判 | 1.5-3 小时/周 |
| `project-status-snapshot` | 复用同一套跨 session 取证流程 | 0.5-1.5 小时/次审计 |
| `codex-engineering-context-optimizer` | 大日志落盘摘要，减少 compaction 和无效上下文 | 取决于长日志任务数量，需用 `context_audit.py` 前后对比 |

## 有效性等级

- 高：SCUDA fresh performance runbook、HAMI GPU Flow task lifecycle。
- 中高：HAMI production gray readiness、SCUDA performance evidence review。
- 中：project status snapshot、context optimizer 的本次增强。
- 待验证：新建专项 skills 尚未经过后续真实任务压测；当前只完成结构校验。

## 后续验证

1. 连续一周记录触发次数、是否避免返工、是否减少无效 benchmark/profile 结论。
2. 用 `codex-engineering-context-optimizer/scripts/context_audit.py` 比较启用前后大输出次数、p95/max 输出字符数和 compaction 次数。
3. 对新建专项 skill 收集 2-3 个真实任务样本，必要时再收紧触发词或 Common Mistakes。
