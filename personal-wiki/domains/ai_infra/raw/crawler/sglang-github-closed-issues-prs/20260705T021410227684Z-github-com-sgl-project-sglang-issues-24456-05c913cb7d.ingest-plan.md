# Ingest Plan

Source path: raw/crawler/sglang-github-closed-issues-prs/20260705T021410227684Z-github-com-sgl-project-sglang-issues-24456-05c913cb7d.md

## Durable claims

- This is a page-level SGLang issue snapshot for closed issue #24456, not a joined-comment API refresh.
- The useful operational signal is a scale-dependent inference-runtime hot path: with Kimi K2 FP8 and TP=DP=EP=32, enabling `--enable-return-routed-experts` made decode traces show apparent long DeepEP dispatch/combine collectives.
- The issue diagnosis attributes those bubbles to late-entering ranks rather than slow collectives: a finishing DP rank synchronously gathers routed-experts output and serializes a tensor on the scheduler main thread, while the other DP ranks wait at the next collective.
- The raw estimates each long finished request can stall the scheduler thread for roughly 300-600 ms, which is several decode steps at the cited 30-80 ms step time. Treat this as issue-level diagnosis, not a merged fix or benchmark guarantee.

## Target pages

- Update `wiki/references/sglang-github-closed-issues-prs.md` as the corpus index and operational lead list.
- Update `wiki/references/inference-runtime-infrastructure.md` because the claim is about serving-runtime scheduler hot-path behavior and collective attribution.
- Update `wiki/references/ai-infra-coverage-map.md` only as a navigation/status summary, not as a duplicate detailed explanation.
- Update `ingest.md` after curated pages cite the raw source.

## Non-goals

- Do not create a new concept or project page; the existing SGLang and inference-runtime pages are the smallest useful homes.
- Do not merge this page-level snapshot into API corpus counts.
- Do not claim the issue proves a code fix, a general Kimi K2 performance profile, or a production postmortem.

## Compact decision

- Raw size before curation: 4509 bytes. Keep the Markdown raw source readable; gzip compaction is not useful for this small source.

## Next steps

- Apply the three curated wiki updates above.
- Rebuild the domain index and backlinks.
- Run domain and full validation.
