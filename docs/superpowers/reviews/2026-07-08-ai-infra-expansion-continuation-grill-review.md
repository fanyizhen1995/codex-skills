# Grill-Me Review: AI Infra 资料拓展 Loop 继续执行方案

日期：2026-07-08

审核对象：`docs/superpowers/plans/2026-07-08-ai-infra-expansion-continuation.md`

## 结论

通过，但有一个 P0 前置条件：不能直接用当前 `run-autonomous` 恢复资料拓展，必须先让审计 cadence 按“父任务”计数生效，或用 wrapper 聚合父任务后再触发 Auditor。否则当前边界审计行为会继续过度介入，违背用户要求的“两个父任务一次审计”。

方案已把该问题列为 P0，因此可以进入用户评审。

## 关键追问和判定

### P0：父任务定义是否足够清楚？

判定：清楚。方案把父任务定义为顶层资料拓展目标，而不是单个 URL、单次 generator attempt 或单条 wiki 编辑。这个定义能让 Dashboard 面向第三方读者解释“这轮到底在做什么”。

风险：当前 harness 的 autonomous task 概念不等同于这里的父任务。如果执行时不做 wrapper 或 cadence state，Planner 可能还是按子任务计数。

要求：执行前必须验证 run state 中存在父任务计数，或者 Dashboard 能展示父任务边界。

### P0：审计频率是否真的能控制？

判定：现在不能保证。当前 `run-autonomous` 在 planning boundary 调用 audit boundary，存在每个子任务后都写 audit report 的风险。

方案处理：把“确认审计 cadence 能按父任务工作”列为 P0，且拒绝“启动现有 runtime 后人工忽略过多审计报告”。

要求：实际执行前必须补测试证明父任务 1 完成后不会触发普通 Auditor，父任务 2 完成后会触发。

### P0：未提交资料是否会污染新 loop？

判定：方案处理正确。当前 SGLang #24456 wiki 更新和 ingest-plan 是已存在的未归属入库，必须先作为第 0 步收尾提交，不应算进父任务 1。

要求：第 0 步必须独立 commit，且补 `ingest.md`、index、validate、API/frontend visibility。

### P1：安全闸门和 Auditor cadence 是否混淆？

判定：方案区分得比较清楚。安全闸门可以立即阻断，普通 Auditor 按两父任务一次触发。

剩余风险：事件触发例外如果定义过宽，会再次变成“每轮都审计”。方案把例外限制到 secrets、dirty path、连续 evaluator fail、Dashboard 不可见、服务全挂、目标偏离，范围可以接受。

### P1：是否避免浅抓取？

判定：比旧方案更强。方案要求深挖父任务必须有两类来源或多页证据，并把单页 `raw/links` 限制为小缺口补充或 blocked evidence。

要求：Evaluator 必须检查父任务是否把“单页抓取”冒充为深挖。

### P1：是否避免重复 blocked 空转？

判定：基本覆盖。方案要求同 identity key、同失败原因的 needs 项不原样重试，KServe 父任务只做廉价复探，抓不到就更新 needs 状态。

要求：复探 artifact 必须记录 DNS/TLS/HTTP/final_url/error_class，不能只写自然语言。

### P1：Dashboard 和服务可见性是否足够？

判定：覆盖到了，但执行时要小心。方案要求 campaign run、父任务、Auditor、Evaluator 和日志都在 Dashboard 可见，并且每个父任务开始/结束记录 crawler backend/frontend/dashboard/auto-resume 状态。

要求：Evaluator 不能只查 API JSON，至少要有一次前端页面级验证。

### P1：提交和 push 策略是否可执行？

判定：可执行。方案把 wiki/crawler 入库 commit、代码修复 commit 分开，并要求 main 上提交后推送 origin。

风险：如果资料拓展运行在 feature worktree，自动 push main 的语义会变复杂。

要求：执行前说明当前运行分支。如果在 main 上执行，commit 后 push；如果在 feature branch 执行，先 checkpoint，合入 main 后 push。

## 必须保留的执行约束

- 不把 `.codex`、pid/log、`generated/`、`.worktrees`、secrets、tokens、cookies、`.env` 纳入提交。
- 不把 `stopped_budget` 当作全局完成。
- 不让 Planner 主观声明高价值项目，必须先过 hard gates。
- 不把 blocked-source evidence 当成 source-backed 行为事实。
- 不让 Auditor 替代单父任务 evaluator。

## 最终意见

Approve with conditions:

1. 先收尾 SGLang #24456 未归属入库。
2. 先修正或验证父任务级审计 cadence。
3. 再创建 continuation run 并执行前两个父任务。
4. 第一次 Auditor 只在父任务 1 和父任务 2 都完成后触发，除非出现安全闸门级问题。
