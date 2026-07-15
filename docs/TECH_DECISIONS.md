# 技术决策记录

## File-first Codex skills
**用途**：每个 skill 用目录和 `SKILL.md` 表达可复用工作流。
**选择原因**：仓库 README 和目录结构显示主要目标是复用 Codex 工作流，文件式组织便于本地安装、版本化和逐个发布。
**替代方案**：集中式数据库或服务端 skill registry；当前仓库以本地文件和 Git 版本控制为主，不需要运行服务。
**注意事项**：项目专属状态不要写回通用 skill，避免污染可复用模板。

## Personal Wiki file model
**用途**：用 Markdown frontmatter、`raw/` 证据和 `wiki/` curated 页面维护个人知识库。
**选择原因**：`personal-wiki/WIKI.md` 和 CLI 表明核心原则是 file-first、可审计和可压缩。
**替代方案**：SQLite/向量库作为事实源；当前选择保留 Markdown 和 raw evidence 作为主记录，数据库只服务 crawler workbench 状态。
**注意事项**：删除或移动 raw evidence 前必须更新 `source_refs`、links 和 manifest。

## FastAPI crawler backend
**用途**：为本地 crawler workbench 提供 API、scheduler、SQLite 状态和 Codex ingest 入口。
**选择原因**：FastAPI 与 Pydantic 适合快速构建本地 API，TestClient 支持低成本测试。原始选型原因需要维护者确认。
**替代方案**：Flask、Django、纯 CLI。当前项目需要 UI 和 API，所以 FastAPI 是轻量选择。
**注意事项**：服务无登录能力，不应暴露到不可信网络。

## React/Vite frontend
**用途**：提供 crawler sources、queue、settings、knowledge graph 等本地 UI。
**选择原因**：Vite 能快速开发 TypeScript React 单页应用。原始选型原因需要维护者确认。
**替代方案**：Next.js、Svelte、纯 HTML。当前 UI 不需要 SSR，Vite 更简单。
**注意事项**：前端依赖 backend `/api` 代理，远程访问时只需打开 frontend 地址。

## SQLite state store
**用途**：保存 crawler source profiles、fetch runs、raw items、ingest tasks、validation runs 和 commits。
**选择原因**：单用户本地应用不需要外部数据库，SQLite 易于隔离 state dir 和测试。
**替代方案**：PostgreSQL、纯文件队列。当前复杂度下 SQLite 足够。
**注意事项**：evaluator 场景应使用隔离 state dir，避免复用开发者本地状态。

## SQLite Loop Supervisor control store
**用途**：保存 loop run projection、action queue、lease、failure、Reviewer、user decision、service、freshness、skill snapshot 和 retention aggregate。
**选择原因**：旧 JSONL 每个 tick 重复写相同决策，无法可靠提供原子租约、幂等队列、分页查询和恢复账本。标准库 `sqlite3` 的 WAL、foreign keys、busy timeout 和显式事务满足本地单仓库控制面的并发边界，无需增加服务依赖。
**替代方案**：继续使用 JSONL watcher、引入 PostgreSQL、把控制状态写回 `run.json`。JSONL 缺少事务语义，PostgreSQL 对本地单用户运行时过重，`run.json` 不适合承载 project-global queue/review 状态。
**注意事项**：`run.json` 和 retained artifacts 仍是可移植事实；SQLite 只是可重建运行时源。迁移必须 streaming、先 snapshot、后 validate，shadow compare 增加用户介入时必须阻止切换。Supervisor 决策与 Worker 执行分离，transition registry 是唯一 policy 来源。

## Step4 evaluator gates
**用途**：用 Stop/SubagentStop hooks 和 repo-side evaluator bundle 强制独立验证关键任务。
**选择原因**：用户明确要求独立 evaluator 作为使用方验证 wiki crawler 功能，Step4 提供任务级 scenario、bundle 和 result contract。
**替代方案**：只跑单元测试或人工验收；这不能覆盖 agent 自评不可信的问题。
**注意事项**：当前 Codex CLI 的 Stop hook 需要真实交互式 session 才能证明自动触发，`codex exec` 不能单独证明。

## 待人工确认
- 各历史 skill 的业务背景和保守收益估算是否仍准确。
- crawler frontend 是否计划长期保持无登录本地工具，还是未来要加入认证和多用户模型。
