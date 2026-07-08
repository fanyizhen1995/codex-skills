# codex-skills — Agent 工作指南

## 这是什么项目
这是一个可复用 Codex skills、配套脚本和个人 wiki 工具集合。仓库同时包含 `personal-wiki` 文件式知识库，以及 `personal-wiki/apps/crawler_workbench` 本地单用户 crawler workbench。

## 快速定向
- **我在哪个目录？** 运行 `pwd`，目标根目录是 `/home/fyz/codex-skills`
- **技术栈**：Markdown skills + Python 工具/测试 + FastAPI backend + React/Vite frontend
- **主要入口**：skill 入口是各目录 `SKILL.md`；wiki CLI 是 `personal-wiki/tools/wiki_cli/cli.py`；crawler backend 是 `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py`
- **初始化命令**：`bash init.sh`
- **wiki 验证**：`python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate`
- **crawler backend 测试**：`cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q`
- **crawler frontend 测试**：`cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build`

## Crawler Workbench 本地开发 / 部署
这是本仓库当前主要的本地应用。服务无登录能力，能触发本地 `codex exec` 并写入仓库；只在可信网络中绑定 `0.0.0.0`。

### 长驻开发服务
Backend 默认端口是 `8765`，scheduler 默认启用：

```bash
tmux new -s personal-wiki-crawler-backend
cd /home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=$PWD \
PW_WORKBENCH_REPO_ROOT=/home/fyz/codex-skills \
PW_WORKBENCH_SCHEDULER_INTERVAL_SECONDS=60 \
python3 -m uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765
```

Frontend 默认端口是 `5173`，Vite 会把 `/api` 代理到 `http://localhost:8765`：

```bash
tmux new -s personal-wiki-crawler-frontend
cd /home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

前端访问：`http://127.0.0.1:5173`。如果需要指向其他 backend，用 `VITE_API_TARGET=http://127.0.0.1:<port> npm run dev -- --host 0.0.0.0 --port 5173`。

Loop Dashboard 默认端口是 `8766`。当用户需要远程持续观察 loop 状态时，必须保持它在线并绑定可信网络地址：

```bash
tmux new -s loop-dashboard
cd /home/fyz/codex-skills
PYTHONPATH=apps/loop_dashboard/backend \
python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766
```

Loop Dashboard 访问：`http://127.0.0.1:8766`。它无登录能力，只读展示 `.codex/loop-runs` 和 evaluator artifacts；只在可信网络中绑定 `0.0.0.0`。

### 启动后检查
```bash
curl --noproxy '*' http://127.0.0.1:8765/api/health
curl --noproxy '*' -I http://127.0.0.1:5173/
curl --noproxy '*' http://127.0.0.1:8766/api/health
curl --noproxy '*' -X POST http://127.0.0.1:8765/api/accelerator-candidates/999999999/trust-source
```

最后一条应返回业务错误 `candidate not found: 999999999`。如果返回路由级 `{"detail":"Not Found"}`，说明端口上跑的是旧 backend，先重启 `personal-wiki-crawler-backend`。

在 AI infra 资料扩充、crawler 入库或 loop 开发运行期间，`personal-wiki-crawler-backend`、`personal-wiki-crawler-frontend` 和 `loop-dashboard` 必须尽量保持在线，方便用户持续检查状态。确需重启时，先记录原因，重启后立即跑上述三项健康检查，并在最终汇报中列出访问 URL。

### 新知识入库后的刷新验证
每次新增或整理知识入库后，都必须同步确认后端和前端已经反映新数据：

1. 后端：确认 `/api/wiki/pages`、`/api/wiki/page` 或相关业务 API 能读到新 wiki/raw 内容；涉及全文检索时，通过普通 `/api/search` 查询验证搜索索引已自动刷新，不要只依赖手动 `/api/search/rebuild`。
2. 服务：如果改了 backend 代码、schema、搜索索引逻辑或运行配置，重启长驻 `personal-wiki-crawler-backend`；如果改了 frontend 代码或 Vite 配置，重启 `personal-wiki-crawler-frontend`；如果改了 loop dashboard 代码或 run artifact 展示契约，重启 `loop-dashboard`。
3. 前端：通过 Vite 代理或 Playwright 模拟用户操作，验证页面能看到新入库内容。知识工作台至少搜索一个新资料关键词；Wiki 浏览至少确认新页面标题或正文可见。
4. Loop 看板：确认对应 run 能在 Loop Dashboard 看到，且 agent 动作、子任务状态、evaluator 场景、错误/阻塞和用户决策字段可读。
5. 证据：最终汇报必须包含验证命令或页面级验证结果，以及是否重启了 backend/frontend/dashboard。

### Wiki / Crawler 入库提交规则
每次 wiki/crawler 完成抓取、整理或入库后，都必须把本次新增 raw、ingest-plan、curated wiki、索引和 ingest log 作为独立 commit 提交：

1. 先运行相关 wiki 验证，至少包含 `python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain <domain>`；跨 domain 或共享文件变更时再运行全仓库 validate。
2. 只 stage 本次入库相关路径，不能混入 `.codex/*.log`、pid、临时 `generated/`、本地服务状态或无关工作树改动。
3. 提交信息使用 `chore(wiki): ...` 或 `docs(wiki): ...`，并在最终汇报中列出 commit hash、入库来源范围和验证命令。
4. 如果入库后还需要前后端刷新验证，按上一节完成搜索、Wiki 浏览或相关 API 的可见性检查后再提交或补交。
5. 入库 commit 创建或合入 `main` 后，立即执行 `git push origin main`；如果推送失败，在最终汇报中说明远端、错误输出和当前分支状态。

### 隔离验证
```bash
cd /home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_api.py tests/test_discovery.py

cd /home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/frontend
npm test -- src/App.test.tsx
npm run build
npm run test:ui
npm run test:ui:live

cd /home/fyz/codex-skills
python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01
```

`npm run test:ui:live` 和 `scripts/wiki_crawler_e2e_evaluator.py` 会启动隔离 backend/frontend、设置临时状态目录、禁用 scheduler，并通过 Playwright 模拟用户点击；它们不应复用长驻开发 backend。

## 知识库地图
在做任何修改前，先阅读相关文档：

| 我想了解... | 去读这个文件 |
|------------|-------------|
| 整体架构、模块划分 | `docs/ARCHITECTURE.md` |
| 命名规则、代码风格 | `docs/CONVENTIONS.md` |
| 技术选型原因 | `docs/TECH_DECISIONS.md` |
| 什么叫完成 | `docs/QUALITY.md` |
| 当前计划 | `docs/superpowers/plans/` 和 `docs/exec-plans/active/` |
| 待开发功能 | `docs/exec-plans/backlog.md` |
| 已知技术债务 | `docs/exec-plans/tech-debt-tracker.md` |
| personal-wiki 规则 | `personal-wiki/WIKI.md`、`personal-wiki/docs/` |
| crawler workbench | `personal-wiki/apps/crawler_workbench/README.md` |
| evaluator gates | `docs/harness/` |

## 工作规范
1. **改之前先读**：修改 skill、wiki、crawler 或 harness 前，先读对应文档和附近测试。
2. **保护用户改动**：工作树可能有无关未提交改动；不要 revert 或提交不是本任务创建的文件。
3. **小步验证**：每个脚本或工作流改动都要跑对应验证命令，并记录不能运行的原因。
4. **同步文档**：如果修改架构、约定、任务状态或 evaluator 流程，同步更新 `docs/`、`tasks.json` 或 `progress.md`。
5. **证据优先**：完成声明必须引用实际命令、产物路径或 evaluator bundle。

## 任务管理
### 新增任务时，必须：
1. 填写 `tasks.json` 里的所有字段，不能省略。
2. 对照以下标准判断 `requires_eval`，不能默认填 false：
   - 新功能 / 涉及安全权限 / 改动超过 3 个文件 / 重构 -> true
   - 纯 bug 修复 / 文档更新 / 配置调整 -> false

### 每次完成一个任务后，必须按顺序执行：
1. 执行 `tasks.json` 中该任务 `verify` 字段描述的验证步骤。
2. 若 `requires_eval=true`，运行或等待 Step4 evaluator gate 通过后再标记 `done`。
3. 提交只属于本任务的文件，commit 格式优先用 `type(scope): summary`。
4. 在 `progress.md` 顶部追加本次记录和证据路径。
5. 任务 commit 创建或合入 `main` 后，立即执行 `git push origin main`；如果推送失败，不要静默忽略，必须报告失败原因和待处理状态。

## 禁止事项
- 不要把 token、cookie 或私有凭据写入 wiki、sources yaml 或 git。
- 不要在 crawler workbench 里默认开启公网暴露；它无登录能力，只能用于可信网络。
- 不要删除 `personal-wiki/domains/*/raw/` 证据；压缩或移动必须更新引用和 manifest。
- 不要把 Step4 evaluator 的项目专属逻辑写回 skill 模板；项目场景留在本仓库。
- 不要跳过 `tasks.json` 的 `verify` 步骤自行判断任务完成。
