---
name: hami-production-gray-readiness
description: Use when preparing or reviewing HAMi, hami-core/libvgpu, GPU Flow, Volcano, Helm, Kubernetes, production deployment, gray rollout, rollback, production login, kubeconfig, image/tag, chart, submodule, or cluster readiness work.
---

# HAMi Production Gray Readiness

## Core Rule

Production gray rollout work is a readiness review first. Do not run production `kubectl`, `helm`, cleanup, restart, or deploy commands until the target cluster, credentials, change set, verification, rollback, and user approval are explicit.

## Workflow

1. Restore local project state: read `AGENTS.md`, `progress.md`, `tasks.json`, relevant `docs/design/*`, `git status --short --branch`, recent commits, and submodule status.
2. Identify the target: local k3s, staging, production, or unknown. If the target is production and kubeconfig/context is missing or ambiguous, stop at a checklist and ask for the exact access path.
3. Build the change inventory:
   - parent repo branch/commit and dirty files;
   - `libvgpu`/hami-core gitlink, branch, commit, and remote reachability;
   - chart/version/image tag changes;
   - RBAC, namespace, CRD, scheduler, device-plugin, webhook, and runtime changes.
4. Compare desired state with current cluster state using read-only commands only after target access is confirmed. Prefer `kubectl get/describe`, `helm list/get values`, image tags, pod status, events, and logs.
5. Prepare the rollout packet:
   - exact commands to deploy or upgrade;
   - preflight checks;
   - gray scope and blast radius;
   - health signals and timeout;
   - rollback commands;
   - cleanup commands and what they remove.
6. For GPU Flow / Volcano coexistence, verify scheduler boundary conditions: no Pod enters both Volcano and HAMi paths, no duplicated GPU resource ownership, and production-only Volcano custom fields are not copied into local assumptions without confirmation.
7. If the user asks to keep gray state for follow-on PoC work, record the active release revision, image, Volcano config, node labels/resources, lock file, and exact rollback target before ending the task.
8. For rollback or restore tasks, compare desired pre-change state with live state first, then record the restore commands, final live revision/config, health checks, and any failed/no-op attempt separately from successful evidence.
9. After any approved rollout, retained gray state, or rollback, record evidence paths, command outputs, versions, observed health, rollback readiness, and open risks in `progress.md` or the relevant plan.

## Output

Use concise Chinese:

- `当前状态`: repo, submodules, chart/image, cluster target.
- `缺口/风险`: missing credentials, dirty state, unpushed submodule, chart drift, cluster uncertainty.
- `灰度包`: preflight, deploy, verify, rollback, cleanup.
- `需要确认`: only the decisions or secrets the agent cannot infer safely.

## Common Mistakes

- Do not assume production login information from memory; confirm exact host, user, kubeconfig/context, and scope.
- Do not mutate production while answering “是否有登录信息” or “能否部署”.
- Do not ignore nested `libvgpu`/hami-core commits; a parent repo change may depend on an unpublished gitlink.
- Do not mark tasks done before the user confirms manual acceptance if project rules require it.
- Do not copy local Volcano/HAMi values into production without checking production custom chart fields and resource names.
- Do not leave retained gray state without a lock, rollback target, and progress entry that future sessions can find.
- Do not report rollback complete from a failed `kubectl apply` or stale `resourceVersion`; verify the live ConfigMap, Helm revision, node resources, and relevant Pods after restore.

## Existing Coverage

Use project scripts and docs first: `hack/deploy-helm.sh`, benchmark scripts, design docs, and `harness` state files. This skill supplies the safety gate and rollout packet structure.
