# AI Infra 资料拓展 Loop 继续执行方案

日期：2026-07-08

## 目标

恢复中断的 `ai_infra` domain 资料拓展 loop，但按治理后的规则运行：避免浅抓取、避免重复抓取、避免 blocked 空转，保持 Crawler Workbench、Loop Dashboard 和 loop-auto-resume 在线，并把 Auditor 审计频率控制为每完成 2 个父任务触发一次。

本方案先约束下一次执行方式，不直接开始抓取。

## 当前基线

- `main` 已同步 `origin/main`，最近提交包含 Loop Auditor、自动审计整改、auto-resume watcher 和 crawler freshness 文档。
- Crawler Workbench backend `8765`、frontend `5173`、Loop Dashboard `8766` 当前均在线。
- `loop-auto-resume` tmux 会话在线，当前没有可恢复候选。
- 上一轮资料拓展 `ai-infra-expansion-2026-07-07-r10` 已完成并入库，commit 为 `7f931cf chore(wiki): autonomous knowledge update ai-infra-expansion-2026-07-07-r10`。
- `personal-wiki/domains/ai_infra` 当前 domain validate 通过，Crawler Workbench 搜索 API 能查到 r10 入库内容。
- 当前工作树仍有一组未归属的 SGLang #24456 入库改动：两篇 wiki 更新和一个 untracked ingest-plan。恢复新 loop 前必须先收尾提交，避免混入后续父任务。

## 术语定义

**父任务**：一个顶层资料拓展目标，必须能被第三方读者理解为一件完整工作。例如“整理 SGLang 2026-07 调度补充中的已闭环 runtime 线索”、“深挖 KServe deployment/canary primary sources”、“补齐一批硬件字段解析”。父任务可以包含最多 3 个子任务，但不是单个 URL、单次 generator attempt 或单条 wiki 编辑。

**子任务**：父任务内部的具体动作，例如来源探测、raw 抓取、PDF 保存/抽取、GitHub API backfill、wiki 页面整理、coverage-map 更新、前端可见性验证。

**Auditor 审计频率**：按父任务计数。每完成 2 个父任务后触发一次 Auditor 审计。这里的“完成”要求 evaluator 通过、wiki validate 通过、必要的 crawler/backend/frontend/dashboard 可见性证据齐全、commit 完成且需要推送时已推送。

**安全闸门**：不等同于 Auditor。secret 泄露、未归属 dirty path、required evidence 缺失、服务全挂、Evaluator 连续失败等硬安全问题仍可立即阻断；但普通方向控制、空转、钻牛角尖和 skill 膨胀审计按每 2 个父任务一次执行，避免过度干预。

## P0 执行前门槛

1. **收尾未归属入库**  
   先处理 SGLang #24456 已有改动：确认 raw 已跟踪，提交 ingest-plan、两篇 wiki 更新、`ingest.md` 和必要的 coverage/index 更新。运行：
   - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index ai_infra`
   - `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`
   - Crawler Workbench search/API 和前端可见性检查

2. **确认审计 cadence 能按父任务工作**  
   当前 `run-autonomous` 在 planning boundary 会调用 audit boundary，存在“每个子任务后都审计”的风险。恢复资料拓展前必须选择并验证一种实现：
   - 首选：在 harness policy/run state 中加入 `audit_cadence.unit=parent_task`、`mode=fixed_interval`、`interval=2`，让 ordinary Auditor 只在父任务计数达到 2 时运行。
   - 备选：新增一个 AI infra expansion supervisor/wrapper，负责把多个 autonomous 子任务聚合成父任务，并只在两个父任务完成后调用 `run-auditor`。
   - 不接受：直接启动现有 runtime 然后依赖人工忽略过多审计报告。

3. **创建可见的顶层运行**  
   新建稳定 run ID，例如 `ai-infra-expansion-continuation-20260708`。Loop Dashboard 必须能看到 campaign run、当前父任务、已完成父任务、Auditor 结果、Evaluator 验收和阻塞诊断。

4. **服务持续在线**  
   每个父任务开始和结束都记录：
   - `curl --noproxy '*' http://127.0.0.1:8765/api/health`
   - `curl --noproxy '*' -I http://127.0.0.1:5173/`
   - `curl --noproxy '*' http://127.0.0.1:8766/api/health`
   - `tmux has-session -t loop-auto-resume`

## 父任务选择规则

Planner 每次只能从 `coverage-map.json` 和 `loop-state.json` 中选出一个父任务，并必须先写 gap proof。父任务进入执行前必须满足：

- 有明确 layer 和 coverage gap。
- 本地 wiki/raw/source profile 检查证明不是重复抓取。
- blocked/needs 队列中同 identity key、同失败原因的项不会被原样重试。
- 高价值项目必须先通过 hard gates，不允许 Planner 直接宣布高价值。
- 深挖父任务必须证明至少两类来源或多页证据可获得，例如 official docs + releases/issues，或 docs sitemap + GitHub closed issues。
- 单页 `raw/links` 只允许用于小缺口补充、已知文档的特定字段、或 blocked evidence 记录；不能冒充深挖。

候选优先级：

1. 已有本地 raw 但未完全整理的资料，优先整理入库而不是重复抓取。
2. 可通过 Domain Channels/crawler workbench 长期订阅的官方 docs、release notes、GitHub closed issues/PRs。
3. 对 coverage gap 有明显增益且能产生多页或多来源证据的项目。
4. 硬件字段只在 product-specific table、datasheet、PDF 或明确单卡边界存在时解析。
5. 连续 blocked 或需要鉴权、seed URL、人工判断的项进入 needs 队列，不消耗普通父任务。

## 每个父任务的执行流程

1. Planner 写父任务说明、约束、停止条件、gap proof、预计子任务和验收证据。
2. Generator 执行最多 3 个子任务，按 `raw -> ingest-plan -> wiki -> index/backlinks -> validate` 处理。
3. 如新增长期来源，必须通过 Domain Channels/source profile 记录 base URL、probe 状态、fetcher、cadence 和子来源关系。
4. Evaluator 验证：
   - source_refs 和引用路径存在；
   - wiki validate 通过；
   - search/API 能看到新内容；
   - 前端知识工作台或 Wiki 浏览能看到新内容；
   - Loop Dashboard 能看到当前父任务、agent 行为、evaluator 场景和日志；
   - 没有 secrets、`.codex`、pid/log、`generated/`、`.worktrees` 混入提交；
   - 若改了 crawler/harness/frontend/backend，相关单测和浏览器 E2E 必须通过。
5. 提交策略：
   - wiki/crawler 入库 commit 独立提交，优先 `chore(wiki): ...` 或 `docs(wiki): ...`。
   - 代码修复 commit 与资料入库 commit 分开。
   - 如果提交已在 `main`，按既定要求推送到 `origin`。
6. 父任务完成后更新 campaign run 状态和 Dashboard reader summary。

## Auditor 触发规则

正常路径：

```text
父任务 1 完成 -> 不触发普通 Auditor，只记录 counters
父任务 2 完成 -> 触发 Auditor 审计
审计 pass -> 继续父任务 3
父任务 3 完成 -> 不触发普通 Auditor
父任务 4 完成 -> 触发 Auditor 审计
```

Auditor 输入必须包括：

- 最近两个父任务的 planner/generator/evaluator/artifact/commit 证据；
- coverage-map 和 loop-state diff；
- blocked/needs 队列变化；
- git status 和 commit/push 状态；
- Crawler Workbench backend/frontend freshness 证据；
- Loop Dashboard 当前 run 可见性证据；
- skill inventory 摘要。

Auditor 只审计跨父任务行为：是否空转、偏航、钻牛角尖、重复犯错、浅抓取、skill 膨胀或流程债务复发。它不替代单个父任务的 evaluator。

事件触发例外仅限硬安全或流程失真：

- 发现 secret/token/cookie 进入候选提交；
- unclassified dirty paths 与父任务范围冲突；
- 连续 2 次 evaluator fail/blocked；
- Dashboard 无法显示当前 active run；
- Crawler backend/frontend 全部不可用且重启后仍失败；
- Planner 试图执行与用户目标无关的任务。

这些情况可以立即进入 `audit_blocked` 或 `stopped_blocked`，但报告中必须说明这是安全/流程中断，不是普通 cadence 审计。

## 全局停止条件

全局 loop 继续运行，直到满足以下任一条件：

- `coverage-map.json` 的 8 个 layer 都没有 immediate actionable gap，剩余项全部在 `needs_network`、`needs_auth`、`needs_seed_url` 或 `needs_human_judgement` 中，且每项有等待条件。
- 连续 2 个父任务规划周期没有发现 high/medium value 且可获取的候选，形成 `stopped_no_action` 证据。
- Auditor 连续指出方向偏离或 tunnel vision，整改后仍无法恢复有效进展，进入 `stopped_blocked` 请求用户决策。
- 网络、鉴权或来源访问条件使外部拓展不可行动，只能整理本地 raw；本地 raw 也整理完后停止。
- 预算达到用户后续设定的上限。未设上限时，每完成 4 个父任务做一次人工状态汇报，但不要求每次都暂停。

## 本次恢复的首批建议父任务

恢复前第 0 步不是父任务：先提交 SGLang #24456 未归属入库。

父任务 1 候选方向：`SGLang scheduled refresh triage`  
整理 2026-07-05 到 2026-07-07 scheduled crawler supplement 中已有 local raw 的已闭环 inference-runtime 线索，避免重复 GitHub 抓取。该任务适合检验“已有 raw 优先整理”的治理规则。

父任务 2 候选方向：`KServe and inference deployment evidence reprobe`  
对 r9 blocked 的 KServe autoscaling/canary/SLO trace 来源做廉价 DNS/HTTP 复探。只有网络和内容可抓取时才进入多页 primary-source capture；否则更新 needs_network/blocked evidence，不写浅层假入库。

父任务 1 和父任务 2 完成后触发第一次 Auditor。若 Auditor 认为方向过窄或 SGLang/KServe 仍在消耗局部问题，则父任务 3 改向 training/network-storage/security-cost 中的高价值候选，而不是继续钻 inference-runtime。

## 验证清单

每个父任务完成必须至少提供：

- `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`
- 相关 API 搜索或 wiki 页面读取证据
- 前端可见性证据
- Loop Dashboard run detail 可见性证据
- `git status --short` 分类结果
- commit hash，若在 main 则包含 push 结果

每两个父任务完成必须额外提供：

- Auditor report path
- deterministic signals path
- open `must_fix` 是否为 0
- 若有 `must_fix`，整改任务路径和复审结果

## 执行入口

用户确认本方案后，执行顺序为：

1. 收尾并提交 SGLang #24456 未归属入库。
2. 注册/更新 `tasks.json` 中的本次 continuation task。
3. 修正或验证父任务级 `audit_cadence` 能生效。
4. 创建可在 Loop Dashboard 展示的 continuation run。
5. 执行父任务 1 和父任务 2。
6. 触发第一次 Auditor 审计。
7. 根据 Auditor 结果继续、整改或停止。
