---
type: RawSource
title: Policy Enforcement Deletion Retention And Audit Official Sources
source_kind: web
url: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/
secondary_urls:
  - https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/
  - https://open-policy-agent.github.io/gatekeeper/website/docs/audit/
  - https://kyverno.io/docs/policy-types/cluster-policy/validate/
  - https://kyverno.io/docs/policy-reports/
captured: 2026-07-07
status: ingested
---
# Source

Official Kubernetes ValidatingAdmissionPolicy documentation: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/

Official Kubernetes auditing documentation: https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/

Official OPA Gatekeeper audit documentation: https://open-policy-agent.github.io/gatekeeper/website/docs/audit/

Official Kyverno validate-rule documentation: https://kyverno.io/docs/policy-types/cluster-policy/validate/

Official Kyverno policy reports documentation: https://kyverno.io/docs/policy-reports/

Captured as a concise source note for `ai_infra` policy-as-code enforcement, audit, and reporting evidence. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Kubernetes ValidatingAdmissionPolicy provides in-process admission validation based on CEL expressions. A ValidatingAdmissionPolicyBinding connects a policy to selected resources and controls enforcement behavior.
- ValidatingAdmissionPolicy bindings can use validation actions such as deny, warn, and audit. This is evidence for policy-as-code behavior at Kubernetes admission time, not for post-admission data deletion propagation.
- Kubernetes audit logging records API-server requests and responses according to an audit policy. Audit events can capture request metadata and stages, so API operations against namespaces, queues, policies, indexes, or cleanup jobs can be made reviewable when audit policy is configured.
- OPA Gatekeeper audit periodically evaluates existing Kubernetes resources against constraints and reports violations even if the violating object already existed before a matching admission request.
- Kyverno validate rules can check resource configuration using patterns, deny conditions, or CEL expressions; validation failure behavior can be configured for audit-style reporting or enforcement.
- Kyverno PolicyReports aggregate policy-rule results for Kubernetes resources, creating a reporting surface separate from the admission decision itself.
- These sources support Kubernetes resource-policy enforcement and audit/reporting mechanics for AI platform namespaces, accelerator labels, queue configuration, storage/index cleanup jobs, and operator-managed resources.
- These sources do not prove end-to-end RAG policy enforcement, delete propagation, retention propagation, access audit, or incident closure across source systems, search/vector indexes, caches, and evaluation datasets. That chain still needs source-specific evidence and a run or audit artifact that connects every hop.

# Use In Wiki

Use this source note for bounded claims about Kubernetes admission policy, audit logging, Gatekeeper constraint audit, Kyverno validation, and policy-reporting surfaces. Pair it with the existing source-to-vector deletion/retention and RAG access-policy notes when discussing AI data governance. Do not use it to claim production enforcement success, incident remediation, or complete source-to-vector/cache/evaluation propagation without run evidence.
