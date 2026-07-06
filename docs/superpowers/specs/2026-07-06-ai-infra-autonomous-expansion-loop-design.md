# AI Infra 自治资料扩充 Loop 设计

日期：2026-07-06

## 背景

用户希望通过现有 Planner -> Generator -> Evaluator -> Planner loop 扩充 `personal-wiki/domains/ai_infra`，覆盖从上层训练、推理到下层硬件、网络、存储的 AI infrastructure 资料和 wiki 内容。

这不是一次普通 wiki 入库任务。它需要长期、分轮、自动规划，并且在运行中可能发现 crawler、harness、前端、后端或索引刷新逻辑存在问题。用户已确认：资料扩充 loop 可以在必要时修改任意仓库内容并提交，但必须避免重复抓取本地已有资料或之前已经抓取过的资料。

当前 `autonomous-knowledge` 实现是保守版本：自动提交范围主要限制在 `personal-wiki/domains/**` 证据、wiki、source、manifest 和 `loop-state.json`。因此本设计先补齐 AI infra 资料扩充的 preflight 约束、去重规则、覆盖矩阵、验收规则和扩展 policy 草案。正式运行前，Planner 必须把这些规则写入本次 run 的 `preflight.md` 和 `planner-output.json`；如果需要 repo-wide 自动修复能力，还必须先接入扩展 policy 或由需求开发 loop 实现对应支持。

## 用户已确认的需求

- 覆盖范围：AI infrastructure 从上层训练、推理到底层硬件都要全面涉及。
- 来源范围：采用来源策略 B，包括官方文档、GitHub releases/issues/PRs、论文、厂商技术博客、高质量第三方 benchmark 和实践报告。
- 自动循环：每轮最多执行 3 个子任务，多轮之间自动继续。
- 修改权限：运行中允许修改任意仓库内容并 commit，包括 crawler、harness、crawler workbench 前端/后端和测试。
- 入库要求：新知识入库后需要前后端同步刷新验证。
- 去重要求：不要重复本地已有资料或之前已经抓取过的资料；每个候选任务都必须先给出缺口证明。
- 当前阶段：先补齐方案、约束、停止条件和策略草案，经用户确认后再启动正式扩充 loop。

## 目标

1. 定义 AI infra 资料扩充的覆盖矩阵，让“全面”可以被 Planner 和 Evaluator 判断。
2. 定义每个候选任务进入 Generator 前必须满足的去重和缺口证明。
3. 定义扩展 autonomous policy 草案，允许 repo-wide 自动修复，但仍禁止 secrets、凭据、运行产物和高风险路径。
4. 定义任务级和轮次级 Evaluator 验收标准，包括 wiki、raw、搜索、前端、dashboard 和代码测试。
5. 定义“无可行动缺口”的停止条件，避免 loop 因重复候选或泛化目标无限运行。
6. 定义 commit 分组和工作树安全规则，避免把已有 dirty raw 产物、`.codex` 日志或 `generated/` 混入错误提交。

## 非目标

- 本 spec 不直接抓取或入库新的 AI infra 资料。
- 本 spec 不直接修改 current `autonomous-knowledge` hardcoded scope 行为。
- 本 spec 不允许自动提交 token、cookie、`.env`、凭据、私有 key、浏览器缓存、`.codex` 运行日志、`generated/` 临时目录或 `.worktrees/` 内容。
- 本 spec 不要求一次性历史全量抓取整个互联网或所有项目 issue。
- 本 spec 不把第三方 benchmark 当作无条件事实来源；第三方结论必须标注来源等级和适用边界。

## 覆盖矩阵

Planner 必须按以下 layer 维护覆盖状态。每个 layer 至少要能回答：已有本地页面是什么、已有 raw 证据是什么、缺口是什么、候选来源是什么、最近扫描时间是什么。

| Layer | 范围 | 初始高优先级主题 |
| --- | --- | --- |
| training-distributed | 分布式训练、并行策略、checkpoint、容错、通信、集群作业生命周期 | Megatron/DeepSpeed/FSDP、NCCL、checkpointing、elastic training |
| inference-runtime | 推理 serving、batching、routing、KV cache、runtime、模型格式 | vLLM、SGLang、TensorRT-LLM、Triton、llama.cpp、ONNX Runtime GenAI |
| orchestration-scheduling | Kubernetes AI workload 调度、队列、device plugin、quota、gang scheduling | Kubernetes、Volcano、Kueue、Ray、Slurm on Kubernetes |
| data-rag-vector | 数据管道、embedding、向量数据库、RAG serving infra、feature/metadata infra | Milvus、Weaviate、Qdrant、pgvector、Kafka/Flink for AI pipelines |
| eval-observability-reliability | 评测平台、观测、trace、profiling、incident、SLO、debug 工具 | OpenTelemetry for LLM apps、LangSmith/Langfuse、NVIDIA Nsight、NCCL observability |
| security-governance-cost | AI 平台安全、租户隔离、合规、成本、容量规划 | GPU 多租户、MIG、confidential computing、quota/cost attribution |
| hardware-accelerator | GPU、NPU、TPU、DPU、IPU、FPGA、DSA、AI ASIC 参数和 SKU | NVIDIA/AMD/Intel/Google/华为/寒武纪/燧原/壁仞/摩尔线程/沐曦/天数智芯 |
| network-storage-cluster | AI cluster 网络、存储、拓扑、RDMA、InfiniBand、Ethernet、parallel filesystem | InfiniBand、RoCE、Spectrum-X、Lustre、Weka、Ceph、NVMe-oF |

覆盖状态可以先用 `personal-wiki/domains/ai_infra/loop-state.json` 的现有字段表达：

- `known_sources`: 已确认来源，`evidence` 写入 source profile、wiki 页面、raw manifest 或 gap proof artifact。
- `candidate_backlog`: 待处理候选资料或候选来源。
- `coverage_gaps`: 因鉴权、网络、反爬、范围过大或需要人工判断而 blocked 的缺口。
- `blocked_items`: 需要用户输入、凭据、授权或策略决策的项。
- `no_action_evidence`: 停止前的覆盖矩阵和去重扫描证据。

如后续需要结构化查询 coverage，应新增单独的 `coverage-map.json` 或扩展 loop-state schema；在未改 schema 前，不把自定义对象塞进现有字段以免破坏 validator。

## 来源策略

来源优先级从高到低：

1. 官方文档、release notes、规格表、白皮书。
2. 项目 GitHub releases、closed issues、closed PRs、discussions 中已闭环的工程问题。
3. 论文和技术报告，优先 DOI、arXiv ID 或会议版本稳定的来源。
4. 厂商工程博客、云厂商实践博客、项目维护者博客。
5. 高质量第三方 benchmark、生产实践报告和事故复盘。

规则：

- 第三方来源不能单独支撑强事实结论，除非页面明确标注为第三方观点或 benchmark 条件。
- 对硬件规格，官方规格表优先于新闻稿、百科、经销商页面。
- 对 GitHub issue/PR，只入库 closed 状态或 release-linked 结论；open issue 只能作为候选，不作为已闭环事实。
- 对论文，必须用 DOI、arXiv ID 或稳定 URL 做去重键。
- 对需要鉴权的来源，Planner 只能把它放入 `blocked_items`，不能要求用户在仓库或 source yaml 中提交 token。

## 去重和缺口证明

每个候选任务进入 Generator 前，Planner 必须生成 gap proof。建议路径：

```text
.codex/loop-runs/<run-id>/gap-proofs/<task-id>.json
```

该文件是 run artifact，不默认提交。Planner 需要在 `planner-output.json` 的 `next_planning_hint` 或 `allowed_paths` 旁引用它。

Gap proof 必填字段：

```json
{
  "task_id": "ai-infra-expansion-task-001",
  "layer": "inference-runtime",
  "candidate": {
    "title": "vLLM prefix caching operational notes",
    "source_type": "official_docs",
    "canonical_url": "https://docs.vllm.ai/...",
    "identity_key": "url:https://docs.vllm.ai/..."
  },
  "local_checks": {
    "url_canonicalization": "pass",
    "raw_manifest_scan": "no_existing_capture",
    "wiki_search": "no_existing_curated_page",
    "source_profile_scan": "source_known_or_new",
    "domain_index_scan": "no_duplicate_page",
    "specialized_identity_scan": "not_applicable"
  },
  "gap_reason": "No curated ai_infra page explains this runtime behavior with source-backed operational guidance.",
  "planned_outputs": [
    "raw evidence capture",
    "curated wiki page or update",
    "index/backlinks/search refresh"
  ]
}
```

去重键规则：

- Web 文档：canonical URL，去掉 tracking query，规范化 host、path、fragment。
- GitHub issue/PR：`github:<owner>/<repo>#<number>`。
- GitHub release：`github-release:<owner>/<repo>@<tag>`。
- 论文：`doi:<doi>` 或 `arxiv:<id>`。
- 硬件型号：`hardware:<vendor>:<normalized_model>:<sku_or_memory_variant>`。
- Crawler source：`source-profile:<source_id>` 和 base URL trust 规则。
- 本地 wiki 页面：frontmatter `title`、aliases、路径和全文检索关键词组合。

如果本地已有 raw 但没有 curated wiki，任务可以是“整理入库”，不能重复抓取原始来源。  
如果已有 curated wiki 但缺少某个关键版本、SKU 或 release 后的变化，任务必须写明增量点。  
如果连续 2 轮只发现重复候选，Planner 必须把重复扫描证据写入 `no_action_evidence`，而不是继续制造等价任务。

## 扩展权限策略

本次 AI infra 扩充需要两层策略：

### 保守执行策略

在当前 orchestrator 未接入扩展 policy 前，正式 `run-autonomous` 只能安全使用现有 `autonomous-knowledge` 能力：

- 自动提交 wiki/raw/source/manifest/loop-state。
- 如遇到必须修改 crawler、harness、frontend、backend 或 tests 的情况，当前实现会因为 scope check 停在 `stopped_blocked`。
- 停住后应启动需求开发 loop 修复代码，再恢复 AI infra 资料扩充。

### 扩展执行策略草案

文件：`docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json`

意图：

- 仍使用 `autonomous_knowledge` 语义。
- 允许 repo-wide 修改以修复资料扩充链路，包括 `docs/**`、`scripts/**`、`apps/**`、`personal-wiki/**`、`tasks.json`、`progress.md`、`AGENTS.md`。
- 禁止 secrets、凭据、`.codex/**`、`.worktrees/**`、`generated/**`、依赖缓存、build 输出和本地服务 pid/log。
- 依赖文件变更必须提供 supply-chain necessity 和 verification evidence。

要真正无人值守生效，需要后续实现以下任一项：

1. `harness_loop_orchestrator.py` 支持从 policy fixture 读取 allowed/manual/deny patterns，并在 preflight/run 中记录所用 policy file。
2. 新增专用 mode，例如 `autonomous-knowledge-expanded`，但仍保持 no auto merge main。

在这项实现完成前，扩展 policy 只能作为 preflight 约束和 evaluator 检查依据，不能假设 runtime 已自动采用。

## Evaluator 验收标准

每个子任务必须通过以下检查，缺一项不能 pass：

- `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra`
- gap proof 存在，且包含 local duplicate checks。
- raw evidence 存在，或任务明确是基于已有 raw 的整理入库。
- curated wiki 页面或已有页面更新包含 `source_refs`。
- `wiki/index.md` 或索引产物反映新增/更新页面。
- 搜索/API 可见性：通过 `/api/wiki/pages`、`/api/wiki/page` 或 `/api/search` 能查到新增内容；如果本轮未启动服务，必须记录原因。
- 前端可见性：知识工作台或 Wiki 浏览页至少验证一个新关键词或新页面标题；涉及 UI 变更时必须用 Playwright 模拟用户操作。
- Crawler Workbench 及时刷新：新 source、fetch run、queue 状态、raw capture、wiki 页面和 search 结果必须能通过 backend API 读到；如果长驻 backend/frontend 正在运行，Evaluator 必须验证页面无需人工重建仓库状态即可看到最新数据，必要时记录已重启的服务和原因。
- Loop Dashboard 及时刷新：每个子任务至少写入 reader summary、agent action、scenario result、错误/阻塞和用户决策字段；Dashboard 必须能显示当前 run、已完成 run、子任务进度、Planner/Generator/Evaluator 正在做什么，以及 evaluator 模拟用户验收过哪些场景。
- 链接检查：新引入的外部链接至少执行连接性探测；失败需要记录 HTTP 状态、DNS/TLS/timeout 原因或 blocked/auth 原因。
- secrets scan：本次 changed paths 中不能出现 GitHub token、Authorization bearer、cookie、private key 或 `.env` 内容。
- 若修改代码：运行对应单元测试、集成测试或 UI 测试，不能只跑 wiki validate。
- 若修改 crawler source profile：执行连接探测或 fetch dry-run，并记录是否需要鉴权。
- 若新增或修改来源订阅：必须走新 Domain Channels 模型，而不是只改旧 `sources.yaml`。Planner/Generator 需要确定 target domain、channel、base URL trust、secret/probe readiness、child source 关系、fetcher_type 和 scheduler cadence；Evaluator 需要验证 `/domains`、`/channels`、`/sources?domain=...`、probe API、source run continuity 和前端 Domain Channels 页面。

## Domain Channels 和来源订阅约束

AI infra 扩充会频繁新增来源，必须使用新开发的 Domain Channels 功能作为来源管理入口：

- `ai_infra` 是本次默认 target domain。跨 domain 资料只能在 Planner 明确说明边界后加入。
- 每个长期来源必须属于一个 channel；临时 one-shot URL 可进入 inbox 或临时 channel，但不能绕过 domain/source 可见性。
- 如果 base URL 已被用户标记可信，新增同 base URL 子来源可以继承信任，但仍要记录 canonical URL、source id 和去重键。
- 需要鉴权的 channel 只保存 synthetic/metadata readiness，不把 token 写入仓库；缺少凭据时写入 `blocked_items`。
- 新增 channel/source 后必须执行 probe 或 fetch dry-run。失败要记录 DNS、TLS、HTTP、timeout、auth、rate limit 或 robots/反爬原因。
- 调度规则：已有型号/已有静态规格不需要高频重复抓；新型号/新规格发现默认月度扫描。高频 release notes 或 GitHub closed issue 同步必须单独说明 cadence。
- Crawler Workbench 前端验收必须覆盖 Domain Channels 页面的 domain 筛选、channel/source 可见性、probe 结果、child source 创建或展示，以及旧 Sources/Queue 页不会丢失新 source。

## 运行可见性和刷新约束

每轮知识入库后，loop 不只要提交文件，还要证明用户能在 UI 和 API 里看到变化：

- Crawler backend：验证 `/api/wiki/pages`、`/api/wiki/page`、`/api/search`、`/api/sources`、`/api/channels`、`/api/queue` 或对应 run API 返回最新数据。
- Crawler frontend：用 Playwright 搜索一个新关键词，打开新 wiki 页面，查看相关 source/channel 或 queue 记录。
- Search/index：优先验证自动刷新；只有自动刷新失败或 schema/index 逻辑变更时才手动 `/api/search/rebuild`，并记录原因。
- 服务重启：修改 backend 代码、schema、搜索索引逻辑或运行配置后重启 crawler backend；修改 frontend 代码或 Vite 配置后重启 crawler frontend；只改 wiki/raw 时不默认重启，但必须验证 API/前端读到新内容。
- Loop Dashboard：验证当前 run 出现在运行列表，子任务状态和事件随 artifact 更新而变化，完成后的 run 仍能从历史中看到。
- 报告格式：每个 run 的最终摘要必须让不了解项目背景的人读懂任务是什么、进展到哪里、验收了哪些用户场景、是否有错误、是否需要用户决策。

## 测试方案

正式开发或首次运行前，至少执行：

```bash
python3 -m json.tool docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json >/dev/null
python3 - <<'PY'
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, validate_loop_policy_payload
for path in Path("docs/harness/loop-policies").glob("*.json"):
    validate_loop_policy_payload(read_json_file(path))
PY
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
git diff --check
```

当后续实现扩展 policy runtime 支持时，必须新增单元测试覆盖：

- policy fixture 能被 preflight/run 读取。
- repo-wide allowed path 能通过 scope check。
- `.codex/**`、`.worktrees/**`、`generated/**`、secret/token/credential 路径仍被拒绝。
- dependency file 变更没有 supply-chain evidence 时被拒绝。
- baseline dirty paths 不会被误归入当前任务。

## E2E 测试用例设计

### E2E-1：纯 wiki 扩充闭环

用户目标：验证现有 `autonomous-knowledge` 可以完成一个去重后的 ai_infra wiki/raw 入库任务。

步骤：

1. 创建隔离 clone 或 worktree。
2. 写入包含一个候选项的 `personal-wiki/domains/ai_infra/loop-state.json`。
3. 运行 `run-autonomous`，使用 fake 或受控 codex-exec driver。
4. 验证新增 raw/wiki/loop-state 被提交。
5. 验证第二轮 planner 因 no-action evidence 停止。

预期：

- 进入 `stopped_no_action` 或在任务上限处 `stopped_budget`。
- `commit-result.json` 存在。
- wiki validate 通过。
- gap proof 和 no-action evidence 可读。

### E2E-2：重复候选不会重复抓取

用户目标：验证已有 URL、GitHub issue、论文或硬件型号不会重复入库。

步骤：

1. 在测试仓库中准备已有 raw manifest 和 curated wiki。
2. Planner 生成相同 canonical URL 或 identity key 的候选。
3. Evaluator 检查 gap proof。

预期：

- Generator 不重复抓取 raw。
- Planner 将候选标记为 duplicate 或 convert-to-curation-only。
- 连续 duplicate-only 达到阈值时写入 no-action evidence。

### E2E-3：代码修复需求触发扩展策略

用户目标：验证资料扩充中需要改 crawler/backend/frontend 时不会被错误当作普通 wiki 入库。

步骤：

1. 让 Generator 声明需要修改 `scripts/**` 或 `apps/**`。
2. 在当前保守 runtime 下，确认 scope check 会停在 `stopped_blocked` 并提示需要扩展 policy 或需求开发 loop。
3. 在后续扩展 runtime 实现后，确认同类路径可在扩展 policy 下通过，但 denylist 路径仍失败。

预期：

- 当前实现不会静默提交非 allowlist 代码改动。
- 扩展实现必须有 scope、supply-chain、测试和 evaluator 证据。

### E2E-4：前后端刷新可见性

用户目标：验证新知识入库后，前端能看到。

步骤：

1. 入库一个唯一关键词的 ai_infra 页面。
2. 如后端索引逻辑或运行配置变更，重启 backend；如前端代码变更，重启 frontend。
3. 调用 `/api/search` 查询唯一关键词。
4. 用 Playwright 打开知识工作台或 Wiki 浏览页，搜索或打开该页面。

预期：

- API 返回新内容。
- 前端显示标题或正文片段。
- evaluator artifact 记录截图或 DOM 断言。

## 停止条件

任一条件满足时停止：

- `stopped_no_action`: 所有 coverage layer 无高优先级 actionable gap；`candidate_backlog` 为空；`coverage_gaps` 为空或仅含 blocked 且已写明原因；`known_sources` 覆盖所有 layer；`last_scan_at` 在 30 天 TTL 内；`no_action_evidence` 包含覆盖矩阵、来源扫描摘要和重复候选摘要。
- `stopped_budget`: 单次 invocation 达到 4 轮、12 个子任务、240 分钟、20 次网络抓取或 250 MB 新 raw 证据任一上限。
- `stopped_blocked`: 遇到需要用户鉴权、付费访问、法律/许可不明、反爬限制、连续 3 次网络失败、dirty path 触碰用户未提交改动、denylist 路径、或 evaluator 连续失败。
- `repair_needed`: evaluator 发现可修复问题且仍在当前子任务 attempt 限制内。
- `manual_review_required`: 需要合入 `main`、需要新增长期凭据、需要扩大来源范围、需要改变 stop condition 或需要删除/压缩 raw 证据。

重复候选专门规则：

- 单轮发现的候选如果超过 80% 是 duplicate，只允许保留真实增量项。
- 连续 2 轮 duplicate-only 时，本次 loop 必须停止为 no-action，并把 duplicate proof 写入 `no_action_evidence`。

## Commit 规则

自动或人工整理提交时按类型拆分：

- `docs(wiki): expand ai infra <layer>`：curated wiki、index、source refs。
- `chore(wiki): capture ai infra raw sources`：raw evidence、manifest、ingest log。
- `chore(crawler): add ai infra source profile`：source profile、scheduler 配置。
- `fix(crawler): ...`、`fix(harness): ...`、`fix(loop-dashboard): ...`：运行中发现并修复的代码问题。
- `docs(harness): define ai infra expansion loop`：本 spec、policy、harness 文档。

禁止把以下内容提交进资料入库 commit：

- `.codex/*.log`、pid、loop dashboard 本地服务日志。
- `generated/` 临时目录。
- `.worktrees/` 内容。
- 浏览器、Playwright、node、Python cache。
- 与本轮 gap proof 无关的旧 raw 产物。

## 正式启动前 Checklist

1. 用户确认本 spec 的覆盖矩阵、去重规则、权限策略和停止条件。
2. 当前工作树 dirty paths 已分类：本任务产物、已有 crawler raw、运行日志、无关改动。
3. 如果使用当前保守 autonomous runtime，接受“代码修复会 blocked，需要另起需求开发 loop”的限制。
4. 如果要求 repo-wide 自动修复不停机，先实现 policy fixture runtime 接入并通过 E2E-3。
5. 创建 ai_infra expansion run 的 `preflight.md`，写入本 spec 的约束和用户确认。
6. 首轮 Planner 只能选择有明确 gap proof 的最多 3 个子任务。
