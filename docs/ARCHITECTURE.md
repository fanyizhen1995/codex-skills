# 架构说明

## 整体结构
本仓库是多技能和工具的 monorepo。一级目录大多是独立 skill，`personal-wiki/` 是文件式知识库和 crawler workbench，`codex-model-router/` 是独立代理工具，`docs/` 保存跨仓库的计划、规格和 harness 文档。

```text
.
├── */SKILL.md                         # 独立 Codex skill 定义
├── */README.md                        # skill 或工具说明
├── codex-model-router/                # OpenAI-compatible 路由代理
├── docs/
│   ├── exec-plans/                    # harness step1/2 计划状态
│   ├── harness/                       # Step4 evaluator 文档和场景
│   └── superpowers/                   # 设计和实现计划
└── personal-wiki/
    ├── tools/wiki_cli/                # 文件式 wiki CLI
    ├── apps/crawler_workbench/        # FastAPI + React crawler UI
    ├── domains/                       # 领域 wiki/raw 证据
    └── skills/personal-wiki-manager/  # wiki 管理 skill
```

## 主要模块职责
- **Skill 目录**：每个 skill 以 `SKILL.md` 为入口，`README.md` 解释用途，`agents/openai.yaml` 提供 agent metadata，`scripts/` 放配套自动化。
- **`personal-wiki/tools/wiki_cli/`**：负责 wiki scaffold、validate、index、backlinks、graph、snapshot 和 ingest-plan。
- **`personal-wiki/apps/crawler_workbench/backend/`**：FastAPI 应用。`api.py` 暴露端点，`fetch_service.py` 抓取 source，`ingest.py` 管理审批和 ingest，`wiki_cli.py` 调用 wiki CLI。
- **`personal-wiki/apps/crawler_workbench/frontend/`**：React/Vite UI，按页面和组件拆分，使用 `/api` 代理访问 backend。
- **`harness-step4-evaluator-gates/`**：本地拉下来的 Step4 skill/template 源。它不是运行时目标；安装后运行时归本仓库 `scripts/`、`docs/harness/` 和 `.codex/evaluations/templates/` 所有。
- **`scripts/loop_supervisor/`**：统一 loop 控制面。Supervisor 负责 reconcile、transition policy、恢复、Reviewer 和队列；Worker 只租约并执行 bounded action；SQLite 是可由 run artifacts 重建的运行时投影。
- **`docs/superpowers/`**：设计和计划记录。已提交的 spec/plan 是当前 harness evaluator 安装的来源。

## 依赖方向规则
- skill 文档和脚本应保持项目无关；项目专属验证逻辑放在目标仓库的 `docs/harness/evaluator-scenarios/` 和 `scripts/`。
- crawler backend 可以调用 wiki CLI 和本地 Codex；wiki CLI 不应反向依赖 crawler backend。
- frontend 只能通过 API 类型和 HTTP 端点访问 backend，不直接读写 repo 文件。
- `raw/` 是事实来源，`wiki/` 是 curated 层。curated 页面必须通过 `source_refs` 或正文引用回 raw 证据。
- Step4 hook driver 必须在没有 repo-side runtime 的目录里安全 no-op，避免影响其他项目。
- loop transition policy 只能来自 `scripts/loop_supervisor/registry.py`；Worker、迁移兼容层和测试不得维护第二套 actionable phase 列表。
- `scripts/harness_loop_orchestrator.py` 只保留 Worker 依赖的低层执行原语和非多轮兼容命令，不是公开运行角色；独立 auto-resume 和 Auditor runtime 已移除。
- 运行时 SQLite 连接必须在打开数据库前持有共享 maintenance lock；`rebuild-db` 持有同一把锁的独占模式完成 quiescence 检查、构建、交换和回滚，Supervisor heartbeat 持久化也使用共享模式。现有 live DB 的 rebuild 只在 Linux/POSIX 上执行 `fcntl` advisory byte-lock preflight；该检查无法识别或证明当前 SQLite VFS，SQLite checkpoint 才是 authoritative safety gate。checkpoint 后生成的独立 DELETE-mode DB 用于一次原子替换回滚，每次正向或回滚替换后都 fsync live DB 目录，原始 DB/WAL/SHM triad 只保留作 forensic evidence。

## 主要数据流
### Personal Wiki CLI
用户或脚本调用 `personal-wiki/tools/wiki_cli/cli.py`，CLI 根据 `--root` 定位 wiki 根目录，然后执行 validate、index、backlinks、ingest-plan 等文件操作。输出是 Markdown、JSON 或退出码。

### Crawler Workbench
`Settings` 解析 repo root 和 state dir -> `main.create_app()` 初始化 SQLite 和 source profiles -> `fetch_service.run_source_once()` 调用对应 fetcher -> `raw_store.write_raw_item()` 写入 raw evidence -> `ingest_tasks` 入队 -> API 或脚本 approve -> `ingest.run_approved_task()` 执行 ingest-plan、Codex curation、index、backlinks、validate 和可选 commit。

### Step4 Evaluator
交互式 Codex session 结束触发 Stop hook -> `scripts/harness_evaluator_hook_driver.py` 解析 session/task 状态 -> 创建 evaluator bundle -> `harness_evaluator_orchestrator.py` 运行 read-only evaluator 或 shell scenario -> `result.json` 和 `summary.md` 写入 `.codex/evaluations/tasks/<task-id>/...`。

### Loop Supervisor
`run.json` 和 retained transition artifacts -> Supervisor reconcile -> SQLite run/action/recovery/review projection -> Worker 原子租约 -> 单个 bounded primitive -> result/evidence -> 下一次 reconcile。Reviewer cadence 从稳定 lineage 的 semantic-parent completion records 重建，每两个 parent 触发一次 project-global read-only review。JSONL 迁移必须逐行读取，先在 Git index 外保存快照，再验证 count、first/last timestamp、decision status、run projection 和 cadence；shadow compare 增加用户介入时禁止切换。

## 待人工确认
- 部分 historical skill 的原始设计动机只能从 README 和提交历史推断，需要维护者补充更精确的背景。
