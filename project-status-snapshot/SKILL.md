---
name: project-status-snapshot
description: 当用户要求检查、恢复、梳理或继续一个项目的当前状态、任务进展、阻塞点、近期工作、重复工作流、skill/automation 候选、性能进展、部署就绪情况、生产灰度状态，或从中断的 Codex 历史中恢复上下文时使用。
---

# 项目状态快照

## 目标

为活跃工程项目生成基于证据的状态快照。先检查仓库状态、项目文档、日志和可用的 Codex 历史，再下结论。

## 证据顺序

只收集回答当前问题所需的信息，但优先按这个顺序检查：

1. 当前上下文：`pwd`、仓库根目录、分支、`git status --short`、近期 commit。
2. 项目说明：`AGENTS.md`、`README*`、`docs/`、`plans/`、`reports/`、`bench*`、`sprint*`、活跃设计文档或执行计划。
3. 工作证据：近期文件修改时间、当前 diff、未提交改动、测试/benchmark 日志、部署配置。
4. Codex 历史：如果存在，检查 `~/.codex/session_index.jsonl`、`~/.codex/state_*.sqlite`、`~/.codex/shell_snapshots` 和相关 shell history。

优先使用 `rg`/`rg --files`。查询 SQLite 时使用窄查询，不要直接扫描大型日志库：

```bash
sqlite3 ~/.codex/state_5.sqlite \
  "SELECT title,cwd,tokens_used,datetime(updated_at,'unixepoch','localtime')
   FROM threads
   WHERE cwd LIKE '%/project-name%'
   ORDER BY updated_at DESC LIMIT 20;"
```

## 工作流程

1. 从用户请求中识别项目和时间范围；如果不明确，根据 cwd/open files 推断，并明确说明这个假设。
2. 先读项目指引，再解释文件和日志。
3. 根据 commit、修改文件、文档、日志和 Codex thread 标题整理一条紧凑时间线。
4. 区分证据和推断；不确定的结论用“可能/倾向于”表述。
5. 如果用户想继续推进工作，最后给出按优先级排列的下一步行动。

## 重复工作流审计

当用户要求回顾过去一段时间、寻找可打包工作流、评估 skill/agent/automation 收益时，在状态快照之后增加这一层：

1. 按证据优先级检查 Codex session/task 摘要、Codex Memories/汇总记录、Chronicle（如存在，仅用于发现）、项目文档、已有 skill/custom agent/automation。
2. 统计候选出现次数、项目、代表 thread/title、相对 token/上下文消耗；`tokens_used` 只能当相对信号，除非确认其计量口径。
3. 只有同时满足这些条件才建议创建或增强：至少发生两次或重来代价高；输入稳定；流程可重复；输出明确；能改善速度、质量或可靠性；现有工具未覆盖。
4. 先列候选清单，再处理高置信度项目。优先复用/增强已有 skill 或 automation，不重复造轮子。
5. 输出按 `Skill`、`Custom subagent`、`Automation`、`Skip`、`需要更多证据` 分类，并说明跳过原因。

## 输出格式

保持简洁，优先使用这些小节：

- `当前状态`：当前已确认事实，包括 branch/cwd 和相关 dirty files。
- `近期进展`：按时间排序的进展，尽量带日期、commit 或文件路径。
- `阻塞/风险`：缺失数据、失败测试、不清楚的归属、部署风险、过期文档。
- `下一步`：3-6 个具体行动，从最安全/收益最高的一步开始。
- `已检查证据`：简短列出查看过的命令和文件。

不要粘贴长日志或大段文件内容。用摘要说明，并引用路径或命令。

## 针对此用户的启发式

- SCUDA/HAMI 任务通常需要同时检查代码、文档、benchmark 结果和历史 Codex thread。
- “当前任务状态”“梳理项目现状”“任务中断”“性能进展”“灰度/生产环境”都要求先做状态快照，再提出实现方案。
- 性能类问题只有在 benchmark artifact 支撑时，才报告 baseline/native/same-host/cross-host 数字。
- 部署类问题需要检查 service 状态、配置、近期错误，以及可访问的灰度/回滚状态。
- review 密集型工作流要区分顶层用户 thread 和 subagent review thread。

## 常见错误

- 仓库或 Codex 历史可用时，不要凭记忆回答。
- 不要把 thread 标题当作任务完成证据；要用文件、commit 或日志交叉验证。
- 除非窄查询无法回答问题，不要广泛扫描多 GB 的 Codex 日志。
- 除非用户明确要求在快照后执行操作，不要修改文件、重启服务或运行长时间 benchmark。
