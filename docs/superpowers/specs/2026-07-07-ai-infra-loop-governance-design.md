# AI Infra Loop Governance Design

日期：2026-07-07

## 背景

`ai_infra` 自治资料扩充 loop 已经证明了现有 Planner -> Generator -> Evaluator -> Planner 架构可以持续产出知识入库 commit，但近期运行暴露出策略层问题：资料扩充成果长期停留在 feature worktree、部分轮次从真实爬取退化成单页 `raw/links` 抓取、历史网络失败导致 blocked evidence 重复记账、crawler workbench source profiles 与 autonomous loop 取数路径脱节、定时 crawler 产物没有及时整理入库，以及 coverage 完整度主要由同一套 agent 自评。

因此，当前优先级从“继续跑下一轮知识拓展”调整为“治理 loop 行为”。治理本身也通过需求开发 loop 分轮执行；等当前 r10 轮自然结束并完成 evaluator、验证和 commit 后，暂停创建 r11，优先进入治理整改。治理通过后，再恢复 AI infra 知识拓展。

## 目标

1. 让资料扩充 loop 在进入下一轮前能判断候选任务是否真的值得做。
2. 把连续 blocked 的网络、鉴权、缺 seed URL、需人工判断项分流，不再重复消耗轮次。
3. 把“高价值项目深挖”改成显式评分门，而不是 Planner 主观标记。
4. 让 crawler workbench Domain Channels/source profiles 成为长期来源的默认入口。
5. 设立知识入库 checkpoint 和 main 合入节奏，避免成果长期只留在 worktree。
6. 把 evaluator 从“验证自述和文件存在”提升为“验证资料质量、前后端可见性和 loop 可读性”。
7. 保留 autonomous knowledge 的自动能力，但把 stop/no-action/budget/block 的语义收紧到可审计状态。

## 非目标

- 不在本 spec 中继续抓取新的 AI infra 资料。
- 不删除现有 `autonomous_knowledge` 和 `demand_development` loop。
- 不默认把当前 feature branch 自动合入 `main`；合入仍需要用户确认。
- 不把 token、cookie、私有凭据、`.env`、`.codex` 日志、pid/log、`generated/` 或 `.worktrees/` 内容写入 git。
- 不把任意热门项目默认视为高价值项目。
- 不要求一次性补齐所有历史 raw 或全互联网资料。

## 当前事实基线

治理 loop 的 preflight 必须先记录以下事实，而不是依赖记忆：

- 当前工作区：`.worktrees/ai-infra-meta-loop-runtime`，分支 `ai-infra-meta-loop-runtime`。
- 当前 r10 轮仍可能在后台运行；治理只能在 r10 当前子任务自然结束、验证、提交或明确 stopped 后开始。
- 当前分支相对 `main` 有大量未合入 commit；需要区分 harness 修复、wiki 入库、运行产物和无关文件。
- `personal-wiki/domains/ai_infra/coverage-map.json` 仍包含可行动 gap，尚未达到全局 `stopped_no_action`。
- 历史 gap proof 中存在 DNS/temporary failure/blocked 记录；正式治理前要重新探测当前网络状态，因为网络可能已恢复。
- main 工作区曾出现未提交 crawler raw 产物和 `generated/` 之类无关文件；治理需要先清理归属。

## 总体运行形态

治理使用需求开发多子任务 loop：

```text
r10 收尾
  -> Governance Parent Run
     -> Child 1: 状态与 checkpoint 治理
     -> Child 2: blocked/needs 队列治理
     -> Child 3: 高价值判定门和深挖任务门槛
     -> Child 4: crawler workbench / Domain Channels 联动
     -> Child 5: evaluator 完整度和前端可见性验收
     -> Child 6: 恢复知识拓展策略与停止条件
  -> passed_waiting_human_merge 或 stopped_blocked
```

治理通过后，新的 AI infra 知识拓展 loop 才能继续创建下一轮 autonomous run。后续资料扩充仍可以每轮最多 3 个子任务，但 Planner 必须优先使用治理后的状态机和评分结果。

## 分轮治理方案

### 第 0 轮：r10 收尾

目的：关闭当前正在运行的资料扩充轮次，避免治理 spec、实现和 r10 generator 的脏文件互相污染。

要求：

- 等待 `ai-infra-expansion-2026-07-07-r10-task-3` 进入 evaluator、artifact hygiene、cleanup 和 commit，或明确 stopped。
- 运行 `python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`。
- 只提交 r10 本轮入库相关文件，不混入治理文档、`.codex`、pid/log、`generated/` 或 main 工作区未归属 crawler 产物。
- r10 完成后不自动创建 r11。

停止条件：

- r10 终态为 `stopped_budget`、`stopped_blocked` 或 `stopped_no_action`。
- 如果 r10 stuck 在 generator 超时或孤儿进程，先走 harness timeout cleanup 和 resume 规则。

### 第 1 轮：状态与 checkpoint 治理

目的：把当前成果从“长期挂在 worktree”变成可审计 checkpoint。

要求：

- 生成分支相对 `main` 的 commit 分类报告：harness fix、wiki 入库、crawler source/profile、frontend/backend/dashboard、纯文档。
- 清点未提交文件，按本任务、r10 入库、定时 crawler raw、无关本地文件、禁止提交文件分类。
- 将已经完成且验证通过的 wiki/crawler 入库整理成独立 commit。
- 对治理前已有未归属 raw，执行 ingest triage：已有 raw 无 wiki 时进入整理入库；重复 raw 记录重复证据；无关或 generated 文件不提交。
- 给后续知识扩充设 checkpoint 策略：每个资料入库子任务独立 commit；每 N 轮或治理阶段结束后创建 branch checkpoint；合入 `main` 仍需用户确认。

验收：

- `git status --short` 中没有未分类 dirty paths。
- 分支 commit 分类报告能说明每类成果是否应合入 main。
- wiki 入库 commit 不包含 `.codex`、pid/log、`generated/` 或凭据。

### 第 2 轮：blocked/needs 队列治理

目的：阻止 loop 对同一 blocked gap 反复 probe 和写“为什么抓不到”的资料。

新增状态语义：

```json
{
  "actionable_gaps": [],
  "needs_network": [],
  "needs_auth": [],
  "needs_seed_url": [],
  "needs_human_judgement": [],
  "deferred_duplicates": [],
  "blocked_retry_policy": {
    "max_same_reason_retries": 1,
    "retry_only_after": [
      "network_state_changed",
      "auth_configured",
      "seed_url_added",
      "source_profile_changed",
      "user_requested_retry"
    ]
  }
}
```

规则：

- DNS/TLS/timeout/HTTP 403/robots/captcha/auth/rate limit 必须分别记录，不允许统一写成 blocked。
- 同一个 identity key、同一失败类型、同一来源边界连续失败后，进入对应 needs 队列。
- needs 队列中的项不计入 immediate actionable gaps，但仍计入全局未完成事实。
- `stopped_no_action` 只有在 `actionable_gaps` 为空且 needs 队列都有明确等待条件时才允许出现。
- 当前网络状态恢复时，Planner 可以把 `needs_network` 中符合条件的项移回 `actionable_gaps`，但必须先记录新的 link probe 证据。

`network_state_changed` 的判定必须是机器可验证的。最小证据包括：同一 canonical host 或 probe URL 在最近一次 probe 中从 DNS/TLS/timeout 失败变为 HTTP reachable，或从 HTTP 5xx/429/403 变为可抓取状态；证据必须记录 `probe_url`、`started_at`、`finished_at`、`dns_status`、`tls_status`、`http_status`、`final_url`、`error_class` 和 `summary`。如果只是 agent 推断“网络可能好了”，不得触发重试。

验收：

- 连续 blocked gap 不会在下一轮被原样重试。
- coverage map 和 loop-state 能区分“可行动缺口”和“等待外部条件”。
- dashboard 能显示 needs 队列和等待条件。

### 第 3 轮：高价值判定门和深挖任务门槛

目的：Planner 不能直接声明某项目高价值；必须先评分，再决定任务类型。

每个候选项目先进入 `candidate_scoring`。评分输出写入 run artifact，并在被采纳时沉淀到 `loop-state.json` 或 coverage map 的候选记录中。

评分 artifact 必须使用固定契约，避免 Planner 只写主观结论：

```json
{
  "candidate_id": "project:vllm",
  "identity_key": "github:vllm-project/vllm",
  "layer": "inference-runtime",
  "scores": {
    "ecosystem_impact": 0,
    "local_gap": 0,
    "source_availability": 0,
    "engineering_value": 0,
    "update_frequency": 0,
    "verifiability": 0,
    "duplication_risk": 0
  },
  "hard_gates": {
    "has_gap_proof": false,
    "has_two_source_types_for_deep_dive": false,
    "has_evaluator_scenario": false,
    "has_domain_channel_plan": false
  },
  "evidence": {
    "wiki_search_paths": [],
    "raw_paths": [],
    "source_profile_ids": [],
    "link_probe_artifacts": [],
    "github_repo": "",
    "release_or_docs_urls": []
  },
  "classification": "high_value | medium_value | low_value | needs_more_evidence | blocked",
  "rationale": ""
}
```

`classification=high_value` 必须同时满足分数阈值和 hard gates；分数达标但 hard gate 不满足时只能是 `needs_more_evidence` 或 `medium_value`。

评分维度：

| 维度 | 分值 | 判定问题 |
| --- | --- | --- |
| 生态影响 | 0-5 | 是否是 AI infra 主流组件、标准接口或关键路径 |
| 本地缺口 | 0-5 | 当前 wiki/raw 是否缺少系统性资料或关键版本变化 |
| 资料可得性 | 0-5 | 是否有可抓取的一手来源，如 docs、release notes、closed issues/PRs、design docs、benchmark |
| 工程价值 | 0-5 | 是否能解释训练、推理、调度、观测、成本、安全、硬件等实际基础设施问题 |
| 更新频率 | 0-3 | 是否仍在快速迭代，值得定期同步 |
| 可验证性 | 0-3 | evaluator 能否基于来源、API、前端、dashboard 验证质量 |
| 去重风险 | -5-0 | 是否只是已有内容重复、相邻改写或来源边界不清 |

分类：

- `high_value`: 总分 >= 18，且资料可得性 >= 3，可验证性 >= 2，去重风险 > -4。
- `medium_value`: 总分 11-17，允许单次补充、观察或轻量整理。
- `low_value`: 总分 <= 10，不自动抓取，除非用户指定。
- `needs_more_evidence`: 资料可得性不足或可验证性不足，先做来源探测，不入库。
- `blocked`: 需要网络、鉴权、seed URL 或人工判断。

深挖门槛：

- 高价值项目必须至少有两类一手或强证据来源可用，不能只靠一个 URL。
- 可用来源类型包括官方 docs/design docs、release notes/changelog、closed issues/PRs、benchmark/profiling、deployment examples、production notes 或 incident/postmortem。
- `vLLM`、`TensorRT-LLM`、`Triton`、`KServe`、`Ray` 只能作为候选示例；必须先评分和 gap proof，不能默认高价值。
- 深挖任务必须声明预计抓取范围、去重键、最大抓取量、是否需要 GitHub token、是否进入 Domain Channels、更新 cadence 和 evaluator 验收场景。

验收：

- Planner 输出中没有未评分的 `high_value` 深挖任务。
- medium/low/blocked/needs_more_evidence 项不会被误送入深挖 generator。
- evaluator 抽样检查 scoring evidence 与实际来源和本地缺口一致。

### 第 4 轮：crawler workbench / Domain Channels 联动

目的：长期来源不再绕过 crawler 基建。

规则：

- 长期来源必须建 Domain Channel 和 source profile；一次性 URL 才允许直接进入 `raw/links`。
- source profile 记录 target domain、channel、base URL trust、fetcher type、scheduler cadence、auth readiness、probe status 和 child source 关系。
- 如果 base URL 已可信，新 child source 可以继承可信边界，但仍需记录 canonical URL 和去重键。
- 需要鉴权的来源只记录 synthetic readiness，不提交 token。
- 已有 93 个 source profiles 要被分类：ready、disabled_by_design、needs_auth、needs_browser、network_failed、duplicate、stale。
- 定时 crawler 产物必须进入 ingest triage 队列，不能无限堆在 raw/crawler 未提交状态。

SQLite 是 crawler workbench 的运行时 source of truth，但治理需要可审计快照。任何新增或修改长期来源后，Generator 必须导出非敏感 channel/source snapshot 到 repo-tracked manifest，例如 `personal-wiki/domains/ai_infra/manifest-<run-id>-source-profile-snapshot.json`。快照只包含 channel id、base URL、trust level、auth state、source id、fetcher type、schedule、probe summary、canonical URL 和去重键；不得包含 token、cookie、header 明文、加密密文、nonce 或本地 key 路径。

验收：

- 新增长期来源能在 Crawler Workbench API 和前端 Domain Channels 页面看到。
- probe 或 fetch dry-run 记录 DNS/TLS/HTTP/timeout/auth/rate-limit/robots 结果。
- scheduler cadence 与来源类型匹配：静态硬件型号默认月度，新 release/issue 项目可单独更短周期。

### 第 5 轮：Evaluator 完整度治理

目的：Evaluator 要像用户一样验证资料、前后端和看板，而不是接受 generator 自述。

每个知识入库任务必须验证：

- gap proof 存在且通过去重检查。
- raw evidence 存在，或明确复用已有 raw。
- curated wiki 页面包含 `source_refs`，并更新 index。
- `python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` 通过。
- `/api/wiki/pages`、`/api/wiki/page` 或 `/api/search` 能看到新增资料。
- 前端知识工作台或 Wiki 浏览页能看到新增关键词或页面标题。
- Loop Dashboard 能看到当前 run、子任务摘要、agent action、验收场景、错误/阻塞和用户决策。
- Crawler Workbench 能看到 source/channel/fetch run/raw/wiki/search 的刷新状态。
- 新外链有 link probe 或明确 blocked/auth 证据。
- changed paths 通过 secret scan 和 denylist 检查。
- 如果修改代码，必须跑对应 backend/frontend/harness 测试。

涉及前端或看板时，evaluator 必须用 Playwright 或现有 live evaluator 模拟用户点击。仅 curl API 不足以证明前端可用。

验收：

- evaluator 结果包含人读摘要，说明验收了哪些用户场景。
- dashboard 适合不了解项目背景的人阅读：能看到任务是什么、进展到哪、验收过什么、是否有错误、是否需要决策。
- failed/blocked 不得被折算为 pass。

### 第 6 轮：恢复知识拓展策略与停止条件

目的：治理后恢复 AI infra 知识拓展，但改变任务选择策略。

新的每轮策略：

- 每轮最多 3 个子任务。
- Planner 优先从 `actionable_gaps` 选任务。
- 至少一个任务应来自高价值评分或明确 coverage gap；如果没有高价值项，允许执行 medium_value 或整理入库。
- 至少检查一次定时 crawler 产物 triage，避免 raw 积压。
- 如果出现 runtime bug，仍停留在 auto mode 自动创建治理/修复子任务，修复后再回到资料扩充。

全局停止条件：

- `stopped_budget` 只表示单轮预算结束，不是全局停止。
- `stopped_no_action` 需要同时满足：`actionable_gaps` 为空、candidate backlog 为空、needs 队列都有等待条件、coverage map 每层有新鲜扫描证据、no-action evidence 引用 coverage map。
- `stopped_blocked` 只用于需要用户决策、凭据、权限、denylist、无法自动修复的代码问题，或同一阻塞条件在恢复后仍重复出现。

## 数据和产物

新增或扩展的主要产物：

- `docs/superpowers/specs/2026-07-07-ai-infra-loop-governance-design.md`
- `docs/superpowers/plans/2026-07-07-ai-infra-loop-governance.md`
- `.codex/loop-runs/<run-id>/candidate-scoring/*.json`
- `.codex/loop-runs/<run-id>/governance-report.json`
- `.codex/loop-runs/<run-id>/needs-queue-transition.json`
- `personal-wiki/domains/ai_infra/loop-state.json`
- `personal-wiki/domains/ai_infra/coverage-map.json`
- `personal-wiki/domains/ai_infra/ingest.md`
- `personal-wiki/domains/ai_infra/manifest-<run-id>-source-profile-snapshot.json`
- crawler workbench SQLite runtime state and related API responses

Run-local artifacts under `.codex/**` are evidence, not git-tracked source. If a summary needs长期留存，应把摘要写入 docs、wiki 或 manifest，而不是提交 `.codex` 目录。

## 测试方案

治理实现阶段必须先写测试，再改实现。至少覆盖：

1. Candidate scoring unit tests
   - 未评分候选不能进入 `high_value` 深挖任务。
   - 分数达标但资料可得性不足时分类为 `needs_more_evidence`。
   - 去重风险过高时不能分类为 `high_value`。

2. Needs queue unit tests
   - 同 identity key 同失败原因连续 blocked 后进入正确 needs 队列。
   - 网络恢复并有新 link probe 后，`needs_network` 可回到 `actionable_gaps`。
   - `stopped_no_action` 在 needs 队列无等待条件时失败。

3. Crawler linkage tests
   - 长期来源创建时必须关联 Domain Channel/source profile。
   - base URL trust 可被 child source 继承，但 child source 仍保留 canonical URL 和去重键。
   - 需要鉴权的 channel 不会把 secret 写入仓库。

4. Evaluator gate tests
   - 缺少 search/API/frontend/dashboard 证据时不能 pass。
   - Playwright 用户点击场景失败时不能 pass。
   - changed paths 命中 denylist 或 secret pattern 时 blocked。

5. Commit hygiene tests
   - `.codex`、pid/log、`generated/`、`.worktrees` 不会进入 wiki/crawler 入库 commit。
   - r10/r11 入库文件和治理 spec/代码 commit 能被分开提交。

## E2E 测试用例

E2E-1：r10 后治理接管

- 准备一个已有 autonomous run 达到 `stopped_budget` 的状态。
- 启动 governance parent run。
- 期望：系统不创建下一轮 expansion run，而是创建治理 child backlog。

E2E-2：blocked 分流

- 构造一个 KServe 或 MLCommons source 连续 DNS/HTTP 失败的 gap proof。
- 再次规划。
- 期望：Planner 不重复生成相同抓取任务，而是写入 `needs_network` 或 `needs_seed_url`。

E2E-3：高价值评分门

- 输入三个候选：一个多源可验证项目、一个单页官方文档、一个本地已覆盖重复项目。
- 期望：只有多源可验证项目进入 `high_value` 深挖；单页文档为 medium 或 needs_more_evidence；重复项目 deferred。

E2E-4：crawler workbench 联动

- 新增一个长期 AI infra 来源。
- 期望：Domain Channel、source profile、probe result、scheduler cadence、frontend Domain Channels 页面都可见。

E2E-5：知识入库可见性

- 执行一个小型整理入库任务。
- 期望：wiki validate 通过，backend search/API 查得到，frontend Wiki/知识工作台看得到，dashboard 显示验收场景。

E2E-6：checkpoint 和合入准备

- 多个治理 child 通过后。
- 期望：commit 分类报告完整，禁止文件未入 git，branch checkpoint 存在，父 run 进入 `passed_waiting_human_merge` 等待用户确认。

## 风险和处理

- r10 后台运行期间写 spec 可能造成脏路径混杂。处理：spec 文档只作为单独文件 stage/commit；r10 入库文件由 r10 自己收尾。
- 网络状态可能恢复或再次失败。处理：每次 blocked 决策都必须基于新鲜 link probe，而不是历史记录。
- 高价值评分可能被 agent 主观操纵。处理：evaluator 抽样检查评分证据和本地缺口；评分 artifact 必须引用 source profile、raw、wiki search 或 link probe。
- crawler workbench 与 autonomous loop 改动范围较大。处理：治理用 demand-development 多子任务 loop 分轮做，不和资料扩充同一子任务混做。
- checkpoint 合入可能遇到 main 冲突。处理：只准备合入候选和报告，实际合入 main 仍由用户确认。

## 成功标准

- 当前 r10 完成后，资料扩充不会继续无治理地创建下一轮。
- loop 能明确区分 actionable gap、needs 队列、duplicate 和 no-action。
- 高价值项目必须先评分，深挖任务必须多源可验证。
- 长期来源通过 crawler workbench Domain Channels/source profiles 管理。
- evaluator 能验证资料质量、服务刷新、前端可见性和 dashboard 可读性。
- wiki/crawler 入库 commit 和治理代码/docs commit 分离清楚。
- 恢复 AI infra 拓展后，每一轮的任务选择、跳过、blocked 和停止原因都能被第三方读懂。
