# scuda-fresh-performance-runbook

SCUDA fresh performance runbook skill，用于准备和执行 benchmark、profile、correctness、native/same-host/cross-host、artifact sync、checksum、cleanup、matrix 和 fresh endpoint 实验。

## 适用场景

- 新跑 SCUDA benchmark/profile/correctness 证据。
- 同步本地/远端 `libscuda_*.so`、`server_*.so` 并记录 checksum。
- 清理 stale endpoint、socket、SHM、server/client 进程。
- 生成可被 `scuda-performance-evidence-review` 复盘的 traceable evidence set。

## 价值

过去一周远端 SCUDA 有 38 次性能/profile/benchmark/gap/CQV2 类会话。该 skill 主要减少 stale endpoint、artifact mismatch、profile/benchmark evidence class 混用、cleanup 未闭环导致的返工。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/scuda-fresh-performance-runbook
cp -R scuda-fresh-performance-runbook ~/.codex/skills/
```

安装后重启 Codex。
