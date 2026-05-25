# codex-engineering-context-optimizer

`codex-engineering-context-optimizer` 是一个中文 Codex skill，用于工程任务中的上下文瘦身：把测试、构建、benchmark、远程日志等大输出落盘，只把结构化摘要放进上下文。

## 适用场景

- Codex 长 session 中 `exec_command`、`write_stdin`、`apply_patch` 高频导致上下文膨胀。
- 测试日志、构建日志、benchmark 输出、远程服务日志太长。
- 需要证明上下文优化是否正确、是否真的节省 token。
- SCUDA/HAMI 等项目反复跑测试、定位失败、比较修改前后结果。

## 目录

```text
codex-engineering-context-optimizer/
├── README.md
├── SKILL.md
├── agents/openai.yaml
└── scripts/
    ├── context_audit.py
    └── run_with_summary.py
```

## 使用

包装大输出命令：

```bash
python3 scripts/run_with_summary.py --cwd "$PWD" --label test -- pytest -q
```

审计 Codex session 的工具输出膨胀：

```bash
python3 scripts/context_audit.py ~/.codex/sessions --since 2026-05-20
```

只看某个项目：

```bash
python3 scripts/context_audit.py ~/.codex/sessions \
  --since 2026-05-20 \
  --cwd-contains /home/fanyz4/scuda
```

## 如何证明正确性

1. 同一命令分别直接运行和用 `run_with_summary.py` 运行。
2. 比较退出码是否一致。
3. 确认摘要里的命令、cwd、失败关键行和原始日志一致。
4. 用摘要给出的日志路径复查原始输出。

## 如何证明效果

1. 用 `context_audit.py` 统计启用前一段时间的 session。
2. 安装并按 skill 使用一段时间。
3. 对启用后一段时间再次统计。
4. 对比大工具输出次数、p95/max 输出字符数、`context_compacted` 次数和任务成功率。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/codex-engineering-context-optimizer
cp -R codex-engineering-context-optimizer ~/.codex/skills/
```

安装后重启 Codex。
