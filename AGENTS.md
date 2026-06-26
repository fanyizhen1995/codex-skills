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

## 禁止事项
- 不要把 token、cookie 或私有凭据写入 wiki、sources yaml 或 git。
- 不要在 crawler workbench 里默认开启公网暴露；它无登录能力，只能用于可信网络。
- 不要删除 `personal-wiki/domains/*/raw/` 证据；压缩或移动必须更新引用和 manifest。
- 不要把 Step4 evaluator 的项目专属逻辑写回 skill 模板；项目场景留在本仓库。
- 不要跳过 `tasks.json` 的 `verify` 步骤自行判断任务完成。
