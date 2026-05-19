---
name: route-to-cheap-model
description: Use when a request or subtask is simple, low-risk, text-only, and can be delegated to a cheaper third-party model; 用于简单、低风险、纯文本、省 token、第三方模型分流、便宜模型、摘要、改写、分类、抽取、格式转换、翻译、小段代码解释、regex 或 SQL 草稿等不需要工具的任务。
---

# 便宜模型分流

## 概览

使用本 skill 将边界清晰的纯文本小任务交给更便宜的 OpenAI-compatible 模型处理，然后由 Codex 在本地复核、修正和整合结果。它是一个路由策略，不是自动中间件：是否安全分流仍由当前 agent 判断。

## 适合使用

- 摘要、改写、翻译、调整语气、文本格式整理。
- 分类、字段抽取、生成表格、小片段格式转换。
- 解释用户粘贴的小段代码，且不需要搜索仓库。
- 起草低风险的 regex、SQL、shell 片段、prompt、标题或 checklist，并由 Codex 复核。
- 大任务中的局部纯文本子任务，且父任务没有禁止使用便宜模型。

## 不要使用

- 需要改文件、执行命令、跑测试、构建、调试、验证、安全审查或代码审查的任务。
- 需要完整对话历史、全仓库上下文、隐私密钥、隐藏凭证，或需要读取尚未提供的工具输出。
- 医疗、法律、金融、安全关键、政策敏感等高风险判断。
- 实时信息、网页查询、价格、日程、新闻，或任何可能已经变化的事实。
- 用户明确要求 Codex 自己完成，或明确要求不要把内容发给外部模型。
- 递归分流：不要再把便宜模型的输出交给另一个便宜模型处理。

## 工作流

1. 判断任务是否适合分流。只要命中“不使用”条件，就由 Codex 本地完成。
2. 最小化上下文。只发送必要指令和必要文本，不发送整段对话或整个仓库背景。
3. 调用脚本：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --task "用 5 个要点总结这段文本" \
  --input "$TEXT" \
  --max-tokens 300
```

多行输入可以通过 stdin 传入：

```bash
printf '%s' "$TEXT" | python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --task "把行动项抽取成 JSON"
```

4. 复核输出。修正明显错误，删除无依据断言，并判断 Codex 是否还需要本地补做工作。
5. 最终回复中不要暗示便宜模型执行过工具、检查过文件、联网查过资料或验证过事实。

每次脚本调用都会写入 JSONL 审计日志，默认路径是 `~/.agents/skills/route-to-cheap-model/logs/route.jsonl`。测试分流策略时，可用该日志确认是否真的调用了便宜模型。

## 配置

脚本默认复用本地 Codex 配置：

- 从 `$CODEX_HOME/config.toml` 或 `~/.codex/config.toml` 读取当前 `model_provider` 的 `base_url` 和 `wire_api`
- 从 `$CODEX_HOME/auth.json` 或 `~/.codex/auth.json` 读取 `OPENAI_API_KEY`
- 默认使用 `gpt-5.4-mini`

日常不需要额外配置环境变量。直接运行即可：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --task "用 3 个要点总结这段文本" \
  --input "$TEXT"
```

这样会继续使用你本地 Codex 的 provider、base URL 和 API key，但本 skill 的调用模型固定默认为 `gpt-5.4-mini`。

如果临时想换模型，用脚本参数：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --model "custom-mini" \
  --task "改写得更正式" \
  --input "$TEXT"
```

也可以显式覆盖 OpenAI-compatible `/chat/completions` 或 `/responses` 接口配置。

通常不需要环境变量；以下变量只用于覆盖默认行为：

- `CHEAP_MODEL_NAME`：覆盖默认模型 `gpt-5.4-mini`
- `CHEAP_MODEL_BASE_URL`：覆盖 Codex provider 的基础 URL，例如 `https://openrouter.ai/api/v1` 或 `http://localhost:8000/v1`
- `CHEAP_MODEL_API_KEY`：Bearer token
- `CHEAP_MODEL_WIRE_API`：`responses` 或 `chat`；未设置时沿用 Codex provider 的 `wire_api`，默认 `chat`
- `CHEAP_MODEL_MAX_INPUT_CHARS`：默认 `12000`
- `CHEAP_MODEL_MAX_TOKENS`：默认 `512`
- `CHEAP_MODEL_TEMPERATURE`：默认 `0`
- `CHEAP_MODEL_TIMEOUT`：默认 `60`
- `CHEAP_MODEL_LOG_FILE`：覆盖 JSONL 审计日志路径

## Subagent 规则

Subagent 只能在小型、纯文本、低风险、无需工具的子任务里使用本 skill。若父 agent 派发的是实现、调试、测试、验证、代码审查或仓库探索任务，subagent 应该自己完成这些工作，不要分流。

如果父 prompt 明确要求使用或避免本 skill，按父 prompt 执行。如果分流会向父 agent 隐藏关键不确定性，不要分流。

## 失败处理

- 如果配置缺失或 API 调用失败，继续由 Codex 本地处理，不要卡住用户。
- 如果输入超过限制，先本地摘要或裁剪。只有在丢弃尾部内容可接受时才使用 `--truncate`。
- 如果返回结果含糊、过度自信，或和已知上下文冲突，丢弃它并由 Codex 本地回答。

## 项目级策略

如果希望某个项目更积极地使用本 skill，把本 skill 目录里的 `AGENTS.routing.md` 内容合并到该项目根目录的 `AGENTS.md`。这能提高 Codex 在局部纯文本子任务上主动分流的概率，但不能强制拦截所有请求。
