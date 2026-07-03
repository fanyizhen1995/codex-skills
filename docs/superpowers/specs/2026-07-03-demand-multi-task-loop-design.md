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
- spec 必须包含测试方案设计和 e2e 测试用例设计；实现阶段必须把 spec 中列出的测试全部跑通，不能只完成代码改动。

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
- 首期不做 child checkpoint commit。所有 child 共享父 feature worktree，父 run 用 `accepted_changed_paths` 记录已通过 child 的改动；所有 child 通过后统一提交和等待合入。
- 看板以父 run 为主要列表项，子 run 在父 run 下折叠和聚合展示。
- evaluator 必须提供用户场景结果；涉及前端或看板时必须模拟浏览器点击。
- Planner、Generator、Evaluator、Orchestrator 都应写结构化事件，让看板不只显示文件更新时间。
- 进入开发前必须把测试方案落入 implementation plan；开发完成前必须执行并记录所有单元、集成、e2e 和 evaluator 验证结果。

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

### Phase 约束

父子 run 必须有明确 phase 边界，避免调度器和 dashboard 混用状态。

Parent-only phase：

```text
planning
child_running
passed_waiting_human_merge
```

Child-only phase：

```text
planned
generating
evaluating
artifact_hygiene
cleanup
passed
```

Shared terminal/error phase：

```text
repair_needed
stopped_budget
stopped_blocked
```

约束规则：

- `run_kind=parent` 不允许进入 `generating`、`evaluating`、`artifact_hygiene`、`cleanup`、`passed`。
- `run_kind=child` 不允许进入 `planning`、`child_running`、`passed_waiting_human_merge`。
- 没有 `run_kind` 的旧 single run 继续使用现有 phase 集合。
- `passed` 只能用于 child；父需求完成必须使用 `passed_waiting_human_merge`。
- `repair_needed` 用于 parent 时表示当前 child 需要修复；用于 child 时表示该 child 自身需要修复。
- schema 校验必须覆盖 run_kind/phase 组合，不允许只校验 phase 字符串是否在全局枚举中。

## 执行隔离与提交策略

- 一个父需求使用一个 feature worktree/branch。
- 所有子任务在同一个父 worktree 内顺序执行，后续子任务可以看到前序子任务的代码和文档变化。
- 首期不支持多个 child 并发修改同一个 worktree。
- 子任务通过 evaluator 后不生成 checkpoint commit；父 run 把该 child 的 `changed_paths` 合并进 `accepted_changed_paths`。
- 父 run 只有在所有子任务通过后才进入 `passed_waiting_human_merge`，等待用户统一确认合入 `main`。
- 所有 child 通过后，Generator 或人工合入流程再整理成最终 commit。
- `accepted_changed_paths` 是首期唯一的 child 间 dirty path 继承机制，不能和 child checkpoint commit 混用。

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
  "planner_decision": "next_child | parent_done | blocked | failed",
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
  "blocked_reason": "",
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
- `planner_decision=next_child` 时，必须提供非空 `next_child_task`。
- `planner_decision=parent_done` 时，`next_child_task` 必须为空，且 `done_criteria` 必须能证明父需求已完成。
- `planner_decision=blocked` 时，`next_child_task` 必须为空，`blocked_reason` 必须说明需要用户提供什么或哪个约束阻塞。
- `planner_decision=failed` 时，`blocked_reason` 必须说明 Planner 自身无法产生可靠计划的原因。
- 所有可行动子任务通过后，输出 `planner_decision=parent_done`，请求父 run 进入 `passed_waiting_human_merge`。
- 如果还有缺口但需要鉴权、网络、权限、denylist 路径或用户策略变化，输出 `planner_decision=blocked`，请求父 run 进入 `stopped_blocked`。

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
    update parent accepted_changed_paths
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

### 恢复与重入规则

`run-demand-multi` 必须可重复执行。进程中断或用户重新启动时，调度器按 artifact 状态恢复，而不是重新创建 child。

恢复规则：

- 先读取 parent `current_child_run_id`。
- 如果 current child 存在且 phase 不是 `passed`、`stopped_budget`、`stopped_blocked`，继续该 child 的当前 phase。
- 如果 current child 是 `planned`，继续 child planner 或 generator。
- 如果 current child 是 `generating`，检查 `generator-result.json` 是否存在且有效；有效则进入 evaluator，否则重跑 generator attempt。
- 如果 current child 是 `evaluating`，检查 `evaluator-result.json` 是否存在且有效；有效则应用结果，否则重跑 evaluator attempt。
- 如果 current child 是 `artifact_hygiene` 或 `cleanup`，检查对应 result artifact；有效则推进下一 phase，否则重跑当前 hygiene/cleanup step。
- 如果 current child 是 `repair_needed`，继续修复同一个 child。
- 如果 current child 是 `passed`，确认其 changed paths 已进入 parent `accepted_changed_paths` 后，才允许 parent Planner 选择下一项。
- 已经 `passed` 的 child 绝不重复执行，除非用户显式创建新 run 或清除该 child artifact。
- 如果 parent `child_run_ids` 和磁盘 child artifact 不一致，先通过 child `parent_run_id` 重建索引，再写回 parent，并追加 orchestrator event。
- 所有恢复动作必须追加 `events.jsonl`，说明是 resume 而不是新执行。

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

### 父子关系排序与去重

Dashboard 后端必须定义稳定的父子关系合并规则：

- 父 `child_run_ids` 和 child `parent_run_id` 都指向同一关系时，只保留一个 child。
- 如果父 `child_run_ids` 缺少某个反向指向该父的 child，dashboard 仍展示该 child，并在 diagnostics 中标记“父索引缺失”。
- 如果父 `child_run_ids` 指向不存在的 child，dashboard 在 diagnostics 中标记“child artifact missing”，但不阻塞其它 child 展示。
- 如果 child `parent_run_id` 指向 A，但 A 的 `child_run_ids` 没有它，以 child `parent_run_id` 为准恢复关系。
- 如果一个 child 被多个 parent `child_run_ids` 引用，以 child 自身 `parent_run_id` 为准；没有 `parent_run_id` 时归入最新更新时间的 parent，并标记冲突 diagnostics。
- child 排序优先使用 `child_index`，其次使用 backlog 中的 `priority`，再次使用 `updated_at`，最后使用 `run_id` 字典序。
- run list 排序：未完成 parent 优先按 `updated_at` 倒序，已完成 parent 放在后面；child 不作为顶层项重复出现，除非缺少 parent。
- dashboard API 必须返回 `relationship_diagnostics`，用于展示缺失、冲突、重复和恢复过的父子关系。

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

## 测试方案设计

本需求的测试方案是 spec 的一部分，implementation plan 必须逐条引用并落地。
实现阶段完成标准不是“代码写完”，而是本节列出的测试全部跑通并记录结果。

### 单元测试

覆盖范围：

- `harness_loop_contracts.py`
  - 旧 single run 无 `run_kind` 时仍通过校验。
  - parent run 必须接受 `child_run_ids`、`backlog`、`aggregate_acceptance`、`reader_summary` 和 `accepted_changed_paths`。
  - child run 必须接受 `parent_run_id`、`child_index`、child-level `passed`。
  - parent-only、child-only、shared phase 组合分别通过或失败；非法 `run_kind`、非法 parent phase、非法 child phase、缺少 parent linkage 时失败。
  - parent planner output 必须校验 `planner_decision`、`next_child_task`、`blocked_reason` 和 `done_criteria` 的组合关系。
- `harness_loop_orchestrator.py`
  - parent planner 可以创建 backlog 和 next child。
  - `planner_decision=next_child` 时必须有 `next_child_task`。
  - `planner_decision=parent_done` 时不能有 `next_child_task`，且父 run 进入 `passed_waiting_human_merge`。
  - `planner_decision=blocked|failed` 时必须有 `blocked_reason`，且父 run 进入 `stopped_blocked`。
  - child evaluator pass 后更新 parent aggregate acceptance。
  - child evaluator fail 后保持同一 child 进入 repair，不创建新 child。
  - parent 达到 `max_child_tasks`、`max_parent_planner_rounds` 或 wall time 时进入 `stopped_budget`。
  - dirty path 不在 parent baseline、accepted changed paths、当前 child allowed paths 中时进入 `stopped_blocked`。
  - 重启时根据 current child phase 恢复，不重复执行已 passed child。
- Loop Dashboard backend store
  - 同时通过父 `child_run_ids` 和子 `parent_run_id` 恢复父子关系。
  - 父子索引冲突时按 spec 排序与去重规则输出 `relationship_diagnostics`。
  - parent/child run id、artifact path、relationship recovery 都必须拒绝 path traversal。
  - `GET /api/runs` 返回 parent summary、children summary、decision_required。
  - `GET /api/runs/{parent}` 返回 children、reader summary、aggregate acceptance、agent summaries、acceptance summary、blocked diagnostics。
  - 旧 single run 仍可作为顶层 run 展示。
  - `events.jsonl` 优先于文件 mtime 生成日志叙事。
  - 事件和日志脱敏覆盖 token、Authorization、password、secret、api key。

### 集成测试

覆盖范围：

- fake driver 跑完整 `run-demand-multi`：
  - 创建 parent run。
  - Planner 生成 3 个 child。
  - child 1/2/3 顺序 pass。
  - parent 最终进入 `passed_waiting_human_merge`。
- fake driver 跑修复路径：
  - child 2 evaluator 第一次 fail。
  - generator 修复同一个 child 2。
  - child 2 第二次 pass。
  - parent 才继续 child 3。
- fake driver 跑阻塞路径：
  - child 出现 denylist 或 dirty path violation。
  - parent 进入 `stopped_blocked`。
  - dashboard blocked diagnostics 能显示原因。
- dashboard backend + fixture artifact：
  - 用 parent/child fixture run 目录启动 API。
  - API 返回聚合状态与 fixture 一致。
  - 事件日志包含 planner、generator、evaluator、orchestrator 的结构化摘要。
  - 恶意 `run_id`、`child_run_ids` 或 artifact path 不能逃逸 `project_root`。
- resume integration：
  - 分别从 child `generating`、`evaluating`、`artifact_hygiene`、`cleanup`、`repair_needed` 重启。
  - 验证调度器继续当前 phase，不新建 child，不重复执行 passed child。
- agent failure integration：
  - planner/generator/evaluator 返回 timeout、invalid_json、missing artifact 时，parent 进入 `stopped_blocked` 或当前 child 保持可修复状态。
  - dashboard diagnostics 能显示 agent role、attempt、失败类型和下一步。
- human gate integration：
  - 所有 child pass 后 parent 进入 `passed_waiting_human_merge`。
  - 调度器不自动 merge `main`，不自动删除用户未确认的 feature worktree。
  - final commit 或 merge 只能由用户确认后的单独流程触发。

### 回归测试

每次实现阶段必须运行现有相关测试，至少包括：

```text
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
python3 -m unittest discover scripts/tests -v
```

如果某条命令因环境或依赖不存在无法运行，implementation result 必须写明原因，并补充等价验证命令；不能静默跳过。

### 测试可执行性规则

implementation plan 必须把每个测试映射到可执行命令或 evaluator scenario：

- 单元测试必须写明测试文件和测试类/函数。
- 集成测试必须写明 CLI 命令、fixture 目录和预期 artifact。
- E2E 测试必须写明自动化入口、浏览器/服务启动方式、截图或日志 artifact 保存位置。
- 每个 E2E 必须有 pass/fail 判定，不允许只写“人工查看”。
- 如果因环境缺少浏览器、端口、网络或依赖无法运行，必须记录 blocked 原因，并提供最小等价验证；但正式完成前仍需要在可运行环境补跑。

### 验收记录

Generator 和 Evaluator 都必须把测试结果写入 run artifact：

- Generator 写入 `generator-result.json.verify_results`。
- Evaluator 写入 `evaluator-result.json` 和 scenario results。
- Orchestrator 追加 `events.jsonl`，记录每组测试的 pass/fail/blocked 摘要。
- Dashboard 的验收 tab 必须能展示这些测试结论。

## E2E 测试用例设计

E2E 目标是证明“需求开发多子任务 loop”对真实使用者可见、可理解、可验收。

### E2E-01：多子任务需求完整通过

前置：

- 使用 fake driver 或受控 fixture，创建一个 parent run。
- parent backlog 包含 3 个 child。
- 每个 child 都有 planner/generator/evaluator artifact 和 `events.jsonl`。

步骤：

1. 运行 `run-demand-multi`。
2. 确认 child 1、child 2、child 3 顺序执行。
3. 确认每个 child pass 后 parent aggregate acceptance 更新。
4. 确认 parent 最终进入 `passed_waiting_human_merge`。

预期：

- 不需要用户逐个确认 child。
- parent 只在所有 child pass 后等待合入。
- parent run artifact 中能看到 child run IDs、aggregate acceptance、reader summary。
- `main` 不发生自动 merge。
- parent feature worktree 保留到用户确认。

### E2E-02：失败 child 修复后继续

前置：

- child 2 的 evaluator 第一次返回 fail。

步骤：

1. 运行 `run-demand-multi` 到 child 2 fail。
2. 确认 parent phase 为 `repair_needed`。
3. 确认 orchestrator 继续修复 child 2。
4. child 2 pass 后，确认 parent planner 才选择 child 3。

预期：

- 不创建新的 child 绕过 child 2。
- dashboard 子任务队列显示 child 2 曾失败并已修复通过。
- events 里有 fail、repair、pass 三类记录。

### E2E-03：意外 dirty path 阻塞

前置：

- parent baseline dirty paths 已记录。
- child allowed paths 不包含某个新增 dirty path。

步骤：

1. 运行 child generator 后制造或检测到意外 dirty path。
2. 运行 dirty path gate。
3. 打开 dashboard 查看父 run。

预期：

- parent 进入 `stopped_blocked`。
- dashboard blocked diagnostics 显示具体路径、为什么不属于 baseline/accepted/current allowed paths、下一步需要用户如何处理。

### E2E-04：Dashboard 父子任务可读性

前置：

- 启动 Loop Dashboard。
- 准备 parent + child fixture，其中包含长描述、agent action、acceptance summary、blocked diagnostics 和 artifact paths。

步骤：

1. 用浏览器自动化打开 dashboard。
2. 在桌面视口点击父需求 run。
3. 阅读顶部 reader summary。
4. 查看子任务队列。
5. 切换 `验收情况`、`事件与日志`、`阻塞诊断`、`产物` tab。
6. 检查长任务描述和 agent 摘要没有被截断。
7. 检查事件日志中包含 Planner/Generator/Evaluator 的结构化事件。
8. 检查凭据形态文本被脱敏。
9. 切换到移动视口，重复父需求摘要、子任务队列、验收 tab 和日志 tab 的可读性检查。

预期：

- 第三方读者能看懂任务是什么、进行到哪里、验收了什么、是否有错误、是否需要用户决策。
- 日志不只显示文件 update，还显示 Planner/Generator/Evaluator 的结构化事件。
- token、Authorization、password、secret、api key 等文本不会原文展示。
- 桌面和移动视口均无明显文字重叠、关键内容截断或无法点击。

### E2E-05：旧 single run 兼容

前置：

- 准备旧格式 single run fixture，不包含 `run_kind`。

步骤：

1. 启动 dashboard。
2. 打开 run list。
3. 点击旧 single run。

预期：

- 旧 run 仍作为顶层项展示。
- 详情页保持现有单 run 行为。
- 新 parent/child 聚合逻辑不影响旧 run。

### E2E-06：Agent timeout / invalid JSON / missing artifact

前置：

- 准备一个 parent run 和当前 child。
- 通过 fake driver 或 fixture 模拟 generator timeout、evaluator invalid JSON、planner missing `planner-output.json` 三类异常。

步骤：

1. 运行 `run-demand-multi`。
2. 触发其中一种 agent 异常。
3. 打开 dashboard 查看父 run 和当前 child。

预期：

- 调度器不创建新 child 绕过异常。
- parent 或 child phase 进入明确的 `stopped_blocked` 或可修复状态。
- blocked diagnostics 显示 agent role、attempt、异常类型、缺失 artifact 路径和下一步。
- `events.jsonl` 记录异常事件，日志脱敏后可读。

### E2E-07：中断后恢复

前置：

- 准备 parent run，其中 child 1 已 `passed`，child 2 停在 `evaluating` 或 `cleanup`。

步骤：

1. 重新运行 `run-demand-multi`。
2. 检查 child 1 没有重复执行。
3. 检查 child 2 从当前 phase 继续。
4. child 2 通过后，parent Planner 才选择 child 3。

预期：

- 不生成重复 child。
- 不重复写入 child 1 的事件和验收结果。
- parent `accepted_changed_paths` 保持一致。
- dashboard events 显示 resume 事件。

### E2E-08：父子关系冲突与去重

前置：

- 准备 parent A、parent B 和 child fixture。
- child 的 `parent_run_id` 指向 parent A。
- parent B 的 `child_run_ids` 也错误引用同一个 child。
- parent A 缺少另一个反向指向它的 child。

步骤：

1. 启动 dashboard。
2. 打开运行列表。
3. 点击 parent A。
4. 查看子任务队列和 blocked/relationship diagnostics。

预期：

- child 只展示一次。
- child 归属以自身 `parent_run_id` 为准。
- 缺失父索引、重复引用和冲突归属都显示在 `relationship_diagnostics`。
- 子任务排序符合 `child_index`、priority、updated_at、run_id 的优先级。

### E2E-09：Planner blocked / failed 不创建 child

前置：

- parent Planner 输出 `planner_decision=blocked` 或 `planner_decision=failed`。
- `blocked_reason` 非空。

步骤：

1. 运行 `run-demand-multi`。
2. 检查 parent phase。
3. 打开 dashboard 查看父 run。

预期：

- parent 进入 `stopped_blocked`。
- 不创建新的 child run。
- dashboard 显示 `blocked_reason`、用户需要提供什么、下一步建议。

### E2E-10：父子 artifact path traversal 防护

前置：

- 准备 parent run fixture。
- 在 `child_run_ids`、child `parent_run_id`、artifact paths 中放入 `../`、绝对路径和跨 project root 的路径。

步骤：

1. 启动 dashboard backend。
2. 请求 `GET /api/runs`。
3. 请求恶意 run id 的 `GET /api/runs/{run_id}`。
4. 查看 diagnostics。

预期：

- API 不读取 project root 之外的文件。
- 恶意 child 或 artifact 被忽略或标记为 blocked diagnostics。
- 服务不崩溃，合法 run 仍可展示。

## 迁移计划

1. 先把本 spec 的测试方案拆进 implementation plan，明确每个阶段必须跑哪些测试。
2. 扩展 contracts，允许 `run_kind`、父子字段、backlog、aggregate acceptance、reader summary 和 child-level `passed`。
3. 为旧 single run、parent run、child run、非法父子引用补单测，并确认失败用例先能失败。
4. 用 fake driver 先实现 `run-demand-multi` 状态机，并跑通 E2E-01、E2E-02、E2E-03、E2E-06、E2E-07、E2E-09 的非 UI 版本。
5. 增加结构化事件写入和 dashboard 读取。
6. 扩展 dashboard 后端，聚合 parent/child run，并跑通 API 集成测试。
7. 扩展 dashboard 前端，展示父需求列表、子任务队列、agent 动作、验收叙事和日志。
8. 增加 dashboard evaluator 场景和浏览器点击检查，跑通 E2E-04、E2E-05、E2E-06、E2E-07、E2E-08、E2E-09、E2E-10 的 UI 可见性和安全边界部分。
9. 运行全部回归测试和 dashboard evaluator。
10. 用这个“需求开发多子任务 loop”需求本身跑一次新流程，作为最终验收用例。

## 风险与缓解

- **Schema 漂移**：集中在 `harness_loop_contracts.py` 校验，并测试旧 run 兼容。
- **Planner 范围膨胀**：child 必须可追溯到父需求和 preflight 约束。
- **无限创建 child**：强制 `max_child_tasks`、`max_parent_planner_rounds` 和父 done criteria。
- **跳过失败 child**：调度器禁止在当前 child 未修复通过前创建新 child。
- **Dashboard 信息过载**：先展示 reader summary，原始 artifact 放到产物 tab。
- **日志误导**：优先使用结构化事件和 evaluator scenario results，不把文件更新时间当主要结论。
- **脏路径误判**：父 run 维护 `baseline_dirty_paths` 和 `accepted_changed_paths`。
- **未经审查合入**：需求开发父 run 永远停在 `passed_waiting_human_merge` 等用户确认。
- **中断后重复执行**：恢复规则以 `current_child_run_id` 和 child phase 为准，已 passed child 不重复执行。
- **父子关系冲突**：dashboard 输出 `relationship_diagnostics`，并按 child 自身 `parent_run_id` 和 `child_index` 优先恢复。

## Grill-me 审视补强

本轮审视针对最容易造成实现失败的点逐项追问，并把结论写入本 spec：

- **Planner 会不会不断扩大需求范围？**
  结论：child 必须追溯到父需求、preflight 约束和停止条件，超出范围要 `stopped_blocked`。
- **子任务失败后会不会被新子任务绕过？**
  结论：当前 child 处于 repair/evaluate/generate/hygiene/cleanup 时禁止创建新 child。
- **多个子任务如何共享前序改动？**
  结论：父需求使用一个 feature worktree/branch，child 顺序执行。
- **是否会再次出现 baseline dirty path 不同步？**
  结论：父 run 记录 baseline，子任务通过后记录 `accepted_changed_paths`。
- **看板为什么能恢复父子关系？**
  结论：同时使用父 `child_run_ids` 和子 `parent_run_id` 建索引。
- **旧 run 是否会坏？**
  结论：没有 `run_kind` 的 run 按 `single` 处理。
- **用户何时介入？**
  结论：全部 child 通过后的合入门、denylist/权限/鉴权/预算/意外脏路径等阻塞点才需要用户介入。
- **测试是否只是实现后的补充？**
  结论：不是。spec 必须先定义测试方案和 e2e 用例，implementation plan 必须逐条落地，开发结束前必须全部跑通或写明不可运行原因和等价验证。
- **Planner 空输出时调度器如何判断完成还是阻塞？**
  结论：新增 `planner_decision`，禁止调度器通过空 `next_child_task` 猜测状态。
- **child phase 会不会污染 parent phase？**
  结论：新增 parent-only、child-only、shared phase 约束，schema 必须校验 run_kind/phase 组合。
- **child checkpoint commit 和 accepted_changed_paths 是否会分叉？**
  结论：首期不做 child checkpoint commit，只使用 `accepted_changed_paths`，最终父需求统一提交。
- **进程中断后会不会重复创建 child？**
  结论：新增恢复与重入规则，优先恢复 `current_child_run_id`，已 passed child 不重复执行。
- **看板父子关系冲突时谁说了算？**
  结论：child 自身 `parent_run_id` 优先，排序按 `child_index`、priority、updated_at、run_id，冲突写入 `relationship_diagnostics`。
- **测试是否覆盖 agent 真实失败形态？**
  结论：新增 E2E-06 覆盖 timeout、invalid JSON、missing artifact；新增 E2E-07 覆盖中断恢复。

## 实现选择

- child run 目录首期采用扁平兄弟目录：
  `.codex/loop-runs/<parent>-child-001/`。
  这比嵌套目录更兼容当前 store 扫描逻辑。
- 父级最终验收首期可以通过 parent task-contract + scenario commands 完成；
  后续如果需要更强隔离，再独立成 parent evaluator step。
