# hami-production-gray-readiness

HAMi/HAMI 生产灰度准备和回滚检查 skill，用于生产、灰度、Volcano、Helm、Kubernetes、镜像/tag、chart、submodule 和集群访问相关工作。

## 适用场景

- 准备或复盘 HAMI/HAMi 灰度发布。
- 检查生产 kubeconfig/context、Helm release、镜像和 chart 变更。
- 处理 Volcano/HAMi coexistence、GPU Flow 生产边界。
- 保留灰度状态给后续 PoC，或执行 rollback/restore 前后验证。

## 价值

过去一周远端 HAMI 灰度相关会话约 9 次。该 skill 的收益主要是可靠性：强制记录 active release revision、image、Volcano config、node labels/resources、lock file 和 rollback target，降低生产状态遗失和回滚误判风险。

## 安装

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/hami-production-gray-readiness
cp -R hami-production-gray-readiness ~/.codex/skills/
```

安装后重启 Codex。
