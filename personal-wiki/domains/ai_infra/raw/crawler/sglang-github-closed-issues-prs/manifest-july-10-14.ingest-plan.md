# Ingest Plan

Source path: `raw/crawler/sglang-github-closed-issues-prs/manifest-20260710-20260714.json`

## Durable claims

- The 2026-07-10 through 2026-07-14 scheduled batch contains 383 page snapshots: 65 closed issue pages and 318 closed pull-request pages. Of the pull-request pages, 317 have page-visible merged timestamps and one is closed without a merged timestamp.
- Identity reconciliation finds 375 unique item identities inside the batch, five duplicate identities inside the same date range, 21 identities already present in the June API corpus, three identities already present in earlier crawler page supplements, and 352 unique item identities not seen in the API corpus or prior page supplements.
- Existing curated SGLang supplements cover the API corpus, 2026-07-01 through 2026-07-04, 2026-07-05 through 2026-07-07, 2026-07-08, and 2026-07-09. This ingest plan only promotes non-duplicate July 10-14 page-level signals.
- Selected merged pages add bounded evidence for pipeline-parallel abort scanning, NIXL abort handling, KV-transfer fan-out metrics, DP-attention scheduler receive skipping, optimistic prefill queue termination, disaggregated-prefill grammar-error cleanup, GLM/DeepSeek FlashInfer routing stability, GLM-5.2 MTP IndexShare state transfer, HiSparse SWA-tail allocation, and UnifiedRadixCache kv-canary coverage.
- Page-visible benchmark, accuracy, and CI results remain source-owned page evidence. They are not local benchmark baselines, production SLOs, complete postmortems, product rankings, or a substitute for an API refresh with joined comments and review comments.

## Target pages

- Update `wiki/references/sglang-github-closed-issues-prs.md` with batch scope, duplicate/gap proof, and selected operational signals.
- Update `wiki/references/inference-runtime-infrastructure.md` with selected merged runtime reliability and scheduling evidence.
- Update `wiki/references/evaluation-observability-reliability-infrastructure.md` with the KV-transfer metrics semantics evidence and benchmark-caveat wording.
- Update `wiki/references/network-storage-cluster-infrastructure.md` with NIXL/Mooncake/Mori KV-transfer boundary evidence where supported by the selected pages.
- Update `wiki/references/ai-infra-coverage-map.md`, `coverage-map.json`, `loop-state.json`, and `ingest.md` so the new source-backed layer state is discoverable.

## Non-goals

- Do not merge the 383 page snapshots into the June API corpus counts.
- Do not infer issue comments, PR review comments, or linked discussion that is not present in the page snapshots.
- Do not describe the single closed-unmerged page as a shipped fix, and keep closed-unmerged/cache-boundary pages as discovery or failure-boundary evidence only.
- Do not promote benchmark tables into local benchmark baselines, MLCommons results, product rankings, production SLOs, or general performance guarantees.
- Do not modify accelerator catalog data, crawler subscriptions, source profiles, backend/frontend/dashboard code, package files, or harness code.

## Compact decision

The batch is about a few megabytes across 383 Markdown files. Keep the files readable because the manifest provides identity-level navigation and the individual pages are useful troubleshooting evidence; gzip compaction would reduce direct inspectability during the crawler reconciliation.
