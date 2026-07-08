# Loop Auditor And Harness Process Governance Design

日期：2026-07-08

## 背景

当前仓库已经具备两类可运行 loop：

- `demand-development`：父需求 run + 多个 child run，子任务按 Planner -> Generator -> Evaluator 执行，全部通过后进入人工合入门。
- `autonomous-knowledge`：面向 wiki/crawler 资料拓展的 Planner -> Generator -> Evaluator -> Planner 循环，支持 coverage map、gap proof、identity key、required evidence 和自动提交。

近期 AI infra 资料扩充和治理 loop 证明了这套机制可以持续产出代码、文档和知识入库 commit，但也暴露出新的流程风险：loop 会在多轮之后空转、偏离原始目标、重复犯同类错误、过度钻局部问题、积累未归属运行产物，或者沉淀过多相互重叠的 skill。单轮 Evaluator 只判断一个子任务是否通过，不能充分回答“连续多轮整体是否还值得继续”。

因此需要引入独立第三方 `Auditor`，通过内联审计闸门和解耦审计 agent 对连续多轮执行效果进行周期性审计，并在必要时硬阻塞后续普通开发或资料拓展。

## 用户已确认决策

- Auditor 必须是独立第三方审计 agent，不由 Planner、Generator 或 Evaluator 兼任。
- Auditor 拥有硬阻塞权：如果输出 `must_fix`，loop 必须先整改，不能继续普通开发或资料拓展。
- 首期采用“内联闸门 + 解耦 Auditor agent”：硬阻塞执行点在状态机内联，LLM Auditor 作为独立 agent 按 cadence 运行并产出审计 artifact。
- Auditor 必须判断 loop 是否空转、偏航、重复犯错、流程低效。
- Auditor 必须判断 loop 是否过于钻牛角尖；必要时及时制止、更换开发方向或提前终止任务。
- Auditor 必须审视 loop 过程中沉淀的 skill 数量和质量；如果 skill 太多、重叠或低价值，必须建议整合、归一或删除。
- 外部 agent 的流程审视报告作为本设计输入，但需要经过本仓库事实核验后采纳。

## 目标

1. 在 loop 中加入审计闸门和 Auditor artifact，形成 `Planner -> Generator -> Evaluator -> Audit Gate -> Planner` 的可审计循环；Auditor agent 按 cadence 或事件触发运行。
2. 对多轮执行效果建立硬性审计：空转、偏航、重复错误、钻牛角尖、流程缺陷和 skill 膨胀都能被发现并阻塞。
3. 让 Planner 在看到 `must_fix` 审计建议后，只能优先创建整改任务，直到 Auditor 复审关闭。
4. 把外部审视报告中确认属实的 harness 缺陷纳入治理路线：巨石编排、可信证据、runtime artifact 隔离、schema 漂移、codex attempt 和持久化进度台账。
5. 让 Loop Dashboard 对第三方读者可读：能看到最近一次审计结论、阻塞原因、整改动作和复审状态。
6. 形成可复用 skill 候选清单，但由 Auditor 控制数量，避免把所有流程都沉淀成碎片化 skill。

## 非目标

- 不让 Auditor 直接修改代码、wiki、run state 或 git。Auditor 只读证据并输出报告；整改由 Planner/Generator 执行。
- 不把 Evaluator 替换成 Auditor。Evaluator 负责单任务验收，Auditor 负责跨轮过程审计。
- 不在首期实现跨项目 daemon。首期只审计当前项目下 `.codex/loop-runs`。
- 不自动合入 `main`。需求开发最终合入仍受用户确认控制；已确认的 wiki/crawler 入库 commit 按项目规则推送 `origin/main`。
- 不把项目专属 Step4 evaluator 逻辑写回通用 skill 模板。
- 不因纯偏好、命名或轻微格式问题触发 `must_fix`。

## 与现有 AI Infra Governance Loop 的关系

本设计不是替代 `docs/superpowers/specs/2026-07-07-ai-infra-loop-governance-design.md`，而是在其上补充一个跨轮审计层。

- AI Infra Governance 继续负责资料拓展 loop 的候选评分、needs queue、identity key、depth acquisition、source snapshot、formal suspicion 和可见性验收。
- Loop Auditor 负责判断这些治理机制连续运行后是否仍有效：是否空转、偏航、重复犯错、钻牛角尖、skill 膨胀或结构性债务继续复发。
- 已完成的 governance run 不 retroactively 阻塞；新 Auditor 机制只对后续 run 或用户明确要求复审的历史 run 生效。
- 如果 Auditor 发现 governance 规则本身导致空转或过度流程化，整改任务应进入 demand-development loop，而不是继续普通资料拓展。

## 术语

- **Evaluator**：任务级验收者，判断当前 child 或当前 autonomous task 是否符合 contract。
- **Auditor**：跨轮审计者，判断 loop 是否继续有效、是否应整改、换方向或终止。
- **Audit finding**：审计发现，按严重度分为 `must_fix`、`should_fix`、`observe`。
- **Tunnel vision**：loop 对局部问题投入过多轮次或 token，导致整体目标停滞。
- **Skill inventory**：与当前 loop 流程相关的 skill 清单，包括已有 skill、候选 skill、重复 skill 和应删除/整合 skill。
- **Loop runtime root**：loop 运行证据根目录。首期默认仍是 `.codex/loop-runs`，但所有逻辑必须通过统一 resolver 访问，后续可以切换到 worktree 外部路径。

## Grill-Me 审视后修正

本 spec 初稿经过 `grill-me` 视角审视后，补齐以下落地缺口：

- Auditor 虽然是只读 agent，但 audit artifact 必须由 orchestrator 写入，不能让 Auditor 直接写被审计仓库。
- audit finding 必须有稳定 ID 和生命周期，否则 `must_fix` 无法被复审关闭。
- `audit_blocked` 只能作用于 parent run 或 autonomous run；child run 仍通过 `repair_needed` 表示任务内修复。
- Auditor 本身必须有预算和反钻牛角尖约束，否则审计会变成新的空转来源。
- runtime artifact 隔离不能破坏 Loop Dashboard，首期应先统一 runtime root resolver，再逐步迁移出被评估 worktree。
- Phase 1 只提供报告和可见性，不允许宣称已经具备硬阻塞；硬阻塞从 Phase 2 才生效。
- 评审后进一步修正：硬阻塞不要求 LLM Auditor 在线参与每轮 phase pump；真正内联的是“是否存在 open `must_fix`”的确定性闸门，LLM Auditor 解耦运行并写入供闸门消费的 artifact。
- 评审后进一步修正：Auditor 硬阻塞前必须先落地最小 transition/provenance 契约，否则会在已知巨石编排文件上继续叠加漂移风险。

## 架构决策：内联闸门 + 解耦 Auditor Agent

“Auditor 独立第三方”和“Auditor 同步嵌入 loop 控制流”是两个不同维度。本设计采用：

1. **内联硬闸门**：phase pump 每次准备继续普通规划、资料拓展或 human merge 前，只做廉价确定性检查：当前 run 是否存在 open `must_fix` finding。如果存在，阻塞并要求 Planner 创建整改任务。
2. **内联确定性信号检测**：空转、重复失败、dirty path、未推送、coverage 无增长、同 identity key 重复 blocked 等信号由 orchestrator 从 artifact 计算，不依赖 LLM 主观判断。
3. **解耦 Auditor agent**：到达 cadence 或事件触发时，orchestrator 生成 audit bundle，调用独立 Auditor agent 解读确定性信号、判断严重度、提出方向控制和 skill 治理建议。

因此，硬阻塞来自已校验 audit artifact 中的 open `must_fix`，不是来自在线 LLM 的即时判断。这样保留独立第三方审计，同时避免每轮都把 loop 活性绑在 Auditor agent 上。

## 确定性信号层

Auditor 不能凭空判断空转、偏航或重复犯错。Orchestrator 必须先生成确定性信号摘要，作为 audit bundle 的核心输入。

最小信号字段：

```json
{
  "schema_version": 1,
  "run_id": "string",
  "computed_at": "2026-07-08T00:00:00Z",
  "progress_counters": {
    "passed_children_since_last_audit": 0,
    "autonomous_rounds_since_last_audit": 0,
    "commits_since_last_audit": 0,
    "coverage_layers_changed": 0,
    "new_raw_files": 0,
    "new_or_updated_wiki_pages": 0
  },
  "repeat_counters": {
    "same_evaluator_finding_count": 0,
    "same_dirty_path_count": 0,
    "same_identity_key_blocked_count": 0,
    "same_file_modified_consecutively": 0
  },
  "hygiene_counters": {
    "unclassified_dirty_paths": 0,
    "unpushed_commits": 0,
    "missing_required_evidence": 0,
    "dashboard_visibility_failures": 0
  },
  "tunnel_vision_inputs": {
    "same_local_issue_rounds": 0,
    "core_goal_progress_delta": "none | low | medium | high",
    "remaining_value_estimate": "low | medium | high"
  }
}
```

LLM Auditor 可以解读这些信号，但不能伪造或替换它们。若缺少确定性信号摘要，Auditor 最多输出 `observe` 或 `blocked`，不能输出硬阻塞 `must_fix`。

## Auditor 独立性和写入权

Auditor 是独立第三方 agent，但这里的独立是角色隔离，不是对抗式安全边界。Auditor 仍运行在同一项目环境中，因此必须依赖 orchestrator provenance 和 deterministic signals 来约束判断。它不直接写 git 工作树，也不直接修改 run state。执行方式是：

1. Orchestrator 收集审计输入，生成只读 audit bundle。
2. Auditor 读取 bundle，返回一个 JSON payload。
3. Orchestrator 校验 payload schema、补充 provenance、写入 audit artifact。
4. Orchestrator 根据已校验 artifact 更新 run phase 和 `next_action`。

因此，`created_by` 必须区分：

- `auditor_payload.created_by`: Auditor agent 的角色声明，只用于说明谁产生判断。
- `audit_artifact.created_by`: 必须是 `harness_loop_orchestrator`，表示 artifact 由 orchestrator 校验并落盘。

关键阻塞状态只信任 orchestrator 写入的 audit artifact。Auditor 不能通过直接编辑 `run.json` 让 loop 进入或离开 `audit_blocked`。

## 运行模型

### 状态机

在现有 loop phase 基础上新增或映射以下审计状态。它们表达审计闸门和 finding 生命周期，不表示每轮都同步执行 LLM Auditor：

```text
audit_pending
auditing
audit_passed
audit_blocked
```

phase 适用范围：

- `run_kind=parent` 可进入 `audit_pending`、`auditing`、`audit_passed`、`audit_blocked`。
- `autonomous-knowledge` single run 可进入 `audit_pending`、`auditing`、`audit_passed`、`audit_blocked`。
- `run_kind=child` 不进入 `audit_blocked`；child 内部问题继续用 `repair_needed`，父 run 根据 child 结果和 audit report 决定是否阻塞。
- 旧 single demand run 首期保持兼容；没有 `run_kind` 的历史 run 只被 Dashboard 展示，不强制 retroactive audit。

需求开发 loop 的控制流：

```text
Parent Planner
  -> Child Planner -> Child Generator -> Child Evaluator
  -> Deterministic audit gate
  -> Auditor agent when due
  -> Parent Planner
  -> ...
  -> Deterministic audit gate + Auditor before human merge
  -> passed_waiting_human_merge
```

资料拓展 loop 的控制流：

```text
Autonomous Planner
  -> Generator
  -> Evaluator
  -> Commit Gate
  -> Deterministic audit gate
  -> Auditor agent when due
  -> Planner
  -> stopped_no_action | stopped_budget | stopped_blocked
```

如果 Auditor 输出 `must_fix`：

```text
audit_blocked
  -> Planner must create audit-remediation child/task
  -> Generator fixes
  -> Evaluator verifies
  -> Auditor re-checks previous finding
  -> audit_passed
```

### 硬阻塞规则

`audit_blocked` 是硬阻塞状态。进入该状态后：

- `demand-development` 父 Planner 只能选择审计整改 child，不能选择普通功能 child。
- `autonomous-knowledge` Planner 只能选择治理/修复/整理任务，不能继续普通资料扩充。
- 如果整改需要用户凭据、许可、扩大权限、删除 raw 证据或改变停止条件，Planner 必须停在 `stopped_blocked` 并请求用户决策。
- Auditor 复审没有关闭 `must_fix` 前，不允许进入 human merge gate 或下一轮普通 expansion。

硬阻塞必须绑定至少一个 open finding：

```json
{
  "finding_id": "audit-001-tunnel-vision-001",
  "severity": "must_fix",
  "status": "open",
  "required_planner_action": "create_remediation_child",
  "blocking_reason": "same evaluator finding repeated in two consecutive child runs"
}
```

如果 audit report 没有 open `must_fix` finding，orchestrator 不得把 run 置为 `audit_blocked`。

如果 Auditor agent 超时、返回 invalid JSON 或缺少必要字段：

- 已存在 open `must_fix` 时，内联闸门继续阻塞。
- 没有 open `must_fix` 时，不得因单次 Auditor agent 失败而阻塞普通 loop；orchestrator 记录 `audit_unavailable`，并按 cadence 下次重试。
- human merge 前的 Auditor 失败必须进入 `stopped_blocked` 或请求用户决策，因为合入前审计是强制门。

## Finding 生命周期

每个 finding 必须有稳定 ID，格式为：

```text
<audit-id>-<category>-<three-digit-index>
```

状态：

- `open`：尚未处理。
- `planned`：Planner 已创建可追溯整改任务。
- `in_progress`：整改 child/task 正在执行。
- `resolved_pending_audit`：Evaluator 已通过整改，但 Auditor 尚未复审。
- `closed`：Auditor 复审确认已解决。
- `accepted_risk`：用户明确接受风险后关闭；必须记录用户确认证据。

关闭规则：

- `must_fix` 只能由后续 audit report 关闭，不能由 Planner 或 Evaluator 自行关闭。
- `should_fix` 可由 Planner 解释暂缓，但必须留在 backlog 或 audit report 的 `deferred_findings`。
- `observe` 可以在下一次审计中自动过期，但需要保留历史记录。
- 若相同 finding 在 2 次审计后仍未关闭，Auditor 必须升级严重度或请求用户决策，不能无限重复同一建议。

## 审计触发

### 周期性触发与自适应退避

审计节奏由 loop policy 中的 `audit_cadence` 控制。默认使用自适应退避，而不是固定每轮调用 LLM Auditor。

配置草案：

```json
{
  "audit_cadence": {
    "unit": "round",
    "mode": "adaptive_backoff",
    "min_interval": 1,
    "max_interval": 8,
    "backoff": "geometric",
    "factor": 2,
    "reset_on": ["must_fix", "should_fix", "event_trigger", "phase_transition"],
    "schedule": [1, 2, 4, 8]
  }
}
```

持久化状态：

```json
{
  "audit_cadence_state": {
    "steps_since_last_audit": 0,
    "current_interval": 1,
    "next_audit_at_step": 1,
    "total_audits": 0
  }
}
```

默认语义：

- `demand-development` 的 unit 是 passed child。
- `autonomous-knowledge` 的 unit 是 completed autonomous round。
- 审计连续 pass 时，间隔按 `factor` 增长，直到 `max_interval`。
- 出现 `must_fix`、`should_fix`、事件触发或 phase transition 时，间隔重置为 `min_interval`。
- human merge 前和 phase transition 前必须审计一次，无视 cadence。
- 示例：`min=1,max=8,factor=2` 的顺利路径审计点是第 1、3、7、15、23 步；第 7 步若出现 `should_fix`，下一次间隔重置为 1。

### 事件触发

出现以下任一情况时立即触发：

- 连续 2 次 evaluator `fail` 或 `blocked`。
- 连续 2 轮 coverage map 没有有效增长。
- 同一个 identity key、source、dirty path 或 evaluator finding 重复出现。
- 工作树出现未归属 dirty paths。
- commit 创建后没有按规则推送 `origin/main`。
- Dashboard 无法展示当前 run、child、evaluator 场景或阻塞状态。
- Planner 生成的下一步与 preflight 目标、coverage layer 或用户约束明显不一致。
- 单个局部问题消耗超过预算，疑似 tunnel vision。

事件触发优先级高于 cadence。事件触发后，无论 Auditor verdict 是否阻塞，`audit_cadence_state.current_interval` 都回到 `min_interval`，避免刚出现异常时审计过疏。

## Auditor 输入

Auditor 只读以下证据：

- `.codex/loop-runs/<run-id>/run.json`
- child run 的 `planner-output.json`、`task-contract.json`、`generator-result.json`、`evaluator-result.json`
- `events.jsonl`
- `audit-reports/*.json`
- `coverage-map.json`、`loop-state.json`
- `required-evidence-result.json`、`dirty-paths-result.json`、`commit-result.json`
- git commit 历史、当前 branch、`git status --porcelain`
- Loop Dashboard API 的 run detail
- Crawler Workbench health/source snapshot/search/wiki API
- 当前 repo 中 loop 相关 skill 清单和候选 skill 文档

Auditor 不能采信以下内容作为关键事实：

- Generator 自称“服务可用”“已推送”“已入库”的文字说明。
- 未经 orchestrator 采集或签名的 live evidence。
- 缺少 run id、task id、commit sha 或 artifact hash 绑定的证据。
- 无法在当前 repo 或 run artifact 中解析的路径。

## Auditor 输出

每次审计输出两个 artifact：

```text
<loop-runtime-root>/<run-id>/audit-reports/audit-<n>.json
<loop-runtime-root>/<run-id>/audit-reports/audit-<n>.md
```

首期 `<loop-runtime-root>` 默认为 `.codex/loop-runs`。所有代码、Dashboard 和测试必须通过统一 resolver 获取该路径，不得在新代码中散落硬编码。

JSON 契约草案：

```json
{
  "schema_version": 1,
  "run_id": "string",
  "audit_id": "audit-001",
  "created_at": "2026-07-08T00:00:00Z",
  "auditor": {
    "role": "auditor",
    "driver": "codex-exec | fake",
    "independent_from": ["planner", "generator", "evaluator"]
  },
  "provenance": {
    "payload_created_by": "auditor",
    "artifact_created_by": "harness_loop_orchestrator",
    "artifact_sha256": "",
    "input_bundle_sha256": ""
  },
  "scope": {
    "audited_child_run_ids": [],
    "audited_commits": [],
    "audited_rounds": [],
    "trigger": "periodic | event | pre_merge | phase_transition"
  },
  "deterministic_signals": {
    "artifact_path": "",
    "artifact_sha256": "",
    "summary": {
      "coverage_layers_changed": 0,
      "same_evaluator_finding_count": 0,
      "unclassified_dirty_paths": 0,
      "unpushed_commits": 0
    }
  },
  "cadence": {
    "unit": "round | passed_child",
    "steps_since_last_audit": 0,
    "current_interval": 1,
    "next_interval_after_verdict": 2
  },
  "verdict": "pass | must_fix | should_fix | observe",
  "loop_health": {
    "progressing": true,
    "stagnating": false,
    "drifting": false,
    "repeating_errors": false,
    "tunnel_vision": false,
    "skill_sprawl": false
  },
  "stagnation_findings": [],
  "drift_findings": [],
  "repeated_error_findings": [],
  "tunnel_vision_findings": [],
  "process_improvement_findings": [],
  "skill_inventory_findings": [],
  "harness_architecture_findings": [],
  "finding_lifecycle": {
    "open_findings": [],
    "planned_findings": [],
    "closed_findings": [],
    "deferred_findings": []
  },
  "direction_control": {
    "action": "continue | refocus | switch_task | stop_early | ask_user",
    "reason": "",
    "recommended_next_focus": ""
  },
  "required_planner_actions": [],
  "closed_previous_audit_findings": [],
  "evidence": {
    "artifact_paths": [],
    "dashboard_urls": [],
    "commands": []
  }
}
```

Schema 校验还必须检查：

- `verdict=must_fix` 时至少有一个 open `must_fix` finding。
- `verdict=must_fix` 时必须引用 deterministic signal artifact；纯 LLM 判断不能独立触发硬阻塞。
- `direction_control.action=ask_user` 时必须提供具体用户问题。
- artifact paths 必须解析到 loop runtime root 或 repo root 的允许读路径。
- `artifact_created_by` 必须是 `harness_loop_orchestrator`。

## 审计维度

### 空转

Auditor 判断 loop 是否在消耗轮次但没有有效产出。信号包括：

- 多轮只写 blocked evidence，没有新增 raw、wiki、代码修复、测试或 coverage。
- coverage map 连续无增长，且 Planner 仍继续生成等价任务。
- 同一 needs item 未满足重试条件却反复被探测。
- 多个 commit 只修改流程文件或日志摘要，没有推动原始目标。

高风险空转应输出 `must_fix`，要求 Planner 分流到 needs 队列、切换任务或停止。

### 偏航

Auditor 判断子任务是否偏离 preflight 目标、用户约束、coverage layer 或父需求。信号包括：

- 子任务不在 Planner 允许范围内。
- 资料拓展绕过 Domain Channels/source profiles 创建长期来源。
- 需求开发在未确认的范围内修改 crawler/frontend/backend/harness。
- Planner 使用新目标替换原目标，但没有用户确认或 phase transition 证据。

### 重复犯错

Auditor 汇总多轮 evaluator findings、dirty path、blocked source 和 repair loops。以下情况应升级：

- 同类 evaluator finding 连续出现 2 次。
- 同一 dirty path 类别反复导致 blocked。
- 同一个 source 因同一 DNS/TLS/auth/robots/rate-limit 原因被重复重试。
- 同一测试被反复修到通过又失败。

### 钻牛角尖

Auditor 判断 loop 是否过度投入局部问题，导致整体目标收益递减。典型信号：

- 同一文件、同一测试、同一 UI 细节反复修改超过阈值。
- 连续多轮都在修同类边缘问题，但核心目标没有推进。
- 为通过某个 evaluator 场景不断特化实现，而非解决真实用户需求。
- 反复增加流程文件、报告、gate，但知识或功能产出没有增长。
- 对低价值问题投入超过预算，例如纯样式微调、日志格式、命名争议。
- 修复前一轮修复引入的问题，形成 repair loop。
- 任务已达到可接受完成度，但 loop 继续追求过度完备。

Auditor 可以输出方向控制：

- `continue`：继续当前方向。
- `refocus`：继续同一任务，但重排下一轮重点，并明确哪些局部问题不再继续。
- `switch_task`：停止当前局部修复，切换到更高价值子任务。
- `stop_early`：当前任务已经足够可用，进入 final verification、commit 和 human merge gate。
- `ask_user`：方向涉及取舍，必须用户决策。

如果 `direction_control.action` 为 `refocus`、`switch_task`、`stop_early` 或 `ask_user`，且风险为 high，或连续两次出现同类 tunnel vision finding，则 Auditor 必须输出 `must_fix`。

Auditor 自身也受限制：

- 每次审计最多 5 条 findings。
- `must_fix` 最多 3 条。
- 每条 `must_fix` 必须说明如果不处理会怎样影响整体目标。
- 不允许把纯偏好、命名、格式微调升级为 `must_fix`。
- 建议终止或换方向时，必须给出当前完成度证据和剩余收益递减证据。
- 单次审计必须有预算上限：最多读取最近 10 个 child run、最近 20 个 commits、最近 5 份 evaluator result，除非用户要求深度审计。
- Auditor 不能连续两次只新增流程治理 finding 而不关闭旧 finding；否则下一次审计必须先自检是否过度审计。

### Skill 数量治理

Skill inventory 是 repo 级慢变量，不应在每次 loop 审计中强制深扫。首期把它作为周期性仓库卫生审计项，由 Auditor 在以下场景检查：

- human merge 前。
- 每完成一个治理阶段。
- 新增或修改 skill 后。
- Planner/Generator 因 skill 选择冲突、重复流程或漏执行关键流程而失败。

普通 cadence 审计只读取上一次 skill inventory 摘要，不重新扫描全部 skill。

需要统计：

- 已存在 loop/harness/wiki/crawler 相关 skill。
- 本轮新增或建议新增的 skill。
- skill 间职责重叠。
- skill 是否被实际调用过。
- skill 中哪些规则应转为 harness gate，哪些只是人工流程指导。

规则：

- 如果多个 skill 覆盖同一流程，Auditor 应建议合并。
- 如果 skill 只被使用一次且没有长期价值，建议删除或降级为 docs/checklist。
- 如果 skill 内容过大，建议拆成核心 skill + reference 文档。
- 如果 skill 与 harness gate 重叠，机器可验证部分优先放入 harness，skill 只保留人工流程指导。
- 如果某一类 loop 相关 skill 数量超过 policy 阈值，Auditor 至少输出 `should_fix`。默认阈值可从 7 开始，但必须记录在 policy 中，不能硬编码在检测器里。
- 如果 skill 膨胀导致 Planner/Generator 选择冲突、重复执行或漏执行关键流程，Auditor 输出 `must_fix`。

首批候选 skill 不应一次性全部创建。建议优先沉淀：

1. `pge-loop-agent-contract`：Planner/Generator/Evaluator/Auditor 的通用职责边界、证据委托和只读/写入规则。
2. `loop-closeout-audit`：每轮结束的 git dirty 分类、validate、commit、push、Dashboard/API/前端可见性检查。

以下候选先保留为 docs/checklist，等待复用超过阈值再 skill 化：

- blocked/needs queue 分流策略。
- 候选价值 hard gate vs advisory score。
- 改动后端到端可见性验证。

## 外部流程审视报告的采纳结果

外部 agent 提出的五类系统性缺陷基本成立，但需要调整为本仓库可落地的治理项。

### P0：拆分巨石编排文件

已核验事实：

- `scripts/harness_loop_orchestrator.py` 约 4740 行、195KB。
- 同一文件内包含 state machine、fake driver、codex driver、dirty path、commit gate、evidence gate 和 CLI。
- 状态赋值和 stop phase 逻辑分散，维护成本高。

治理方向：

- 不做一次性 big-bang rewrite。
- 先抽 `state_model` 和声明式 transition table。
- 再抽 `phase_engine`、`drivers`、`gates` 和 `test_drivers`。
- fake driver 移出生产 driver enum，首期通过 test fixtures 注入。

### P0：可信证据框架

已核验事实：

- 历史提交显示 live evidence、visibility evidence、commit evidence 曾多次出现假通过/假失败。
- 现有 trusted-live-evidence 是局部机制，还没有统一 provenance contract。

治理方向：

- 关键事实必须由 orchestrator 采集或绑定。
- Generator 不得自证服务可用、commit 已创建、推送已完成或前端可见。
- Evaluator 不跑自己能力范围外的 live probe；它验证 orchestrator 委托的 trusted artifact。
- 所有 trusted artifact 绑定 run id、task id、artifact hash、created_by 和 captured_at。

### P0：runtime artifact 与被评估工作树隔离

已核验事实：

- 当前工作树仍可能残留 `.codex/*.log`、pid、`generated/` 和临时 ingest-plan。
- 现有 dirty path 获取在 git/OSError/非零退出时返回空列表，有“失败当干净”的风险。

治理方向：

- git dirty 获取失败必须返回 explicit error，不得当作 clean。
- runtime artifact 要么移出被评估 git worktree，要么使用 canonical ignored runtime root，并在 dirty gate 中明确归类。
- Loop Dashboard 可以继续读取 runtime root，但不能要求 runtime artifact 被 git 跟踪。

### P1：共享 schema/validator source of truth

治理方向：

- `contracts.py` 继续作为 public validation API，但不要无限膨胀为第二个巨石。
- 将 run state、transition、evidence provenance、audit report、coverage map schema 分模块实现，由统一入口 re-export。
- Planner、Generator、Evaluator、Auditor、Dashboard 和 Crawler Workbench 必须 import 同一 validator。

### P1：codex-attempt 抽象

治理方向：

- 抽统一 `codex_attempt` 模块，负责进程组、原子输出、timeout、final message recovery、teardown 和 capability cache。
- 消除 planner/generator/evaluator/scenario command 中重复的 timeout 和 cleanup 实现。

### P1：持久化进度台账

治理方向：

- 不再从局部变量推导任务完成数量。
- 预算、已完成 task ids、attempt ids、accepted changed paths、audit finding 状态都从持久化 run state 派生。
- 删除或迁移 `_autonomous_completed_task_ids` 等未 schema 化内部键。

## Planner 响应审计的规则

Planner 读取最近一次 audit report 后：

- 如果 `verdict=pass`，可继续普通计划。
- 如果 `verdict=observe`，继续普通计划，但必须在 `reader_summary` 里说明已记录观察项。
- 如果 `verdict=should_fix`，必须把建议加入 backlog，并说明是否本轮处理。
- 如果 `verdict=must_fix`，必须创建整改 child/task，且 `next_child_task.title` 或 task kind 必须能追溯到 `audit_id` 和 finding id。
- 如果 `direction_control.action=stop_early`，Planner 必须进入 final verification / commit / human merge gate，而不是继续扩展 scope。
- 如果 `direction_control.action=ask_user`，Planner 必须停在 `stopped_blocked`，并明确提问。

Planner 输出必须包含 `audit_response`：

```json
{
  "audit_response": {
    "audit_id": "audit-001",
    "handled_findings": ["audit-001-tunnel-vision-001"],
    "planned_remediation_task": "child-004",
    "deferred_findings": [],
    "reason": "must_fix finding requires refocus before continuing expansion"
  }
}
```

没有 `audit_response` 的 Planner 输出不得从 `audit_blocked` 进入普通 planning。

## Dashboard 展示

Loop Dashboard 需要展示：

- 最近一次审计结论。
- 是否处于 `audit_blocked`。
- Auditor 发现的空转、偏航、重复错误、钻牛角尖和 skill 膨胀摘要。
- `direction_control.action` 和推荐下一焦点。
- `must_fix` findings 是否已有 Planner 整改任务。
- 整改任务是否通过 Evaluator。
- Auditor 复审是否关闭上一轮 finding。
- Skill inventory 数量、重复项和建议合并/删除项。

页面原则：审计内容面向不了解项目背景的第三方读者，默认显示人读摘要；JSON 只作为展开详情。

## 测试方案

实现阶段必须先写测试，再改代码。

### Unit Tests

1. Audit report schema
   - 接受合法 `pass/must_fix/should_fix/observe`。
   - 拒绝缺少 `run_id`、`audit_id`、`verdict`、`direction_control` 的报告。
   - 拒绝超过 5 条 findings 或超过 3 条 `must_fix`。
   - 拒绝 `verdict=must_fix` 但没有 open `must_fix` finding 的报告。
   - 拒绝非 orchestrator provenance 的阻塞型 audit artifact。

2. Audit trigger policy
   - adaptive cadence 在连续 pass 后按 factor 退避。
   - `must_fix`、`should_fix`、event trigger 和 phase transition 会重置到 min interval。
   - demand loop 使用 passed child 作为 unit。
   - autonomous loop 使用 completed round 作为 unit。
   - 连续 failed/blocked、coverage 无增长、重复 finding、dirty path 异常触发。

3. Hard block semantics
   - `must_fix` 让 run 进入 `audit_blocked`。
   - `audit_blocked` 时 Planner 只能创建 audit remediation task。
   - `must_fix` 未关闭时不能进入 ordinary expansion 或 human merge。
   - child run 不进入 `audit_blocked`，而是通过父 run 阻塞。
   - Planner 缺少 `audit_response` 时不能离开 `audit_blocked`。

4. Tunnel vision detection
   - 同一文件/测试连续反复修改超过阈值时，由 deterministic signal 记录计数。
   - Auditor 基于计数和目标进展判断是否生成 `refocus` 或 `stop_early`。
   - 纯格式偏好不能升级为 `must_fix`。

5. Skill inventory governance
   - policy 阈值超限或存在重复 skill 时生成 `should_fix`。
   - skill 冲突导致流程漏执行时生成 `must_fix`。
   - 可机器验证规则应建议进入 harness gate，而不是 skill。
   - 普通 cadence 审计不会重新深扫 skill inventory。

6. Trusted evidence integration
   - Generator 自产 live evidence 不能作为 pass。
   - Orchestrator trusted artifact 绑定 hash/run/task 后可被 Auditor 接受。

7. Dirty path failure handling
   - git status 报错不能返回 clean。
   - runtime artifact 被归类为 ignored runtime artifact，而不是混入任务产物。

8. Finding lifecycle
   - open -> planned -> resolved_pending_audit -> closed 的转换被接受。
   - Planner/Evaluator 不能直接关闭 `must_fix`。
   - 相同 finding 连续 2 次未关闭时升级或请求用户决策。

### E2E Tests

E2E-1：demand loop 周期审计

- 准备 parent run，触发 adaptive cadence 到期。
- Orchestrator 生成 deterministic signals，然后运行 auditor。
- 期望产生 audit report，verdict pass 时 parent 继续 planning。

E2E-2：audit must_fix 硬阻塞

- 构造重复 evaluator finding。
- Auditor 输出 `must_fix`。
- 期望 parent phase 进入 `audit_blocked`，Planner 下一步只能创建整改 child。
- 整改 child 通过 Evaluator 后，Auditor 复审关闭 finding，parent 才能继续普通 planning。

E2E-3：autonomous loop 空转制动

- 构造连续两轮 coverage 无增长、只写 blocked evidence。
- Deterministic signals 记录 coverage delta 为 0 和 repeated blocked source。
- Auditor 输出 `must_fix` + `direction_control.action=switch_task` 或 `stop_early`。
- 期望 autonomous run 不继续普通资料抓取。

E2E-4：钻牛角尖提前停止

- 构造同一 UI 文案/样式问题连续多轮修改且核心目标已达成。
- Auditor 输出 `stop_early`。
- 期望 Planner 进入 final verification / commit / human merge gate。

E2E-5：skill 膨胀治理

- policy 阈值设为 7，构造 8 个 loop 相关 skill，其中 3 个职责重叠。
- Auditor 输出 `should_fix` 或 `must_fix`，要求合并/删除。
- 期望 Dashboard 显示 skill inventory finding。

E2E-6：Dashboard 审计可读性

- 启动 Loop Dashboard。
- 验证页面能看到最近审计、阻塞原因、方向控制、整改状态和 skill inventory。

E2E-7：证据可信性

- Generator 写一个自称服务可用的 evidence。
- Orchestrator 未采集 trusted live evidence。
- Auditor 必须拒绝该证据，并输出 finding。

## 分阶段落地

### Phase 0：使能性结构约束

- 抽最小 transition table 或 phase transition helper，停止继续散落新增 audit phase 字符串赋值。
- 定义统一 provenance contract，至少覆盖 audit artifact、trusted live evidence 和 deterministic signal artifact。
- 修正 git dirty failure semantics：git status 失败返回 explicit error，不得当作 clean。
- 新增 loop runtime root resolver，Dashboard 和 harness 通过 resolver 读取 `.codex/loop-runs`。

### Phase 1：确定性信号和只读审计报告

- 新增 deterministic audit signals schema。
- 新增 audit report schema。
- 新增 `run-audit` CLI。
- 读取 run artifacts，先由 orchestrator 计算 deterministic signals，再交给 Auditor agent 解读。
- Dashboard 展示最近审计。
- 不改变现有 loop 调度。
- 不宣称具备硬阻塞能力；该阶段只能作为观察和 UI 验证。

### Phase 2：内联硬闸门接入状态机

- 新增 `audit_pending/auditing/audit_passed/audit_blocked` phase。
- phase pump 内联检查 open `must_fix` finding；不要求 LLM Auditor 每轮在线。
- Planner 必须响应 `must_fix`。
- human merge 前必须 audit pass。
- 实现 finding lifecycle 和 `audit_response`。
- 确认 child run 不直接进入 `audit_blocked`。

### Phase 3：自适应审计节奏

- 将 `audit_cadence` 和 `audit_cadence_state` 接入 policy/run state。
- 实现 adaptive backoff、event trigger reset 和 phase transition reset。
- human merge / phase transition 前强制审计。

### Phase 4：反空转/反偏航/反钻牛角尖规则

- 实现 stagnation/drift/repeated-error/tunnel-vision detectors。
- 接入 coverage map、evaluator findings、dirty path、commit history。

### Phase 5：Skill inventory governance

- 作为周期性仓库卫生审计扫描可用 skill。
- 建立 loop 相关 skill registry。
- 输出合并、降级、删除建议。

### Phase 6：Harness 结构性债务治理

- 拆 state model 和 transition table。
- 抽 trusted evidence framework。
- 修正 git dirty failure semantics。
- 抽 codex-attempt。
- fake driver 移出生产路径。

## 成功标准

- 多轮 loop 不再只依赖单轮 Evaluator 判断是否继续。
- `must_fix` 审计建议能硬阻塞普通下一轮。
- Planner 能自动创建审计整改任务并在复审后关闭 finding。
- Dashboard 能让第三方读懂 loop 是否健康、是否空转、是否偏航、是否钻牛角尖。
- Skill 数量和职责保持受控，不因流程沉淀造成 skill 膨胀。
- harness 结构性债务被纳入持续治理，而不是继续通过零散闸门补丁处理。
