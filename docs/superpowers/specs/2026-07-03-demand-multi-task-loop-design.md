# 需求开发多子任务 Loop 设计

日期：2026-07-03

## 背景

当前 Planner -> Generator -> Evaluator loop 把 `demand_development` 设计成
单任务闭环。真实需求开发通常不是一个子任务能完成的，例如一个看板需求可能同时
需要状态模型、调度器、后端聚合、前端展示、evaluator 场景和最终集成验证。

现有 `autonomous_knowledge` 已经具备
Planner -> Generator -> Evaluator -> Planner 的持续规划形态，但它服务于知识
拓展，允许在 allowlist 范围内自动提交，并以“无可行动缺口”为停止条件。
需求开发也需要同样的迭代形态，但必须保留整个需求级别的人工合入门。

本设计把需求开发升级为“父需求 run + 子任务 run”：

```text
Parent Planner
  -> Child Planner -> Child Generator -> Child Evaluator
  -> Parent Planner
  -> Child Planner -> Child Generator -> Child Evaluator
  -> ...
  -> Parent passed_waiting_human_merge
```

## 目标

- 一个需求开发 run 可以按顺序自动完成多个相关子任务。
- 每个子任务仍有独立的 planner、generator、evaluator、日志、artifact 和修复轮次。
- 每个子任务通过后回到父 Planner，由父 Planner 基于当前仓库状态选择下一项。
- evaluator 失败时修复同一个子任务，不创建新子任务绕过失败。
- 所有可行动子任务通过后，父 run 统一进入 `passed_waiting_human_merge`。
- Loop Dashboard 展示父需求、子任务队列、每个 agent 做了什么、验收了什么、哪里失败、是否需要用户决策。
- 兼容现有单 run artifact，不破坏历史 dashboard 和 evaluator 读取路径。

## 非目标

- 不删除现有单任务 `demand_development` 支持。
- 不让需求开发自动合入 `main`。
- 不把 `demand_development` 和 `autonomous_knowledge` 的权限语义混在一起。
- 不默认要求用户逐个审批子任务。
- 不把原始 JSON 作为看板主要阅读体验。
- 不让看板执行、删除、重启、合入或修复 run。

## 已确认决策

- 需求开发也采用 Planner -> Generator -> Evaluator -> Planner 的循环形态。
- 实现采用父 run + 子 run，而不是把所有子任务塞进一个 run。
- 合入门只在父 run：全部子任务通过后，等待用户统一确认合入 `main`。
- 子任务顺序执行。首期不做多个 child 并行开发，避免共享 worktree 冲突。
- 看板以父 run 为主要列表项，子 run 在父 run 下折叠和聚合展示。
- evaluator 必须提供用户场景结果；涉及前端或看板时必须模拟浏览器点击。
- Planner、Generator、Evaluator、Orchestrator 都应写结构化事件，让看板不只显示文件更新时间。

## 运行模型

### 父 Run

父 run 表示一个完整用户需求。它保存 preflight 讨论结果、全局约束、backlog、当前子任务指针、聚合验收结果和最终人工合入门。

新增字段：

```json
{
  "run_kind": "parent",
  "run_id": "loop-dashboard-multitask-dev",
  "policy": "demand_development",
  "requirement": "string",
  "phase": "planning | child_running | repair_needed | passed_waiting_human_merge | stopped_budget | stopped_blocked",
  "child_run_ids": ["loop-dashboard-multitask-dev-child-001"],
  "current_child_run_id": "loop-dashboard-multitask-dev-child-004",
  "backlog": [
    {
      "child_id": "child-004",
      "title": "恢复验收和日志叙事",
      "description": "展示 evaluator 模拟用户操作、前端点击、API 检查、findings、重试、清理和用户决策。",
      "status": "pending | running | passed | failed | blocked | skipped",
      "priority": 40,
      "depends_on": ["child-003"],
      "evidence": []
    }
  ],
  "aggregate_acceptance": {
    "total": 5,
    "passed": 3,
    "failed": 0,
    "blocked": 0,
    "pending": 2,
    "user_decision_required": false
  },
  "reader_summary": {
    "purpose": "string",
    "current_progress": "string",
    "next_step": "string",
    "decision_needed": "string"
  },
  "accepted_changed_paths": []
}
```

现有 `task_id` 字段继续保留。父 run 可以不绑定具体 `task_id`，也可以绑定一个父级 task-contract 用于最终集体验收。

### 子 Run

子 run 表示父 backlog 中的一个可执行任务。它继续使用现有单任务 artifact：

```text
planner-output.json
generator-result.json
evaluator-result.json
task-contract.json
events.jsonl
stdout/stderr logs
artifact hygiene result
cleanup result
```

新增字段：

```json
{
  "run_kind": "child",
  "parent_run_id": "loop-dashboard-multitask-dev",
  "child_index": 4,
  "task_id": "loop-dashboard-multitask-dev-child-004-task",
  "phase": "planned | generating | evaluating | repair_needed | artifact_hygiene | cleanup | passed | stopped_budget | stopped_blocked",
  "reader_summary": {
    "purpose": "string",
    "planner_action": "string",
    "generator_action": "string",
    "evaluator_action": "string",
    "acceptance_result": "string"
  }
}
```

`passed` 是子 run 的终态，只表示该子任务通过，不表示父需求可以合入。

### 旧 Run 兼容

没有 `run_kind` 的 run 按 `single` 处理。现有字段、phase、dashboard 展示和 evaluator 读取路径继续有效。

## 执行隔离与提交策略

- 一个父需求使用一个 feature worktree/branch。
- 所有子任务在同一个父 worktree 内顺序执行，后续子任务可以看到前序子任务的代码和文档变化。
- 首期不支持多个 child 并发修改同一个 worktree。
- 子任务通过 evaluator 后，可以在 feature branch 内生成 checkpoint commit；这不是合入 `main`。
- 父 run 只有在所有子任务通过后才进入 `passed_waiting_human_merge`，等待用户统一确认合入 `main`。
- 如果实现阶段暂时不做 checkpoint commit，必须在父 run 中记录 `accepted_changed_paths`，让后续 dirty path 检查能区分“已验收的子任务改动”和“意外脏路径”。

### Dirty Path 规则

为避免再次出现 baseline dirty path 与任务路径不同步的问题，父子 run 共享一套脏路径规则：

- 父 run 在 preflight 时记录 `baseline_dirty_paths`。
- 子 run 开始前的允许基线是：父 `baseline_dirty_paths` + 父 `accepted_changed_paths`。
- 子 run 只能新增或修改 Planner 允许路径内的文件。
- 如果出现不在父 baseline、不在已验收改动、也不在当前 child allowed paths 中的 dirty path，父 run 进入 `stopped_blocked`。
- dashboard 必须把这些路径标成“意外脏路径”，而不是混入当前子任务验收结果。

## Planner 契约

父 Planner 输出在现有 `planner-output.json` 基础上扩展：

```json
{
  "task_id": "optional-parent-task",
  "policy": "demand_development",
  "task_kind": "registered_task",
  "title": "需求开发多子任务 loop",
  "goal": "string",
  "allowed_paths": [],
  "denylist_paths": [],
  "verify_commands": [],
  "evaluator_scenarios_path": "",
  "stop_conditions": ["passed_waiting_human_merge", "stopped_budget", "stopped_blocked"],
  "backlog": [],
  "next_child_task": {
    "child_id": "child-004",
    "title": "恢复验收和日志叙事",
    "description": "string",
    "allowed_paths": [],
    "denylist_paths": [],
    "verify_commands": [],
    "scenario_commands": [],
    "done_criteria": []
  },
  "done_criteria": [],
  "reader_summary": {
    "purpose": "string",
    "current_progress": "string",
    "next_step": "string",
    "decision_needed": "string"
  },
  "decision_required": false,
  "next_planning_hint": "string"
}
```

Planner 规则：

- 如果父 run 没有 backlog，先创建初始 backlog。
- 子任务必须能追溯到父需求、preflight 约束和停止条件，不能借循环扩大范围。
- 子任务通过后，刷新 backlog 状态并选择下一项可行动子任务。
- 子任务失败后，继续聚焦同一个子任务直到修复通过或耗尽尝试次数。
- 所有可行动子任务通过后，请求父 run 进入 `passed_waiting_human_merge`。
- 如果还有缺口但需要鉴权、网络、权限、denylist 路径或用户策略变化，请求父 run 进入 `stopped_blocked` 并写明需要用户提供什么。

## Task Contract 与 tasks.json

- 父需求应在 `tasks.json` 中有一个父级任务条目，记录需求、验证入口和当前状态。
- 子任务首期可以使用 `task_contract_only`，即在 child run 目录写 `task-contract.json`，通过现有 evaluator CLI 的 `--task-contract` 执行。
- 需要长期追踪、复用或人工检视的子任务，可以同步注册到 `tasks.json`。
- evaluator 场景仍优先放在 `docs/harness/evaluator-scenarios/<task-id>.json`，临时子任务也可以由 `task-contract.json` 内联 scenario commands。

## 调度器流程

新增需求多子任务入口，例如：

```text
python3 scripts/harness_loop_orchestrator.py run-demand-multi \
  --repo-root . \
  --run-id <parent-run-id> \
  --planner-driver codex-exec \
  --generator-driver codex-exec \
  --evaluator-driver codex-exec
```

状态机：

```text
load parent run
if parent phase is preflight:
  stop and wait for confirmation

if backlog is missing or parent planner requested refresh:
  run parent planner

while budget remains:
  if all actionable children passed:
    parent -> passed_waiting_human_merge
    stop

  create or select next child run

  run child planner
  run child generator
  run child evaluator

  if evaluator pass:
    mark child passed
    update parent aggregate_acceptance
    update accepted_changed_paths or checkpoint commit
    run parent planner again
    continue

  if evaluator fail:
    parent phase -> repair_needed
    repair same child until retry limit
    continue

  if blocked, denylist violation, dirty path violation, or budget exceeded:
    parent -> stopped_blocked or stopped_budget
    stop
```

调度器不能在当前 child 处于 `repair_needed`、`generating`、`evaluating`、`artifact_hygiene` 或 `cleanup` 时创建新 child。

## 停止条件

- **全部子任务通过**：父 run 进入 `passed_waiting_human_merge`。
- **Evaluator fail**：修复同一个 child，不推进新 child。
- **Evaluator blocked**：父 run 进入 `stopped_blocked`。
- **Planner blocked**：父 run 进入 `stopped_blocked`。
- **Denylist 或非 allowlist 路径**：父 run 进入 `stopped_blocked`。
- **意外 dirty path**：父 run 进入 `stopped_blocked`。
- **预算耗尽**：父 run 进入 `stopped_budget`。
- **无可行动 child 且无失败 child**：如果 Planner 证明父需求 done criteria 满足，则父 run 进入 `passed_waiting_human_merge`；否则进入 `stopped_blocked` 并说明缺什么。

默认限制：

```json
{
  "max_child_tasks": 8,
  "max_generator_attempts_per_child": 2,
  "max_eval_attempts_per_child": 3,
  "max_parent_planner_rounds": 10,
  "max_wall_time_minutes": 90
}
```

## Dashboard 设计

看板从“选中一个 run”升级为“选中一个父需求并查看其子任务树”。

### 左侧运行列表

父 run 作为主列表项，展示：

- 需求标题和简短描述
- 整体状态
- 已通过子任务数 / 总子任务数
- 当前子任务
- 是否需要用户决策
- 最近更新时间

子 run 默认折叠在父 run 下。没有父子关系的旧 single run 仍作为顶层项展示。

### 右侧父需求详情

顶部优先展示给第三方读者看的摘要：

- 这个需求是什么
- 为什么在跑
- 当前做到哪一步
- 下一步是什么
- 是否有错误或阻塞
- 是否需要用户决策

然后展示：

- 父需求流程图
- 子任务队列
- Planner、Generator、Evaluator 当前动作
- `概览`、`子任务`、`Agent 结果`、`验收情况`、`事件与日志`、`阻塞诊断`、`产物` tab

### 子任务队列

每个 child 必须展示：

- 子任务标题和完整描述，不截断
- 状态
- Planner 动作摘要
- Generator 修改路径和验证摘要
- Evaluator 场景结果和模拟用户行为
- 失败或阻塞原因
- artifact 路径

### 验收与日志

看板优先展示结构化、可阅读事件：

- Planner 创建或更新 backlog
- Planner 选择下一项 child
- Generator 修改了哪些路径
- Generator 运行了哪些验证命令
- Evaluator 模拟了哪些浏览器点击或 API 检查
- Evaluator 场景结果
- findings、重试、清理和用户决策点

文件更新时间仍可展示，但不能作为主要叙事。

日志展示必须继续做脱敏，至少隐藏 token、Authorization、password、secret、api key 等明显凭据。

## Dashboard API

首期可以在现有 API 上扩展，而不是新增写接口。

`GET /api/runs` 返回：

```json
{
  "run_id": "loop-dashboard-multitask-dev",
  "run_kind": "parent | child | single",
  "parent_run_id": "",
  "task_summary": "string",
  "phase": "child_running",
  "health": "progressing",
  "children_summary": {
    "total": 5,
    "passed": 3,
    "failed": 0,
    "blocked": 0,
    "pending": 2
  },
  "current_child_run_id": "loop-dashboard-multitask-dev-child-004",
  "decision_required": false
}
```

`GET /api/runs/{run_id}` 对父 run 返回：

```json
{
  "run_id": "loop-dashboard-multitask-dev",
  "run_kind": "parent",
  "reader_summary": {},
  "aggregate_acceptance": {},
  "children": [],
  "flow_nodes": [],
  "agents": {},
  "acceptance_summary": {},
  "blocked_diagnostics": [],
  "artifact_paths": []
}
```

后端聚合子任务时同时使用：

- 父 run 的 `child_run_ids`
- child run 的 `parent_run_id`

这样即使父 run 某次写入不完整，dashboard 仍可从 child 反向索引恢复关系。

## 事件契约

每个 agent 和 orchestrator 追加结构化事件：

```text
.codex/loop-runs/<run-id>/events.jsonl
```

事件格式：

```json
{
  "timestamp": "2026-07-03T10:42:00Z",
  "run_id": "loop-dashboard-multitask-dev-child-004",
  "parent_run_id": "loop-dashboard-multitask-dev",
  "child_id": "child-004",
  "actor": "planner | generator | evaluator | orchestrator",
  "event_type": "plan | implement | verify | evaluate | repair | blocked | decision | artifact",
  "summary": "中文可读摘要",
  "details": {},
  "artifact_paths": []
}
```

事件写入规则：

- append-only。
- 写入前做敏感信息脱敏。
- `summary` 必须是给人读的短句，不能只写文件名或 JSON key。
- `details` 可以保留结构化信息，但 dashboard 默认不展开原始 JSON。

Dashboard 数据优先级：

1. `events.jsonl`
2. planner/generator/evaluator result JSON 的结构化字段
3. evaluator scenario results
4. stdout/stderr 摘要
5. artifact 文件更新时间

## Evaluator 要求

Evaluator 验证子任务和父需求两层。

子任务 evaluator 必须验证：

- child done criteria 是否满足
- 必要测试和 scenario commands 是否通过
- changed paths 是否在 scope 内
- 涉及用户界面时，用户可见行为是否真的可用
- 是否写出了结构化 scenario results

父需求 evaluator 必须验证：

- child 数量和状态聚合正确
- dashboard 能展示父需求和所有 child
- child 描述、agent 动作、验收结果、错误、决策和 artifact 路径可读
- dashboard/frontend 任务必须通过浏览器模拟点击
- 只有全部可行动 child 通过后，父 phase 才能是 `passed_waiting_human_merge`

看板相关任务的 evaluator 必须模拟第三方读者：

- 打开看板
- 选择一个父需求 run
- 阅读父需求摘要
- 查看子任务队列
- 切换验收和日志 tab
- 验证关键任务描述没有被截断
- 验证错误、阻塞和用户决策状态可见

## 迁移计划

1. 扩展 contracts，允许 `run_kind`、父子字段、backlog、aggregate acceptance、reader summary 和 child-level `passed`。
2. 为旧 single run、parent run、child run、非法父子引用补单测。
3. 用 fake driver 先实现 `run-demand-multi` 状态机。
4. 增加结构化事件写入和 dashboard 读取。
5. 扩展 dashboard 后端，聚合 parent/child run。
6. 扩展 dashboard 前端，展示父需求列表、子任务队列、agent 动作、验收叙事和日志。
7. 增加 dashboard evaluator 场景和浏览器点击检查。
8. 用这个“需求开发多子任务 loop”需求本身跑一次新流程，作为验收用例。

## 风险与缓解

- **Schema 漂移**：集中在 `harness_loop_contracts.py` 校验，并测试旧 run 兼容。
- **Planner 范围膨胀**：child 必须可追溯到父需求和 preflight 约束。
- **无限创建 child**：强制 `max_child_tasks`、`max_parent_planner_rounds` 和父 done criteria。
- **跳过失败 child**：调度器禁止在当前 child 未修复通过前创建新 child。
- **Dashboard 信息过载**：先展示 reader summary，原始 artifact 放到产物 tab。
- **日志误导**：优先使用结构化事件和 evaluator scenario results，不把文件更新时间当主要结论。
- **脏路径误判**：父 run 维护 `baseline_dirty_paths` 和 `accepted_changed_paths`。
- **未经审查合入**：需求开发父 run 永远停在 `passed_waiting_human_merge` 等用户确认。

## Grill-me 审视补强

本轮审视针对最容易造成实现失败的点逐项追问，并把结论写入本 spec：

- **Planner 会不会不断扩大需求范围？**
  结论：child 必须追溯到父需求、preflight 约束和停止条件，超出范围要 `stopped_blocked`。
- **子任务失败后会不会被新子任务绕过？**
  结论：当前 child 处于 repair/evaluate/generate/hygiene/cleanup 时禁止创建新 child。
- **多个子任务如何共享前序改动？**
  结论：父需求使用一个 feature worktree/branch，child 顺序执行。
- **是否会再次出现 baseline dirty path 不同步？**
  结论：父 run 记录 baseline，子任务通过后记录 `accepted_changed_paths` 或 checkpoint commit。
- **看板为什么能恢复父子关系？**
  结论：同时使用父 `child_run_ids` 和子 `parent_run_id` 建索引。
- **旧 run 是否会坏？**
  结论：没有 `run_kind` 的 run 按 `single` 处理。
- **用户何时介入？**
  结论：全部 child 通过后的合入门、denylist/权限/鉴权/预算/意外脏路径等阻塞点才需要用户介入。

## 实现选择

- child run 目录首期采用扁平兄弟目录：
  `.codex/loop-runs/<parent>-child-001/`。
  这比嵌套目录更兼容当前 store 扫描逻辑。
- 父级最终验收首期可以通过 parent task-contract + scenario commands 完成；
  后续如果需要更强隔离，再独立成 parent evaluator step。
