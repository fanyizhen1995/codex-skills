# codex-skills

可复用的 Codex skills 和配套工具集合。

## 目录结构

每个 skill 使用独立目录，目录名与 `SKILL.md` 中的 `name` 保持一致。skill 相关说明放在对应目录的 `README.md` 中。

```text
skill-name/
├── README.md
├── SKILL.md
├── agents/
└── scripts/
```

非 skill 的配套工具使用独立目录，但不包含 `SKILL.md`。

## Skill 索引

| Skill | 说明 |
| --- | --- |
| [codex-engineering-context-optimizer](./codex-engineering-context-optimizer/README.md) | 工程任务中压缩测试、构建和日志输出上下文，保留可追溯摘要。 |
| [hami-gpu-flow-task-lifecycle](./hami-gpu-flow-task-lifecycle/README.md) | HAMI GPU Flow PoC 任务认领、验证、验收和合入状态机。 |
| [hami-production-gray-readiness](./hami-production-gray-readiness/README.md) | HAMi/HAMI 生产灰度、retained state 和 rollback readiness 检查。 |
| [long-running-experiment](./long-running-experiment/README.md) | 长时间实验和验证任务的低日志上下文工作流。 |
| [project-status-snapshot](./project-status-snapshot/README.md) | 从仓库、文档、日志和 Codex 历史恢复项目现状与下一步。 |
| [route-to-cheap-model](./route-to-cheap-model/README.md) | 将简单、低风险、纯文本任务分流给便宜模型处理。 |
| [scuda-fresh-performance-runbook](./scuda-fresh-performance-runbook/README.md) | SCUDA fresh benchmark/profile/correctness 执行、artifact sync 和 cleanup runbook。 |
| [scuda-performance-evidence-review](./scuda-performance-evidence-review/README.md) | SCUDA benchmark/profile 证据、provenance 和 cleanup state 复盘。 |

## 有用程度与效果对比

基于 `2026-05-27` 到 `2026-06-04` 在远端 `100.106.201.107` 上的 HAMI/SCUDA Codex 会话审计。详细报告见 [2026-06-03 远端重复工作流与 skill 收益报告](./reports/2026-06-03-remote-workflow-skill-roi.md)。

| Skill | 有用程度 | 主要证据 | 保守收益 |
| --- | --- | --- | --- |
| `scuda-fresh-performance-runbook` | 高 | SCUDA performance/profile/benchmark/gap/CQV2 类 thread 38 次/周 | 6-13 小时/周，减少 stale endpoint、artifact mismatch 和 cleanup 返工 |
| `hami-gpu-flow-task-lifecycle` | 高 | HAMI “认领未完成任务”类 thread 6 次/周 | 1-2 小时/周，减少任务状态、验收和合入证据遗漏 |
| `hami-production-gray-readiness` | 中高 | HAMI 灰度相关 thread 9 次/周 | 1.5-3 小时/周，降低 retained state/rollback 误判风险 |
| `scuda-performance-evidence-review` | 中高 | SCUDA 性能结论反复依赖 benchmark/profile/provenance 审核 | 1-3 小时/周，减少无效证据导致的错误结论 |
| `project-status-snapshot` | 中 | 多次跨 session 恢复和重复工作流审计 | 0.5-1.5 小时/次审计 |
| `codex-engineering-context-optimizer` | 中 | 长日志、benchmark 和 compaction 场景 | 需用 `context_audit.py` 前后对比；收益取决于大输出任务数量 |
| `long-running-experiment` | 中 | 长实验/benchmark 已有稳定适用面 | 主要收益是日志可追溯和减少上下文膨胀 |
| `route-to-cheap-model` | 条件有效 | 简单低风险文本任务 | 节省模型成本；不适合高风险工程判断 |

`tokens_used` 在远端库中的绝对值只作为相对上下文消耗信号，不直接换算 API 成本。新建专项 skills 已通过结构校验，但仍需要后续真实任务压测。

## Tool 索引

| Tool | 说明 |
| --- | --- |
| [codex-model-router](./codex-model-router/README.md) | 部署在 Codex 和 sub2api 之间的 OpenAI-compatible 模型路由代理。 |

## 让 Codex 安装

推荐直接把下面的提示词发给 Codex，让 Codex 自己使用 `skill-installer` 或合适的安装流程完成安装。安装后重启 Codex 以重新加载 skill metadata。

### 从远程仓库安装单个 skill

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 codex-engineering-context-optimizer skill。仓库路径是 codex-engineering-context-optimizer。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 route-to-cheap-model skill。仓库路径是 route-to-cheap-model。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 long-running-experiment skill。仓库路径是 long-running-experiment。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 project-status-snapshot skill。仓库路径是 project-status-snapshot。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 scuda-fresh-performance-runbook skill。仓库路径是 scuda-fresh-performance-runbook。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 scuda-performance-evidence-review skill。仓库路径是 scuda-performance-evidence-review。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 hami-gpu-flow-task-lifecycle skill。仓库路径是 hami-gpu-flow-task-lifecycle。安装完成后告诉我需要重启 Codex。
```

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 hami-production-gray-readiness skill。仓库路径是 hami-production-gray-readiness。安装完成后告诉我需要重启 Codex。
```

也可以使用完整 URL：

```text
请使用 skill-installer 安装这个 Codex skill：
https://github.com/fanyizhen1995/codex-skills/tree/main/route-to-cheap-model
安装完成后告诉我需要重启 Codex。
```

### 从远程仓库安装所有 skills

```text
请从 GitHub 仓库 fanyizhen1995/codex-skills 安装该项目下所有包含 SKILL.md 的 Codex skills。安装完成后告诉我安装了哪些 skill，并提醒我重启 Codex。
```

### 从本地项目安装

如果你已经 clone 了本仓库，可以让 Codex 从本地目录安装：

```text
请把当前项目中的 codex-engineering-context-optimizer skill 安装到我的 Codex skills 目录。skill 目录是 ./codex-engineering-context-optimizer。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 route-to-cheap-model skill 安装到我的 Codex skills 目录。skill 目录是 ./route-to-cheap-model。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 long-running-experiment skill 安装到我的 Codex skills 目录。skill 目录是 ./long-running-experiment。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 project-status-snapshot skill 安装到我的 Codex skills 目录。skill 目录是 ./project-status-snapshot。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 scuda-fresh-performance-runbook skill 安装到我的 Codex skills 目录。skill 目录是 ./scuda-fresh-performance-runbook。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 scuda-performance-evidence-review skill 安装到我的 Codex skills 目录。skill 目录是 ./scuda-performance-evidence-review。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 hami-gpu-flow-task-lifecycle skill 安装到我的 Codex skills 目录。skill 目录是 ./hami-gpu-flow-task-lifecycle。安装完成后告诉我需要重启 Codex。
```

```text
请把当前项目中的 hami-production-gray-readiness skill 安装到我的 Codex skills 目录。skill 目录是 ./hami-production-gray-readiness。安装完成后告诉我需要重启 Codex。
```

安装本地项目下所有 skills：

```text
请扫描当前项目下所有包含 SKILL.md 的一级目录，并把这些 Codex skills 安装到我的 Codex skills 目录。安装完成后告诉我安装了哪些 skill，并提醒我重启 Codex。
```

### 更新已安装 skill

```text
请从 GitHub 仓库 fanyizhen1995/codex-skills 重新安装 route-to-cheap-model，覆盖我本地已安装的旧版本。安装完成后提醒我重启 Codex。
```
