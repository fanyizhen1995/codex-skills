# Planner Generator Evaluator Loop 设计

日期：2026-07-02

## 背景

本项目已经有较完整的 evaluator harness：`tasks.json` 记录任务与验证命令，`docs/harness/evaluator-scenarios/` 记录用户场景契约，`scripts/harness_evaluator_orchestrator.py` 可以通过 `codex-exec` 运行只读 evaluator，并把结果写入 `.codex/evaluations/` bundle。

当前缺口不是 evaluator，而是外层自动化工作流：如何从一个需求进入规划，如何把规划交给实现者，如何把 evaluator findings 回灌给实现者，以及在适合自动化的知识入库场景中，如何让 planner 在一轮通过后继续规划下一轮。

参考 Anthropic harness 设计思路和 `loop-engineering` 的 loop engineering 实践，本项目将把单次 agent 执行提升为可审计、可恢复、可停止的 Planner → Generator → Evaluator 循环。

## 目标

实现两类 loop：

1. **需求驱动单任务闭环**：`Planner → Generator → Evaluator`
   - 用于新功能、bugfix、前端优化、harness 开发等。
   - 通过 evaluator 后产出 commit。
   - 合入 `main` 前必须等待人工确认。

2. **持续规划自治闭环**：`Planner → Generator → Evaluator → Planner`
   - 用于 wiki 资料拓展、定期抓取、资料整理、领域知识补全等。
   - evaluator 通过后，Planner 读取最新仓库和 wiki 状态继续拆分下一项任务。
   - 只允许在明确 allowlist 范围内自动提交。
   - 终止目标是“无可行动缺口”，而不是固定 commit 数、页面数或抓取批次数。

## 非目标

- 不替换现有 `tasks.json`、`progress.md`、evaluator bundle 和 crawler/wiki 验证流程。
- 不让同一个 agent 同时承担规划、实现和验收。
- 不默认自动合入 `main`。
- 不允许自动修改 secrets、凭据、生产基础设施、认证、支付、账单等高风险路径。
- 不在需求未讨论清楚时直接生成任务和进入自动开发。
- 不把 autonomous knowledge loop 扩展成全仓库无人值守开发；它可以为了资料拓展自动修改 crawler、crawler workbench 后端/前端和相关测试，但仍必须受 allowlist、denylist、重试上限、artifact hygiene 和 evaluator gate 约束。

## 角色模型

### loop_orchestrator

`loop_orchestrator` 是状态机执行器，不承担智能开发判断。

职责：

- 读取和写入 `.codex/loop-runs/<run-id>/run.json`。
- 调用 Planner、Generator、Evaluator。
- 根据 evaluator 结果决定 repair、stop、human gate 或继续规划。
- 写入 `loop-run-log.md`。
- 执行 path allowlist、denylist、attempt、budget、wall time 等硬约束。

### planner_agent

Planner 负责把意图变成可执行任务，不做业务实现。

输入：

- 用户需求，或 autonomous loop 的当前 wiki/source 状态。
- `AGENTS.md`、`LOOP.md`、`tasks.json`、`progress.md`。
- 最近的 `loop-run-log.md`。
- 相关 wiki/source manifest/search 状态。
- 领域级 loop state，例如 `personal-wiki/domains/<domain>/loop-state.json`。
- preflight 讨论结果。

输出：

- `tasks.json` 任务条目或候选任务条目。
- `docs/harness/evaluator-scenarios/<task-id>.json`。
- `.codex/loop-runs/<run-id>/planner-output.json`。
- `.codex/loop-runs/<run-id>/generator-prompt.md`。
- verify command 列表。
- stop condition 和下一轮 planning hint。

Planner 决策：

- loop policy 是 `demand_development` 还是 `autonomous_knowledge`。
- 是否创建新任务，还是继续已有任务。
- 任务 scope、allowlist、denylist、验证命令。
- evaluator 必须模拟哪些用户行为。
- autonomous loop 是否继续规划下一项。
- 如果下一项需要修改 crawler、crawler workbench 后端/前端或相关测试，Planner 可以在 `autonomous_knowledge` 内生成 `autonomous_implementation_task`，并继续自动执行。
- 如果下一项触碰 denylist、生产基础设施、凭据、认证、支付、账单，或超出 autonomous allowlist，Planner 必须停止并升级给用户。

### generator_agent

Generator 负责按 Planner 的任务契约实现和修复。

输入：

- `generator-prompt.md`。
- `planner-output.json`。
- `tasks.json` 任务定义。
- 修复轮次中的 evaluator `result.json` 和 `summary.md`。

行为：

- 在隔离 worktree 或明确 baseline 下工作。
- 只修改任务允许的路径。
- 运行任务 verify command。
- 写入实现结果和验证证据。
- 可以生成 commit，但不能判定最终完成。
- 在 `demand_development` 中不能自动合入 `main`。
- 在 `autonomous_knowledge` 中，仅当所有路径都在 allowlist 且 evaluator pass 后，才允许自动提交。

输出：

- git diff 或 commit。
- verification logs。
- `.codex/loop-runs/<run-id>/generator-result.json`。
- 必要的 `progress.md` 或 `loop-run-log.md` 更新。

### evaluator_agent

Evaluator 独立验收，不修代码。

输入：

- evaluator bundle `input.json`。
- `artifacts.json`。
- verify logs。
- UI/e2e artifacts。
- git diff 或 committed paths。

行为：

- 复用 `scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver codex-exec`。
- 对 crawler/wiki/frontend 任务必须像用户一样模拟点击或 API 查询。
- 对 wiki 入库任务必须检查 raw evidence、wiki page、search/API/UI 可见性。
- 不允许仅根据 Generator 自述判定 pass。
- `blocked` 不能当作 pass。

输出：

```json
{
  "status": "pass | fail | blocked",
  "findings": [],
  "scenario_results": [],
  "next_action": "repair_and_reevaluate | proceed_to_human_merge | continue_planning | stop"
}
```

## Preflight 讨论门

在任何需求进入正式 loop 前，必须先进入 preflight 讨论门：

```text
user requirement
  -> planner_preflight_discussion
  -> user says "讨论清楚 / 确认进入 loop"
  -> Planner writes task/spec/scenario/verify
  -> Generator
  -> Evaluator
```

Preflight 必须确认：

- **目的**：这次 loop 要解决什么问题，成功后应看到什么产物。
- **约束**：哪些路径能改，哪些不能改；是否允许联网、抓取、写 wiki、写代码、重启服务、自动 commit。
- **停止条件**：什么时候算完成，最多跑几轮，遇到网络、鉴权、脏工作区、验证失败时如何停。
- **领域状态契约**：如果是 `autonomous_knowledge`，必须和用户确认 `loop-state.json` 的领域目标、扫描范围、来源清单、资料缺口字段，以及“无可行动缺口”的判定标准。

`grill-me` 接入要求：

- 如果 `grill-me` skill 已安装，Planner Preflight 必须调用它来追问目的、约束、停止条件。
- 如果未安装，实现阶段先尝试安装。
- 如果安装不可用，loop runner 使用内置 `preflight_questionnaire` fallback，并在 run artifact 中标记 `grill_me_unavailable=true`。
- 只有用户明确说“讨论清楚 / 确认 / 进入 loop”后，Planner 才允许写 `tasks.json`、scenario 和 generator prompt。
- 在新 session 中，用户一句“进入 Planner loop”足以启动 preflight；如果缺少 mode、allowlist、max tasks 或停止条件，不能执行，只能继续追问。
- `grill-me` 是交互式讨论能力，不假设存在 headless CLI。headless orchestrator 只能调用 fallback questionnaire，或把待讨论问题写入 `preflight.md` 等待用户答复。

Fallback questionnaire 的最小问题集：

1. 本次 loop 的目标产物是什么？
2. 这是 `demand_development`、`autonomous_knowledge`，还是需要由 Planner 判断？
3. 哪些路径允许修改，哪些路径必须禁止修改？
4. 是否允许联网、抓取外部内容、调用 GitHub/API、重启本地服务？
5. 是否允许自动 commit？是否允许合入 `main`？
6. 最多允许多少任务、多少修复轮次、多少 evaluator 轮次、多少运行时间？
7. 遇到鉴权、网络失败、脏工作区、非 allowlist 路径、代码改动需求时如何继续、停止或升级？
8. 如果是 `autonomous_knowledge`，`loop-state.json` 需要追踪哪些领域目标、来源、资料缺口、候选 backlog、blocked item 和 no-action 证据？
9. 如果是 `autonomous_knowledge`，什么证据足以证明“无可行动缺口”？扫描 TTL、来源覆盖、blocked/auth 项是否计入缺口？
10. 用户是否明确说“讨论清楚 / 确认进入 loop”？

## 状态与产物

新增状态和产物不替代现有 harness，而是串联现有 harness。

```text
LOOP.md
  项目级 loop 说明：有哪些 loop、cadence、权限、allowlist、human gate。

loop-run-log.md
  追加式运行日志：每次 planner/generator/evaluator 做了什么、结果是什么。

.codex/loop-runs/<run-id>/
  run.json
  preflight.md
  planner-output.json
  generator-prompt.md
  generator-result.json
  evaluator-summary.md
  repair-prompt.md

docs/harness/loop-policies/
  demand-development.json
  autonomous-knowledge.json

docs/harness/evaluator-scenarios/<task-id>.json
  继续使用现有 evaluator 场景契约。

tasks.json
  继续作为正式任务注册表。

personal-wiki/domains/<domain>/loop-state.json
  autonomous knowledge loop 的领域状态：资料缺口、已处理来源、候选下一步、无可行动缺口判断证据。
```

机器可读 policy id 统一使用 `demand_development` 和 `autonomous_knowledge`。文件名和 CLI 参数可以接受 `demand-development`、`autonomous-knowledge` 作为别名，但进入 `run.json`、`planner-output.json` 和 evaluator metadata 前必须规范化为下划线形式。

事实来源划分：

- `tasks.json` 是“任务是否存在、如何验证”的事实来源。
- `.codex/loop-runs/` 是“某次 loop 怎么跑”的事实来源。
- `docs/harness/evaluator-scenarios/` 是“用户视角怎么验收”的事实来源。
- `loop-run-log.md` 是给人看的审计记录。
- `LOOP.md` 是长期运行规则。
- `personal-wiki/domains/<domain>/loop-state.json` 是某个知识领域持续规划的事实来源。

## 结构化契约

所有 JSON 产物必须有 schema 校验。首期可以用 Python 标准库校验必填字段，后续再独立 JSON Schema 文件。

`run.json` 必填字段：

```json
{
  "run_id": "string",
  "policy": "demand_development | autonomous_knowledge",
  "phase": "preflight | planned | generating | verifying | evaluating | repair_needed | artifact_hygiene | cleanup | passed_waiting_human_merge | planning | committed | stopped_no_action | stopped_budget | stopped_blocked",
  "task_id": "string",
  "domain": "string",
  "branch": "string",
  "worktree": "string",
  "baseline_dirty_paths": [],
  "allowed_paths": [],
  "denylist_paths": [],
  "attempts": {
    "planner": 0,
    "generator": 0,
    "evaluator": 0,
    "artifact_hygiene": 0,
    "cleanup": 0
  },
  "limits": {
    "max_tasks_per_run": 3,
    "max_generator_attempts_per_task": 2,
    "max_eval_attempts_per_task": 3,
    "max_wall_time_minutes": 60,
    "agent_timeout_minutes": 30,
    "cleanup_retention_days": 7
  },
  "last_result": "pass | fail | blocked | none",
  "next_action": "string",
  "attempt_history": [],
  "cleanup": {
    "worktrees_removed": [],
    "processes_stopped": [],
    "retained_artifacts": []
  }
}
```

`planner-output.json` 必填字段：

```json
{
  "task_id": "string",
  "policy": "demand_development | autonomous_knowledge",
  "task_kind": "registered_task | candidate_task | task_contract_only | autonomous_implementation_task",
  "title": "string",
  "goal": "string",
  "non_goals": [],
  "allowed_paths": [],
  "denylist_paths": [],
  "verify_commands": [],
  "evaluator_scenarios_path": "string",
  "stop_conditions": [],
  "next_planning_hint": "string"
}
```

`generator-result.json` 必填字段：

```json
{
  "task_id": "string",
  "status": "implemented | repaired | blocked | failed",
  "changed_paths": [],
  "commit": "string",
  "verify_commands": [],
  "verify_results": [],
  "artifacts": [],
  "cleanup_required": true,
  "notes": "string"
}
```

`agent-attempt.json` 必填字段：

```json
{
  "run_id": "string",
  "role": "planner | generator | evaluator",
  "attempt": 1,
  "started_at": "ISO-8601 timestamp",
  "finished_at": "ISO-8601 timestamp",
  "exit_code": 0,
  "status": "pass | fail | blocked | timeout | invalid_json",
  "prompt_path": "string",
  "stdout_path": "string",
  "stderr_path": "string",
  "output_json_path": "string",
  "diff_patch_path": "string",
  "verify_log_paths": []
}
```

`artifact-hygiene-result.json` 必填字段：

```json
{
  "status": "pass | redacted | blocked",
  "scanned_paths": [],
  "redacted_paths": [],
  "omitted_paths": [],
  "manifest_path": "string",
  "redaction_manifest_path": "string",
  "original_hashes": {},
  "redaction_map": [],
  "findings": []
}
```

`loop-state.json` 必填字段：

```json
{
  "domain": "string",
  "domain_goal": "string",
  "last_scan_at": "ISO-8601 timestamp",
  "next_scan_after": "ISO-8601 timestamp",
  "scan_ttl_days": 30,
  "known_sources": [],
  "coverage_gaps": [],
  "candidate_backlog": [],
  "processed_items": [],
  "blocked_items": [],
  "no_action_evidence": [],
  "last_planner_decision": "planned | no_action | blocked | failed",
  "stop_reason": "string"
}
```

`coverage_gaps`、`candidate_backlog`、`processed_items` 和 `blocked_items` 条目必须至少包含 `id`、`title`、`source`、`status`、`updated_at` 和 `evidence`。`blocked_items` 还必须包含 `blocked_reason`、`required_human_input`、`retry_after`、`retry_count`、`last_error` 和 `requires_user_input`。

“无可行动缺口”的最低判定标准：

- 这些标准必须在 preflight 阶段与用户确认；Planner 只能在用户确认过的领域目标和扫描范围内判定 no-action。
- `candidate_backlog` 为空。
- `coverage_gaps` 为空，或剩余 gap 全部有明确 `blocked_reason`。
- `last_scan_at` 未超过 `scan_ttl_days`。
- `known_sources` 中本轮 scope 内的来源都已扫描或记录了不可连接原因。
- `no_action_evidence` 至少包含本轮 Planner 扫描摘要、来源列表、查询条件和验证命令结果。
- 如果存在 `blocked_auth`、凭据缺失、denylist 命中或需要用户授权的来源，该来源必须进入 `blocked_items`，不能归类为“无可行动缺口”的证据。
- 单个来源 blocked 不应停止整个 autonomous loop；Planner 应继续处理其它 `candidate_backlog` 或 `coverage_gaps`。只有所有剩余工作都被 blocked，或 blocked item 触碰 denylist/凭据/生产权限，才进入 `stopped_blocked`。

Policy JSON 必填字段：

```json
{
  "policy": "demand_development | autonomous_knowledge",
  "auto_commit": true,
  "auto_merge_main": false,
  "allowed_paths": [],
  "manual_confirm_paths": [],
  "denylist_paths": [],
  "limits": {},
  "required_evidence": []
}
```

### Candidate Task 与 Registered Task

Planner 在 preflight 后可以先生成 `candidate_task`，写入 `.codex/loop-runs/<run-id>/planner-output.json`。只有满足以下条件时才写入 `tasks.json` 成为 `registered_task`：

- demand development 已经通过 preflight，且用户确认进入 loop。
- autonomous knowledge 的本轮任务确实需要长期进入项目任务列表，而不是一次性资料拓展或自动修复。
- evaluator 需要任务契约时，orchestrator 优先为 autonomous knowledge 生成临时 task metadata，放在 `.codex/loop-runs/<run-id>/task-contract.json`，不自动修改 `tasks.json`。

如果 autonomous knowledge 规划出的下一步需要修改 crawler、crawler workbench 后端/前端或相关测试，Planner 输出 `task_kind=autonomous_implementation_task`，仍停留在 autonomous mode 内执行。只有当改动超出 allowlist、触碰 denylist、需要用户凭据或需要生产基础设施动作时，才停止并升级给用户。

### Task Contract 与 Evaluator CLI

现有 evaluator CLI 需要支持临时 `task-contract.json`：

```bash
python3 scripts/harness_evaluator_cli.py prepare-task \
  --repo-root "$PWD" \
  --task-contract .codex/loop-runs/<run-id>/task-contract.json \
  --attempt <n>
```

`task-contract.json` 必填字段：

```json
{
  "task_id": "string",
  "title": "string",
  "description": "string",
  "verify_commands": [],
  "scenario_commands": [],
  "artifact_paths": [],
  "required_services": [],
  "evaluator_driver": "harness_auto_gate | wiki_crawler_e2e | playwright_live | custom",
  "eval_policy": {},
  "allowed_scope": "string",
  "must_simulate": true,
  "user_scenarios": []
}
```

当 `--task-contract` 存在时，`prepare-task` 从该文件读取 task definition、verify commands、scenario commands、artifact paths、required services、eval policy 和 user scenarios，不再要求任务已经存在于 `tasks.json` 或 `docs/harness/evaluator-scenarios/<task-id>.json`。这让 autonomous loop 可以完成一次性资料拓展、自动修复和验证，而不污染长期任务注册表。

`scenario_commands` 由 evaluator orchestrator 在 LLM 判定前执行，用于 Playwright、wiki crawler e2e、API health check 或专用验证脚本。命令输出写入 `artifacts.json`，LLM evaluator 只能把这些 artifacts 作为主要证据，不能只根据自然语言场景判定通过。

## Agent 调用、重试与清理

首期 Planner 和 Generator 均由 orchestrator 通过 `codex exec` 启动。Evaluator 继续复用现有 `harness_evaluator_orchestrator.py run-task-auto-gate --driver codex-exec`。

Planner 调用约定：

```bash
codex exec --json --output-last-message .codex/loop-runs/<run-id>/planner-message.json \
  "$(cat .codex/loop-runs/<run-id>/planner-prompt.md)"
```

Generator 调用约定：

```bash
codex exec --json --output-last-message .codex/loop-runs/<run-id>/generator-message.json \
  "$(cat .codex/loop-runs/<run-id>/generator-prompt.md)"
```

约束：

- Planner 必须写出 `planner-output.json`，Generator 必须写出 `generator-result.json`。
- stdout 只作为诊断信息，不作为状态事实来源。
- 非 0 退出码、超时、缺少 JSON、JSON schema 校验失败，都视为 `blocked` 或 `failed_attempt`。
- 每次失败尝试必须保留 prompt、stdout/stderr、diff summary、verify logs 和退出码。
- Generator 每次尝试使用隔离 worktree，例如 `.worktrees/<run-id>-attempt-<n>`。
- repair 重试前，orchestrator 必须先保存失败尝试的 diff patch 和日志，再清理或重建 worktree。
- 成功 commit 后，orchestrator 清理临时 worktree、停止临时 backend/frontend/evaluator 进程，并在 `run.json` 记录 cleanup 结果。
- 如果进程中断，下一次 `run --run-id` 必须能根据 `run.json` 执行 cleanup 或恢复到最近可重试阶段。

## 状态机

### Demand Loop

```text
preflight
  -> planned
  -> generating
  -> verifying
  -> evaluating
  -> repair_needed -> generating
  -> passed_waiting_human_merge
  -> merged_or_closed
```

结果处理：

- `pass`：停止在 `passed_waiting_human_merge`，等待人工确认合入。
- `fail`：把 findings 变成 `repair-prompt.md`，回到 Generator。
- `blocked`：Planner 判断是否能重新规划；不能则升级给用户。
- 超过最大 attempts：停止并记录 human inbox。

### Autonomous Knowledge Loop

```text
preflight
  -> planning
  -> generating
  -> evaluating
  -> artifact_hygiene
  -> committed
  -> cleanup
  -> planning
  -> stopped_no_action | stopped_budget | stopped_blocked
```

结果处理：

- `pass`：如果 changed paths 全部在 allowlist 内，自动 commit，记录日志，回到 Planner。
- `fail`：最多修复指定轮次；仍失败则停止。
- `blocked_network`：记录 URL、错误、重试次数，不无限重试。
- `blocked_auth`：记录所需 token/scope 到 `blocked_items`，继续处理其它来源；如果所有剩余项都 blocked，才停止等待用户。
- `blocked_scope`：Planner 可拆小任务；仍触碰非 allowlist 则停止。
- `artifact_hygiene_failed`：尝试 redaction；redaction 成功则继续提交，redaction 失败则停止。
- `dirty_baseline`：如果不是本轮创建的路径，停止并让用户确认。

## 安全策略

### demand_development

- Planner 自动建任务和场景。
- Generator 自动开发并提交到任务分支或 worktree。
- Evaluator 自动验证。
- 通过后等待人工确认合入 `main`。

### autonomous_knowledge

允许自动提交的路径：

```text
personal-wiki/domains/**/raw/**
personal-wiki/domains/**/wiki/**
personal-wiki/domains/**/sources/**
personal-wiki/domains/**/data/**
personal-wiki/apps/crawler_workbench/**
scripts/*crawl*.py
scripts/*crawler*.py
scripts/compute_*.py
scripts/github_*.py
scripts/wiki_*.py
scripts/tests/test_*crawl*.py
scripts/tests/test_*crawler*.py
scripts/tests/test_compute_*.py
scripts/tests/test_github_*.py
package*.json
requirements*.txt
.codex/loop-runs/**
.codex/evaluations/**
loop-run-log.md
progress.md
personal-wiki/domains/**/loop-state.json
```

仍需停止并升级给用户的路径：

```text
docs/harness/**
tasks.json
AGENTS.md
LOOP.md
pyproject.toml
```

说明：`tasks.json` 对 autonomous loop 是关键元数据。Autonomous loop 默认用 `task-contract.json`，不自动修改 `tasks.json`。如果确实要把某个自动任务升级为长期任务注册表条目，必须由 Planner 显式生成 candidate patch，并通过 evaluator 验证后才允许提交。

`package*.json` 和 `requirements*.txt` 允许 autonomous loop 修改，但必须满足额外供应链检查：

- Planner 必须说明为什么需要新增或升级依赖，且该依赖是完成资料抓取、解析、验证或 UI 展示所必需。
- 只能新增直接依赖，不能批量升级无关依赖。
- 必须运行对应 lockfile/安装验证、backend/frontend 测试和相关 evaluator scenario。
- 必须记录依赖来源、版本、许可证摘要和已知风险检查结果。
- 如果依赖安装失败、许可证不可接受、来源不可信、或风险检查无法完成，则停止并升级给用户。

`.codex/loop-runs/**` 和 `.codex/evaluations/**` 需要保留在 git 中作为审计证据，但提交前必须做 artifact hygiene：

- 单文件大小超过阈值时，用 manifest 记录文件路径、大小、hash 和本地保留位置，默认不直接提交原文件；默认阈值 5 MiB。
- 总 artifact 大小超过阈值时，只提交 summary/manifest/result/scenario evidence；默认阈值 50 MiB。
- 扫描 token、secret、cookie、authorization header、private key 关键词。
- 文本文件命中敏感模式时先 redaction，再提交 redacted 文件；原始文件只保留本地并在 manifest 中记录 hash，不入 git。
- 二进制文件命中敏感模式或无法扫描时，不提交原文件，只提交 manifest。
- redacted artifact 必须同时写出 `redaction-manifest.json`，包含原始文件 hash、redacted 文件 hash、redaction 规则 id、字段路径或行号范围、处理原因和不可逆处理说明。
- evaluator result 和 summary 必须标注引用的是原始本地 artifact 还是 redacted artifact；git 中的审计证据以 redacted artifact 和 manifest 为准，本地复现以 manifest hash 校验原始 artifact。
- 默认提交 summary、manifest、result、scenario evidence；大型截图、trace、HTML report 可记录路径和 hash，是否入 git 由 policy 决定。
- 如果 redaction 或 manifest 生成失败，即使 evaluator pass 也不能自动 commit。

### denylist

任何 loop 都不能自动修改：

```text
.env
.env.*
**/secrets/**
**/credentials/**
**/*token*
**/*secret*
**/*key*
**/auth/**
**/billing/**
**/payments/**
.terraform/**
k8s/production/**
```

触碰这些路径直接 `blocked` 并升级给用户。

## Baseline 与提交规则

loop 开始时必须记录 baseline：

- 当前分支。
- 当前 worktree 路径。
- `git status --porcelain`。
- 已存在 dirty paths。

提交规则：

- Demand Loop：只提交任务归属文件，不自动合入 `main`。
- Autonomous Knowledge Loop：只有所有 changed paths 都在 allowlist，evaluator pass，wiki validate pass，才允许自动 commit。
- `.codex/loop-runs/**` 和 `.codex/evaluations/**` 只有通过 artifact hygiene 后才允许自动 commit。
- 如果 baseline 已经 dirty，loop 只能提交本轮创建或明确归属的文件。
- 如果发现 baseline dirty paths 超出任务范围，停止并记录错误，避免再次出现 “baseline dirty paths include files outside task”。

commit message 示例：

```text
feat(harness): add planner generator evaluator loop
docs(wiki): ingest ai infra source batch
chore(loop): record autonomous knowledge run
```

## 停止条件

Autonomous Loop 每轮 Planner 必须检查：

- `max_tasks_per_run` 达到。
- `max_tokens_per_run` 达到。
- `max_wall_time_minutes` 达到。
- 连续 no-action 次数达到。
- 连续 fail/blocked 次数达到。
- 遇到鉴权、无法 redaction 的敏感 artifact、非 allowlist 代码路径或 denylist 路径。
- 涉及非 allowlist 路径。
- 所有剩余 `candidate_backlog` 和 `coverage_gaps` 都处于 blocked，且没有可处理的其它来源。
- 领域 `loop-state.json` 判定当前目标已达到“无可行动缺口”。

建议默认值：

```json
{
  "max_tasks_per_run": 3,
  "max_generator_attempts_per_task": 2,
  "max_eval_attempts_per_task": 3,
  "max_wall_time_minutes": 60,
  "max_no_action_rounds": 1,
  "agent_timeout_minutes": 30,
  "cleanup_retention_days": 7
}
```

## CLI 与 Workflow 入口

新增统一入口：

```bash
python3 scripts/harness_loop_orchestrator.py preflight \
  --mode demand-development \
  --requirement "..."

python3 scripts/harness_loop_orchestrator.py run \
  --run-id <run-id>

python3 scripts/harness_loop_orchestrator.py run-autonomous \
  --policy autonomous-knowledge \
  --domain ai_infra \
  --max-tasks 3
```

阶段：

```text
preflight
  - 调 grill-me 或 fallback questionnaire
  - 写 .codex/loop-runs/<run-id>/preflight.md
  - 等用户确认进入 loop

plan
  - 通过 codex exec 启动 planner_agent
  - 写 planner-output.json
  - 写 candidate task 或 registered task
  - 写 scenario、verify contract 或临时 task-contract.json

generate
  - 创建隔离 worktree
  - 通过 codex exec 启动 generator_agent
  - 运行 verify
  - 写 generator-result.json

evaluate
  - 调现有 harness_evaluator_orchestrator.py run-task-auto-gate
  - 读取 result.json 和 summary.md

decide
  - fail: 生成 repair-prompt.md 回到 generate
  - blocked: 记录 human inbox
  - pass + demand: 停在 waiting_human_merge
  - pass + autonomous: artifact hygiene 后自动 commit allowlist 内容，然后 cleanup，再回到 plan
```

## 与现有 Harness 的关系

继续复用：

```text
tasks.json
docs/harness/evaluator-scenarios/*.json
scripts/harness_evaluator_cli.py
scripts/harness_evaluator_orchestrator.py
scripts/wiki_crawler_e2e_evaluator.py
```

新增：

```text
LOOP.md
loop-run-log.md
docs/harness/loop-policies/*.json
scripts/harness_loop_orchestrator.py
scripts/harness_planner_agent.py
scripts/harness_generator_agent.py
docs/harness/planner-generator-evaluator-loop.md
```

## 新 Session 使用方式

用户可以在新 session 中这样下发：

```text
进入 Planner loop。
```

这句话足以启动 preflight，但不足以直接执行。Planner 必须继续追问目的、约束和停止条件，直到用户明确确认进入 loop。

更完整的下发方式：

```text
进入 Planner loop。模式：demand-development。
需求：给 crawler workbench 增加 GitHub issue 查询页面。
合入 main 前需要我确认。
```

或：

```text
进入 Planner loop。模式：autonomous-knowledge。
需求：持续拓展 ai_infra wiki 中 GPU/NPU/TPU 资料。
允许自动改 personal-wiki/domains/** 下的 raw/wiki/sources/data，以及 crawler workbench、crawler 脚本、相关测试和必要依赖；仍受 denylist、供应链检查和 evaluator gate 约束。
每轮最多 3 个任务，通过 evaluator 后自动 commit 并继续规划。
```

新 session 中，loop runner 通过 `LOOP.md`、`tasks.json`、`.codex/loop-runs/`、`loop-run-log.md` 和领域 `loop-state.json` 恢复上下文，不依赖旧聊天记录。

## 首期实现范围

实现按阶段推进，不要求一次性完成全部 autonomous 能力。

### Phase 1

1. 实现 preflight 讨论门和 `grill-me` fallback。
2. 实现 JSON contract 校验、run 目录、`run.json`、`planner-output.json`、`generator-result.json`。
3. 实现 `demand-development` 单任务闭环骨架。
4. 接入 `codex exec` Planner/Generator agent wrapper 的最小可运行路径。
5. 接入现有 evaluator gate，并能把 fail findings 回灌给 Generator。
6. 通过 evaluator 后停在 human merge gate。

### Phase 2

1. 扩展 evaluator CLI 支持 `task-contract.json`。
2. 增加 `scenario_commands`、required services、artifacts 采集。
3. 增加失败重试、attempt 证据保存、临时 worktree cleanup 和中断恢复。
4. 增加 artifact hygiene、redaction 和 redaction manifest。

### Phase 3

1. 实现 `autonomous-knowledge` policy。
2. 增加领域 `loop-state.json` 和“无可行动缺口”判定。
3. 允许 wiki/raw/sources/data、crawler workbench、crawler 脚本、相关测试和必要依赖在 auto mode 内自动修改。
4. 为 autonomous dependency changes 增加供应链检查。
5. 后续再接 crawler workbench UI，展示 loop run、状态、日志和 evaluator 结果。

## 验收标准

- 能从一个需求生成 task/spec/scenario/verify。
- 能启动 generator agent 完成实现或修复。
- 能自动运行 evaluator。
- evaluator fail 时能进入 repair。
- evaluator pass 后，Demand Loop 停在 human merge gate。
- Autonomous Knowledge Loop 能在 pass 后自动 commit 并继续规划下一项。
- Autonomous Knowledge Loop 能在领域 `loop-state.json` 中记录资料缺口，并在“无可行动缺口”时停止。
- Autonomous Knowledge Loop 的 `loop-state.json` schema 和“无可行动缺口”判定标准必须在 preflight 阶段与用户确认。
- Autonomous Knowledge Loop 发现需要 crawler、crawler workbench 后端/前端或相关测试改动时，能在 auto mode 内自动实现、验证、redaction、提交。
- Autonomous Knowledge Loop 修改 `package*.json` 或 `requirements*.txt` 时必须通过供应链检查、安装验证和相关 evaluator scenario。
- `.codex` artifacts 通过大小和敏感信息扫描；敏感文本 redaction 后继续提交，无法 redaction 的原始 artifact 不入 git。
- Redacted artifact 必须有原始 hash、redacted hash 和 redaction manifest，evaluator summary 必须说明引用的是原始还是 redacted 证据。
- `task-contract.json` 支持 `scenario_commands`，并能把命令输出纳入 evaluator artifacts。
- 单个 blocked source 不会停止整个 autonomous loop；Planner 会继续处理其它来源，直到无可处理项或达到停止条件。
- Planner/Generator `codex exec` 失败、超时、JSON 无效时能按 attempt 规则重试并清理临时 worktree/进程。
- dirty baseline、denylist、max attempts 能正确停止。
- `loop-run-log.md` 和 `.codex/loop-runs/<run-id>/` 有完整证据。

## 风险与缓解

- **Planner 过度拆任务**：preflight 必须明确目标和停止条件；Planner 输出要包含 non-goals。
- **Generator 修改无关文件**：baseline + allowlist + evaluator scope check 双重限制。
- **Evaluator 只看自述不做验证**：继续使用 scenario-first evaluator contract，必须有 evidence。
- **Autonomous loop 无限跑**：max tasks、max attempts、max wall time、no-action stop 必须硬编码。
- **知识入库自动提交错误内容**：只允许 allowlist 内改动，且必须通过 wiki validate、search/API/UI 可见性检查。
- **Autonomous code 改动扩大范围**：crawler workbench 和 crawler 脚本相关路径可自动改；denylist、生产基础设施、凭据、认证、支付、账单仍阻断。
- **依赖供应链风险**：允许 autonomous 修改 `package*.json` 和 `requirements*.txt`，但必须有必要性说明、安装验证、测试、许可证和风险检查。
- **`.codex` artifacts 泄露敏感信息或过大**：提交前执行 artifact hygiene；敏感文本 redaction 后继续提交，无法处理的原始 artifact 不入 git。
- **Redaction 破坏证据链**：提交 redacted artifact 时必须保留原始 hash、redacted hash 和 redaction manifest；summary 必须说明证据引用关系。
- **`tasks.json` 成为 autonomous loop 阻塞点**：区分 candidate task、registered task 和临时 task contract；autonomous 默认使用 `task-contract.json`。
- **单个 blocked source 卡住整个领域**：blocked source 进入 `blocked_items`，Planner 继续处理其它来源；只有所有剩余项 blocked 或触碰硬边界才停止。
- **失败尝试堆积 worktree 或进程**：每次 retry 前保存证据并重建 worktree；pass、blocked 或中断恢复时执行 cleanup。
- **grill-me 不可用**：使用 fallback questionnaire，并在 run artifact 中记录。
