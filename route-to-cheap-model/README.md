# route-to-cheap-model

`route-to-cheap-model` 是一个 Codex skill，用于把简单、低风险、纯文本任务分流给更便宜的第三方模型处理，减少主模型上下文和 token 消耗。

## 适用场景

- 摘要、改写、翻译、调整语气、格式整理。
- 分类、字段抽取、表格生成、小片段格式转换。
- 解释用户粘贴的小段代码，且不需要搜索仓库。
- 起草低风险的 regex、SQL、shell 片段、prompt、标题或 checklist。

不要用于文件编辑、命令执行、测试、构建、调试、验证、安全审查、代码审查、实时信息查询或任何高风险判断。

## 工作方式

skill 本体位于：

```text
route-to-cheap-model/
├── AGENTS.routing.md
├── SKILL.md
├── agents/openai.yaml
└── scripts/
    ├── route.py
    └── test_route.py
```

`route.py` 默认复用本地 Codex 配置：

- `$CODEX_HOME/config.toml` 或 `~/.codex/config.toml`
- `$CODEX_HOME/auth.json` 或 `~/.codex/auth.json`
- 当前 Codex provider 的 `base_url` 和 `wire_api`
- `OPENAI_API_KEY`

默认分流模型为 `gpt-5.4-mini`。通常不需要额外环境变量。

脚本默认写入 JSONL 审计日志：

```text
~/.agents/skills/route-to-cheap-model/logs/route.jsonl
```

每次真实调用都会记录任务、模型、输入长度、输出长度、usage 和成功状态。这个日志只能证明“发生过分流”；如果 Codex 没触发 skill，就不会有日志。

## 安装

从本仓库安装到当前用户的 Codex skills 目录：

```bash
mkdir -p ~/.agents/skills
cp -R route-to-cheap-model ~/.agents/skills/
```

如果已安装旧版本，先删除再复制：

```bash
rm -rf ~/.agents/skills/route-to-cheap-model
cp -R route-to-cheap-model ~/.agents/skills/
```

安装后重启 Codex，让新的 skill metadata 被重新加载。

## 使用

显式触发：

```text
$route-to-cheap-model 把这段话总结成 3 点：……
```

脚本直连测试：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --task "只回复 OK" \
  --input "测试" \
  --max-tokens 20
```

临时覆盖模型：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --model "custom-mini" \
  --task "改写得更正式" \
  --input "$TEXT"
```

禁用本次审计日志：

```bash
python3 ~/.agents/skills/route-to-cheap-model/scripts/route.py \
  --task "只回复 OK" \
  --input "测试" \
  --no-log
```

## 项目级分流策略

如果希望某个项目更积极地使用该 skill，可以把本目录的 `AGENTS.routing.md` 内容合并到目标项目根目录的 `AGENTS.md`。

```bash
cp route-to-cheap-model/AGENTS.routing.md /path/to/project/AGENTS.md
```

如果目标项目已经有 `AGENTS.md`，不要直接覆盖，把其中的分流策略段落追加进去即可。这样能提高 Codex 在 README 草稿、commit message、摘要、翻译、分类、字段抽取等局部纯文本子任务上主动分流的概率。

## 可选配置

通常不需要配置环境变量。以下变量只用于覆盖默认行为：

- `CHEAP_MODEL_NAME`：覆盖默认模型 `gpt-5.4-mini`
- `CHEAP_MODEL_BASE_URL`：覆盖 Codex provider 的基础 URL
- `CHEAP_MODEL_API_KEY`：覆盖 Codex auth 中的 API key
- `CHEAP_MODEL_WIRE_API`：`responses` 或 `chat`
- `CHEAP_MODEL_MAX_INPUT_CHARS`：默认 `12000`
- `CHEAP_MODEL_MAX_TOKENS`：默认 `512`
- `CHEAP_MODEL_TEMPERATURE`：默认 `0`
- `CHEAP_MODEL_TIMEOUT`：默认 `60`
- `CHEAP_MODEL_LOG_FILE`：覆盖 JSONL 审计日志路径

## 验证

在仓库根目录运行：

```bash
python3 route-to-cheap-model/scripts/test_route.py
```

如果本机安装了 Codex skill 校验脚本，也可以运行：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ./route-to-cheap-model
```
