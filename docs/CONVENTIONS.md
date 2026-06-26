# 代码约定

## 文件命名
- Skill 目录使用短横线小写命名，例如 `route-to-cheap-model/`、`project-status-snapshot/`。
- Skill 入口固定为 `SKILL.md`，说明文档固定为 `README.md`，agent metadata 放在 `agents/openai.yaml`。
- Python 模块使用 snake_case，例如 `wiki_cli.py`、`fetch_service.py`、`context_audit.py`。
- Python 测试使用 `test_*.py`，例如 `personal-wiki/tests/test_validate.py` 和 `codex-model-router/tests/test_router.py`。
- React 组件和页面使用 PascalCase，例如 `Layout.tsx`、`SourceWorkbenchPage.tsx`；API/types 使用 `api.ts`、`types.ts`。

## 变量和函数命名
- Python 函数、变量、CLI helpers 使用 snake_case，例如 `run_source_once`、`open_db`、`validate_domain`。
- Python 异常类使用 PascalCase，例如 `SourceNotFoundError`、`InvalidTaskStateError`。
- React 组件使用 PascalCase，普通 TypeScript 函数和变量使用 camelCase。
- JSON task id 使用短横线命名并包含模块前缀，例如 `wiki-crawler-e2e-eval-01`。

## 目录组织
- 独立 skill 的脚本留在该 skill 的 `scripts/` 目录，除非安装流程明确复制到目标 repo runtime。
- 跨 session 的设计和计划放在 `docs/superpowers/specs/`、`docs/superpowers/plans/`。
- Harness evaluator 场景放在 `docs/harness/evaluator-scenarios/`。
- Repo-side automation 放在根 `scripts/`；crawler app 自身代码留在 `personal-wiki/apps/crawler_workbench/`。
- Wiki raw evidence 放在 `personal-wiki/domains/<domain>/raw/`，curated 页面放在 `personal-wiki/domains/<domain>/wiki/`。

## 注释风格
- 文档和 skill 说明优先写操作边界、命令和安全规则。
- 代码注释只解释不明显的约束或复杂流程，不重复函数名已经说明的内容。
- 测试名应描述行为，例如 `test_rss_fetcher_fetches_article_body_and_records_feed_metadata`。

## Git Commit 格式
从近期提交看，仓库同时存在 `feat(scope): summary` 和简短祈使句格式。新提交优先使用：

```text
type(scope): 做了什么
```

常用 type：`feat`、`fix`、`docs`、`test`、`refactor`、`chore`。

## 待人工确认
- 是否要强制所有新增 skill 都提供 `README.md`、`agents/openai.yaml` 和脚本测试，目前这是强约定但未由 CI 统一检查。
