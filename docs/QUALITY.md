# 质量标准

## Definition of Done
一个任务算完成，必须满足：

- [ ] `tasks.json` 中对应任务的 `verify` 命令已执行，或记录了明确 blocker。
- [ ] 相关 Python 测试、TypeScript 测试或 wiki validate 已按改动范围运行。
- [ ] `git diff --check` 通过。
- [ ] 涉及 wiki curated 内容时，`source_refs` 指向实际 raw evidence。
- [ ] 涉及 crawler workbench 时，backend API/服务逻辑有 pytest 覆盖，frontend 行为有 Vitest 或 Playwright 覆盖。
- [ ] 涉及 `requires_eval=true` 的任务时，Step4 evaluator result 为 `pass`，或记录 `fail/blocked` 的证据和后续动作。
- [ ] 如修改架构、约定、任务状态或 evaluator 流程，已同步更新 `docs/`、`tasks.json` 或 `progress.md`。

## 代码审查检查清单
**正确性**
- [ ] 数据流是否符合 `docs/ARCHITECTURE.md` 的依赖方向。
- [ ] crawler 写入 raw evidence 后是否能从 DB 和文件系统追溯。
- [ ] 失败路径是否保留可诊断错误，而不是静默跳过。
- [ ] evaluator `pass` 是否包含 scenario evidence，而不是只依赖 verify 命令成功。

**可维护性**
- [ ] 新脚本是否有清晰 CLI 参数和退出码。
- [ ] 是否避免把项目专属逻辑写入通用 skill 模板。
- [ ] 是否避免大范围无关重构。
- [ ] 是否保护现有未提交改动。

**安全**
- [ ] 没有提交 token、cookie、私有 header 或本地凭据。
- [ ] crawler workbench 的无登录风险已在文档或输出中说明。
- [ ] Codex hook 命令在非 harness repo 中可以安全 no-op。

## 推荐验证命令
按改动范围选择最小足够集合：

```bash
bash init.sh
python3 -m json.tool tasks.json > /dev/null
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build
python3 harness-step4-evaluator-gates/scripts/test_step4_skill.py
git diff --check
```

## 待人工确认
- 是否需要为每个 skill 统一增加结构校验 CI。
- crawler workbench 的生产化标准目前未定义；现阶段按本地单用户工具验收。
