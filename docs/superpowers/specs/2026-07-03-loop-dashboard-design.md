# Loop Dashboard 设计

日期：2026-07-03

## 背景

Planner Generator Evaluator loop 已经具备本地状态机、agent attempt
记录、evaluator artifact、artifact hygiene、cleanup 和 human merge gate。
但当前状态主要散落在 `.codex/loop-runs/`、`.codex/evaluations/`、
Codex session jsonl 和 stdout/stderr 日志里。用户需要一个独立本地看板，
判断某个项目下 loop 是否正常推进，并能看懂每个 agent 和 skill 正在做什么。

本需求也用于验证需求开发 loop 是否能承接一个真实前端/后端功能开发任务。

## 目标

首版实现一个独立本地 Loop Dashboard 服务，默认监控当前项目：

```text
/home/fyz/codex-skills
```

看板必须回答这些问题：

- 当前有哪些 loop run？
- 每个 run 对应的任务是什么？
- 当前 run 是否正常推进，停在什么阶段？
- Planner、Generator、Evaluator 当前正在做什么，最近完成了什么？
- 有哪些 skill/tool/agent 日志和关键 artifact？
- 如果 run 停住，原因是什么，下一步应该看哪里？

## 非目标

- 不集成进 Crawler Workbench。
- 不做远程多机聚合。
- 不做用户体系、权限系统或多人协作。
- 不提供执行、删除、重启、合入、回滚等写操作。
- 不改变现有 loop orchestrator 的状态写入模型。
- 不自动修复 loop，也不自动 merge `main`。

## 约束

1. 首版只监控当前项目 `/home/fyz/codex-skills`，但代码结构要预留
   `project_root` 参数，后续可扩展到不同项目。
2. 独立本地服务，默认只读文件系统。
3. 数据来源优先使用现有产物：
   - `.codex/loop-runs/<run-id>/run.json`
   - `planner-output.json`
   - `generator-result.json`
   - `evaluator-result.json`
   - `artifact-manifest.json`
   - `cleanup-result.json`
   - `commit-result.json`
   - `dirty-paths-result.json`
   - `supply-chain-result.json`
   - `.codex/evaluations/tasks/**/result.json`
   - agent attempt stdout/stderr
   - Codex session jsonl 中的 agent、tool、skill、token 事件
4. 前端使用轮询刷新，默认 3 秒一次。
5. UI 默认中文展示。
6. 必须展示任务简述，以及 Planner、Generator、Evaluator 当前动作和最近结果。
7. 必须展示可视化 loop 流程图，标出当前阶段、完成阶段、等待阶段和失败回路。
8. 日志展示必须做基础敏感信息过滤，至少隐藏 token、Authorization、
   password、secret、api key 等明显凭据。
9. 不触碰已有 wiki/crawler dirty 文件，不把无关改动纳入提交。
10. evaluator 必须像用户一样通过前端点击验证主要路径。

## 信息架构

首版页面采用三栏布局。

### 左侧：项目与运行列表

展示当前项目、轮询状态和 run 列表。

每个 run item 至少展示：

- `run_id`
- 任务简述
- policy
- phase
- last_result
- next_action
- agent attempt 状态摘要
- 最近更新时间

已完成 run 也必须展示，包括：

- `passed_waiting_human_merge`
- `stopped_no_action`
- `stopped_budget`
- `stopped_blocked`

如果当前项目没有 `.codex/loop-runs`，展示清晰空状态，说明尚无 loop
run artifact。

### 中间：当前 Run 详情

展示当前 run 的主要判断信息：

- 推进健康度
- 当前阶段
- 下一步动作
- Planner/Generator/Evaluator attempt 计数
- 安全 gate 状态
- 任务简述
- 约束摘要
- 停止条件摘要

### 中间：Loop 可视化流程图

需求开发 loop 显示：

```text
Preflight -> Planner -> Generator -> Evaluator -> Artifact Hygiene -> Cleanup -> Human Merge Gate
```

如果 evaluator 失败，图中显示：

```text
Evaluator -> repair_needed -> Generator -> Evaluator
```

自动知识扩展 loop 显示：

```text
Planner -> Generator -> Evaluator -> Artifact Hygiene -> Cleanup -> Commit -> Planner
```

并显示停止条件：

```text
stopped_no_action | stopped_budget | stopped_blocked
```

每个节点展示：

- 节点状态：完成、运行中、等待、阻塞
- 当前动作摘要
- 最近结果摘要
- 对应 artifact 文件路径

### 中间：Agent 当前动作

每个 agent 卡片展示：

- agent 名称
- 当前动作短句
- 最近完成事项
- attempt 编号
- 状态
- 输出 artifact
- 可点击查看相关日志

当前动作摘要的来源优先级：

1. `planner-output.json` / `generator-result.json` / `evaluator-result.json`
   中的结构化字段。
2. agent attempt stdout/stderr 中的最近 agent message。
3. Codex session jsonl 中最近的 `agent_message`、tool call 和 skill 事件。
4. 无法可靠推断时显示“暂无可用摘要”，不能编造。

### 右侧：实时事件与日志

展示按时间排序的事件流：

- agent message
- tool call
- skill 使用
- evaluator scenario 结果
- stdout/stderr
- token 统计事件
- 关键 artifact 更新时间

日志支持：

- 按 run 过滤
- 按 planner/generator/evaluator 过滤
- 按 skill/tool/stderr 过滤
- 关键字过滤
- 基础脱敏后展示

### 阻塞诊断

如果 run 进入阻塞或失败状态，优先展示：

- stopped phase
- blocked reason
- dirty path 违规
- allowlist/denylist 违规
- supply-chain evidence 缺失
- artifact hygiene 失败
- evaluator findings
- scenario command 失败
- next_action

## 后端设计

首版可以实现为仓库内独立 app，例如：

```text
apps/loop_dashboard/
  backend/
  frontend/
```

或使用轻量 Python 后端加前端构建产物。实现阶段按仓库现有约定和依赖选择。

后端只读 API：

```text
GET /api/projects/current
GET /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/events
GET /api/runs/{run_id}/logs
GET /api/health
```

核心解析模块：

- `LoopRunStore`：读取 `.codex/loop-runs`。
- `EvaluatorStore`：读取 `.codex/evaluations`。
- `SessionEventStore`：读取相关 Codex session jsonl。
- `LogRedactor`：脱敏日志。
- `RunSummarizer`：生成任务简述、agent 当前动作、阻塞诊断。

所有路径都必须限制在 `project_root` 内，禁止 path traversal。

## 前端设计

前端默认中文。

首版页面：

- Run 列表
- Run 详情
- Loop 流程图
- Agent 当前动作
- 阻塞诊断
- 实时事件与日志
- 空状态和错误状态

交互要求：

- 默认选中最近活跃 run。
- 点击 run 更新详情、流程图和日志。
- 轮询刷新后保留当前选中 run。
- 过滤日志时不改变 run 选择。
- 如果 run 文件被删除或不存在，显示可恢复错误。

视觉方向：

- 工作台风格，信息密度适中。
- 不做营销页。
- 不使用大面积装饰背景。
- 关键状态使用明确颜色和文本，避免只靠颜色表达。

## 数据模型

API 返回的 run summary 结构建议：

```json
{
  "run_id": "loop-dashboard-dev",
  "project_root": "/home/fyz/codex-skills",
  "task_summary": "实现一个独立本地看板，用于监控当前项目 loop 是否正常推进。",
  "policy": "demand_development",
  "phase": "evaluating",
  "last_result": "none",
  "next_action": "run_artifact_hygiene",
  "health": "progressing",
  "updated_at": "2026-07-03T10:00:00Z",
  "agents": {
    "planner": {
      "status": "pass",
      "attempt": 1,
      "current_action": "已完成需求拆解和验收口径。",
      "last_result": "写入 planner-output.json。"
    },
    "generator": {
      "status": "pass",
      "attempt": 1,
      "current_action": "等待 evaluator 验收。",
      "last_result": "完成 dashboard API 和页面实现。"
    },
    "evaluator": {
      "status": "running",
      "attempt": 1,
      "current_action": "正在模拟用户点击看板详情页。",
      "last_result": "已打开页面并开始检查日志过滤。"
    }
  },
  "blocked_reason": "",
  "artifact_paths": []
}
```

## 日志脱敏

日志展示前必须替换明显敏感字段：

- `Authorization: Bearer ...`
- `ghp_...`
- `api_key=...`
- `token=...`
- `password=...`
- `secret=...`

脱敏后保留上下文，例如：

```text
Authorization: Bearer [REDACTED]
token=[REDACTED]
```

首版脱敏不承诺覆盖所有敏感格式，但必须覆盖上述常见模式，并在 UI 中标记
“日志已做基础脱敏”。

## 错误处理

- `.codex/loop-runs` 不存在：显示空状态。
- 单个 run JSON 损坏：该 run 标记为 `invalid_artifact`，其它 run 继续展示。
- session jsonl 过大或不可读：跳过并记录 warning，不阻塞 run 状态展示。
- artifact 缺失：显示缺失文件名和来源字段。
- 后端读取路径超出 `project_root`：返回 400 并记录安全诊断。

## 验收与停止条件

完成条件：

1. 本地 dashboard 服务能启动，并给出可访问 URL。
2. 前端能展示当前项目 loop run 列表；无真实 run 时显示清晰空状态。
3. 点击某个 run 后能看到任务简述、phase、next_action、last_result、
   attempts。
4. 能看到 Planner、Generator、Evaluator 的当前动作摘要和最近结果。
5. 能看到中文可视化流程图，并正确高亮当前阶段。
6. 能看到日志流，支持按 agent/tool/skill/stderr 或关键字过滤。
7. 能展示 completed loop 状态，包括 `passed_waiting_human_merge`、
   `stopped_no_action`、`stopped_budget`、`stopped_blocked`。
8. 页面轮询刷新有效，后端数据变化后几秒内前端能更新。
9. 单元测试、前端构建、后端 API 测试通过。
10. evaluator 通过前端点击验证主要页面可用，并记录结果。
11. 需求开发 loop 进入 human merge gate，等待用户确认合入。

## 实施策略

本设计进入正式开发时使用 `demand_development` loop。

建议任务边界：

1. 后端只读解析 API。
2. 前端中文看板和流程图。
3. 日志脱敏、事件归并和空状态。
4. evaluator 场景：启动服务，通过前端点击验证 run 列表、详情、描述、
   流程图、日志过滤和 completed run 展示。

首版应避免改动 crawler workbench、wiki ingest 和已有 raw evidence 文件。
