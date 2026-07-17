# AI Infra Selection Governor Design

日期：2026-07-17

任务：`ai-infra-selection-governor-01`

## 状态

本方案已在对话中确认。它补充并收紧以下设计中的 autonomous knowledge 选题部分：

- `docs/superpowers/specs/2026-07-06-ai-infra-autonomous-expansion-loop-design.md`
- `docs/superpowers/specs/2026-07-07-ai-infra-loop-governance-design.md`
- `docs/superpowers/specs/2026-07-14-loop-supervisor-unification-design.md`

本 spec 只改变 AI Infra autonomous loop 的候选生成、选择、验证和停止条件，不改变 Planner、Generator、Evaluator、Supervisor Reviewer 的公共角色边界。没有新的 Dashboard 布局或交互，因此不新增 mock；选择理由通过现有任务摘要、日志和 artifact 展示。

## 问题陈述

AI Infra wiki 已有 29 个 curated Markdown 页面，名义上覆盖 8 个层级，但最近扩充组合明显偏向已有资料最丰富的方向：

- parent-18 到 parent-28 共 11 个父任务，其中 4 个是计算卡或 DPU，4 个是 SGLang 或 NCCL，合计 8/11。
- `raw/crawler/sglang-github-closed-issues-prs` 已有约 1356 个文件；当前仍有约 101 个未跟踪 SGLang raw 和 10 个 NCCL release raw。
- 最近提交中 `ai-infra-coverage-map.md` 被触达 54 次、计算卡参数比较 20 次、计算卡 catalog 18 次、网络/存储页 16 次、推理页 14 次。
- `loop-state.json` 的 `candidate_backlog` 为空；仅有的 3 个 coverage gap 仍保留 2026-07-07 DNS 失败状态，网络恢复后没有重新探测。
- `ingest.md` 声明没有 pending ingest，但本地存在未分类 raw backlog。
- 当前 duplicate gate 识别 URL、issue、PR、SKU 和 raw hash 重复，不能识别“新 ID 但仍是相同主题方向”的语义饱和。

现有 Planner 遵循“优先使用本地 raw”是合理的获取策略，但在资料供给极度偏斜时形成 exploitation trap：本地越多的 SGLang、NCCL 和硬件资料越容易继续被选择，较弱层级始终缺少新候选。Evaluator 验证来源、范围、入库和可见性，Supervisor Reviewer 关注恢复、commit、push 和流程健康，都没有一个确定性组件对跨轮知识组合负责。

## 目标

1. 在 Planner 之前用确定性 Selection Governor 选择 AI Infra 候选。
2. 最近 8 个已完成语义父任务中，同一主题族最多出现 2 次。
3. 最近 8 个父任务至少覆盖 6 个不同主层级；不足时优先补未覆盖或最弱层级。
4. 将语义新颖性从 URL/issue/SKU 新颖性中分离出来。
5. 网络恢复后重新激活 KServe、推理事故复盘和 MLCommons Storage 等旧 blocked gap。
6. 区分 raw 数量增长与可形成知识任务的 semantic delta。
7. 让 Planner、Evaluator 和 Supervisor Reviewer 使用同一份选择证据。
8. 在没有合格候选时干净进入 `stopped_no_action`，不为保持 loop 运转而重复旧方向。

## 非目标

- 不停止 SGLang、NCCL 或计算卡的月度 raw 抓取。
- 不删除现有 raw、curated 页面、coverage map 或已完成父任务记录。
- 不把简单文件数量当作层级深度或知识价值。
- 不让 LLM 自行决定是否忽略配额。
- 不引入新的外部数据库、队列或调度系统。
- 不修改 Dashboard 布局、分页或交互。
- 不把所有 blocked gap 强制变成 actionable；必须有新的机器可验证证据。
- 不默认把任何项目标记为高价值。

## 已确认决策

- 采用滚动配额，而不是固定冻结或软降权。
- `window_size=8`。
- `max_per_topic_family=2`。
- `min_distinct_layers=6`。
- 弱覆盖层优先于候选 advisory score。
- 普通新 issue、PR、release、blog 或 SKU 不构成语义新颖性。
- 重大版本、安全事故、生产故障和全新硬件代际可申请例外，但必须有确定性 exception evidence。
- 无合格候选时停止，不回退到旧 Planner 自由选题。
- 现有 recovery/commit 整改完成后，在创建下一个知识 parent 前切换。

## 术语

### Primary Layer

每个候选必须且只能有一个 `primary_layer`：

1. `training-distributed`
2. `inference-runtime`
3. `orchestration-scheduling`
4. `data-rag-vector`
5. `eval-observability-reliability`
6. `security-governance-cost`
7. `hardware-accelerator`
8. `network-storage-cluster`

候选可以有多个 `secondary_layers`，但滚动覆盖只计算 `primary_layer`，防止一个任务同时给多个层级虚增覆盖。

### Topic Family

`topic_family` 表示会造成方向重复的稳定语义族，而不是项目名或来源名。首期 taxonomy：

- `accelerator-catalog`
- `collective-communication`
- `distributed-training-runtime`
- `inference-serving-runtime`
- `orchestration-and-scheduling`
- `data-and-rag-pipeline`
- `evaluation-observability-reliability`
- `security-governance-cost`
- `network-storage-cluster`

SGLang、vLLM、TensorRT-LLM、Triton 和 KServe 的 serving/runtime 候选通常属于 `inference-serving-runtime`；NCCL collective、通信算法和通信运行问题属于 `collective-communication`；GPU/NPU/DPU/TPU/DSA 型号参数属于 `accelerator-catalog`。Planner 不得通过创建更细项目族规避配额。

### Semantic Gap

`semantic_gap` 是候选要关闭的、可验证的知识缺口。必须包含稳定 `gap_id`、当前缺失边界、预期证据类型和完成判据。以下内容单独存在时不构成新 gap：

- 新 issue/PR 编号；
- 新 release tag；
- 同一厂商同类 SKU 的少量字段；
- 同一主题的新 blog；
- 月度 crawler 文件数增加；
- 对已有 curated 段落的同义改写。

### Evidence Class

允许的 `evidence_class`：

- `official_docs`
- `design_or_architecture`
- `release_or_changelog`
- `issue_or_pr`
- `benchmark_or_measurement`
- `incident_or_postmortem`
- `deployment_or_operations`
- `security_advisory`
- `product_specification`

### Novelty Key

每个候选使用：

```text
<topic_family>:<normalized_capability_boundary>:<evidence_class>
```

`novelty_key` 与 canonical URL、GitHub identity、hardware identity 和 raw SHA-256 并存。URL identity 证明来源不重复，`novelty_key` 证明知识增量不只是同方向的新 ID。

## 架构

新增 `scripts/harness_ai_infra_selection.py`，作为独立、纯确定性的 Selection Governor。它不调用 LLM，不修改 git，不直接执行抓取。

```text
coverage-map.json + loop-state.json + selection-policy.json
  + completed semantic parent artifacts
  + crawler manifests / ingest state
  + fresh network probe artifacts
                  |
                  v
       AI Infra Selection Governor
          | normalize candidates
          | rebuild rolling window
          | compute layer depth
          | enforce novelty and diversity
          | classify/defer/reprobe
                  |
                  v
          selection-decision.json
                  |
        +---------+----------+
        |                    |
      Planner             Evaluator
        |                    |
        +------ Supervisor Reviewer
```

Supervisor Worker 在执行 AI Infra Planner action 前调用 Governor。Planner prompt 只包含被选中的 candidate 和只读 selection decision；Planner 不能从 raw backlog 自行选择其他候选。

## 仓库级策略契约

新增 `personal-wiki/domains/ai_infra/selection-policy.json`：

```json
{
  "schema_version": 1,
  "policy_id": "ai-infra-selection-v1",
  "window_size": 8,
  "max_per_topic_family": 2,
  "min_distinct_layers": 6,
  "scan_ttl_days": 30,
  "max_network_reprobes_per_round": 10,
  "exception_types": [
    "major_release",
    "security_incident",
    "production_incident",
    "new_hardware_generation"
  ],
  "primary_layers": [
    "training-distributed",
    "inference-runtime",
    "orchestration-scheduling",
    "data-rag-vector",
    "eval-observability-reliability",
    "security-governance-cost",
    "hardware-accelerator",
    "network-storage-cluster"
  ],
  "topic_families": [
    "accelerator-catalog",
    "collective-communication",
    "distributed-training-runtime",
    "inference-serving-runtime",
    "orchestration-and-scheduling",
    "data-and-rag-pipeline",
    "evaluation-observability-reliability",
    "security-governance-cost",
    "network-storage-cluster"
  ]
}
```

未知 layer、family、evidence class 或 exception type 必须验证失败，不能由 Planner 动态扩展 taxonomy。

## Loop State 扩展

`loop-state.json` 新增：

```json
{
  "selection_policy_version": "ai-infra-selection-v1",
  "recent_parent_topics": [],
  "candidate_backlog": [],
  "deferred_by_diversity": [],
  "unclassified_raw": [],
  "reprobe_queue": []
}
```

`recent_parent_topics` 每项必须包含 `semantic_parent_id`、run/task id、accepted commit、primary layer、topic family、gap id、novelty key、evidence classes 和完成时间。只统计通过 Evaluator、完成 commit/push 或明确 no-op commit/push、并被 Supervisor 记为 completed semantic parent 的任务。recovery、cleanup、Reviewer remediation、服务重启和纯 harness 修复不进入窗口。

`candidate_backlog` 是 Governor 的结构化输入，不允许为空数组同时依赖 Planner 临时扫描。空 backlog 必须有同轮 `candidate-scan.json` 和 `no_action_evidence`。

`deferred_by_diversity` 记录 quota、layer breadth 或 semantic novelty 拒绝，包含 `retry_after_parent_position`。它不是 blocked，也不在下一轮原样重试。

`unclassified_raw` 只记录缺少 manifest 或 semantic classification 的 raw 集合摘要，不为每个文件创建父任务。

`reprobe_queue` 记录旧 `needs_network` gap 的下次轻量探测时间和上次 DNS/TLS/HTTP 证据。

## Candidate 契约

```json
{
  "candidate_id": "candidate:kserve-autoscaling-canary",
  "identity_key": "gap:kserve-inference-deployment-source-capture",
  "primary_layer": "inference-runtime",
  "secondary_layers": ["orchestration-scheduling"],
  "topic_family": "inference-serving-runtime",
  "gap_id": "kserve-inference-deployment-source-capture",
  "semantic_gap": "KServe autoscaling and canary deployment controls lack current primary-source evidence.",
  "normalized_capability_boundary": "kserve-autoscaling-canary-controls",
  "evidence_classes": ["official_docs", "deployment_or_operations"],
  "novelty_key": "inference-serving-runtime:kserve-autoscaling-canary-controls:official_docs",
  "source_refs": [],
  "acquisition_path": "crawler_workbench",
  "obtainable": true,
  "exception": null
}
```

候选缺少任一承重字段时不能进入 Planner。`evidence_classes` 可以有多个，但 `novelty_key` 使用本轮主要新证据类型。

## Layer Depth

层级深度不使用 raw 文件数量。每层记录 0-5 的确定性 milestone：

1. 有至少一个 source-backed curated 页面。
2. 有至少两个独立 source family，不是同一项目的多个 issue/PR。
3. 有至少两个 evidence class。
4. 有 `benchmark_or_measurement`、`incident_or_postmortem` 或 `deployment_or_operations` 中至少一种强运行证据。
5. 最近 30 天完成扫描，且没有未分类的 major gap。

`depth_level` 是满足的 milestone 数量。选择时先按 `depth_level` 升序，再按未覆盖层、gap severity、obtainable、hard gates 和 advisory priority 排序。文件多不能提升 depth；同一 SGLang corpus 的 1000 个 issue 仍只算一个 source family 和一个 evidence class。

## 滚动窗口与配额

Governor 每轮从 canonical completed parent artifacts 重建最近 8 个语义父任务，不信任 Planner 自报或手工维护计数器。

规则：

1. 候选 topic family 在窗口中已出现 2 次时，普通候选进入 `deferred_by_diversity`。
2. 窗口中 distinct primary layers 少于 6 时，只允许未覆盖层或当前最低 depth 层进入普通选择。
3. 一个候选只能增加一个 primary layer。
4. 多个合格候选先选择未覆盖层，再选择最低 depth，再使用 advisory priority。
5. 如果缺失层没有 obtainable 候选，Governor 先处理对应 needs/reprobe；仍无候选则 `stopped_no_action`，不能回选饱和层。
6. 窗口少于 8 个任务时，family cap 仍生效；层级广度目标为 `min(6, completed_count + 1)`。

### 首次迁移窗口

从 parent-21 到 parent-28 重建：

- parent-21、22：`hardware-accelerator / accelerator-catalog`
- parent-23、24：`inference-runtime / inference-serving-runtime`
- parent-25、28：`training-distributed / collective-communication`
- parent-26：`inference-runtime / inference-serving-runtime`
- parent-27：`data-rag-vector / data-and-rag-pipeline`

该窗口只有 4 个 distinct primary layer，并且 `inference-serving-runtime` 已超过上限。因此切换后的普通候选必须优先来自 orchestration、eval/observability、security/governance 或 network/storage；普通 SGLang、NCCL 和 accelerator catalog 候选进入冷却。

## Exception 契约

例外不能由 Planner 只写一句 rationale。必须有：

```json
{
  "exception_type": "production_incident",
  "evidence_refs": ["..."],
  "detected_at": "2026-07-17T00:00:00Z",
  "material_change": "...",
  "why_delay_is_harmful": "...",
  "validated_by": "harness_ai_infra_selection"
}
```

例外条件：

- `major_release`：新的 major version 或明确 breaking-change boundary，不是普通 patch release。
- `security_incident`：官方 advisory 或可验证披露，影响现有 covered system。
- `production_incident`：有 impact、timeline、remediation 或 owner 中至少三项，不是普通 issue 报告。
- `new_hardware_generation`：厂商明确的新代际/架构边界，不是同代 SKU、内存变体或聚合系统字段补充。

Evaluator 必须验证 evidence 与 exception type 匹配。失败时按普通配额重新分类，不能继续执行。

## Raw 与 Ingest 状态

Crawler 抓取和知识父任务解耦：

- 月度 crawler 可以继续保存 raw。
- 没有 manifest 的 raw 进入 `unclassified_raw` 汇总。
- manifest 必须声明新增 identity、semantic gaps、evidence classes、重复数量和候选聚合边界。
- 只有存在新 `gap_id` 或新 novelty key 的 manifest 才进入 candidate backlog。
- 同一批 101 个 SGLang raw 只能形成一个 batch candidate，不能形成 101 个父任务。
- 数量增长但没有 semantic delta 的 batch 记录为 `captured_no_semantic_delta`，不消耗父任务。
- `ingest.md` 的 Pending/In Progress 从 manifest 和 candidate state 生成或校验；存在 unclassified/pending raw 时不能写 `No pending ingest.`。

## 网络 Gap 复探

当前 3 个旧 gap 首轮必须复探：

- `kserve-inference-deployment-source-capture`
- `inference-serving-postmortem-source-capture`
- `network-storage-exact-benchmark-result-capture`

复探使用低成本 DNS + TLS + HEAD 或小流量 GET，最多 10 个 host/round。artifact 必须记录 `probe_url`、started/finished、DNS、TLS、HTTP status、final URL、error class 和 summary。

只有同一 canonical host 从旧 DNS/TLS/timeout 失败变为 HTTP reachable，或旧 403/429/5xx 变为可抓取，才设置 `network_state_changed=true` 并移回 backlog。复探成功不等于资料通过质量门；后续仍需 source acquisition 和 semantic gap validation。

## Selection Decision Artifact

每个 AI Infra Planner action 前写入 run 级 `selection-decision.json`：

```json
{
  "schema_version": 1,
  "run_id": "...",
  "task_id": "...",
  "policy_id": "ai-infra-selection-v1",
  "window": [],
  "layer_depth": {},
  "candidate_counts": {
    "scanned": 0,
    "eligible": 0,
    "deferred": 0,
    "needs_reprobe": 0
  },
  "selected_candidate": {},
  "rejections": [],
  "decision": "selected | stopped_no_action | stopped_blocked",
  "created_by": "harness_ai_infra_selection"
}
```

Artifact 必须在 Planner 前由 Worker/Supervisor-owned code 写入。Planner 只读，不能生成或覆盖。Evaluator 根据 artifact SHA-256、run/task identity 和 policy id 验证 provenance。

## Planner、Evaluator 与 Reviewer 集成

### Planner

- prompt 只包含 selected candidate。
- `planner-output.json` 的 gap、layer、family、novelty key 必须与 decision 完全一致。
- Planner 不能改选候选、修改 exception 或动态扩展 taxonomy。

### Evaluator

- 验证 selection decision provenance、schema 和 run/task binding。
- 重新计算 rolling family counts、distinct layers、depth ordering 和 novelty key。
- 缺 artifact、artifact 伪造、quota 违规、例外证据不足或 Planner 换题均为失败。
- 形式化怀疑 pass 至少构造一个反例：移除 semantic gap、把新 issue ID 当 novelty、或把 source count 当 depth，确认实现会拒绝。

### Supervisor Reviewer

- 每两次语义父任务审视最近 8 轮层级分布、family count、deferred 原因和 stopped_no_action。
- 确定性 quota 违规直接 `auto_remediate`，不由 Reviewer LLM 决定是否忽略。
- Reviewer 负责判断 taxonomy 是否导致钻空子、任务是否过于钻研局部问题、候选方向是否仍偏离整体目标。
- 连续两次 review 仍违反同一方向治理时 `refocus`；只有权限、不可逆操作或全局策略变更才请求用户。

## Supervisor 与停止条件

AI Infra Planner action 的 transition 变为：

```text
planning
  -> run_selection_governor
  -> selected -> run_planner
  -> stopped_no_action
  -> stopped_blocked
```

停止条件：

- `stopped_no_action`：没有 eligible candidate，所有 gap 已 deferred、needs external condition 或 captured without semantic delta，并有完整 scan evidence。
- `stopped_blocked`：policy/state/schema/provenance 无法验证，历史窗口无法重建，或网络 probe 机制错误。
- 不允许 fallback 到 Planner 自由选题。

## Dashboard 可见性

本任务不修改前端。现有 Dashboard 必须通过已有字段显示：

- 任务摘要：selected candidate 的 gap 和 primary layer。
- Planner 动作：Governor 选择理由。
- 日志：候选数、quota、弱层、deferred 和 reprobe 结果。
- Artifact：`selection-decision.json`。
- 阻塞诊断：policy/schema/provenance 错误或 no-action 解释。

如果现有 Dashboard 无法显示这些通用任务/日志/artifact 字段，属于现有契约回归；实现时修复数据映射，但不新增视觉布局。若必须增加新 UI 元素，必须先补 mock 并修改本 spec。

## 切换与迁移

1. 等当前 recovery/commit remediation 自然完成。
2. 暂停创建下一个知识 parent，不停止 crawler、Dashboard、Supervisor 或 Worker 服务。
3. 写入并验证 `selection-policy.json`。
4. 从 parent-21 到 parent-28 artifact 重建窗口。
5. 扫描 manifest/raw，填充 `candidate_backlog`、`unclassified_raw` 和 `deferred_by_diversity`。
6. 复探 3 个旧网络 gap。
7. 运行 fake/fixture E2E，证明弱层候选被选择。
8. 启用新的 `run_selection_governor` transition。
9. 首个 live parent 通过 Evaluator、commit/push、Dashboard 可见性后才认为切换完成。

迁移失败时保持 loop 停止，不恢复旧选题逻辑。Crawler frontend/backend 和 Loop Dashboard 在切换期间保持在线。

## 测试方案

### 单元测试

1. 窗口中 `accelerator-catalog` 已有 2 次，第 3 个普通硬件候选被 deferred。
2. 窗口只有 4 个 primary layer 时，已覆盖层候选不能击败可获取的缺失层候选。
3. 新 SGLang issue 只有新 ID、没有新 gap 或 evidence class 时被拒绝。
4. 一个 source family 的 1000 个 raw 文件不能提升 layer depth 的 source-family milestone。
5. production incident exception 有完整证据时可突破配额；普通 issue rationale 不可突破。
6. completed semantic parent 计入窗口，recovery/cleanup/remediation 不计入。
7. 历史缺失或 fingerprint 不匹配时阻塞，不猜测窗口。
8. unclassified raw 按 batch 聚合，不按文件创建候选。
9. ingest log 在存在 pending/unclassified raw 时拒绝 `No pending ingest.`。
10. policy、candidate、decision、loop-state schema 拒绝未知字段和 taxonomy 值。

### 网络测试

1. 旧 DNS failure + 新 HTTP 200 产生 `network_state_changed=true`。
2. 新 probe 仍是 DNS failure 时保留 needs_network，并按 TTL 延迟。
3. HTTP reachable 但正文/来源质量不足时只回 backlog，不直接选择。
4. 每轮最多 10 个 probe。

### Planner/Evaluator 集成测试

1. Planner 输出与 selected candidate 完全匹配时通过。
2. Planner 换成 SGLang/NCCL/硬件候选时失败。
3. selection decision 缺失、SHA 错、run/task 不匹配时失败。
4. Evaluator 独立重算 quota 和 depth，不能采信 Planner 自述。
5. 形式化反例测试能证明“新 issue ID 即新方向”的错误实现被拒绝。

### E2E 场景

创建 `scripts/ai_infra_selection_e2e_evaluator.py`，至少覆盖：

1. 过度集中窗口：2 hardware + 3 inference + 2 collective + 1 data。
2. 旧 KServe gap 的网络从 DNS failure 变为 reachable。
3. Governor 选择 orchestration、eval/security 或 network/storage 的弱层候选。
4. Planner -> Generator -> Evaluator 完成一个 fixture parent。
5. 下一轮自动继续并遵守更新后的窗口。
6. Dashboard API/页面能看到任务摘要、选择理由、Evaluator 场景和 artifact。
7. Crawler frontend/backend、Dashboard 和 Supervisor/Worker 在测试前后在线。

### 回归测试

- autonomous recovery、commit/push、partial artifact recovery 不回归。
- Supervisor Reviewer cadence 和 decision application 不回归。
- demand development loop 不经过 AI Infra Governor。
- wiki validation、search refresh 和 existing Dashboard pagination 通过。

## 验收标准

1. `selection-policy.json`、loop-state 扩展和 selection decision 均有严格 validator。
2. 最近 8 轮 family cap 和 layer breadth 由确定性测试证明。
3. parent-21 到 parent-28 迁移窗口可复现且 fingerprint-bound。
4. 3 个旧网络 gap 被重新探测并得到新的机器证据。
5. 普通 SGLang、NCCL 和 accelerator catalog 候选在首次窗口被正确冷却。
6. untracked raw 被分类为 candidate、unclassified、duplicate 或 captured-no-delta，不再与 `No pending ingest` 矛盾。
7. 至少一个弱层 fixture parent 完成完整 PGE 流程。
8. Evaluator 对 selection completeness、quota、semantic novelty、exception 和 provenance 执行独立验证及反例测试。
9. Dashboard 通过现有布局显示选择与验收信息。
10. 任务 `verify`、Step 4 evaluator、wiki validate、服务健康和 `git diff --check` 全部通过。

## 安全与提交纪律

- 不把 token、cookie、sudo 密码、Tailscale 凭据或 probe authorization 写入 artifact。
- 网络 probe 只保存 bounded metadata，不保存响应中的凭据或隐私内容。
- 只提交策略、实现、测试、repo-owned evidence、wiki 状态和文档。
- `.codex` runtime、日志、pid、SQLite、`generated/` 和无关 raw 不进入实现 commit。
- autonomous wiki 入库仍独立 commit 并推送 `origin/main`。
- Selection Governor 实现作为独立 harness commit，不与知识入库 commit 混合。

## 实现阶段

1. 契约与纯选择算法：policy、candidate、window、depth、quota、novelty、exception validators。
2. 状态与来源治理：loop-state 扩展、raw/manifest 分类、ingest consistency、network reprobe。
3. Runtime 集成：Supervisor transition、Worker pre-Planner action、Planner/Evaluator/Reviewer binding。
4. E2E、迁移和 live cutover：重建 parent-21 到 parent-28，复探旧 gap，运行首个弱层 parent。
