# scuda-performance-evidence-review

SCUDA 性能证据复盘 skill，用于 review 已存在的 benchmark/profile 产物、native/same-host/cross-host 对比、CQV2/streaming gate、profile counters、provenance 和 cleanup state。

## 适用场景

- 判断已有 SCUDA 性能数字是否能支持优化结论。
- 对比 native、baseline、same-host、cross-host 和 candidate path。
- 区分 accepted evidence 与 debug clue。
- 复盘 report、summary、profile log、parser output 和 progress chart。

## 价值

该 skill 与 `scuda-fresh-performance-runbook` 分工互补：runbook 负责产生新证据，review 负责判断已有证据是否可接受。边界明确后，可以减少“边复盘边补跑”造成的证据污染。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/scuda-performance-evidence-review
cp -R scuda-performance-evidence-review ~/.codex/skills/
```

安装后重启 Codex。
