# Wiki Agent Protocol

This repository is optimized for LLM and agent use. Follow this protocol for
query, ingest, maintenance, and refactoring work.

## Read Order

1. Read this `WIKI.md`.
2. Identify the target domain.
3. Read `domains/<domain>/DOMAIN.md`.
4. Read `domains/<domain>/wiki/index.md`.
5. Open specific wiki pages by following links or matching titles, aliases, and tags.
6. Open raw sources only when validating or ingesting claims.

Avoid full-repository scans unless the user explicitly asks for cross-domain
research, repository-wide validation, or duplicate detection.

## Knowledge Layers

raw/ is the fact source. It contains captured sources, notes, transcripts,
paper extractions, screenshots, snapshots, and raw image evidence.

wiki/ is the curated knowledge layer. It contains OKF-style Markdown pages
with YAML frontmatter, concise descriptions, links, and citations.

Do not rewrite raw sources into polished conclusions. Create or update wiki
pages instead.

## Domain Boundary

The default context boundary is one domain under `domains/<domain>/`.

Use `global/wiki/` only for concepts, people, organizations, and references that
are reused across multiple domains.

Cross-domain links must be explicit. Do not move content into `global/` merely
because it is interesting.

## Ingest Rules

Ingest is explicitly triggered by the user. A typical request names a raw file,
for example:

```text
ingest domains/ai-infra/raw/inbox/flashattention.md
```

Before creating a new wiki page, check the domain index and nearby pages for an
existing concept. Prefer updating existing pages over creating duplicates.

When updating a page:

- Preserve useful existing structure.
- Add or revise the smallest section that satisfies the task.
- Preserve existing `source_refs`.
- Add citations for new claims.
- Update `ingest.md`.

The user has given standing approval to promote curated wiki pages to
`reviewed` by default when source coverage is complete. Leave a page as `draft`
if evidence is incomplete, citations are missing, or open questions remain.

## Agent Usage Guide

Use the `personal-wiki-manager` skill when maintaining this repository through
Codex, Claude Code, or another coding agent. If the skill is not auto-loaded,
read `skills/personal-wiki-manager/SKILL.md` after this file.

Default agent workflow:

```text
source material -> raw/ -> ingest-plan -> wiki/ -> index -> validate
```

### Complete Function Map

Use these one-line prompts when delegating work to an agent. Replace
`<domain>`, `<url>`, `<raw-path>`, `<question>`, and `<page>` as needed.

Composite prompts for common workflows:

| Workflow | One-line prompt |
| --- | --- |
| Create | `使用 personal-wiki-manager 创建 domain <domain>，补充 DOMAIN.md 边界、核心主题、别名规则和跨 domain 规则，初始化后运行 validate 并报告文件。` |
| Ingest | `使用 personal-wiki-manager，目标 domain: <domain>，入库 <url-or-raw-path>，按 raw->ingest-plan->wiki->index->validate 完整流程处理；大型资料 raw 保完整、wiki 只沉淀索引/综合/关键结论，优先更新已有页面，报告文件和验证结果。` |
| Organize | `使用 personal-wiki-manager，目标 domain: <domain>，整理现有 wiki/raw/ingest log：去重、补 source_refs/citations、重构页面关系、必要时评估 global 抽取，保持事实不变，最后重建 index、生成 backlinks 检查并 validate。` |
| Query | `使用 personal-wiki-manager，目标 domain: <domain>，基于已有 wiki/raw 回答 <question>，引用路径；如果答案有长期复用价值，沉淀进最小合适 curated wiki 页面，然后 index+validate 并报告文件。` |
| Export | `使用 personal-wiki-manager，目标 domain: <domain>，导出查询/整理结果：按需生成 backlinks、graph JSON、visualize HTML，并汇总相关 wiki/raw 路径、关键结论和验证状态。` |

| Function | Agent guidance | One-line prompt |
| --- | --- | --- |
| Create domain | Create one domain scaffold, then define its boundary in `DOMAIN.md`. | `使用 personal-wiki-manager 创建 domain <domain>，补充 DOMAIN.md 边界，然后 validate。` |
| Query | Answer from the active domain index, curated pages, and raw files only when needed. | `使用 personal-wiki-manager，目标 domain: <domain>，基于已有 wiki/raw 回答：<question>，请引用路径。` |
| Query and promote | Answer first, then persist durable synthesis into the smallest existing curated page. | `使用 personal-wiki-manager，目标 domain: <domain>，先回答 <question>，若有长期价值则沉淀进最小合适 wiki 页面并 validate。` |
| URL ingest | Snapshot the URL into `raw/links`, create an ingest plan, curate minimal pages, rebuild index, validate. | `使用 personal-wiki-manager，目标 domain: <domain>，入库 URL <url>，按 raw->ingest-plan->wiki->index->validate，报告文件。` |
| Local file ingest | Put the original under the domain `raw/` tree before ingesting. | `使用 personal-wiki-manager，目标 domain: <domain>，入库 raw 文件 <raw-path>，优先更新已有页面，最后 index+validate。` |
| Large-source ingest | Preserve full source material in `raw/`; curate indexes, summaries, and durable synthesis instead of mirroring everything. | `使用 personal-wiki-manager，目标 domain: <domain>，入库大型资料 <url-or-raw-path>，raw 保完整，wiki 只沉淀索引/综合/关键结论。` |
| Image note | Ensure the image is a valid raw source, create a draft Reference page, explain meaning and source, validate. | `使用 personal-wiki-manager，目标 domain: <domain>，为图片 <raw-image-path> 创建 image-note，补充含义/来源并 validate。` |
| Validate | Run domain validation after domain edits; run full validation after shared or broad changes. | `使用 personal-wiki-manager，验证 personal wiki；若改过 <domain>，同时跑 domain 和全仓库 validate，只报告问题。` |
| Fix validation | Read each issue, make the smallest correction, rerun validation. | `使用 personal-wiki-manager，修复 validate 报错，保持事实不变，完成后报告修改文件和验证结果。` |
| Refactor | Reorganize pages without changing facts; preserve links, aliases, `source_refs`, and citations. | `使用 personal-wiki-manager，目标 domain: <domain>，重构 wiki 组织结构但不改变事实，完成后 index+validate。` |
| Rebuild index | Regenerate `wiki/index.md` from page frontmatter after curated page changes. | `使用 personal-wiki-manager，目标 domain: <domain>，重建 index 并 validate。` |
| Backlinks | Inspect or write reverse-link data for navigation/debugging. | `使用 personal-wiki-manager，目标 domain: <domain>，生成 backlinks；需要落盘时加 --write-json。` |
| Graph JSON | Export wiki nodes and edges for analysis or tooling. | `使用 personal-wiki-manager，目标 domain: <domain>，导出 graph JSON 到 <out-path>。` |
| Graph HTML | Generate a simple HTML graph view for inspection. | `使用 personal-wiki-manager，目标 domain: <domain>，生成 visualize HTML 到 <out-path>。` |
| Reviewed promotion | Promote by default when source_refs/citations are complete; otherwise keep draft. | `使用 personal-wiki-manager，将 <page> 提升为 reviewed；先检查 source_refs/citations，缺证据则保持 draft。` |
| Global extraction | Use `global/` only for knowledge reused across multiple domains. | `使用 personal-wiki-manager，评估 <page-or-topic> 是否应放入 global；只有跨多个 domain 复用时才抽取，并更新链接后 validate。` |
| Raw status cleanup | Keep raw evidence intact; update raw status only as bookkeeping after curated pages cite it. | `使用 personal-wiki-manager，整理 <domain> raw 状态；不要改原始证据，只更新状态/日志并 validate。` |
| Ingest log cleanup | Keep `ingest.md` aligned with pending, in-progress, done, and rejected source state. | `使用 personal-wiki-manager，整理 <domain>/ingest.md，使 pending/in-progress/done/rejected 与实际 wiki 状态一致。` |

### CLI Commands

Agents should prefer these commands for repository operations:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <domain>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki snapshot-url <domain> <url> --fetch
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki ingest-plan <domain> <raw-path>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note <domain> <image-path>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index <domain>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate [--domain <domain>] [--json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks [--domain <domain>] [--write-json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki graph [--domain <domain>] [--out graph.json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki visualize [--domain <domain>] [--out graph.html]
```

To create a domain, ask the agent to run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <domain>
```

Then update `domains/<domain>/DOMAIN.md` with the domain boundary: what belongs
there, what does not, and when cross-domain links are allowed.

To add a URL, ask the agent to:

1. Run `snapshot-url <domain> <url>` to create a raw web source.
2. Run `ingest-plan <domain> <raw-path>` for the generated raw file.
3. Read the domain index and nearby wiki pages before creating new pages.
4. Prefer updating existing pages over creating duplicates.
5. Preserve `source_refs` and citations for new claims.
6. Run `index <domain>` and `validate --domain <domain>`.

To add a local file, first place or copy the original content under the active
domain's `raw/` tree:

- `raw/inbox/` for unclassified source material.
- `raw/notes/` for personal notes.
- `raw/papers/` for papers and long-form technical references.
- `raw/images/` for original visual evidence.

Then ask the agent to run `ingest-plan` for that raw path and apply the plan to
the smallest useful set of curated wiki pages.

Recommended prompt for URL or file ingest:

```text
Use personal-wiki-manager.
Target domain: <domain>.
Input source: <url-or-raw-path>.
Follow raw -> ingest-plan -> wiki -> index -> validate.
Prefer updating existing pages over creating duplicates.
Keep new claims tied to source_refs or citations.
Promote pages to reviewed when source_refs/citations are complete; otherwise keep draft.
Report changed files and validation results.
```

Recommended prompt for queries:

```text
Use personal-wiki-manager.
Target domain: <domain>.
Answer from existing wiki and raw files.
Read wiki/index.md first, then relevant pages.
Use raw sources only when needed to validate claims.
Cite wiki paths and raw source paths in the answer.
```

To promote a useful query result into the curated wiki:

1. Treat the answer as a draft synthesis, not as a new source.
2. Re-open the target domain index, the existing curated page to update, and
   the raw sources cited by the answer.
3. Add the smallest durable section to an existing page when possible. Create a
   new page only when the synthesis is a reusable concept, project, decision,
   paper, or reference that does not already exist.
4. Preserve or extend `source_refs`, and cite the raw sources used for every
   new factual claim. Label interpretation as synthesis when it goes beyond a
   single source.
5. Run `index <domain>` and `validate --domain <domain>` after editing.

Recommended prompt for query-to-wiki promotion:

```text
Use personal-wiki-manager.
Target domain: <domain>.
Question: <question>.
Answer from existing wiki and raw files first.
If the answer contains durable analysis worth reusing, update the smallest
appropriate curated wiki page and keep all claims tied to source_refs or
citations.
Prefer updating existing pages over creating duplicates.
Promote pages to reviewed when source_refs/citations are complete; otherwise keep draft.
Run index <domain> and validate --domain <domain>.
Report changed files and validation results.
```

Recommended prompt for validation-only checks:

```text
Use personal-wiki-manager.
Validate the personal wiki.
Run both domain-level and full-repository validation when a domain changed.
Report issues with file paths and do not edit unless I ask for fixes.
```

Recommended prompt for refactors:

```text
Use personal-wiki-manager.
Target domain: <domain>.
Refactor the existing wiki organization without changing facts.
Preserve links, aliases, backlinks, source_refs, and citations.
Promote pages to reviewed when source_refs/citations are complete; otherwise keep draft.
Run index <domain> and validate --domain <domain>.
Report changed files and validation results.
```

Operational notes:

- For large source sets, keep the full capture in `raw/` and curate only the
  reusable index, summary, trend, decision, or reference material. Avoid
  recreating a vendor manual or paper verbatim in `wiki/`.
- Use `backlinks`, `graph`, and `visualize` when checking navigation,
  relationship coverage, duplicate concepts, or orphan pages. Generated graph
  outputs are derived artifacts; create them when requested or useful for a
  review.
- Use `global/wiki/` only when a page is reused by multiple domains. If a page
  moves or splits into `global/`, update links in the source domains and run
  validation.
- Promote curated pages to `reviewed` by default when factual claims have
  `source_refs` or citations and no blocking open questions remain. If evidence
  is incomplete, leave the page as `draft` and add an open question.
- `raw/` files are evidence. Do not rewrite captured content. Status or ingest
  log cleanup is bookkeeping only and must not change the original evidence.

## Agent 使用指南（中文）

通过 Codex、Claude Code 或其他 coding agent 维护本仓库时，优先使用
`personal-wiki-manager` skill。如果该 skill 没有自动加载，先要求 agent
读取本文件，再读取 `skills/personal-wiki-manager/SKILL.md`。

默认处理流程：

```text
资料 -> raw/ 原始层 -> ingest-plan -> wiki/ 知识层 -> index -> validate
```

### 完整功能速查

把下面的一行提示词复制给 agent 使用，并替换 `<domain>`、`<url>`、
`<raw-path>`、`<question>`、`<page>` 等占位符。

常用复合流程提示词：

| 流程 | 一行提示词 |
| --- | --- |
| 创建 | `使用 personal-wiki-manager 创建 domain <domain>，补充 DOMAIN.md 边界、核心主题、别名规则和跨 domain 规则，初始化后运行 validate 并报告文件。` |
| 入库 | `使用 personal-wiki-manager，目标 domain: <domain>，入库 <url-or-raw-path>，按 raw->ingest-plan->wiki->index->validate 完整流程处理；大型资料 raw 保完整、wiki 只沉淀索引/综合/关键结论，优先更新已有页面，报告文件和验证结果。` |
| 整理 | `使用 personal-wiki-manager，目标 domain: <domain>，整理现有 wiki/raw/ingest log：去重、补 source_refs/citations、重构页面关系、必要时评估 global 抽取，保持事实不变，最后重建 index、生成 backlinks 检查并 validate。` |
| 查询 | `使用 personal-wiki-manager，目标 domain: <domain>，基于已有 wiki/raw 回答 <question>，引用路径；如果答案有长期复用价值，沉淀进最小合适 curated wiki 页面，然后 index+validate 并报告文件。` |
| 导出 | `使用 personal-wiki-manager，目标 domain: <domain>，导出查询/整理结果：按需生成 backlinks、graph JSON、visualize HTML，并汇总相关 wiki/raw 路径、关键结论和验证状态。` |

| 功能 | Agent 使用指南 | 一行提示词 |
| --- | --- | --- |
| 创建 domain | 只创建一个 domain，并补充 `DOMAIN.md` 边界。 | `使用 personal-wiki-manager 创建 domain <domain>，补充 DOMAIN.md 边界，然后 validate。` |
| 查询 | 默认只查一个 domain；先看 index 和 curated 页面，必要时读 raw。 | `使用 personal-wiki-manager，目标 domain: <domain>，基于已有 wiki/raw 回答：<question>，请引用路径。` |
| 查询并沉淀 | 先回答，再把可复用的长期分析写进最小合适 curated 页面。 | `使用 personal-wiki-manager，目标 domain: <domain>，先回答 <question>，若有长期价值则沉淀进最小合适 wiki 页面并 validate。` |
| URL 入库 | URL 先 snapshot 到 `raw/links`，再 ingest-plan、wiki、index、validate。 | `使用 personal-wiki-manager，目标 domain: <domain>，入库 URL <url>，按 raw->ingest-plan->wiki->index->validate，报告文件。` |
| 本地文件入库 | 原始文件必须先放到目标 domain 的 `raw/` 树内。 | `使用 personal-wiki-manager，目标 domain: <domain>，入库 raw 文件 <raw-path>，优先更新已有页面，最后 index+validate。` |
| 大型资料入库 | `raw/` 保留完整资料，`wiki/` 只沉淀索引、综合和关键结论。 | `使用 personal-wiki-manager，目标 domain: <domain>，入库大型资料 <url-or-raw-path>，raw 保完整，wiki 只沉淀索引/综合/关键结论。` |
| 图片笔记 | 图片必须是有效 raw source；创建 Reference 页并解释图像含义。 | `使用 personal-wiki-manager，目标 domain: <domain>，为图片 <raw-image-path> 创建 image-note，补充含义/来源并 validate。` |
| 只验证 | domain 修改后跑 domain validation；宽范围修改后跑全仓库。 | `使用 personal-wiki-manager，验证 personal wiki；若改过 <domain>，同时跑 domain 和全仓库 validate，只报告问题。` |
| 修复验证问题 | 逐条读 validation issue，最小改动修复，再复跑。 | `使用 personal-wiki-manager，修复 validate 报错，保持事实不变，完成后报告修改文件和验证结果。` |
| 重构 | 只调整组织结构，不改事实；保留链接、别名和来源。 | `使用 personal-wiki-manager，目标 domain: <domain>，重构 wiki 组织结构但不改变事实，完成后 index+validate。` |
| 重建索引 | curated 页面变化后用 frontmatter 重新生成 `wiki/index.md`。 | `使用 personal-wiki-manager，目标 domain: <domain>，重建 index 并 validate。` |
| Backlinks | 检查反向链接，用于导航、孤立页面和关系覆盖审查。 | `使用 personal-wiki-manager，目标 domain: <domain>，生成 backlinks；需要落盘时加 --write-json。` |
| Graph JSON | 导出 wiki 节点和边，供分析或外部工具使用。 | `使用 personal-wiki-manager，目标 domain: <domain>，导出 graph JSON 到 <out-path>。` |
| Graph HTML | 生成简易 HTML 图谱，用于人工检查关系。 | `使用 personal-wiki-manager，目标 domain: <domain>，生成 visualize HTML 到 <out-path>。` |
| Reviewed 提升 | 默认在来源/引用完整时提升；证据不足则保持 draft。 | `使用 personal-wiki-manager，将 <page> 提升为 reviewed；先检查 source_refs/citations，缺证据则保持 draft。` |
| Global 抽取 | 只有跨多个 domain 复用的知识才放入 `global/`。 | `使用 personal-wiki-manager，评估 <page-or-topic> 是否应放入 global；只有跨多个 domain 复用时才抽取，并更新链接后 validate。` |
| Raw 状态整理 | 不改原始证据，只做状态或日志 bookkeeping。 | `使用 personal-wiki-manager，整理 <domain> raw 状态；不要改原始证据，只更新状态/日志并 validate。` |
| Ingest log 整理 | 让 `ingest.md` 与 pending/in-progress/done/rejected 实际状态一致。 | `使用 personal-wiki-manager，整理 <domain>/ingest.md，使 pending/in-progress/done/rejected 与实际 wiki 状态一致。` |

### CLI 命令

Agent 应优先使用这些命令执行仓库操作：

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <domain>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki snapshot-url <domain> <url> --fetch
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki ingest-plan <domain> <raw-path>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note <domain> <image-path>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki index <domain>
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate [--domain <domain>] [--json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki backlinks [--domain <domain>] [--write-json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki graph [--domain <domain>] [--out graph.json]
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki visualize [--domain <domain>] [--out graph.html]
```

创建新领域时，让 agent 执行：

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki init-domain <domain>
```

创建后，补充 `domains/<domain>/DOMAIN.md`：说明该领域包含什么、不包含什么、
什么时候允许跨领域链接。

通过 URL 入库时，让 agent 按这个流程处理：

1. 运行 `snapshot-url <domain> <url>`，把网页记录成 raw source。
2. 对生成的 raw 文件运行 `ingest-plan <domain> <raw-path>`。
3. 先读取领域索引和附近 wiki 页面，再决定是否创建新页面。
4. 优先更新已有页面，避免创建重复概念。
5. 新增事实必须保留 `source_refs` 或 citation。
6. 最后运行 `index <domain>` 和 `validate --domain <domain>`。

通过本地文件入库时，先把原始资料放到目标领域的 `raw/` 目录：

- `raw/inbox/`：未分类资料。
- `raw/notes/`：个人笔记。
- `raw/papers/`：论文或长篇技术资料。
- `raw/images/`：原始图片证据。

然后让 agent 对该 raw path 运行 `ingest-plan`，再按计划整理最小必要的
curated wiki 页面。

推荐的 URL 或文件入库 prompt：

```text
使用 personal-wiki-manager。
目标 domain：<domain>。
输入资料：<url-or-raw-path>。
请按 raw -> ingest-plan -> wiki -> index -> validate 的流程处理。
优先更新已有页面，避免创建重复概念。
新事实必须绑定 source_refs 或 citation。
source_refs/citations 完整时默认提升为 reviewed；证据不足则保持 draft。
完成后报告新增/修改文件和 validation 结果。
```

推荐的查询 prompt：

```text
使用 personal-wiki-manager。
目标 domain：<domain>。
请基于已有 wiki 和 raw 文件回答。
先读取 wiki/index.md，再打开相关页面。
只有在需要验证事实时才读取 raw source。
回答中引用 wiki 路径和 raw source 路径。
```

如果查询结果值得沉淀进 curated wiki，让 agent 按这个流程处理：

1. 把回答视为待整理的综合分析，不把回答本身当作新的事实来源。
2. 重新打开目标领域索引、需要更新的 curated 页面，以及回答中引用过的
   raw source。
3. 优先在已有页面增加最小、可复用的小节。只有当该综合分析本身是新的可复用
   concept、project、decision、paper 或 reference，且现有页面无法承载时，才创建新页面。
4. 保留或补充 `source_refs`，每个新增事实都要引用对应 raw source。超出单一来源
   的归纳要标明这是 synthesis。
5. 编辑后运行 `index <domain>` 和 `validate --domain <domain>`。

推荐的“查询并沉淀” prompt：

```text
使用 personal-wiki-manager。
目标 domain：<domain>。
问题：<question>。
请先基于已有 wiki 和 raw 文件回答。
如果回答中有值得复用的长期分析，请更新最小合适的 curated wiki 页面。
所有新增事实必须绑定 source_refs 或 citation。
优先更新已有页面，避免创建重复概念。
source_refs/citations 完整时默认提升为 reviewed；证据不足则保持 draft。
运行 index <domain> 和 validate --domain <domain>。
完成后报告新增/修改文件和 validation 结果。
```

推荐的只验证 prompt：

```text
使用 personal-wiki-manager。
请验证 personal wiki。
如果刚修改过某个 domain，同时运行 domain 级和全仓库 validation。
报告带文件路径的问题；除非我要求修复，否则不要修改文件。
```

推荐的重构 prompt：

```text
使用 personal-wiki-manager。
目标 domain：<domain>。
请只重构现有 wiki 组织结构，不改变事实。
保留 links、aliases、backlinks、source_refs 和 citations。
source_refs/citations 完整时默认提升为 reviewed；证据不足则保持 draft。
运行 index <domain> 和 validate --domain <domain>。
完成后报告新增/修改文件和 validation 结果。
```

操作补充：

- 大型资料集入库时，`raw/` 保留完整抓取，`wiki/` 只整理可复用的索引、
  摘要、趋势、决策或 reference，不要把厂商手册或论文全文重写进 wiki。
- 检查导航、关系覆盖、重复概念或孤立页面时，使用 `backlinks`、`graph`
  和 `visualize`。这些输出是派生产物，只在用户要求或审查有用时生成。
- 只有跨多个 domain 复用的知识才放入 `global/wiki/`。如果移动或拆分到
  `global/`，必须更新来源 domain 的链接并运行 validation。
- 用户已给出默认 reviewed 授权：curated 页面在事实性内容具备 `source_refs`
  或 citations、且没有阻塞性 open question 时，默认提升为 `reviewed`。证据不足
  时保持 `draft` 并写入 open question。
- `raw/` 是证据层，不改写已抓取内容。raw status 或 ingest log 整理只属于
  bookkeeping，不能改变原始证据。

## Image Rules

`raw/images/` stores original visual evidence.

`wiki/assets/images/` stores curated images that wiki pages reference.

Wiki pages should normally reference `wiki/assets/images/`, not `raw/images/`.
Important images should have a `Reference` page that explains image meaning,
image source, and supported concepts.

For important images, ask the agent to run:

```bash
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki image-note <domain> raw/images/<image-file>
```

Then fill in what the image shows, why it matters, and which wiki concepts it
supports. Validate the domain after editing the image Reference page.

## Source Integrity

New factual claims need a `source_refs` entry or a citation. If sources conflict,
add `# Conflicts` or `# Open Questions` instead of forcing a conclusion.

When answering the user, cite wiki paths and raw source paths when they are used.
