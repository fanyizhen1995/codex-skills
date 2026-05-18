# codex-skills

可复用的 Codex skills 集合。

## 目录结构

每个 skill 使用独立目录，目录名与 `SKILL.md` 中的 `name` 保持一致。skill 相关说明放在对应目录的 `README.md` 中。

```text
skill-name/
├── README.md
├── SKILL.md
├── agents/
└── scripts/
```

## Skill 索引

| Skill | 说明 |
| --- | --- |
| [route-to-cheap-model](./route-to-cheap-model/README.md) | 将简单、低风险、纯文本任务分流给便宜模型处理。 |

## 让 Codex 安装

推荐直接把下面的提示词发给 Codex，让 Codex 自己使用 `skill-installer` 或合适的安装流程完成安装。安装后重启 Codex 以重新加载 skill metadata。

### 从远程仓库安装单个 skill

```text
请使用 skill-installer 从 GitHub 仓库 fanyizhen1995/codex-skills 安装 route-to-cheap-model skill。仓库路径是 route-to-cheap-model。安装完成后告诉我需要重启 Codex。
```

也可以使用完整 URL：

```text
请使用 skill-installer 安装这个 Codex skill：
https://github.com/fanyizhen1995/codex-skills/tree/main/route-to-cheap-model
安装完成后告诉我需要重启 Codex。
```

### 从远程仓库安装所有 skills

```text
请从 GitHub 仓库 fanyizhen1995/codex-skills 安装该项目下所有包含 SKILL.md 的 Codex skills。安装完成后告诉我安装了哪些 skill，并提醒我重启 Codex。
```

### 从本地项目安装

如果你已经 clone 了本仓库，可以让 Codex 从本地目录安装：

```text
请把当前项目中的 route-to-cheap-model skill 安装到我的 Codex skills 目录。skill 目录是 ./route-to-cheap-model。安装完成后告诉我需要重启 Codex。
```

安装本地项目下所有 skills：

```text
请扫描当前项目下所有包含 SKILL.md 的一级目录，并把这些 Codex skills 安装到我的 Codex skills 目录。安装完成后告诉我安装了哪些 skill，并提醒我重启 Codex。
```

### 更新已安装 skill

```text
请从 GitHub 仓库 fanyizhen1995/codex-skills 重新安装 route-to-cheap-model，覆盖我本地已安装的旧版本。安装完成后提醒我重启 Codex。
```
